from pathlib import Path

from flask import Blueprint, current_app, render_template, request, jsonify
from database.database import get_connection

main = Blueprint("main", __name__)


# =====================================================
# GALERIA E VÍDEO
# =====================================================
#
# Fotos: qualquer imagem em static/img/momentos/ entra no
# carrossel, em ordem alfabética (dica: 01-evento.jpg,
# 02-feira.jpg...). Pasta vazia -> fotos de exemplo.
#
# Vídeo: static/video/apresentacao.mp4 (capa opcional:
# static/video/capa.jpg).

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

EXAMPLE_PHOTOS = [
    "https://images.unsplash.com/photo-" + photo_id + "?auto=format&fit=crop&w=1600&q=80"
    for photo_id in (
        "1505236858219-8359eb29e329",
        "1492684223066-81342ee5ff30",
        "1511578314322-379afb476865",
        "1507504031003-b417219a0fde",
        "1519167758481-83f550bb49b3",
        "1540575467063-178a50c2df87",
    )
]


def gallery_photos():

    folder = Path(current_app.static_folder) / "img" / "momentos"

    if folder.is_dir():
        files = sorted(
            f.name for f in folder.iterdir()
            if f.suffix.lower() in PHOTO_EXTENSIONS
        )
        if files:
            return [f"/static/img/momentos/{name}" for name in files]

    return EXAMPLE_PHOTOS


def presentation_video():

    folder = Path(current_app.static_folder) / "video"

    if not (folder / "apresentacao.mp4").is_file():
        return None

    has_cover = (folder / "capa.jpg").is_file()

    return {
        "src": "/static/video/apresentacao.mp4",
        "poster": "/static/video/capa.jpg" if has_cover else None,
    }


@main.route("/")
def index():
    return render_template(
        "index.html",
        fotos_momentos=gallery_photos(),
        video=presentation_video(),
        # aviso "coloque o vídeo aqui" só no seu computador
        mostrar_aviso_video=request.host.split(":")[0] in ("localhost", "127.0.0.1"),
    )


@main.route("/disponibilidade")
def disponibilidade():

    date = request.args.get("date", "").strip()

    if not date:
        return jsonify([])

    connection = get_connection()

    slots = connection.execute("""
        SELECT
            id,
            start_time,
            end_time
        FROM availability
        WHERE date = ?
        AND status = 'AVAILABLE'
        ORDER BY start_time ASC
    """, (date,)).fetchall()

    connection.close()

    return jsonify([
        {
            "id": slot["id"],
            "start_time": slot["start_time"],
            "end_time": slot["end_time"]
        }
        for slot in slots
    ])