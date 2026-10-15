// Порядок словарей: перетаскивание мышью (за всю строку) или кнопки ↑↓ (клавиатура, телефон).
// Порядок чекбоксов в DOM = порядок, в котором форма отправит словари на сервер.
(function () {
  "use strict";

  const list = document.getElementById("providers");
  if (!list) return;
  let dragged = null;

  list.addEventListener("dragstart", (e) => {
    dragged = e.target.closest(".sort-item");
    if (!dragged) return;
    dragged.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", "");
  });

  list.addEventListener("dragover", (e) => {
    if (!dragged) return;
    e.preventDefault();
    const over = e.target.closest(".sort-item");
    if (!over || over === dragged) return;
    const rect = over.getBoundingClientRect();
    const after = e.clientY > rect.top + rect.height / 2;
    list.insertBefore(dragged, after ? over.nextSibling : over);
  });

  list.addEventListener("dragend", () => {
    if (dragged) dragged.classList.remove("dragging");
    dragged = null;
  });

  list.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-move]");
    if (!btn) return;
    const item = btn.closest(".sort-item");
    if (btn.dataset.move === "-1" && item.previousElementSibling) {
      list.insertBefore(item, item.previousElementSibling);
    } else if (btn.dataset.move === "1" && item.nextElementSibling) {
      list.insertBefore(item.nextElementSibling, item);
    }
    btn.focus();
  });
})();
