from flask import Blueprint, render_template, request, Response
from database.database import get_connection
import csv
import io
import json
from auth_utils import login_required
import datetime

# IMPORTAR A DATA ATUAL PARA O NOME DO ARQUIVO CSV
date = datetime.date.today()

reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/admin/relatorios"
)

@reports_bp.route("/")
@login_required
def reports():

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

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

    connection = get_connection()

    # -------------------------
    # FILTRO DE DATA
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
    # AGENDA
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

    connection.close()

    return render_template(
        "admin/reports.html",
        stats=stats,
        leads=leads,
        slots=slots,
        start_date=start_date,
        end_date=end_date
    )


# =========================================================
# CSV
# =========================================================

@reports_bp.route("/exportar/csv")
@login_required
def export_csv():

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
        f"attachment; filename=relatorio_{date}.csv"
    )

    return response


# =========================================================
# JSON
# =========================================================

@reports_bp.route("/exportar/json")
@login_required
def export_json():

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
        f"attachment; filename=relatorio_{date}.json"
    )

    return response