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
  requestForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const result = requestForm.querySelector("[data-form-result]");
    if (result) {
      result.textContent = "Заявка подготовлена. На следующем этапе её можно будет сохранять в базе данных.";
    }
  });
}
