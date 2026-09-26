from flask import Blueprint, render_template, request, Response
from database.database import get_connection
import csv
import io
import json
import datetime
from auth_utils import login_required


reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/admin/relatorios"
)


# =========================================================
# LABELS DE APOIO (usados no template)
# =========================================================

HISTORY_ACTION_LABELS = {
    "CRIACAO": "Criação",
    "ALTERACAO_STATUS": "Alteração manual",
    "EXCLUSAO": "Exclusão",
    "RESERVA_AUTOMATICA": "Reserva automática",
    "LIBERACAO_AUTOMATICA": "Liberação automática"
}

HISTORY_STATUS_LABELS = {
    "AVAILABLE": "Disponível",
    "BOOKED": "Ocupado",
    "BLOCKED": "Bloqueado",
    "DELETED": "Excluído"
}


# =========================================================
# CONSULTA DE HISTÓRICO (reutilizada pela tela e pelos exports)
# =========================================================

def fetch_history(
    connection,
    start_date,
    end_date,
    history_client,
    history_action,
    history_admin,
    limit=None
):

    conditions = []
    params = []

    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)

    if history_client:
        conditions.append("affected_client_name LIKE ?")
        params.append(f"%{history_client}%")

    if history_action:
        conditions.append("action = ?")
        params.append(history_action)

    if history_admin:
        conditions.append("admin_username LIKE ?")
        params.append(f"%{history_admin}%")

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    limit_clause = ""

    if limit:
        limit_clause = f"LIMIT {int(limit)}"

    return connection.execute(
        f"""
        SELECT *
        FROM availability_history
        {where_clause}
        ORDER BY created_at DESC
        {limit_clause}
        """,
        params
    ).fetchall()


@reports_bp.route("/")
@login_required
def reports():

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Filtros específicos do histórico da agenda
    history_client = request.args.get("history_client", "").strip()
    history_action = request.args.get("history_action", "").strip()
    history_admin = request.args.get("history_admin", "").strip()

    stats = {
        "total_leads": 0,
        "novos": 0,
        "contato": 0,
        "orcamento": 0,
        "negociacao": 0,
        "fechados": 0,
        "sem_interesse": 0,
        "eventos_confirmados": 0,
        "horarios_disponiveis": 0,
        "horarios_ocupados": 0,
        "horarios_bloqueados": 0,
    }

    leads = []
    slots = []
    history = []

    connection = get_connection()

    # -------------------------
    # FILTRO DE DATA (leads)
    # -------------------------

    date_conditions = []
    date_params = []

    if start_date:
        date_conditions.append("event_date >= ?")
        date_params.append(start_date)

    if end_date:
        date_conditions.append("event_date <= ?")
        date_params.append(end_date)

    where_clause = ""

    if date_conditions:
        where_clause = "WHERE " + " AND ".join(date_conditions)

    # -------------------------
    # LEADS
    # -------------------------

    leads = connection.execute(
        f"""
        SELECT *
        FROM leads
        {where_clause}
        ORDER BY event_date ASC, event_time ASC
        """,
        date_params
    ).fetchall()

    stats["total_leads"] = len(leads)

    # -------------------------
    # STATUS DOS LEADS
    # -------------------------

    for lead in leads:

        status = lead["status"]

        if status == "NOVO":
            stats["novos"] += 1

        elif status == "CONTATO REALIZADO":
            stats["contato"] += 1

        elif status == "ORÇAMENTO ENVIADO":
            stats["orcamento"] += 1

        elif status == "NEGOCIAÇÃO":
            stats["negociacao"] += 1

        elif status == "FECHADO":
            stats["fechados"] += 1

        elif status == "SEM INTERESSE":
            stats["sem_interesse"] += 1

    # -------------------------
    # AGENDA (disponibilidade atual)
    # -------------------------

    availability_conditions = []
    availability_params = []

    if start_date:
        availability_conditions.append("date >= ?")
        availability_params.append(start_date)

    if end_date:
        availability_conditions.append("date <= ?")
        availability_params.append(end_date)

    availability_where = ""

    if availability_conditions:
        availability_where = (
            "WHERE " + " AND ".join(availability_conditions)
        )

    slots = connection.execute(
        f"""
        SELECT *
        FROM availability
        {availability_where}
        ORDER BY date ASC, start_time ASC
        """,
        availability_params
    ).fetchall()

    for slot in slots:

        status = slot["status"]

        if status == "AVAILABLE":
            stats["horarios_disponiveis"] += 1

        elif status == "BOOKED":
            stats["horarios_ocupados"] += 1

        elif status == "BLOCKED":
            stats["horarios_bloqueados"] += 1

    # -------------------------
    # EVENTOS CONFIRMADOS
    # -------------------------

    stats["eventos_confirmados"] = sum(
        1 for lead in leads
        if lead["status"] == "FECHADO"
    )

    # -------------------------
    # HISTÓRICO DA AGENDA
    # -------------------------
    #
    # Usa o mesmo período (start_date/end_date) da tela,
    # aplicado sobre a coluna "date" do histórico (a data
    # do horário afetado, não a data em que a ação ocorreu).
    # Além disso, filtros próprios: cliente, ação e admin.

    history = fetch_history(
        connection,
        start_date,
        end_date,
        history_client,
        history_action,
        history_admin,
        limit=200
    )

    # Lista de admins distintos, para popular o filtro
    # como um select em vez de texto livre.

    history_admins = connection.execute("""
        SELECT DISTINCT admin_username
        FROM availability_history
        ORDER BY admin_username ASC
    """).fetchall()

    connection.close()

    return render_template(
        "admin/reports.html",

        stats=stats,
        leads=leads,
        slots=slots,

        start_date=start_date,
        end_date=end_date,

        history=history,
        history_client=history_client,
        history_action=history_action,
        history_admin=history_admin,
        history_admins=history_admins,

        history_action_labels=HISTORY_ACTION_LABELS,
        history_status_labels=HISTORY_STATUS_LABELS
    )


