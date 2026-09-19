from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from database.database import get_connection
from auth_utils import login_required
from routes.agenda import register_history


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# DASHBOARD
# ============================================================

@admin_bp.route("/")
@login_required
def dashboard():

    connection = get_connection()

    try:
        # ----------------------------------------------------
        # ESTATÍSTICAS
        # ----------------------------------------------------

        total_leads = connection.execute("""
            SELECT COUNT(*) AS total
            FROM leads
        """).fetchone()["total"]

        novos = connection.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE status = 'NOVO'
        """).fetchone()["total"]

        negociacoes = connection.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE status = 'NEGOCIAÇÃO'
        """).fetchone()["total"]

        fechados = connection.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE status = 'FECHADO'
        """).fetchone()["total"]

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        status_filter = request.args.get(
            "status",
            ""
        ).strip()

        search = request.args.get(
            "search",
            ""
        ).strip()

        event_filter = request.args.get(
            "event_type",
            ""
        ).strip()

        date_filter = request.args.get(
            "event_date",
            ""
        ).strip()

        # ----------------------------------------------------
        # CONSULTA DOS LEADS
        # ----------------------------------------------------

        query = """
            SELECT *
            FROM leads
            WHERE 1 = 1
        """

        params = []

        # Filtro por status
        if status_filter:

            query += """
                AND status = ?
            """

            params.append(status_filter)

        # Filtro por tipo de evento
        if event_filter:

            query += """
                AND event_type = ?
            """

            params.append(event_filter)

        # Filtro por data
        if date_filter:

            query += """
                AND event_date = ?
            """

            params.append(date_filter)

        # Pesquisa
        if search:

            query += """
                AND (
                    name LIKE ?
                    OR email LIKE ?
                    OR phone LIKE ?
                    OR event_type LIKE ?
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value,
                search_value,
                search_value
            ])

        # Mais recentes primeiro
        query += """
            ORDER BY created_at DESC
        """

        leads = connection.execute(
            query,
            params
        ).fetchall()

    finally:
        connection.close()

    return render_template(
        "admin/dashboard.html",

        total_leads=total_leads,
        novos=novos,
        negociacoes=negociacoes,
        fechados=fechados,

        leads=leads,

        status_filter=status_filter,
        search=search,
        event_filter=event_filter,
        date_filter=date_filter
    )


# ============================================================
# DETALHES DO LEAD
# ============================================================

@admin_bp.route("/leads/<int:lead_id>")
@login_required
def lead_detail(lead_id):

    connection = get_connection()

    try:

        lead = connection.execute("""
            SELECT *
            FROM leads
            WHERE id = ?
        """, (lead_id,)).fetchone()

    finally:
        connection.close()

    if not lead:

        flash(
            "Lead não encontrado.",
            "error"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "admin/lead.html",
        lead=lead
    )


# ============================================================
# ALTERAR STATUS
# ============================================================

