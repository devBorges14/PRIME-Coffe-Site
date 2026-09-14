console.log("Site do Tio Ale carregado!");
// =====================================================
// MODAL DE CONTATO
// =====================================================

const contactModal = document.getElementById("contactModal");
const contactTriggers = document.querySelectorAll(".contact-trigger");
const closeContact = document.getElementById("closeContact");
const contactOverlay = document.getElementById("contactOverlay");


// Abrir

contactTriggers.forEach((trigger) => {

    trigger.addEventListener("click", () => {

        contactModal.classList.add("active");

        document.body.style.overflow = "hidden";

    });

});


// Fechar

function closeContactModal() {

    contactModal.classList.remove("active");

    document.body.style.overflow = "";

}


closeContact.addEventListener(
    "click",
    closeContactModal
);


contactOverlay.addEventListener(
    "click",
    closeContactModal
);


// Fechar com ESC

document.addEventListener("keydown", (event) => {

    if (event.key === "Escape") {

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


            // Botão

            const submitButton =
                contactForm.querySelector(
                    ".form-submit"
                );


            submitButton.disabled = true;

            submitButton.textContent =
                "Enviando...";


            formMessage.textContent = "";

            formMessage.className =
                "form-message";


            try {

                const formData =
                    new FormData(contactForm);


                const response =
                    await fetch(
                        "/contato",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const data =
                    await response.json();


                // =========================================
                // ERRO
                // =========================================

                if (!response.ok) {

                    formMessage.textContent =
                        data.errors
                            ? data.errors.join(" ")
                            : "Não foi possível enviar.";

                    formMessage.classList.add(
                        "error"
                    );

                    return;
                }


                // =========================================
                // SUCESSO
                // =========================================

                formMessage.textContent =
                    data.message;

                formMessage.classList.add(
                    "success"
                );


                contactForm.reset();


            } catch (error) {

                console.error(error);


                formMessage.textContent =
                    "Erro de conexão. Tente novamente.";

                formMessage.classList.add(
                    "error"
                );


            } finally {

                submitButton.disabled = false;

                submitButton.textContent =
                    "Enviar solicitação →";

            }

        }
    );
    const eventDateInput = document.querySelector(
    'input[name="data_evento"]'
);

const eventTimeSelect = document.querySelector(
    'select[name="horario_evento"]'
);


if (eventDateInput && eventTimeSelect) {

    eventDateInput.addEventListener("change", async () => {

        const date = eventDateInput.value;

        eventTimeSelect.innerHTML = `
            <option value="">
                Carregando horários...
            </option>
        `;

        if (!date) {

            eventTimeSelect.innerHTML = `
                <option value="">
                    Selecione uma data
                </option>
            `;

            return;
        }

        try {

            const response = await fetch(
                `/disponibilidade?date=${encodeURIComponent(date)}`
            );

            const slots = await response.json();

            eventTimeSelect.innerHTML = "";

            if (slots.length === 0) {

                eventTimeSelect.innerHTML = `
                    <option value="">
                        Nenhum horário disponível
                    </option>
                `;

                return;
            }

            const defaultOption = document.createElement("option");

            defaultOption.value = "";
            defaultOption.textContent = "Selecione um horário";

            eventTimeSelect.appendChild(defaultOption);

            slots.forEach(slot => {

                const option = document.createElement("option");

                option.value = slot.start_time;

                option.textContent =
                    `${slot.start_time} às ${slot.end_time}`;

                eventTimeSelect.appendChild(option);

            });

        } catch (error) {

            console.error(
                "Erro ao carregar disponibilidade:",
                error
            );

            eventTimeSelect.innerHTML = `
                <option value="">
                    Erro ao carregar horários
                </option>
            `;
        }

    });

}

}