# =========================================================
# CSV
# =========================================================

@reports_bp.route("/exportar/csv")
@login_required
def export_csv():

    # Calculado a cada requisição (antes ficava fixo na
    # data em que o processo Flask subiu, porque estava
    # no escopo do módulo em vez de dentro da função).
    today = datetime.date.today()

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    conditions = []
    params = []

    if start_date:
        conditions.append("event_date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("event_date <= ?")
        params.append(end_date)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    connection = get_connection()

    leads = connection.execute(
        f"""
        SELECT
            id,
            name,
            email,
            phone,
            event_type,
            event_date,
            event_time,
            event_location,
            guest_count,
            status,
            details,
            notes,
            created_at
        FROM leads
        {where_clause}
        ORDER BY event_date ASC
        """,
        params
    ).fetchall()

    connection.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Nome",
        "Email",
        "Telefone",
        "Tipo de Evento",
        "Data",
        "Horário",
        "Local",
        "Convidados",
        "Status",
        "Detalhes",
        "Observações",
        "Criado em"
    ])

    for lead in leads:

        writer.writerow([
            lead["id"],
            lead["name"],
            lead["email"],
            lead["phone"],
            lead["event_type"],
            lead["event_date"],
            lead["event_time"],
            lead["event_location"],
            lead["guest_count"],
            lead["status"],
            lead["details"],
            lead["notes"],
            lead["created_at"]
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        f"attachment; filename=relatorio_{today}.csv"
    )

    return response


# =========================================================
# JSON
# =========================================================

@reports_bp.route("/exportar/json")
@login_required
def export_json():

    today = datetime.date.today()

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    conditions = []
    params = []

    if start_date:
        conditions.append("event_date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("event_date <= ?")
        params.append(end_date)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    connection = get_connection()

    leads = connection.execute(
        f"""
        SELECT *
        FROM leads
        {where_clause}
        ORDER BY event_date ASC
        """,
        params
    ).fetchall()

    connection.close()

    data = [dict(lead) for lead in leads]

    response = Response(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        mimetype="application/json"
    )

    response.headers["Content-Disposition"] = (
        f"attachment; filename=relatorio_{today}.json"
    )

    return response


# =========================================================
# HISTÓRICO — CSV
# =========================================================

@reports_bp.route("/exportar/csv/historico")
@login_required
def export_history_csv():

    today = datetime.date.today()

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    history_client = request.args.get("history_client", "").strip()
    history_action = request.args.get("history_action", "").strip()
    history_admin = request.args.get("history_admin", "").strip()

    connection = get_connection()

    history = fetch_history(
        connection,
        start_date,
        end_date,
        history_client,
        history_action,
        history_admin
    )

    connection.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Registrado em",
        "Data do horário",
        "Início",
        "Fim",
        "Ação",
        "Status anterior",
        "Status novo",
        "Lead ID",
        "Cliente",
        "Tipo de evento",
        "Administrador",
        "Descrição"
    ])

    for entry in history:

        writer.writerow([
            entry["id"],
            entry["created_at"],
            entry["date"],
            entry["start_time"],
            entry["end_time"],
            HISTORY_ACTION_LABELS.get(
                entry["action"],
                entry["action"]
            ),
            HISTORY_STATUS_LABELS.get(
                entry["old_status"],
                entry["old_status"]
            ),
            HISTORY_STATUS_LABELS.get(
                entry["new_status"],
                entry["new_status"]
            ),
            entry["affected_lead_id"],
            entry["affected_client_name"],
            entry["affected_event_type"],
            entry["admin_username"],
            entry["description"]
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        f"attachment; filename=historico_agenda_{today}.csv"
    )

    return response


# =========================================================
# HISTÓRICO — JSON
# =========================================================

@reports_bp.route("/exportar/json/historico")
@login_required
def export_history_json():

    today = datetime.date.today()

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    history_client = request.args.get("history_client", "").strip()
    history_action = request.args.get("history_action", "").strip()
    history_admin = request.args.get("history_admin", "").strip()

    connection = get_connection()

    history = fetch_history(
        connection,
        start_date,
        end_date,
        history_client,
        history_action,
        history_admin
    )

    connection.close()

    data = [dict(entry) for entry in history]

    response = Response(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        mimetype="application/json"
    )

    response.headers["Content-Disposition"] = (
        f"attachment; filename=historico_agenda_{today}.json"
    )

    return response