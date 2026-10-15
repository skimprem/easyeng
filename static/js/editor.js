// Markdown-редактор: панель кнопок, живой предпросмотр, Ctrl+S.
(function () {
  "use strict";

  const form = document.getElementById("editor");
  if (!form) return;
  const ta = form.querySelector("textarea");
  const preview = document.getElementById("preview");
  const panes = form.querySelector(".editor-panes");
  let dirty = false;

  // ---------- Предпросмотр ----------
  let timer = null, seq = 0;
  async function refresh() {
    const my = ++seq;
    const body = new URLSearchParams({ content: ta.value });
    const resp = await fetch(form.dataset.previewUrl, {
      method: "POST", headers: { "X-CSRFToken": ee.csrf() }, body,
    });
    if (resp.ok && my === seq) preview.innerHTML = await resp.text(); // HTML санитизирован на сервере
  }
  ta.addEventListener("input", () => {
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(refresh, 400);
  });
  refresh();

  // Синхронная прокрутка
  ta.addEventListener("scroll", () => {
    const k = ta.scrollTop / Math.max(ta.scrollHeight - ta.clientHeight, 1);
    preview.scrollTop = k * (preview.scrollHeight - preview.clientHeight);
  });

  // ---------- Вкладки (на телефоне) ----------
  form.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
    form.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("active", x === b));
    panes.classList.toggle("show-preview", b.dataset.tab === "preview");
  }));

  // ---------- Кнопки разметки ----------
  function wrap(before, after, placeholder) {
    const { selectionStart: s, selectionEnd: e, value } = ta;
    const selected = value.slice(s, e) || placeholder;
    ta.setRangeText(before + selected + after, s, e, "end");
    ta.setSelectionRange(s + before.length, s + before.length + selected.length);
  }
  function prefixLines(prefix) {
    const { selectionStart: s, selectionEnd: e, value } = ta;
    const start = value.lastIndexOf("\n", s - 1) + 1;
    const block = value.slice(start, e);
    ta.setRangeText(block.split("\n").map((l) => prefix + l).join("\n"), start, e, "end");
  }
  const actions = {
    bold: () => wrap("**", "**", "текст"),
    italic: () => wrap("_", "_", "текст"),
    heading: () => prefixLines("## "),
    quote: () => prefixLines("> "),
    list: () => prefixLines("- "),
    link: () => wrap("[", "](https://)", "ссылка"),
    hr: () => wrap("\n\n---\n\n", "", ""),
  };
  form.querySelectorAll("[data-md]").forEach((b) => b.addEventListener("click", () => {
    ta.focus();
    actions[b.dataset.md]();
    ta.dispatchEvent(new Event("input"));
  }));

  document.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    const k = e.key.toLowerCase();
    if (k === "s") { e.preventDefault(); dirty = false; form.requestSubmit(); }
    if (document.activeElement === ta && (k === "b" || k === "i")) {
      e.preventDefault();
      actions[k === "b" ? "bold" : "italic"]();
      ta.dispatchEvent(new Event("input"));
    }
  });

  form.addEventListener("submit", () => { dirty = false; });
  window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });
})();
