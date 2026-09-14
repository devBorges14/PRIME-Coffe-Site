from flask import Blueprint, render_template, request, jsonify
from database.database import get_connection

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


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