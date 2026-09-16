console.log("Site do Tio Ale carregado!");


// =====================================================
// MODAL DE CONTATO
// =====================================================

const contactModal =
    document.getElementById("contactModal");

const contactTriggers =
    document.querySelectorAll(".contact-trigger");

const closeContact =
    document.getElementById("closeContact");

const contactOverlay =
    document.getElementById("contactOverlay");


// =====================================================
// ABRIR MODAL
// =====================================================

if (contactModal) {

    contactTriggers.forEach((trigger) => {

        trigger.addEventListener("click", () => {

            contactModal.classList.add("active");

            document.body.style.overflow = "hidden";

        });

    });

}


// =====================================================
// FECHAR MODAL
// =====================================================

function closeContactModal() {

    if (!contactModal) {
        return;
    }

    contactModal.classList.remove("active");

    document.body.style.overflow = "";

}


if (closeContact) {

    closeContact.addEventListener(
        "click",
        closeContactModal
    );

}


if (contactOverlay) {

    contactOverlay.addEventListener(
        "click",
        closeContactModal
    );

}


// =====================================================
// FECHAR COM ESC
// =====================================================

document.addEventListener("keydown", (event) => {

    if (
        event.key === "Escape" &&
        contactModal &&
        contactModal.classList.contains("active")
    ) {

        closeContactModal();

    }

});


// =====================================================
// FORMULÁRIO DE CONTATO
// =====================================================

const contactForm =
    document.getElementById("contactForm");

const formMessage =
    document.getElementById("formMessage");


if (contactForm) {

    contactForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();


            // =================================================
            // VERIFICAÇÃO DA DATA E HORÁRIO
            // =================================================

            const eventDateInput =
                document.getElementById("data_evento");

            const eventTimeInput =
                document.getElementById("horario_evento");


            if (
                eventDateInput &&
                !eventDateInput.value
            ) {

                if (formMessage) {

                    formMessage.textContent =
                        "Selecione uma data para o evento.";

                    formMessage.className =
                        "form-message error";

                }

                return;
            }


            if (
                eventTimeInput &&
                !eventTimeInput.value
            ) {

                if (formMessage) {

                    formMessage.textContent =
                        "Selecione um horário para o evento.";

                    formMessage.className =
                        "form-message error";

                }

                return;
            }


            // =================================================
            // BOTÃO
            // =================================================

            const submitButton =
                contactForm.querySelector(
                    ".form-submit"
                );


            if (submitButton) {

                submitButton.disabled = true;

                submitButton.textContent =
                    "Enviando...";

            }


            if (formMessage) {

                formMessage.textContent = "";

                formMessage.className =
                    "form-message";

            }


            try {

                // =================================================
                // FORMDATA
                // =================================================

                const formData =
                    new FormData(contactForm);


                // =================================================
                // ENVIA PARA O FLASK
                // =================================================

                const response =
                    await fetch(
                        contactForm.action || "/contato",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const data =
                    await response.json();


                // =================================================
                // ERRO
                // =================================================

                if (!response.ok) {

                    if (formMessage) {

                        formMessage.textContent =
                            data.errors
                                ? data.errors.join(" ")
                                : "Não foi possível enviar.";

                        formMessage.classList.add(
                            "error"
                        );

                    }

                    return;
                }


                // =================================================
                // SUCESSO
                // =================================================

                if (formMessage) {

                    formMessage.textContent =
                        data.message ||
                        "Solicitação enviada com sucesso!";

                    formMessage.classList.add(
                        "success"
                    );

                }


                // Limpa o formulário
                contactForm.reset();


                // Limpa também a seleção visual
                resetBooking();


            } catch (error) {

                console.error(
                    "Erro ao enviar formulário:",
                    error
                );


                if (formMessage) {

                    formMessage.textContent =
                        "Erro de conexão. Tente novamente.";

                    formMessage.classList.add(
                        "error"
                    );

                }

            } finally {

                if (submitButton) {

                    submitButton.disabled = false;

                    submitButton.textContent =
                        "Enviar solicitação →";

                }

            }

        }
    );

}


// =====================================================
// CALENDÁRIO DE AGENDAMENTO
// =====================================================

const calendarMonth =
    document.getElementById("calendarMonth");

const calendarDays =
    document.getElementById("calendarDays");

const calendarPrev =
    document.getElementById("calendarPrev");

const calendarNext =
    document.getElementById("calendarNext");

const selectedDateLabel =
    document.getElementById("selectedDateLabel");

