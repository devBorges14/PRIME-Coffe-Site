from flask import Blueprint, request, jsonify

from database.database import get_connection
from database.history import register_lead_history


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

    # =====================================================
    # VALIDAÇÃO
    # =====================================================

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

    if guest_count:

        try:
            guest_count = int(guest_count)

            if guest_count <= 0:
                errors.append(
                    "Número de convidados inválido."
                )

        except ValueError:
            errors.append(
                "Número de convidados inválido."
            )

    else:
        guest_count = None

    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400

    # =====================================================
    # BANCO
    # =====================================================

    connection = get_connection()

    try:

        # =================================================
        # LOCALIZA O HORÁRIO DISPONÍVEL
        # =================================================
        #
        # Isso é só uma VALIDAÇÃO — confirma que o horário
        # escolhido existe e está disponível no momento do
        # envio. O envio do formulário NÃO reserva o horário.
        # A reserva (BOOKED) só acontece quando o admin marca
        # o lead como FECHADO (ver routes/admin.py).
        #
        # Por isso é normal e esperado que mais de um lead
        # aponte para o mesmo availability_id enquanto nenhum
        # deles tiver sido fechado — o admin.py já trata esse
        # cenário na hora de fechar (ver checagem de conflito).

        slot = connection.execute("""
            SELECT *
            FROM availability
            WHERE date = ?
            AND start_time = ?
            AND status = 'AVAILABLE'
            LIMIT 1
        """, (
            event_date,
            event_time
        )).fetchone()

        # =================================================
        # HORÁRIO NÃO DISPONÍVEL
        # =================================================

        if not slot:

            return jsonify({
                "success": False,
                "errors": [
                    "O horário selecionado não está mais disponível."
                ]
            }), 409

        # =================================================
        # CRIA O LEAD
        # =================================================

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
                status,
                availability_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NOVO', ?)
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

        lead_id = cursor.lastrowid

        # =================================================
        # PRIMEIRA ENTRADA DA TIMELINE DO LEAD
        # =================================================
        #
        # old_status = None porque não havia status anterior;
        # changed_by = None porque veio do formulário público.

        register_lead_history(
            connection=connection,
            lead_id=lead_id,
            old_status=None,
            new_status="NOVO",
            changed_by=None,
            description=(
                "Lead criado a partir do formulário público de orçamento."
            )
        )

        # =================================================
        # NÃO OCUPA O HORÁRIO AQUI
        # =================================================
        #
        # (Removido de propósito.) O horário só vira BOOKED
        # quando o admin muda o status do lead para FECHADO,
        # em routes/admin.py. Enviar o formulário não reserva
        # nada — só registra a solicitação.

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Solicitação enviada com sucesso!",
            "lead_id": lead_id
        }), 201

    except Exception:

        connection.rollback()

        return jsonify({
            "success": False,
            "errors": [
                "Ocorreu um erro ao registrar a solicitação."
            ]
        }), 500

    finally:

        connection.close()