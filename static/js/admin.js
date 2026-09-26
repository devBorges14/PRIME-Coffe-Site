document.addEventListener("DOMContentLoaded", () => {

    const statusForms = document.querySelectorAll(".agenda-status-form");
    const deleteForms = document.querySelectorAll(".agenda-delete-form");

    let currentForm = null;
    let currentAction = null;
    let originalStatus = null;

    /*
    =========================================================
    UTILITÁRIOS
    =========================================================
    */

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return "";
        }

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    function formatDate(dateString) {

        if (!dateString) {
            return "-";
        }

        const parts = dateString.split("-");

        if (parts.length !== 3) {
            return dateString;
        }

        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }


    function statusLabel(status) {

        const labels = {
            AVAILABLE: "Disponível",
            BOOKED: "Ocupado",
            BLOCKED: "Bloqueado",
            DELETED: "Excluído"
        };

        return labels[status] || status || "-";
    }


    /*
    =========================================================
    MODAL
    =========================================================
    */

    function createImpactModal() {

        let modal = document.getElementById("agendaImpactModal");

        if (modal) {
            return modal;
        }

        modal = document.createElement("div");

        modal.id = "agendaImpactModal";
        modal.className = "agenda-impact-modal hidden";

        modal.innerHTML = `
            <div
                class="agenda-impact-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="agendaImpactTitle"
            >

                <div class="agenda-impact-icon">
                    ⚠
                </div>

                <h2 id="agendaImpactTitle">
                    Atenção — horário ocupado
                </h2>

                <p class="agenda-impact-warning" id="agendaImpactWarning">
                    Esta alteração afetará uma reserva existente.
                </p>

                <div class="agenda-impact-slot">

                    <div class="agenda-impact-slot-item">
                        <span>Data</span>
                        <strong id="agendaImpactDate">-</strong>
                    </div>

                    <div class="agenda-impact-slot-item">
                        <span>Horário</span>
                        <strong id="agendaImpactTime">-</strong>
                    </div>

                </div>

                <div
                    class="agenda-impact-leads"
                    id="agendaImpactLeads"
                ></div>

                <div class="agenda-impact-actions">

                    <button
                        type="button"
                        class="agenda-impact-cancel"
                        id="agendaImpactCancel"
                    >
                        Cancelar
                    </button>

                    <button
                        type="button"
                        class="agenda-impact-confirm"
                        id="agendaImpactConfirm"
                    >
                        Confirmar alteração
                    </button>

                </div>

            </div>
        `;

        document.body.appendChild(modal);

        const cancelButton =
            document.getElementById("agendaImpactCancel");

        const confirmButton =
            document.getElementById("agendaImpactConfirm");


        cancelButton.addEventListener("click", () => {
            closeImpactModal(true);
        });


        confirmButton.addEventListener("click", () => {
            confirmImpactAction();
        });


        /*
        Fecha clicando fora do modal.
        */

        modal.addEventListener("click", (event) => {

            if (event.target === modal) {
                closeImpactModal(true);
            }

        });


        /*
        ESC também cancela.
        */

        document.addEventListener("keydown", (event) => {

            if (
                event.key === "Escape" &&
                !modal.classList.contains("hidden")
            ) {
                closeImpactModal(true);
            }

        });


        return modal;
    }


    function openImpactModal(data) {

        const modal = createImpactModal();

        const dateElement =
            document.getElementById("agendaImpactDate");

        const timeElement =
            document.getElementById("agendaImpactTime");

        const leadsContainer =
            document.getElementById("agendaImpactLeads");

        const warningElement =
            document.getElementById("agendaImpactWarning");

        const confirmButton =
            document.getElementById("agendaImpactConfirm");


        const slot = data.slot;
        const leads = data.affected_leads || [];


        dateElement.textContent =
            formatDate(slot.date);


        timeElement.textContent =
            `${slot.start_time} — ${slot.end_time}`;


        /*
        Texto diferente dependendo da operação.
        */

        if (currentAction === "delete") {

            warningElement.textContent =
                "Este horário possui uma reserva vinculada. Excluir este horário não apagará o contrato, mas afetará a disponibilidade registrada.";

            confirmButton.textContent =
                "Excluir mesmo assim";

        } else {

            const selectedStatus =
                currentForm
                    ?.querySelector('select[name="status"]')
                    ?.value;

            warningElement.textContent =
                `Este horário possui ${
                    leads.length > 1
                        ? "reservas existentes"
                        : "uma reserva existente"
                }. Alterar o status para "${statusLabel(selectedStatus)}" poderá afetar essa reserva.`;

            confirmButton.textContent =
                "Confirmar alteração";
        }


        /*
        Lista de clientes afetados.
        */

        leadsContainer.innerHTML = "";


        leads.forEach((lead) => {

            const item =
                document.createElement("div");

            item.className =
                "agenda-impact-lead";


            const clientName =
                escapeHtml(
                    lead.name || "Cliente não informado"
                );

            const eventType =
                escapeHtml(
                    lead.event_type || "Evento não informado"
                );

            const leadId =
                escapeHtml(
                    lead.id ?? "-"
                );


            item.innerHTML = `
                <strong>
                    ${clientName}
                </strong>

                <span>
                    Evento: ${eventType}
                </span>

                <span>
                    Contrato/Lead: #${leadId}
                </span>
            `;


            leadsContainer.appendChild(item);

        });


        modal.classList.remove("hidden");

        document.body.style.overflow = "hidden";

        confirmButton.focus();
    }


    function closeImpactModal(restoreForm) {

        const modal =
            document.getElementById("agendaImpactModal");

        if (!modal) {
            return;
        }


        /*
        Se cancelou, restaura o valor
        que existia antes da alteração.
        */

        if (
            restoreForm &&
            currentForm &&
            currentAction === "status" &&
            originalStatus !== null
        ) {

            const select =
                currentForm.querySelector(
                    'select[name="status"]'
                );

            if (select) {
                select.value = originalStatus;
            }

        }


        modal.classList.add("hidden");

        document.body.style.overflow = "";


        currentForm = null;
        currentAction = null;
        originalStatus = null;
    }


    /*
    =========================================================
    CONFIRMAÇÃO
    =========================================================
    */

    function confirmImpactAction() {

        if (!currentForm) {
            closeImpactModal(false);
            return;
        }


        /*
        Evita que o usuário clique várias vezes.
        */

        const confirmButton =
            document.getElementById("agendaImpactConfirm");

        confirmButton.disabled = true;
        confirmButton.textContent = "Processando...";


        /*
        Campo enviado ao backend para informar
        que o impacto foi explicitamente confirmado.
        */

        let confirmationInput =
            currentForm.querySelector(
                'input[name="confirm_impact"]'
            );


        if (!confirmationInput) {

            confirmationInput =
                document.createElement("input");

            confirmationInput.type = "hidden";
            confirmationInput.name = "confirm_impact";

            currentForm.appendChild(
                confirmationInput
            );

        }


        confirmationInput.value = "1";


        /*
        submit() nativo evita disparar novamente
        o listener de submit.
        */

        currentForm.submit();
    }


    /*
    =========================================================
    CONSULTA DE IMPACTO
    =========================================================
    */

    async function checkImpact(form, slotId) {

        const response =
            await fetch(
                `/admin/agenda/${slotId}/impact`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    },
                    credentials: "same-origin"
                }
            );


        if (!response.ok) {
            throw new Error(
                `Erro HTTP ${response.status}`
            );
        }


        return await response.json();
    }


    /*
    =========================================================
    ALTERAÇÃO DE STATUS
    =========================================================
    */

    statusForms.forEach((form) => {

        form.addEventListener("submit", async (event) => {

            event.preventDefault();


            /*
            Se já houve confirmação,
            deixa o formulário seguir.
            */

            const confirmation =
                form.querySelector(
                    'input[name="confirm_impact"]'
                );


            if (
                confirmation &&
                confirmation.value === "1"
            ) {

                form.submit();
                return;
            }


            const slotId =
                form.dataset.slotId;


            const select =
                form.querySelector(
                    'select[name="status"]'
                );


            if (!slotId || !select) {
                return;
            }


            /*
            Guarda o estado anterior.
            */

            originalStatus =
                form.dataset.currentStatus ||
                select.dataset.previousValue ||
                null;


            /*
            Caso o HTML não tenha fornecido
            explicitamente o estado anterior,
            usamos o valor inicial armazenado.
            */

            if (!originalStatus) {

                originalStatus =
                    select.getAttribute(
                        "data-current-status"
                    );

            }


            currentForm = form;
            currentAction = "status";


            /*
            Se não tivermos o estado anterior,
            não impedimos o funcionamento,
            mas tentamos registrar o valor atual.
            */

            if (!originalStatus) {

                originalStatus =
                    select.value;

            }


            try {

                const data =
                    await checkImpact(
                        form,
                        slotId
                    );


                /*
                Nenhum contrato fechado:
                pode alterar imediatamente.
                */

                if (
                    !data.affected_leads ||
                    data.affected_leads.length === 0
                ) {

                    form.submit();
                    return;
                }


                /*
                Existe impacto:
                abre confirmação.
                */

                openImpactModal(data);

            } catch (error) {

                console.error(
                    "Erro ao verificar impacto:",
                    error
                );


                /*
                Restaura a seleção.
                */

                if (originalStatus) {
                    select.value = originalStatus;
                }


                currentForm = null;
                currentAction = null;
                originalStatus = null;


                alert(
                    "Não foi possível verificar se este horário possui uma reserva. A alteração não foi realizada."
                );

            }

        });


        /*
        Guarda o valor inicial do select.
        */

        const select =
            form.querySelector(
                'select[name="status"]'
            );


        if (select) {

            select.dataset.previousValue =
                select.value;

            select.addEventListener(
                "focus",
                () => {

                    select.dataset.previousValue =
                        select.value;

                }
            );


            /*
            CORREÇÃO: o <select> de status não tem
            botão de submit próprio no HTML. Sem este
            listener, trocar a opção no dropdown nunca
            enviava o formulário — a checagem de impacto
            e o próprio salvamento do status nunca eram
            disparados, e por isso a troca "não fazia nada
            e não avisava nada".

            requestSubmit() (em vez de submit()) dispara o
            evento "submit" normalmente, passando pelo
            listener acima que faz a consulta de impacto.
            */

            select.addEventListener(
                "change",
                () => {

                    if (typeof form.requestSubmit === "function") {

                        form.requestSubmit();

                    } else {

                        /*
                        Fallback para navegadores sem
                        requestSubmit(). form.submit() nativo
                        pula os listeners de "submit", então
                        disparamos o evento manualmente.
                        */

                        form.dispatchEvent(
                            new Event(
                                "submit",
                                { cancelable: true }
                            )
                        );

                    }

                }
            );

        }

    });


    /*
    =========================================================
    EXCLUSÃO
    =========================================================
    */

    deleteForms.forEach((form) => {

        form.addEventListener("submit", async (event) => {

            event.preventDefault();


            /*
            Se já foi confirmado,
            envia diretamente.
            */

            const confirmation =
                form.querySelector(
                    'input[name="confirm_impact"]'
                );


            if (
                confirmation &&
                confirmation.value === "1"
            ) {

                form.submit();
                return;
            }


            const slotId =
                form.dataset.slotId;


            if (!slotId) {
                return;
            }


            currentForm = form;
            currentAction = "delete";
            originalStatus = null;


            try {

                const data =
                    await checkImpact(
                        form,
                        slotId
                    );


                /*
                Se não existe contrato fechado,
                fazemos uma confirmação simples.
                */

                if (
                    !data.affected_leads ||
                    data.affected_leads.length === 0
                ) {

                    currentForm = null;
                    currentAction = null;


                    const confirmed =
                        window.confirm(
                            "Tem certeza que deseja excluir este horário?"
                        );


                    if (confirmed) {
                        form.submit();
                    }

                    return;
                }


                /*
                Existe contrato:
                modal completo.
                */

                openImpactModal(data);

            } catch (error) {

                console.error(
                    "Erro ao verificar impacto:",
                    error
                );


                currentForm = null;
                currentAction = null;


                alert(
                    "Não foi possível verificar se este horário possui uma reserva. A exclusão não foi realizada."
                );

            }

        });

    });

});