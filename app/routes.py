from __future__ import annotations

import os
import uuid
from typing import Tuple

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject


bp = Blueprint("main", __name__)


ALLOWED_EXTENSIONS = {"pdf"}


def cm_to_pt(width_cm: float, height_cm: float) -> Tuple[float, float]:
    points_per_cm = 72.0 / 2.54
    return width_cm * points_per_cm, height_cm * points_per_cm


# Target page and content box configuration (in cm)
# Final page must be A4 paysage 29.7cm × 21cm with a content box 11cm × 19cm
# and margins: 1cm top, 1cm bottom, 1cm left
PAGE_WIDTH_CM = 29.7
PAGE_HEIGHT_CM = 21.0
IMAGE_BOX_WIDTH_CM = 11.0
IMAGE_BOX_HEIGHT_CM = 19.0
MARGIN_LEFT_CM = 1.0
MARGIN_BOTTOM_CM = 1.0
MARGIN_TOP_CM = 1.0

PAGE_WIDTH_PT, PAGE_HEIGHT_PT = cm_to_pt(PAGE_WIDTH_CM, PAGE_HEIGHT_CM)
IMAGE_BOX_WIDTH_PT, IMAGE_BOX_HEIGHT_PT = cm_to_pt(IMAGE_BOX_WIDTH_CM, IMAGE_BOX_HEIGHT_CM)
MARGIN_LEFT_PT, MARGIN_BOTTOM_PT = cm_to_pt(MARGIN_LEFT_CM, MARGIN_BOTTOM_CM)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def transform_pdf(input_path: str, output_path: str) -> None:
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Source crop region on an A4 portrait page (21cm × 29.7cm):
    # from top-left: 1cm right and 2cm down, size 11cm × 15cm
    points_per_cm = 72.0 / 2.54
    src_left_pt = 1.0 * points_per_cm
    src_top_pt = 2.0 * points_per_cm
    crop_w_pt = 11.0 * points_per_cm
    crop_h_pt = 15.0 * points_per_cm

    for original_page in reader.pages:
        page_h = float(original_page.mediabox.height)

        # Convert top-left based rectangle to PDF bottom-left coordinates
        llx = src_left_pt
        lly = page_h - (src_top_pt + crop_h_pt)
        urx = llx + crop_w_pt
        ury = page_h - src_top_pt

        crop_rect = RectangleObject((llx, lly, urx, ury))

        # Crop to the specified region (compat mode for older pypdf without within_box)
        try:
            cropped_page = original_page.within_box(crop_rect)  # pypdf >= 4
        except AttributeError:
            # Fallback: adjust mediabox/cropbox directly on a working copy
            cropped_page = original_page
            try:
                cropped_page.cropbox = crop_rect  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                # Ensure the visible page is exactly the crop rect
                cropped_page.mediabox = crop_rect
            except Exception:
                cropped_page.mediabox.lower_left = (llx, lly)
                cropped_page.mediabox.upper_right = (urx, ury)

        target_page = writer.add_blank_page(width=PAGE_WIDTH_PT, height=PAGE_HEIGHT_PT)

        # Compute proportional scale based on cropped size
        s = min(IMAGE_BOX_WIDTH_PT / crop_w_pt, IMAGE_BOX_HEIGHT_PT / crop_h_pt)
        scaled_w = crop_w_pt * s
        scaled_h = crop_h_pt * s

        # Center within the 11×19 cm box with fixed margins
        offset_x = MARGIN_LEFT_PT + (IMAGE_BOX_WIDTH_PT - scaled_w) / 2.0
        offset_y = MARGIN_BOTTOM_PT + (IMAGE_BOX_HEIGHT_PT - scaled_h) / 2.0

        # Normalize cropped content origin to (0, 0) before scaling and placing
        try:
            source_llx = float(cropped_page.mediabox.lower_left[0])  # type: ignore[index]
            source_lly = float(cropped_page.mediabox.lower_left[1])  # type: ignore[index]
        except Exception:
            # Fallback to computed crop lower-left if mediabox access fails
            source_llx = llx
            source_lly = lly

        transform = (
            Transformation()
            .translate(tx=-source_llx, ty=-source_lly)
            .scale(s)
            .translate(tx=offset_x, ty=offset_y)
        )
        target_page.merge_transformed_page(cropped_page, transform)

    with open(output_path, "wb") as f_out:
        writer.write(f_out)


@bp.route("/", methods=["GET", "POST"])
def upload_and_transform():
    if request.method == "POST":
        if "file" not in request.files:
            flash("Aucun fichier fourni.")
            return redirect(url_for("main.upload_and_transform"))

        file = request.files["file"]

        if file.filename == "":
            flash("Aucun fichier sélectionné.")
            return redirect(url_for("main.upload_and_transform"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_id = uuid.uuid4().hex
            base, _ = os.path.splitext(filename)
            saved_name = f"{base}_{unique_id}.pdf"
            upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_name)
            file.save(upload_path)

            output_name = f"{base}_{unique_id}_transformed.pdf"
            output_path = os.path.join(current_app.config["OUTPUT_FOLDER"], output_name)

            try:
                transform_pdf(upload_path, output_path)
            except Exception as e:
                flash(f"Erreur lors de la transformation: {e}")
                return redirect(url_for("main.upload_and_transform"))

            return redirect(url_for("main.result", filename=output_name))

        flash("Format de fichier non supporté. Veuillez fournir un PDF.")
        return redirect(url_for("main.upload_and_transform"))

    return render_template("upload.html")


@bp.route("/result/<path:filename>")
def result(filename: str):
    return render_template("result.html", filename=filename)


@bp.route("/download/<path:filename>")
def download_file(filename: str):
    return send_from_directory(
        directory=current_app.config["OUTPUT_FOLDER"],
        path=filename,
        as_attachment=True,
    )


