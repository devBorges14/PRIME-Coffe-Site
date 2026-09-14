from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from database.database import get_connection


agenda_bp = Blueprint(
    "agenda",
    __name__,
    url_prefix="/admin/agenda"
)


STATUS_LABELS = {
    "AVAILABLE": "DISPONÍVEL",
    "BLOCKED": "BLOQUEADO",
    "BOOKED": "OCUPADO"
}


@agenda_bp.route("/")
def agenda():
    connection = get_connection()

    slots = connection.execute("""
        SELECT *
        FROM availability
        ORDER BY date ASC, start_time ASC
    """).fetchall()

    connection.close()

    return render_template(
        "admin/agenda.html",
        slots=slots,
        status_labels=STATUS_LABELS
    )


@agenda_bp.route("/add", methods=["POST"])
def add_slot():

    date = request.form.get("date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    status = request.form.get("status", "AVAILABLE").strip()
    notes = request.form.get("notes", "").strip()

    allowed_statuses = {
        "AVAILABLE",
        "BLOCKED",
        "BOOKED"
    }

    if not date or not start_time or not end_time:
        return redirect(url_for("agenda.agenda"))

    if status not in allowed_statuses:
        status = "AVAILABLE"

    # Evita horário final menor ou igual ao inicial
    if end_time <= start_time:
        return redirect(url_for("agenda.agenda"))

    connection = get_connection()

    # Verifica conflito de horário no mesmo dia
    conflict = connection.execute("""
        SELECT id
        FROM availability
        WHERE date = ?
        AND start_time < ?
        AND end_time > ?
    """, (
        date,
        end_time,
        start_time
    )).fetchone()

    if conflict:
        connection.close()
        return redirect(url_for("agenda.agenda"))

    connection.execute("""
        INSERT INTO availability (
            date,
            start_time,
            end_time,
            status,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        date,
        start_time,
        end_time,
        status,
        notes
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("agenda.agenda"))


@agenda_bp.route("/<int:slot_id>/status", methods=["POST"])
def update_status(slot_id):

    status = request.form.get("status", "").strip()

    allowed_statuses = {
        "AVAILABLE",
        "BLOCKED",
        "BOOKED"
    }

    if status not in allowed_statuses:
        return redirect(url_for("agenda.agenda"))

    connection = get_connection()

    connection.execute("""
        UPDATE availability
        SET status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        status,
        slot_id
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("agenda.agenda"))


@agenda_bp.route("/<int:slot_id>/delete", methods=["POST"])
def delete_slot(slot_id):

    connection = get_connection()

    connection.execute("""
        DELETE FROM availability
        WHERE id = ?
    """, (slot_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("agenda.agenda"))
@agenda_bp.route("/disponibilidade")
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
@agenda_bp.route(
    "/public/disponibilidade",
    endpoint="public_availability"
)
def public_availability():

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