const timePanelMessage =
    document.getElementById("timePanelMessage");

const timeSlots =
    document.getElementById("timeSlots");

const eventDateInput =
    document.getElementById("data_evento");

const eventTimeInput =
    document.getElementById("horario_evento");


// =====================================================
// INICIALIZA CALENDÁRIO
// =====================================================

if (
    calendarMonth &&
    calendarDays &&
    calendarPrev &&
    calendarNext &&
    selectedDateLabel &&
    timePanelMessage &&
    timeSlots &&
    eventDateInput &&
    eventTimeInput
) {


    // =================================================
    // ESTADO
    // =================================================

    let currentDate = new Date();

    let selectedDate = null;


    // =================================================
    // FORMATA DATA PARA O BACKEND
    // =================================================

    function formatDateForBackend(date) {

        const year =
            date.getFullYear();

        const month =
            String(
                date.getMonth() + 1
            ).padStart(2, "0");

        const day =
            String(
                date.getDate()
            ).padStart(2, "0");

        return `${year}-${month}-${day}`;

    }


    // =================================================
    // FORMATA DATA PARA O USUÁRIO
    // =================================================

    function formatDateLabel(date) {

        return new Intl.DateTimeFormat(
            "pt-BR",
            {
                weekday: "long",
                day: "numeric",
                month: "long"
            }
        ).format(date);

    }


    // =================================================
    // COMPARA DUAS DATAS
    // =================================================

    function isSameDate(dateA, dateB) {

        if (!dateA || !dateB) {
            return false;
        }

        return (
            dateA.getFullYear() ===
                dateB.getFullYear()
            &&
            dateA.getMonth() ===
                dateB.getMonth()
            &&
            dateA.getDate() ===
                dateB.getDate()
        );

    }


    // =================================================
    // RENDERIZA CALENDÁRIO
    // =================================================

    function renderCalendar() {

        calendarDays.innerHTML = "";


        const year =
            currentDate.getFullYear();

        const month =
            currentDate.getMonth();


        // Primeiro dia do mês
        const firstDay =
            new Date(
                year,
                month,
                1
            ).getDay();


        // Quantidade de dias
        const daysInMonth =
            new Date(
                year,
                month + 1,
                0
            ).getDate();


        // Nome do mês
        calendarMonth.textContent =
            new Intl.DateTimeFormat(
                "pt-BR",
                {
                    month: "long",
                    year: "numeric"
                }
            ).format(currentDate);


        // =================================================
        // ESPAÇOS ANTES DO PRIMEIRO DIA
        // =================================================

        for (
            let i = 0;
            i < firstDay;
            i++
        ) {

            const emptyDay =
                document.createElement("div");

            emptyDay.className =
                "calendar-day empty";

            calendarDays.appendChild(
                emptyDay
            );

        }


        // =================================================
        // HOJE
        // =================================================

        const today =
            new Date();

        today.setHours(
            0,
            0,
            0,
            0
        );


        // =================================================
        // CRIA OS DIAS
        // =================================================

        for (
            let dayNumber = 1;
            dayNumber <= daysInMonth;
            dayNumber++
        ) {

            const day =
                document.createElement("button");

            day.type = "button";

            day.className =
                "calendar-day";

            day.textContent =
                dayNumber;


            const date =
                new Date(
                    year,
                    month,
                    dayNumber
                );


            // =================================================
            // DATAS PASSADAS
            // =================================================

            if (date < today) {

                day.classList.add(
                    "disabled"
                );

                day.disabled = true;

            }


            // =================================================
            // HOJE
            // =================================================

            if (
                isSameDate(
                    date,
                    today
                )
            ) {

                day.classList.add(
                    "today"
                );

            }


            // =================================================
            // DATA SELECIONADA
            // =================================================

            if (
                isSameDate(
                    date,
                    selectedDate
                )
            ) {

                day.classList.add(
                    "selected"
                );

            }


            // =================================================
            // CLIQUE
            // =================================================

            if (!day.disabled) {

                day.addEventListener(
                    "click",
                    () => selectDate(date)
                );

            }


            calendarDays.appendChild(day);

        }

    }


    // =====================================================
    // SELECIONAR DATA
    // =====================================================

    async function selectDate(date) {

        selectedDate = date;


        // =================================================
        // SALVA DATA NO INPUT OCULTO
        // =================================================

        eventDateInput.value =
            formatDateForBackend(date);


        // =================================================
        // LIMPA HORÁRIO ANTERIOR
        // =================================================

        eventTimeInput.value = "";


        // =================================================
        // ATUALIZA CALENDÁRIO
        // =================================================

        renderCalendar();


        // =================================================
        // ATUALIZA TEXTO
        // =================================================

        selectedDateLabel.textContent =
            formatDateLabel(date);


        timePanelMessage.textContent =
            "Buscando horários disponíveis...";


        timeSlots.innerHTML = `
            <div class="time-loading">
                Carregando horários...
            </div>
        `;


        // =================================================
        // BUSCA API
        // =================================================

        try {

            const backendDate =
                formatDateForBackend(date);


            const response =
                await fetch(
                    `/disponibilidade?date=${encodeURIComponent(
                        backendDate
                    )}`
                );


            if (!response.ok) {

                throw new Error(
                    "Erro ao consultar disponibilidade."
                );

            }


            const slots =
                await response.json();


            renderTimeSlots(slots);


        } catch (error) {

            console.error(
                "Erro ao carregar horários:",
                error
            );


            timePanelMessage.textContent =
                "Não foi possível carregar os horários.";


            timeSlots.innerHTML = `
                <div class="time-empty">
                    <span>!</span>

                    <p>
                        Erro ao carregar horários.
                        Tente novamente.
                    </p>
                </div>
            `;

        }

    }


    // =====================================================
    // RENDERIZA HORÁRIOS
    // =====================================================

    function renderTimeSlots(slots) {

        timeSlots.innerHTML = "";


        // =================================================
        // NENHUM HORÁRIO
        // =================================================

        if (
            !slots ||
            slots.length === 0
        ) {

            timePanelMessage.textContent =
                "Não há horários disponíveis para esta data.";


            timeSlots.innerHTML = `
                <div class="time-empty">

                    <span>◷</span>

                    <p>
                        Nenhum horário disponível.
                    </p>

                </div>
            `;

            return;

        }


        // =================================================
        // EXISTEM HORÁRIOS
        // =================================================

        timePanelMessage.textContent =
            "Escolha um horário para continuar.";


        slots.forEach((slot) => {

            const button =
                document.createElement("button");


            button.type = "button";


            button.className =
                "time-slot";


            button.textContent =
                `${slot.start_time} às ${slot.end_time}`;


            // Guarda o ID do horário
            button.dataset.slotId =
                slot.id;


            // =================================================
            // SELECIONAR HORÁRIO
            // =================================================

            button.addEventListener(
                "click",
                () => {

                    // Remove seleção anterior

                    document
                        .querySelectorAll(
                            ".time-slot"
                        )
                        .forEach((item) => {

                            item.classList.remove(
                                "selected"
                            );

                        });


                    // Seleciona atual

                    button.classList.add(
                        "selected"
                    );


                    // Envia apenas o horário inicial
                    // para o Flask

                    eventTimeInput.value =
                        slot.start_time;

                }
            );


            timeSlots.appendChild(
                button
            );

        });

    }


    // =====================================================
    // MÊS ANTERIOR
    // =====================================================

    calendarPrev.addEventListener(
        "click",
        () => {

            const today =
                new Date();


            const previousMonth =
                new Date(
                    currentDate.getFullYear(),
                    currentDate.getMonth() - 1,
                    1
                );


            // Não permite voltar antes
            // do mês atual

            const currentMonth =
                new Date(
                    today.getFullYear(),
                    today.getMonth(),
                    1
                );


            if (
                previousMonth <
                currentMonth
            ) {

                return;

            }


            currentDate =
                previousMonth;


            renderCalendar();

        }
    );


    // =====================================================
    // PRÓXIMO MÊS
    // =====================================================

    calendarNext.addEventListener(
        "click",
        () => {

            currentDate =
                new Date(
                    currentDate.getFullYear(),
                    currentDate.getMonth() + 1,
                    1
                );


            renderCalendar();

        }
    );


    // =====================================================
    // RESET DO AGENDAMENTO
    // =====================================================

    function resetBooking() {

        selectedDate = null;


        eventDateInput.value = "";

        eventTimeInput.value = "";


        currentDate =
            new Date();


        selectedDateLabel.textContent =
            "Selecione uma data";


        timePanelMessage.textContent =
            "Escolha um dia para visualizar os horários.";


        timeSlots.innerHTML = `
            <div class="time-empty">

                <span>◷</span>

                <p>
                    Nenhum horário selecionado
                </p>

            </div>
        `;


        renderCalendar();

    }


    // =====================================================
    // PRIMEIRA RENDERIZAÇÃO
    // =====================================================

    renderCalendar();

}