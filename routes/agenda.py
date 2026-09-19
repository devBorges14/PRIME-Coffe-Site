from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from database.database import get_connection
from auth_utils import login_required

agenda_bp = Blueprint("agenda", __name__, url_prefix="/admin/agenda")

STATUS_LABELS = {
    "AVAILABLE": "DISPONÍVEL",
    "BLOCKED": "BLOQUEADO",
    "BOOKED": "OCUPADO",
    "DELETED": "EXCLUÍDO"
}

ALLOWED_STATUSES = {"AVAILABLE", "BLOCKED", "BOOKED"}


def get_affected_leads(connection, slot_id):
    """
    Retorna contratos/clientes FECHADOS vinculados ao horário.
    """
    return connection.execute("""
        SELECT
            id,
            name,
            event_type,
            event_date,
            event_time,
            status
        FROM leads
        WHERE availability_id = ?
          AND status = 'FECHADO'
        ORDER BY id ASC
    """, (slot_id,)).fetchall()


def register_history(
    connection,
    slot,
    action,
    old_status,
    new_status,
    affected_lead=None,
    description=""
):
    """
    Registra uma alteração da agenda no histórico.
    """

    connection.execute("""
        INSERT INTO availability_history (
            availability_id,
            date,
            start_time,
            end_time,
            action,
            old_status,
            new_status,
            affected_lead_id,
            affected_client_name,
            affected_event_type,
            admin_username,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        slot["id"],
        slot["date"],
        slot["start_time"],
        slot["end_time"],
        action,
        old_status,
        new_status,
        affected_lead["id"] if affected_lead else None,
        affected_lead["name"] if affected_lead else None,
        affected_lead["event_type"] if affected_lead else None,
        session.get("username", "desconhecido"),
        description
    ))


@agenda_bp.route("/")
@login_required
def agenda():

    connection = get_connection()

    slots = connection.execute("""
        SELECT *
        FROM availability
        WHERE status != 'DELETED'
        ORDER BY date ASC, start_time ASC
    """).fetchall()

    connection.close()

    return render_template(
        "admin/agenda.html",
        slots=slots,
        status_labels=STATUS_LABELS
    )


@agenda_bp.route("/add", methods=["POST"])
@login_required
def add_slot():

    date = request.form.get("date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    status = request.form.get("status", "AVAILABLE").strip()
    notes = request.form.get("notes", "").strip()

    if not date or not start_time or not end_time:
        return redirect(url_for("agenda.agenda"))

    if status not in ALLOWED_STATUSES:
        status = "AVAILABLE"

    if end_time <= start_time:
        return redirect(url_for("agenda.agenda"))

    connection = get_connection()

    try:

        # Impede horários sobrepostos.
        conflict = connection.execute("""
            SELECT id
            FROM availability
            WHERE status != 'DELETED'
              AND date = ?
              AND start_time < ?
              AND end_time > ?
        """, (date, end_time, start_time)).fetchone()

        if conflict:
            connection.close()
            return redirect(url_for("agenda.agenda"))

        cursor = connection.execute("""
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

        slot_id = cursor.lastrowid

        # Busca o horário recém-criado para registrar no histórico.
        slot = connection.execute("""
            SELECT *
            FROM availability
            WHERE id = ?
        """, (slot_id,)).fetchone()

        register_history(
            connection,
            slot,
            "CRIACAO",
            None,
            status,
            description="Novo horário criado na agenda."
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("agenda.agenda"))


@agenda_bp.route("/<int:slot_id>/impact", methods=["GET"])
@login_required
def slot_impact(slot_id):
    connection = get_connection()

    slot = connection.execute("""
        SELECT *
        FROM availability
        WHERE id = ?
    """, (slot_id,)).fetchone()

    if not slot:
        connection.close()

        return jsonify({
            "error": "Horário não encontrado."
        }), 404

    affected_leads = connection.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            event_type,
            event_date,
            event_time,
            status
        FROM leads
        WHERE availability_id = ?
          AND status = 'FECHADO'
        ORDER BY id ASC
    """, (slot_id,)).fetchall()

    connection.close()

    return jsonify({
        "slot": {
            "id": slot["id"],
            "date": slot["date"],
            "start_time": slot["start_time"],
            "end_time": slot["end_time"],
            "status": slot["status"]
        },
        "affected_leads": [
            {
                "id": lead["id"],
                "name": lead["name"],
                "email": lead["email"],
                "phone": lead["phone"],
                "event_type": lead["event_type"],
                "event_date": lead["event_date"],
                "event_time": lead["event_time"],
                "status": lead["status"]
            }
            for lead in affected_leads
        ]
    })


@agenda_bp.route("/<int:slot_id>/status", methods=["POST"])
@login_required
def update_status(slot_id):

    new_status = request.form.get("status", "").strip()
    confirm_impact = request.form.get("confirm_impact") == "1"

    if new_status not in ALLOWED_STATUSES:
        return redirect(url_for("agenda.agenda"))

    connection = get_connection()

    try:

        slot = connection.execute("""
            SELECT *
            FROM availability
            WHERE id = ?
        """, (slot_id,)).fetchone()

        if not slot:
            return redirect(url_for("agenda.agenda"))

        old_status = slot["status"]

        # Não faz nada se o status já for o mesmo.
        if old_status == new_status:
            return redirect(url_for("agenda.agenda"))

        affected_leads = get_affected_leads(
            connection,
            slot_id
        )

        # Se existe contrato FECHADO e o administrador
        # ainda não confirmou o impacto, não altera nada.
        if affected_leads and not confirm_impact:

            return jsonify({
                "requires_confirmation": True,
                "affected_leads": [
                    {
                        "id": lead["id"],
                        "name": lead["name"],
                        "event_type": lead["event_type"],
                        "event_date": lead["event_date"],
                        "event_time": lead["event_time"]
                    }
                    for lead in affected_leads
                ]
            }), 409

        # Altera o status.
        connection.execute("""
            UPDATE availability
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            new_status,
            slot_id
        ))

        # Registra no histórico.
        if affected_leads:

            for lead in affected_leads:

                register_history(
                    connection,
                    slot,
                    "ALTERACAO_STATUS",
                    old_status,
                    new_status,
                    affected_lead=lead,
                    description=(
                        "Horário alterado manualmente pelo administrador "
                        "mesmo possuindo uma reserva/contrato fechado."
                    )
                )

        else:

            register_history(
                connection,
                slot,
                "ALTERACAO_STATUS",
                old_status,
                new_status,
                description="Status do horário alterado pelo administrador."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("agenda.agenda"))