@admin_bp.route(
    "/leads/<int:lead_id>/status",
    methods=["POST"]
)
@login_required
def update_status(lead_id):

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = {
        "NOVO",
        "CONTATO REALIZADO",
        "ORÇAMENTO ENVIADO",
        "NEGOCIAÇÃO",
        "FECHADO",
        "SEM INTERESSE"
    }

    # --------------------------------------------------------
    # STATUS INVÁLIDO
    # --------------------------------------------------------

    if new_status not in allowed_statuses:

        flash(
            "Status inválido.",
            "error"
        )

        return redirect(
            url_for(
                "admin.lead_detail",
                lead_id=lead_id
            )
        )

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # BUSCAR LEAD
        # ----------------------------------------------------

        lead = connection.execute("""
            SELECT *
            FROM leads
            WHERE id = ?
        """, (lead_id,)).fetchone()

        if not lead:

            flash(
                "Lead não encontrado.",
                "error"
            )

            return redirect(
                url_for("admin.dashboard")
            )

        old_status = lead["status"]

        # ----------------------------------------------------
        # NADA MUDOU
        # ----------------------------------------------------

        if old_status == new_status:

            return redirect(
                url_for(
                    "admin.lead_detail",
                    lead_id=lead_id
                )
            )

        # ----------------------------------------------------
        # BUSCAR HORÁRIO ASSOCIADO
        # ----------------------------------------------------

        availability = None

        if lead["availability_id"]:

            availability = connection.execute("""
                SELECT *
                FROM availability
                WHERE id = ?
            """, (
                lead["availability_id"],
            )).fetchone()

        # ====================================================
        # FECHANDO CONTRATO
        # ====================================================

        if new_status == "FECHADO":

            if availability:

                current_status = availability["status"]

                # --------------------------------------------
                # HORÁRIO EXCLUÍDO
                # --------------------------------------------

                if current_status == "DELETED":

                    flash(
                        "Não é possível fechar este contrato "
                        "porque o horário associado foi excluído.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "admin.lead_detail",
                            lead_id=lead_id
                        )
                    )

                # --------------------------------------------
                # HORÁRIO BLOQUEADO
                # --------------------------------------------

                if current_status == "BLOCKED":

                    flash(
                        "Não é possível fechar este contrato "
                        "porque o horário está bloqueado.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "admin.lead_detail",
                            lead_id=lead_id
                        )
                    )

                # --------------------------------------------
                # HORÁRIO JÁ RESERVADO
                # --------------------------------------------

                elif current_status == "BOOKED":

                    pass

                # --------------------------------------------
                # HORÁRIO DISPONÍVEL
                # --------------------------------------------

                elif current_status == "AVAILABLE":

                    connection.execute("""
                        UPDATE availability
                        SET
                            status = 'BOOKED',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        lead["availability_id"],
                    ))

                    register_history(
                        connection=connection,
                        slot=availability,
                        action="RESERVA_AUTOMATICA",
                        old_status="AVAILABLE",
                        new_status="BOOKED",
                        affected_lead=lead,
                        description=(
                            "Horário reservado automaticamente "
                            "porque o lead foi marcado como FECHADO."
                        )
                    )

        # ====================================================
        # CANCELANDO CONTRATO
        # ====================================================

        elif (
            new_status == "SEM INTERESSE"
            and old_status == "FECHADO"
        ):

            if (
                availability
                and availability["status"] == "BOOKED"
            ):

                connection.execute("""
                    UPDATE availability
                    SET
                        status = 'AVAILABLE',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    lead["availability_id"],
                ))

                register_history(
                    connection=connection,
                    slot=availability,
                    action="LIBERACAO_AUTOMATICA",
                    old_status="BOOKED",
                    new_status="AVAILABLE",
                    affected_lead=lead,
                    description=(
                        "Horário liberado automaticamente "
                        "porque o contrato passou de FECHADO "
                        "para SEM INTERESSE."
                    )
                )

        # ----------------------------------------------------
        # ATUALIZAR STATUS DO LEAD
        # ----------------------------------------------------

        connection.execute("""
            UPDATE leads
            SET status = ?
            WHERE id = ?
        """, (
            new_status,
            lead_id
        ))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

    flash(
        "Status atualizado com sucesso.",
        "success"
    )

    return redirect(
        url_for(
            "admin.lead_detail",
            lead_id=lead_id
        )
    )


# ============================================================
# ATUALIZAR OBSERVAÇÕES
# ============================================================

@admin_bp.route(
    "/leads/<int:lead_id>/notes",
    methods=["POST"]
)
@login_required
def update_notes(lead_id):

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    connection = get_connection()

    try:

        # Verifica se o lead existe
        lead = connection.execute("""
            SELECT id
            FROM leads
            WHERE id = ?
        """, (lead_id,)).fetchone()

        if not lead:

            flash(
                "Lead não encontrado.",
                "error"
            )

            return redirect(
                url_for("admin.dashboard")
            )

        connection.execute("""
            UPDATE leads
            SET notes = ?
            WHERE id = ?
        """, (
            notes,
            lead_id
        ))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

    flash(
        "Observações atualizadas com sucesso.",
        "success"
    )

    return redirect(
        url_for(
            "admin.lead_detail",
            lead_id=lead_id
        )
    )


# ============================================================
# EXCLUIR LEAD
# ============================================================

@admin_bp.route(
    "/leads/<int:lead_id>/delete",
    methods=["POST"]
)
@login_required
def delete_lead(lead_id):

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # BUSCAR LEAD
        # ----------------------------------------------------

        lead = connection.execute("""
            SELECT *
            FROM leads
            WHERE id = ?
        """, (lead_id,)).fetchone()

        if not lead:

            flash(
                "Lead não encontrado.",
                "error"
            )

            return redirect(
                url_for("admin.dashboard")
            )

        # ----------------------------------------------------
        # PROTEGER CONTRATOS FECHADOS
        # ----------------------------------------------------

        if lead["status"] == "FECHADO":

            flash(
                "Clientes com contrato FECHADO não podem "
                "ser excluídos. Preserve o histórico do contrato.",
                "error"
            )

            return redirect(
                url_for(
                    "admin.lead_detail",
                    lead_id=lead_id
                )
            )

        # ----------------------------------------------------
        # EXCLUIR
        # ----------------------------------------------------

        connection.execute("""
            DELETE FROM leads
            WHERE id = ?
        """, (lead_id,))

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

    flash(
        "Lead excluído com sucesso.",
        "success"
    )

    return redirect(
        url_for("admin.dashboard")
    )