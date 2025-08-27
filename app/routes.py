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


bp = Blueprint("main", __name__)


ALLOWED_EXTENSIONS = {"pdf"}


def cm_to_pt(width_cm: float, height_cm: float) -> Tuple[float, float]:
    points_per_cm = 72.0 / 2.54
    return width_cm * points_per_cm, height_cm * points_per_cm


# Page and content box configuration (in cm)
PAGE_WIDTH_CM = 12.0
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

    for src_page in reader.pages:
        # Create target page with required final size
        target_page = writer.add_blank_page(width=PAGE_WIDTH_PT, height=PAGE_HEIGHT_PT)

        src_width = float(src_page.mediabox.width)
        src_height = float(src_page.mediabox.height)

        # Scale proportionally to fit inside the 11cm x 19cm box
        scale_factor = min(IMAGE_BOX_WIDTH_PT / src_width, IMAGE_BOX_HEIGHT_PT / src_height)
        scaled_w = src_width * scale_factor
        scaled_h = src_height * scale_factor

        # Position within the box, centered; left and bottom margins fixed at 1cm
        offset_x = MARGIN_LEFT_PT + (IMAGE_BOX_WIDTH_PT - scaled_w) / 2.0
        offset_y = MARGIN_BOTTOM_PT + (IMAGE_BOX_HEIGHT_PT - scaled_h) / 2.0

        transform = Transformation().scale(scale_factor).translate(tx=offset_x, ty=offset_y)
        target_page.merge_transformed_page(src_page, transform)

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


