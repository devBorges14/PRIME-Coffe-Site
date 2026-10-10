from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
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

        # ------------------------------------------------
        # HORÁRIOS DISPONÍVEIS PARA REAGENDAMENTO
        # ------------------------------------------------
        #
        # Só entram aqui horários realmente AVAILABLE, a
        # partir de hoje. O backend confere de novo no
        # momento do envio (outro admin pode ter ocupado
        # esse horário nesse meio tempo).

        today = datetime.date.today().isoformat()

        available_slots = connection.execute("""
            SELECT *
            FROM availability
            WHERE status = 'AVAILABLE'
              AND date >= ?
            ORDER BY date ASC, start_time ASC
        """, (today,)).fetchall()

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

    # Monta o texto já formatado (DD/MM/AAAA) para o select,
    # pra não precisar de filtro Jinja customizado.

    available_slots_options = []

    for slot in available_slots:

        year, month, day = slot["date"].split("-")

        label = (
            f'{day}/{month}/{year} — '
            f'{slot["start_time"]} às {slot["end_time"]}'
        )

        available_slots_options.append({
            "id": slot["id"],
            "label": label
        })

    # ----------------------------------------------------
    # DATAS: escolhida pelo cliente x reagendada
    # ----------------------------------------------------
    #
    # original_event_date só existe depois do 1º reagendamento.
    # Se foi reagendado de volta para a mesma data/hora do
    # cliente, mostra só a do cliente.

    client_date = format_date_time(
        lead["original_event_date"] or lead["event_date"],
        lead["original_event_time"] if lead["original_event_date"] else lead["event_time"]
    )

    rescheduled_date = None

    if lead["original_event_date"] and (
        lead["original_event_date"], lead["original_event_time"]
    ) != (lead["event_date"], lead["event_time"]):

        rescheduled_date = format_date_time(
            lead["event_date"],
            lead["event_time"]
        )

    return render_template(
        "admin/lead.html",
        lead=lead,
        lead_history=lead_history,
        available_slots=available_slots_options,
        client_date=client_date,
        rescheduled_date=rescheduled_date
    )


def format_date_time(date, time=None):
    """'2026-10-13', '14:00' -> '13/10/2026 às 14:00'."""

    if not date:
        return None

    try:
        year, month, day = date.split("-")
        text = f"{day}/{month}/{year}"
    except ValueError:
        text = date

    if time:
        text += f" às {time}"

    return text


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
# REAGENDAR
# ============================================================

@admin_bp.route(
    "/leads/<int:lead_id>/reagendar",
    methods=["POST"]
)
@login_required
def reschedule_lead(lead_id):

    new_slot_id = request.form.get(
        "new_availability_id",
        ""
    ).strip()

    if not new_slot_id:

        flash(
            "Selecione um novo horário.",
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

        # ----------------------------------------------------
        # BUSCAR NOVO HORÁRIO
        # ----------------------------------------------------

        new_slot = connection.execute("""
            SELECT *
            FROM availability
            WHERE id = ?
        """, (new_slot_id,)).fetchone()

        if not new_slot:

            flash(
                "Horário selecionado não foi encontrado.",
                "error"
            )

            return redirect(
                url_for(
                    "admin.lead_detail",
                    lead_id=lead_id
                )
            )

        # Confere de novo (pode ter sido ocupado por outro
        # admin entre a página carregar e o envio do form).

        if new_slot["status"] != "AVAILABLE":

            flash(
                "Este horário não está mais disponível. "
                "Escolha outro e tente novamente.",
                "error"
            )

            return redirect(
                url_for(
                    "admin.lead_detail",
                    lead_id=lead_id
                )
            )

        if lead["availability_id"] == new_slot["id"]:

            flash(
                "Este já é o horário atual deste lead.",
                "error"
            )

            return redirect(
                url_for(
                    "admin.lead_detail",
                    lead_id=lead_id
                )
            )

        # ----------------------------------------------------
        # HORÁRIO ANTIGO (pode não existir)
        # ----------------------------------------------------

        old_slot = None

        if lead["availability_id"]:

            old_slot = connection.execute("""
                SELECT *
                FROM availability
                WHERE id = ?
            """, (
                lead["availability_id"],
            )).fetchone()

        old_label = (
            f'{old_slot["date"]} {old_slot["start_time"]}'
            if old_slot else "nenhum horário"
        )

        new_label = (
            f'{new_slot["date"]} {new_slot["start_time"]}'
        )

        # ----------------------------------------------------
        # SE O LEAD JÁ ESTÁ FECHADO: libera o slot antigo
        # (que estava BOOKED por causa dele) e reserva o novo.
        # Se o lead ainda não fechou, nenhum dos dois slots
        # precisa mudar de status — só o ponteiro do lead muda.
        # ----------------------------------------------------

        if lead["status"] == "FECHADO":

            if old_slot and old_slot["status"] == "BOOKED":

                connection.execute("""
                    UPDATE availability
                    SET status = 'AVAILABLE',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                      AND status = 'BOOKED'
                """, (
                    old_slot["id"],
                ))

                register_history(
                    connection=connection,
                    slot=old_slot,
                    action="LIBERACAO_AUTOMATICA",
                    old_status="BOOKED",
                    new_status="AVAILABLE",
                    affected_lead=lead,
                    description=(
                        f"Horário liberado por reagendamento "
                        f"(novo horário: {new_label})."
                    )
                )

            connection.execute("""
                UPDATE availability
                SET status = 'BOOKED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_slot["id"],
            ))

            register_history(
                connection=connection,
                slot=new_slot,
                action="RESERVA_AUTOMATICA",
                old_status="AVAILABLE",
                new_status="BOOKED",
                affected_lead=lead,
                description=(
                    f"Horário reservado por reagendamento "
                    f"(horário anterior: {old_label})."
                )
            )

        # ----------------------------------------------------
        # ATUALIZA O LEAD
        # ----------------------------------------------------
        #
        # event_date/event_time também são atualizados para
        # continuarem batendo com o novo horário (são usados
        # no dashboard, relatórios etc. sem precisar de JOIN
        # com availability toda hora).
        #
        # No PRIMEIRO reagendamento, a data escolhida pelo
        # cliente é guardada em original_event_date/time
        # (COALESCE mantém a original nos reagendamentos
        # seguintes).

        connection.execute("""
            UPDATE leads
            SET original_event_date = COALESCE(original_event_date, event_date),
                original_event_time = COALESCE(original_event_time, event_time),
                availability_id = ?,
                event_date = ?,
                event_time = ?
            WHERE id = ?
        """, (
            new_slot["id"],
            new_slot["date"],
            new_slot["start_time"],
            lead_id
        ))

        register_lead_history(
            connection=connection,
            lead_id=lead_id,
            old_status=lead["status"],
            new_status=lead["status"],
            changed_by=session.get("username", "desconhecido"),
            description=(
                f"Reagendado de {old_label} para {new_label}."
            )
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

    flash(
        "Lead reagendado com sucesso.",
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