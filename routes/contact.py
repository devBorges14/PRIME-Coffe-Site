from flask import Blueprint, request, jsonify
from database.database import get_connection

contact_bp = Blueprint("contact", __name__)


@contact_bp.route("/contato", methods=["POST"])
def create_contact():

    name = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("telefone", "").strip()
    event_type = request.form.get("tipo_evento", "").strip()

    event_date = request.form.get("data_evento", "").strip()
    event_time = request.form.get("horario_evento", "").strip()

    event_location = request.form.get("local_evento", "").strip()
    guest_count = request.form.get("convidados", "").strip()
    details = request.form.get("detalhes", "").strip()

    errors = []

    # =========================
    # VALIDAÇÕES BÁSICAS
    # =========================

    if not name:
        errors.append("Nome é obrigatório.")

    if not email:
        errors.append("E-mail é obrigatório.")
    elif "@" not in email:
        errors.append("E-mail inválido.")

    if not phone:
        errors.append("Telefone é obrigatório.")

    if not event_type:
        errors.append("Tipo de evento é obrigatório.")

    if not event_date:
        errors.append("Data do evento é obrigatória.")

    if not event_time:
        errors.append("Horário do evento é obrigatório.")

    # =========================
    # CONVIDADOS
    # =========================

    if guest_count:

        try:
            guest_count = int(guest_count)

            if guest_count <= 0:
                errors.append("Número de convidados inválido.")

        except ValueError:
            errors.append("Número de convidados inválido.")

    else:
        guest_count = None

    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400

    # =========================
    # VERIFICAR AGENDA
    # =========================

    connection = get_connection()

    slot = connection.execute("""
        SELECT *
        FROM availability
        WHERE date = ?
        AND start_time <= ?
        AND end_time > ?
        AND status = 'AVAILABLE'
        ORDER BY start_time ASC
        LIMIT 1
    """, (
        event_date,
        event_time,
        event_time
    )).fetchone()

    if not slot:

        connection.close()

        return jsonify({
            "success": False,
            "errors": [
                "O horário selecionado não está disponível."
            ]
        }), 409

    # =========================
    # CRIAR LEAD
    # =========================

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO leads (
            name,
            email,
            phone,
            event_type,
            event_date,
            event_time,
            event_location,
            guest_count,
            details,
            availability_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        phone,
        event_type,
        event_date,
        event_time,
        event_location,
        guest_count,
        details,
        slot["id"]
    ))

    connection.commit()

    lead_id = cursor.lastrowid

    connection.close()

    return jsonify({
        "success": True,
        "message": "Solicitação enviada com sucesso!",
        "lead_id": lead_id
    }), 201