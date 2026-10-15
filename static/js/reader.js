// Читалка: перевод по двойному клику, перевод выделенной фразы,
// закрепление перевода над словом, настройки шрифта и позиция чтения.
(function () {
  "use strict";

  const reader = document.getElementById("reader");
  if (!reader) return;
  const pop = document.getElementById("popover");
  const chip = document.getElementById("phrase-chip");
  const srcSel = document.getElementById("src-lang");
  const tgtSel = document.getElementById("tgt-lang");
  const bar = document.getElementById("reader-bar");
  const hint = document.getElementById("reader-hint");
  const lookupUrl = reader.dataset.lookupUrl;
  const WORD_RE = /^[\p{L}\p{M}'’\-]+$/u;

  let current = null; // { range, word, translation }
  let requestSeq = 0;

  // ---------- Направление перевода ----------
  const pairKey = "ee-pair-" + reader.dataset.textId;
  const savedPair = ee.store.get(pairKey, "");
  if (savedPair) {
    const [s, t] = savedPair.split(">");
    if (s) srcSel.value = s;
    if (t) tgtSel.value = t;
  }
  [srcSel, tgtSel].forEach((sel) => sel.addEventListener("change", () => {
    ee.store.set(pairKey, srcSel.value + ">" + tgtSel.value);
  }));

  // ---------- Поиск перевода ----------
  async function lookup(word) {
    const params = new URLSearchParams({ w: word, src: srcSel.value, tgt: tgtSel.value });
    const resp = await fetch(lookupUrl + "?" + params, { headers: { Accept: "application/json" } });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Ошибка " + resp.status);
    return data;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function render(data) {
    const main = pop.querySelector(".pop-main");
    const more = pop.querySelector(".pop-more");
    const details = pop.querySelector(".pop-details");
    const withTr = data.results.filter((r) => r.translations && r.translations.length);
    const first = withTr[0];

    if (first) {
      current.translation = first.translations[0];
      current.headword = first.headword;
      main.innerHTML =
        '<div class="tr-opts">' + options(first.translations, first.headword) + "</div>" +
        '<span class="src">' + escapeHtml(first.source) +
        (first.headword.toLowerCase() !== data.word.toLowerCase() ? " · " + escapeHtml(first.headword) : "") + "</span>";
    } else if (data.results.length) {
      current.translation = null;
      main.innerHTML = '<span class="none">Перевода нет, но есть толкование ниже</span>';
    } else {
      current.translation = null;
      const err = data.errors.length ? " (онлайн-словари недоступны)" : "";
      main.innerHTML = '<span class="none">Не найдено' + err + "</span>";
    }

    // Подробные статьи: HTML уже санитизирован на сервере (nh3)
    const sections = data.results
      .filter((r) => r.html || (r !== first && r.translations.length))
      .map((r) => "<section><h4>" + escapeHtml(r.source) + "</h4>" +
        (r !== first && r.translations.length ? '<div class="tr-opts small">' + options(r.translations, r.headword) + "</div>" : "") +
        (r.html || "") + "</section>");
    details.innerHTML = sections.join("");
    numberOptions();
    setStar(data.vocab);
    more.hidden = sections.length === 0;
    more.open = !first && sections.length > 0;
    place(current.range);
  }

  // Варианты перевода — кнопки: клик закрепляет выбранный вариант над словом
  function options(list, headword) {
    return list.map((t) => '<button type="button" class="tr-opt" data-tr="' + escapeHtml(t) +
      '" data-hw="' + escapeHtml(headword) + '">' + escapeHtml(t) + "</button>").join("");
  }

  function numberOptions() {
    pop.querySelectorAll(".tr-opt").forEach((b, i) => {
      b.title = i < 9 ? "Закрепить этот вариант (клавиша " + (i + 1) + ")" : "Закрепить этот вариант";
    });
  }

  // ---------- Всплывающее окно ----------
  function place(range) {
    const rects = range.getClientRects();
    const rect = rects.length ? rects[0] : range.getBoundingClientRect();
    pop.hidden = false;
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    const margin = 10;
    const centerX = rect.left + rect.width / 2;
    let left = Math.min(Math.max(centerX - pw / 2, margin), document.documentElement.clientWidth - pw - margin);
    const barH = bar.classList.contains("hidden") ? 0 : bar.offsetHeight;
    const above = rect.top - ph - 12 > barH;
    const top = above ? rect.top - ph - 10 : rect.bottom + 10;
    pop.classList.toggle("above", above);
    pop.classList.toggle("below", !above);
    pop.style.left = left + window.scrollX + "px";
    pop.style.top = top + window.scrollY + "px";
    pop.style.setProperty("--arrow-x", Math.min(Math.max(centerX - left, 14), pw - 14) + "px");
  }

  async function show(range, word) {
    hideChip();
    const seq = ++requestSeq;
    current = { range: range.cloneRange(), word, translation: null, headword: null };
    setStar(null);
    pop.querySelector(".pop-word").textContent = word;
    pop.querySelector(".pop-main").innerHTML = '<span class="spinner"></span>';
    pop.querySelector(".pop-more").hidden = true;
    place(current.range);
    dismissHint();
    try {
      const data = await lookup(word);
      if (seq === requestSeq) render(data);
    } catch (e) {
      if (seq === requestSeq) {
        pop.querySelector(".pop-main").innerHTML = '<span class="none">' + escapeHtml(e.message) + "</span>";
        place(current.range);
      }
    }
  }

  function hide() {
    pop.hidden = true;
    current = null;
    requestSeq++;
  }

  // ---------- Закреплённые над словами переводы ----------
  // Хранятся на сервере как [{o, w, t}]: o — смещение слова в тексте статьи
  // (без текста самих переводов), w — слово, t — перевод. Если текст отредактировали
  // и по смещению слова уже нет, ищем ближайшее вхождение слова.
  const content = document.getElementById("reader-content");
  const resetBtn = document.getElementById("reset-glosses");
  const resetDialog = document.getElementById("reset-dialog");
  const saveStatus = document.getElementById("save-status");

  function makeGloss(translation) {
    const ruby = document.createElement("ruby");
    ruby.className = "gloss";
    ruby.title = "Клик — убрать перевод";
    ruby.dataset.t = translation;
    return ruby;
  }

  function wrap(range, translation) {
    const ruby = makeGloss(translation);
    try {
      range.surroundContents(ruby);
    } catch (e) {
      return null; // диапазон пересекает границы элементов
    }
    const rt = document.createElement("rt");
    rt.textContent = translation;
    ruby.appendChild(rt);
    return ruby;
  }

  function unwrap(ruby) {
    ruby.querySelectorAll("rt").forEach((rt) => rt.remove());
    ruby.replaceWith(...ruby.childNodes);
  }

  // Текстовые узлы статьи по порядку, без текста переводов (<rt>)
  function textNodes() {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest("rt") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    const nodes = [];
    let pos = 0, n;
    while ((n = walker.nextNode())) {
      nodes.push({ node: n, start: pos });
      pos += n.length;
    }
    return nodes;
  }

  function serialize() {
    const result = [];
    for (const { node, start } of textNodes()) {
      const ruby = node.parentElement.closest("ruby.gloss");
      if (ruby && !result.some((g) => g.el === ruby)) {
        const word = [...ruby.childNodes].filter((c) => c.nodeName !== "RT").map((c) => c.textContent).join("");
        result.push({ el: ruby, o: start, w: word, t: ruby.dataset.t || ruby.querySelector("rt").textContent });
      }
    }
    return result.map(({ o, w, t }) => ({ o, w, t }));
  }

  function locate(nodes, pos, preferEnd) {
    // Узел, содержащий позицию pos; на границе узлов для конца диапазона берём предыдущий
    let lo = 0, hi = nodes.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (nodes[mid].start < pos || (!preferEnd && nodes[mid].start === pos)) lo = mid; else hi = mid - 1;
    }
    return nodes[lo];
  }

  function restore(glosses) {
    if (!glosses.length) return 0;
    const nodes = textNodes();
    if (!nodes.length) return glosses.length;
    const full = nodes.map((x) => x.node.data).join("");

    // 1. Находим позиции по порядку. delta — сдвиг текста после правок, вычисленный
    //    по предыдущему найденному слову: вставка абзаца в начало сдвигает все следующие.
    const found = [];
    let delta = 0, lastEnd = 0;
    for (const g of glosses.slice().sort((a, b) => a.o - b.o)) {
      const guess = g.o + delta;
      let pos = full.substr(guess, g.w.length) === g.w ? guess
        : full.substr(g.o, g.w.length) === g.w ? g.o
        : nearest(full, g.w, guess, lastEnd);
      if (pos < lastEnd) continue; // не нашли или пересекается с предыдущим
      found.push({ pos, g });
      delta = pos - g.o;
      lastEnd = pos + g.w.length;
    }

    // 2. Оборачиваем с конца к началу: обёртка дальнего слова не портит узлы ближних
    let restored = 0;
    for (const { pos, g } of found.reverse()) {
      const a = locate(nodes, pos, false), b = locate(nodes, pos + g.w.length, true);
      const range = document.createRange();
      range.setStart(a.node, pos - a.start);
      range.setEnd(b.node, pos + g.w.length - b.start);
      if (wrap(range, g.t)) restored++;
    }
    return glosses.length - restored;
  }

  function nearest(full, word, from, min) {
    const after = full.indexOf(word, Math.max(from, min));
    const before = from > min ? full.lastIndexOf(word, from) : -1;
    if (before < min) return after; // -1, если слова нет нигде
    if (after < 0) return before;
    return from - before <= after - from ? before : after;
  }

  // ---------- Автосохранение ----------
  // Несохранённое состояние сначала пишется в localStorage: если страницу закрыли
  // или обновили раньше, чем сервер ответил (или пропала сеть), при следующем
  // открытии берётся оно и досылается на сервер.
  const pendingKey = "ee-glosses-pending-" + reader.dataset.textId;
  let saveTimer = null, savePending = false, fadeTimer = null;

  function setStatus(text, cls) {
    clearTimeout(fadeTimer);
    saveStatus.textContent = text;
    saveStatus.className = "save-status " + (cls || "");
    if (cls === "ok") fadeTimer = setTimeout(() => saveStatus.classList.add("fade"), 1500);
  }

  function updateResetButton() {
    const n = content.querySelectorAll("ruby.gloss").length;
    resetBtn.hidden = n === 0;
    resetBtn.querySelector(".count").textContent = n;
    resetDialog.querySelector(".count").textContent = n;
  }

  function scheduleSave() {
    updateResetButton();
    ee.store.set(pendingKey, JSON.stringify(serialize()));
    savePending = true;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, 600);
  }

  async function saveNow(keepalive) {
    clearTimeout(saveTimer);
    if (!savePending) return;
    savePending = false;
    setStatus("Сохраняю…");
    try {
      const resp = await fetch(reader.dataset.glossesUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": ee.csrf() },
        body: JSON.stringify({ glosses: serialize() }),
        keepalive: keepalive === true,
      });
      if (!resp.ok) throw new Error(resp.status);
      if (!savePending) ee.store.remove(pendingKey); // за время запроса новых изменений не было
      setStatus("✓ Сохранено", "ok");
    } catch (e) {
      savePending = true; // попробуем снова при следующем изменении или уходе со страницы
      setStatus("Не сохранено", "error");
    }
  }

  window.addEventListener("pagehide", () => saveNow(true));
  document.addEventListener("visibilitychange", () => { if (document.hidden) saveNow(true); });

  function pin(translation, headword) {
    translation = translation || (current && current.translation);
    if (!current || !translation) return;
    const context = sentenceAround(current.range);
    if (reader.dataset.autoAdd === "1") addToVocab(translation, headword, context);
    if (!wrap(current.range, translation)) return;
    window.getSelection().removeAllRanges();
    hide();
    scheduleSave();
  }

  reader.addEventListener("click", (e) => {
    const ruby = e.target.closest("ruby.gloss");
    if (!ruby || e.detail > 1) return;
    unwrap(ruby);
    content.normalize();
    scheduleSave();
  });

  // ---------- Сброс с подтверждением ----------
  resetBtn.addEventListener("click", () => {
    hide();
    resetDialog.returnValue = "";
    resetDialog.showModal();
  });
  resetDialog.addEventListener("close", () => {
    if (resetDialog.returnValue !== "reset") return;
    content.querySelectorAll("ruby.gloss").forEach(unwrap);
    content.normalize();
    scheduleSave();
    saveNow();
  });
  resetDialog.addEventListener("click", (e) => { if (e.target === resetDialog) resetDialog.close("cancel"); });

  // Восстановление при открытии текста
  let pending = null;
  try { pending = JSON.parse(ee.store.get(pendingKey, "null")); } catch (e) { /* испорченная запись */ }
  const lost = restore(pending || JSON.parse(document.getElementById("glosses-data").textContent || "[]"));
  updateResetButton();
  // pending — досылаем несохранённое; lost — убираем переводы, чьих слов больше нет в тексте
  if (pending || lost) scheduleSave();

  // ---------- Личный словарик ----------
  const star = pop.querySelector("[data-add]");

  function setStar(card) {
    star.classList.toggle("on", !!card);
    star.textContent = card ? "★" : "☆";
    star.title = card ? "В словарике: " + card.translation : "В словарик (S)";
  }

  // Предложение вокруг слова — пригодится на карточке как контекст
  function sentenceAround(range) {
    const block = range.startContainer.parentElement.closest("p, li, blockquote, h1, h2, h3, h4, td") || content;
    const clean = (frag) => {
      frag.querySelectorAll("rt").forEach((rt) => rt.remove());
      return frag.textContent.replace(/\s+/g, " ");
    };
    const before = document.createRange();
    before.setStart(block, 0);
    before.setEnd(range.startContainer, range.startOffset);
    const pos = clean(before.cloneContents()).trimStart().length;
    const text = clean(block.cloneNode(true)).trim();
    const sentences = text.match(/[^.!?…]+[.!?…]*["»”’)]*\s*/g) || [text];
    let acc = 0;
    for (const sentence of sentences) {
      if (acc + sentence.length > pos) return clip(sentence.trim(), pos - acc);
      acc += sentence.length;
    }
    return clip(text, pos);
  }

  // Длинное предложение обрезаем до окна вокруг слова — на карточке нужен короткий контекст
  function clip(sentence, at, radius = 110) {
    if (sentence.length <= radius * 2) return sentence;
    let start = Math.max(0, at - radius), end = Math.min(sentence.length, at + radius);
    if (start > 0) start = sentence.indexOf(" ", start) + 1;
    if (end < sentence.length) end = sentence.lastIndexOf(" ", end);
    return (start > 0 ? "… " : "") + sentence.slice(start, end).trim() + (end < sentence.length ? " …" : "");
  }

  async function addToVocab(translation, headword, context) {
    if (!current) return;
    translation = translation || current.translation;
    if (!translation) return;
    const word = headword || current.headword || current.word;
    try {
      const resp = await fetch(reader.dataset.vocabUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": ee.csrf() },
        body: JSON.stringify({
          word, translation, form: current.word, src: srcSel.value, tgt: tgtSel.value,
          context: context || sentenceAround(current.range), text_id: reader.dataset.textId,
        }),
      });
      if (!resp.ok) throw new Error(resp.status);
      const card = await resp.json();
      if (current) setStar(card);
      setStatus(card.created ? "★ «" + card.word + "» в словарике" : "★ уже в словарике", "ok");
    } catch (e) {
      setStatus("Не удалось добавить в словарик", "error");
    }
  }

  // ---------- Выделение слова / фразы ----------
  function selectionInReader() {
    const sel = window.getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return null;
    const range = sel.getRangeAt(0);
    if (!reader.contains(range.commonAncestorContainer)) return null;
    return { sel, range, text: sel.toString().replace(/\s+/g, " ").trim() };
  }

  function trimRange(range) {
    // Firefox/Windows при двойном клике захватывают пробел после слова
    const r = range.cloneRange();
    if (r.endContainer.nodeType === Node.TEXT_NODE) {
      while (r.endOffset > r.startOffset && /[\s.,;:!?"»”)]/.test(r.endContainer.textContent[r.endOffset - 1] || "")) {
        r.setEnd(r.endContainer, r.endOffset - 1);
      }
    }
    return r;
  }

  reader.addEventListener("dblclick", (e) => {
    if (e.target.closest("ruby.gloss")) return;
    const s = selectionInReader();
    if (!s) return;
    const range = trimRange(s.range);
    const word = range.toString().trim().replace(/^['’\-]+|['’\-]+$/g, "");
    if (!word || !WORD_RE.test(word) || word.length > 40) return;
    s.sel.removeAllRanges();
    s.sel.addRange(range);
    show(range, word);
  });

  function hideChip() { chip.hidden = true; }

  document.addEventListener("selectionchange", () => {
    clearTimeout(document._chipTimer);
    document._chipTimer = setTimeout(() => {
      const s = selectionInReader();
      if (!s || !/\s/.test(s.text) || s.text.length > 200 || s.text.split(" ").length > 12) return hideChip();
      const rect = s.range.getBoundingClientRect();
      chip.hidden = false;
      chip.style.left = rect.left + rect.width / 2 + window.scrollX + "px";
      chip.style.top = rect.top + window.scrollY - chip.offsetHeight - 8 + "px";
    }, 250);
  });

  chip.addEventListener("mousedown", (e) => e.preventDefault()); // не сбрасывать выделение
  chip.addEventListener("click", () => {
    const s = selectionInReader();
    if (s) show(s.range, s.text);
  });

  pop.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) hide();
    if (e.target.closest("[data-pin]")) pin();
    if (e.target.closest("[data-add]")) addToVocab();
    const opt = e.target.closest(".tr-opt");
    if (opt) pin(opt.dataset.tr, opt.dataset.hw);
  });

  document.addEventListener("mousedown", (e) => {
    if (!pop.hidden && !pop.contains(e.target) && !reader.contains(e.target)) hide();
  });
  reader.addEventListener("mousedown", (e) => { if (!pop.hidden && e.detail === 1) hide(); });
  document.addEventListener("keydown", (e) => {
    if (resetDialog.open) return;
    if (e.key === "Escape") { hide(); hideChip(); }
    if (pop.hidden || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "p") pin();
    if (e.key === "s") addToVocab();
    if (/^[1-9]$/.test(e.key)) {
      const opt = pop.querySelectorAll(".tr-opt")[parseInt(e.key, 10) - 1];
      if (opt) pin(opt.dataset.tr, opt.dataset.hw);
    }
  });
  window.addEventListener("resize", () => { if (current) place(current.range); });

  // ---------- Подсказка для новичка ----------
  function dismissHint() {
    hint.classList.add("gone");
    ee.store.set("ee-hint-seen", "1");
  }
  if (ee.store.get("ee-hint-seen", "")) hint.classList.add("gone");
  else setTimeout(dismissHint, 9000);

  // ---------- Размер шрифта ----------
  const root = document.documentElement;
  function applyFont(size) {
    size = Math.min(Math.max(size, 14), 32);
    root.style.setProperty("--read-size", size + "px");
    ee.store.set("ee-font", String(size));
    return size;
  }
  let fontSize = applyFont(parseInt(ee.store.get("ee-font", ""), 10) || parseInt(getComputedStyle(root).getPropertyValue("--read-size"), 10) || 20);
  document.querySelectorAll("[data-font]").forEach((b) => b.addEventListener("click", () => {
    fontSize = applyFont(fontSize + 2 * parseInt(b.dataset.font, 10));
    if (current) place(current.range);
  }));

  // ---------- Панель: прячется при чтении, появляется при прокрутке вверх ----------
  let lastY = window.scrollY;
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    bar.classList.toggle("scrolled", y > 10);
    bar.classList.toggle("hidden", y > lastY && y > 200 && pop.hidden);
    lastY = y;
    hideChip();
    saveProgressSoon();
  }, { passive: true });

  // ---------- Позиция чтения ----------
  function progress() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    return max > 0 ? Math.min(window.scrollY / max, 1) : 1;
  }
  let progressTimer = null;
  function saveProgressSoon() {
    clearTimeout(progressTimer);
    progressTimer = setTimeout(() => {
      fetch(reader.dataset.progressUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": ee.csrf() },
        body: JSON.stringify({ progress: progress() }),
        keepalive: true,
      }).catch(() => {});
    }, 1500);
  }
  const saved = parseFloat(reader.dataset.progress) || 0;
  if (saved > 0.01 && saved < 0.999 && !location.hash) {
    window.addEventListener("load", () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo(0, saved * max);
    });
  }
})();
