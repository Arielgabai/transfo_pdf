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


TARGET_WIDTH_PT, TARGET_HEIGHT_PT = cm_to_pt(20.0, 10.0)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def transform_pdf(input_path: str, output_path: str) -> None:
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for src_page in reader.pages:
        target_page = writer.add_blank_page(width=TARGET_WIDTH_PT, height=TARGET_HEIGHT_PT)

        src_width = float(src_page.mediabox.width)
        src_height = float(src_page.mediabox.height)

        # Compute proportional scale to fit within 20cm x 10cm
        scale_factor = min(TARGET_WIDTH_PT / src_width, TARGET_HEIGHT_PT / src_height)
        scaled_w = src_width * scale_factor
        scaled_h = src_height * scale_factor

        # Center the content
        offset_x = (TARGET_WIDTH_PT - scaled_w) / 2.0
        offset_y = (TARGET_HEIGHT_PT - scaled_h) / 2.0

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


