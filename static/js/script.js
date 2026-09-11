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

}