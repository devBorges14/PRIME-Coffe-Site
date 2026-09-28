import re

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app
)

from database.database import get_connection
from database.history import register_lead_history
from extensions import limiter


contact_bp = Blueprint("contact", __name__)


# =====================================================
# LIMITES E FORMATOS ACEITOS
# =====================================================

MAX_LENGTHS = {
    "nome": 120,
    "email": 254,
    "telefone": 30,
    "tipo_evento": 80,
    "local_evento": 200,
    "detalhes": 2000,
}

MAX_GUESTS = 100000

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

# Telefone: dígitos, espaço, +, -, ( ) — entre 10 e 15 dígitos
PHONE_ALLOWED = re.compile(
    r"^[\d\s+\-()]+$"
)


@contact_bp.route("/contato", methods=["POST"])
@limiter.limit("5 per minute; 20 per hour")
def create_contact():

    # -------------------------------------------------
    # CAMPO-ARMADILHA ANTI-SPAM (honeypot)
    # -------------------------------------------------
    #
    # O formulário tem um campo "website" escondido do
    # usuário humano. Robôs costumam preencher todos os
    # campos; se veio preenchido, descartamos em silêncio
    # e respondemos "sucesso" para o robô não tentar de novo.

    if request.form.get("website", "").strip():

        current_app.logger.warning(
            "Honeypot acionado em /contato: ip=%s",
            request.remote_addr
        )

        return jsonify({
            "success": True,
            "message": "Solicitação enviada com sucesso!"
        }), 201

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
    elif len(name) > MAX_LENGTHS["nome"]:
        errors.append("Nome muito longo.")

    if not email:
        errors.append("E-mail é obrigatório.")
    elif len(email) > MAX_LENGTHS["email"]:
        errors.append("E-mail muito longo.")
    elif not EMAIL_PATTERN.match(email):
        errors.append("E-mail inválido.")

    if not phone:
        errors.append("Telefone é obrigatório.")
    elif len(phone) > MAX_LENGTHS["telefone"]:
        errors.append("Telefone inválido.")
    else:

        digits = re.sub(r"\D", "", phone)

        if (
            not PHONE_ALLOWED.match(phone)
            or not 10 <= len(digits) <= 15
        ):
            errors.append("Telefone inválido.")

    if not event_type:
        errors.append("Tipo de evento é obrigatório.")
    elif len(event_type) > MAX_LENGTHS["tipo_evento"]:
        errors.append("Tipo de evento inválido.")

    if not event_date:
        errors.append("Data do evento é obrigatória.")

    if not event_time:
        errors.append("Horário do evento é obrigatório.")

    if len(event_location) > MAX_LENGTHS["local_evento"]:
        errors.append("Local do evento muito longo.")

    if len(details) > MAX_LENGTHS["detalhes"]:
        errors.append(
            "Detalhes muito longos "
            f"(máximo {MAX_LENGTHS['detalhes']} caracteres)."
        )

    if guest_count:

        try:
            guest_count = int(guest_count)

            if guest_count <= 0 or guest_count > MAX_GUESTS:
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

        current_app.logger.info(
            "Novo lead: id=%s ip=%s",
            lead_id,
            request.remote_addr
        )

        return jsonify({
            "success": True,
            "message": "Solicitação enviada com sucesso!",
            "lead_id": lead_id
        }), 201

    except Exception:

        connection.rollback()

        current_app.logger.exception(
            "Erro ao registrar lead"
        )

        return jsonify({
            "success": False,
            "errors": [
                "Ocorreu um erro ao registrar a solicitação."
            ]
        }), 500

    finally:

        connection.close()
