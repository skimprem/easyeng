// Общие мелочи: CSRF, тема, подтверждения, индикатор долгих операций.
(function () {
  "use strict";

  window.ee = window.ee || {};

  ee.csrf = function () {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  };

  ee.store = {
    get(key, fallback) { try { const v = localStorage.getItem(key); return v === null ? fallback : v; } catch (e) { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* приватный режим */ } },
    remove(key) { try { localStorage.removeItem(key); } catch (e) { /* приватный режим */ } },
  };

  const THEMES = ["light", "sepia", "dark"];
  document.addEventListener("click", (e) => {
    if (!e.target.closest("[data-theme-cycle]")) return;
    const cur = document.documentElement.dataset.theme || "light";
    const next = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
    document.documentElement.dataset.theme = next;
    ee.store.set("ee-theme", next);
  });

  // Закрывать выпадающие меню по клику вне их
  document.addEventListener("click", (e) => {
    document.querySelectorAll("details.menu[open]").forEach((d) => {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });

  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      e.preventDefault();
      return;
    }
    if (form.dataset.busy) {
      const btn = form.querySelector("button:not([type=button])");
      if (btn) { btn.disabled = true; btn.textContent = form.dataset.busy; }
    }
  });
})();
