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
    event_location = request.form.get("local_evento", "").strip()
    guest_count = request.form.get("convidados", "").strip()
    details = request.form.get("detalhes", "").strip()

    errors = []

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

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO leads (
            name,
            email,
            phone,
            event_type,
            event_date,
            event_location,
            guest_count,
            details
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        phone,
        event_type,
        event_date,
        event_location,
        guest_count,
        details
    ))

    connection.commit()

    lead_id = cursor.lastrowid

    connection.close()

    return jsonify({
        "success": True,
        "message": "Solicitação enviada com sucesso!",
        "lead_id": lead_id
    }), 201