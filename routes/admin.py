from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

import datetime

from database.database import get_connection
from database.history import register_lead_history, get_lead_history
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
        # INDICADORES — FASE 5 (DASHBOARD)
        # ----------------------------------------------------

        today = datetime.date.today().isoformat()

        # Eventos fechados com data a partir de hoje

        eventos_proximos = connection.execute("""
            SELECT COUNT(*) AS total
            FROM leads
            WHERE status = 'FECHADO'
              AND event_date >= ?
        """, (
            today,
        )).fetchone()["total"]

        # Lista curta para exibir no dashboard (não só a contagem)

        proximos_eventos = connection.execute("""
            SELECT *
            FROM leads
            WHERE status = 'FECHADO'
              AND event_date >= ?
            ORDER BY event_date ASC, event_time ASC
            LIMIT 5
        """, (
            today,
        )).fetchall()

        # Disponibilidade da agenda

        horarios_disponiveis = connection.execute("""
            SELECT COUNT(*) AS total
            FROM availability
            WHERE status = 'AVAILABLE'
        """).fetchone()["total"]

        horarios_ocupados = connection.execute("""
            SELECT COUNT(*) AS total
            FROM availability
            WHERE status = 'BOOKED'
        """).fetchone()["total"]

        # Taxa de conversão (fechados / total de leads)

        if total_leads:

            taxa_conversao = round(
                (fechados / total_leads) * 100,
                1
            )

        else:

            taxa_conversao = 0

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

        eventos_proximos=eventos_proximos,
        proximos_eventos=proximos_eventos,
        horarios_disponiveis=horarios_disponiveis,
        horarios_ocupados=horarios_ocupados,
        taxa_conversao=taxa_conversao,

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

    lead_history = get_lead_history(lead_id)

    return render_template(
        "admin/lead.html",
        lead=lead,
        lead_history=lead_history
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

                    # Verifica se o BOOKED atual pertence a
                    # OUTRO lead FECHADO. Se pertencer, isso é
                    # um conflito real (dois contratos no mesmo
                    # horário) e o fechamento deve ser barrado.

                    conflicting_lead = connection.execute("""
                        SELECT id, name, event_type
                        FROM leads
                        WHERE availability_id = ?
                          AND status = 'FECHADO'
                          AND id != ?
                        LIMIT 1
                    """, (
                        lead["availability_id"],
                        lead["id"]
                    )).fetchone()

                    if conflicting_lead:

                        flash(
                            f"Não é possível fechar este contrato: o horário "
                            f"já está ocupado pelo cliente "
                            f"{conflicting_lead['name']} "
                            f"(lead #{conflicting_lead['id']}).",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "admin.lead_detail",
                                lead_id=lead_id
                            )
                        )

                    # Se chegou aqui, o BOOKED já pertence a
                    # este mesmo lead (ex.: reabriu e fechou
                    # de novo) — pode seguir sem novo histórico.

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
        # SAINDO DE FECHADO (qualquer status de destino)
        # ====================================================
        #
        # Antes, esta liberação só acontecia quando o novo
        # status era exatamente "SEM INTERESSE". Isso deixava
        # o horário preso em BOOKED para sempre se o admin
        # movesse o lead de FECHADO para qualquer outro status
        # (ex.: voltar para NEGOCIAÇÃO por engano), sem gerar
        # nenhum registro no histórico. Agora qualquer saída de
        # FECHADO libera o horário e registra a mudança.

        elif (
            old_status == "FECHADO"
            and new_status != "FECHADO"
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
                      AND status = 'BOOKED'
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
                        f"Horário liberado automaticamente "
                        f"porque o contrato deixou de estar FECHADO "
                        f"(novo status do lead: {new_status})."
                    )
                )

        # ----------------------------------------------------
        # REGISTRAR NO HISTÓRICO DO LEAD
        # ----------------------------------------------------
        #
        # Registrado antes do UPDATE, mas dentro da mesma
        # transação (só é gravado de fato no commit()
        # abaixo, junto com tudo o mais).

        register_lead_history(
            connection=connection,
            lead_id=lead_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=session.get("username", "desconhecido"),
            description=(
                f"Status alterado de {old_status} para {new_status} "
                f"pelo administrador."
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

        # A exclusão é permanente e não deixa rastro no banco,
        # então registramos no log quem excluiu e qual lead era.

        current_app.logger.warning(
            "Lead excluido: id=%s nome=%r status=%s por=%r",
            lead_id,
            lead["name"],
            lead["status"],
            session.get("username")
        )

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
