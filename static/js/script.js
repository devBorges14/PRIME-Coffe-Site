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