@agenda_bp.route("/<int:slot_id>/delete", methods=["POST"])
@login_required
def delete_slot(slot_id):

    confirm_impact = request.form.get("confirm_impact") == "1"

    connection = get_connection()

    try:

        slot = connection.execute("""
            SELECT *
            FROM availability
            WHERE id = ?
        """, (slot_id,)).fetchone()

        if not slot:
            return redirect(url_for("agenda.agenda"))

        old_status = slot["status"]

        affected_leads = get_affected_leads(
            connection,
            slot_id
        )

        # Impede exclusão sem confirmação.
        if affected_leads and not confirm_impact:

            return jsonify({
                "requires_confirmation": True,
                "affected_leads": [
                    {
                        "id": lead["id"],
                        "name": lead["name"],
                        "event_type": lead["event_type"],
                        "event_date": lead["event_date"],
                        "event_time": lead["event_time"]
                    }
                    for lead in affected_leads
                ]
            }), 409

        # EXCLUSÃO LÓGICA.
        # Não usamos DELETE porque os leads continuam
        # apontando para este availability_id.
        connection.execute("""
            UPDATE availability
            SET status = 'DELETED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (slot_id,))

        if affected_leads:

            for lead in affected_leads:

                register_history(
                    connection,
                    slot,
                    "EXCLUSAO",
                    old_status,
                    "DELETED",
                    affected_lead=lead,
                    description=(
                        "Disponibilidade excluída manualmente pelo "
                        "administrador. O contrato foi preservado."
                    )
                )

        else:

            register_history(
                connection,
                slot,
                "EXCLUSAO",
                old_status,
                "DELETED",
                description="Disponibilidade excluída pelo administrador."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
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


@agenda_bp.route("/public/disponibilidade", endpoint="public_availability")
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