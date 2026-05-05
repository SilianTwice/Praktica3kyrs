document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const target = document.querySelector(link.getAttribute("href"));
    if (!target) {
      return;
    }

    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const navToggle = document.querySelector(".nav-toggle");

if (navToggle) {
  navToggle.addEventListener("click", () => {
    const isOpen = document.body.classList.toggle("nav-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
}

const requestForm = document.querySelector("[data-request-form]");

if (requestForm) {
  const result = requestForm.querySelector("[data-form-result]");
  const status = new URLSearchParams(window.location.search).get("status");

  if (result && status === "sent") {
    result.textContent = "Заявка сохранена. Мастер сможет увидеть её в разделе заявок.";
    result.classList.add("form-alert-success");
  }

  if (result && status === "error") {
    result.textContent = "Заполните имя и контакт для связи.";
    result.classList.add("form-alert-error");
  }

  if (window.location.protocol === "file:") {
    requestForm.addEventListener("submit", (event) => {
      event.preventDefault();

      if (result) {
        result.textContent = "Для сохранения заявки откройте сайт через локальный сервер.";
        result.classList.add("form-alert-error");
      }
    });
  }
}
