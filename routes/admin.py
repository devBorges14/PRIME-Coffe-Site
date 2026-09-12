from flask import Blueprint, render_template, request, redirect, url_for
from database.database import get_connection

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

# =====================================================
# DASHBOARD
# =====================================================

@admin_bp.route("/")
def dashboard():

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    event_filter = request.args.get("event_type", "").strip()
    date_filter = request.args.get("event_date", "").strip()

    connection = get_connection()
    cursor = connection.cursor()

    # =====================================================
    # ESTATÍSTICAS
    # =====================================================

    cursor.execute("""
        SELECT
            COUNT(*) AS total,

            SUM(
                CASE
                    WHEN status = 'NOVO'
                    THEN 1 ELSE 0
                END
            ) AS novos,

            SUM(
                CASE
                    WHEN status = 'CONTATO REALIZADO'
                    THEN 1 ELSE 0
                END
            ) AS contato,

            SUM(
                CASE
                    WHEN status = 'ORÇAMENTO ENVIADO'
                    THEN 1 ELSE 0
                END
            ) AS orcamento,

            SUM(
                CASE
                    WHEN status = 'NEGOCIAÇÃO'
                    THEN 1 ELSE 0
                END
            ) AS negociacao,

            SUM(
                CASE
                    WHEN status = 'FECHADO'
                    THEN 1 ELSE 0
                END
            ) AS fechados

        FROM leads
    """)

    stats = cursor.fetchone()

    # =====================================================
    # CONSULTA DOS LEADS
    # =====================================================

    query = """
        SELECT *
        FROM leads
        WHERE 1 = 1
    """

    params = []

    # PESQUISA
    if search:
        query += """
            AND (
                name LIKE ?
                OR email LIKE ?
                OR phone LIKE ?
            )
        """
        search_value = f"%{search}%"
        params.extend([search_value, search_value, search_value])

    # FILTRO DE STATUS
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    # FILTRO DE TIPO DE EVENTO
    if event_filter:
        query += " AND event_type = ?"
        params.append(event_filter)

    # FILTRO DE DATA
    if date_filter:
        query += " AND event_date = ?"
        params.append(date_filter)

    # ORDENAÇÃO
    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    leads = cursor.fetchall()
    connection.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        leads=leads,
        search=search,
        status_filter=status_filter,
        event_filter=event_filter,
        date_filter=date_filter
    )


# =====================================================
# DETALHES DO LEAD
# =====================================================

@admin_bp.route("/lead/<int:lead_id>")
def lead_detail(lead_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    lead = cursor.fetchone()
    connection.close()

    if not lead:
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/lead.html", lead=lead)


# =====================================================
# ATUALIZAR STATUS
# =====================================================

@admin_bp.route("/lead/<int:lead_id>/status", methods=["POST"])
def update_status(lead_id):
    new_status = request.form.get("status")

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (new_status, lead_id))
    connection.commit()
    connection.close()

    return redirect(url_for("admin.lead_detail", lead_id=lead_id))


# =====================================================
# ATUALIZAR OBSERVAÇÕES
# =====================================================

@admin_bp.route("/lead/<int:lead_id>/notes", methods=["POST"])
def update_notes(lead_id):
    notes = request.form.get("notes")

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE leads SET notes = ? WHERE id = ?", (notes, lead_id))
    connection.commit()
    connection.close()

    return redirect(url_for("admin.lead_detail", lead_id=lead_id))


# =====================================================
# EXCLUIR LEAD
# =====================================================

@admin_bp.route("/lead/<int:lead_id>/delete", methods=["POST"])
def delete_lead(lead_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    connection.commit()
    connection.close()

    return redirect(url_for("admin.dashboard"))