from database.database import get_connection


def register_lead_history(
    connection,
    lead_id,
    old_status,
    new_status,
    changed_by=None,
    description=""
):
    """
    Registra uma entrada no histórico do lead.

    old_status  -> None na criação do lead (não havia status anterior)
    changed_by  -> None quando a mudança vem do formulário público;
                   username do admin quando vem do CRM
    """

    connection.execute("""
        INSERT INTO leads_history (
            lead_id,
            old_status,
            new_status,
            changed_by,
            description
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        lead_id,
        old_status,
        new_status,
        changed_by,
        description
    ))


def get_lead_history(lead_id):
    """
    Retorna o histórico completo de um lead,
    do mais antigo para o mais recente (ordem
    natural de leitura de uma timeline).
    """

    connection = get_connection()

    history = connection.execute("""
        SELECT *
        FROM leads_history
        WHERE lead_id = ?
        ORDER BY created_at ASC
    """, (
        lead_id,
    )).fetchall()

    connection.close()

    return history