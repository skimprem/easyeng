// Повторение карточек: свайп вправо — знаю, влево — не знаю (слово вернётся
// в этой же сессии и уйдёт на заучивание). Сначала нужно открыть карточку —
// ответить «вслепую» нельзя, это защищает от угадывания.
(function () {
  "use strict";

  const root = document.getElementById("review");
  if (!root) return;

  const $ = (id) => document.getElementById(id);
  const cardEl = $("card"), front = $("front"), back = $("back"), hint = $("hint"), badge = $("badge");
  const btnRight = $("btn-right"), btnWrong = $("btn-wrong"), dirSel = $("direction");
  const AGAIN_GAP = 3;          // через сколько карточек показать снова слово «не знаю»
  const SWIPE_THRESHOLD = 110;  // px

  const total = JSON.parse($("cards-data").textContent);
  const queue = total.map((c) => Object.assign({}, c));
  const result = { right: 0, wrong: new Map(), finished: 0 };
  let card = null, flipped = false, side = "forward", busy = false;

  // ---------- Направление ----------
  dirSel.value = ee.store.get("ee-review-dir", "forward");
  dirSel.addEventListener("change", () => {
    ee.store.set("ee-review-dir", dirSel.value);
    if (card) show(card);
  });

  // ---------- Отрисовка ----------
  function esc(s) {
    return (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function markWord(context, c, mask) {
    let html = esc(context);
    const terms = [c.form, c.word].filter(Boolean).sort((a, b) => b.length - a.length);
    for (const t of terms) {
      const re = new RegExp("(?<![\\p{L}])(" + esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![\\p{L}])", "giu");
      html = html.replace(re, mask ? '<span class="blank">＿＿＿</span>' : "<mark>$1</mark>");
    }
    return html;
  }

  function wordHtml(c) {
    const form = c.form && c.form.toLowerCase() !== c.word.toLowerCase() ? '<div class="form">' + esc(c.form) + "</div>" : "";
    return '<div class="word">' + esc(c.word) + "</div>" + form;
  }

  function show(c) {
    side = dirSel.value === "mixed" ? (Math.random() < 0.5 ? "forward" : "reverse") : dirSel.value;
    flipped = false;
    cardEl.classList.remove("flipped");
    back.hidden = true;
    const ctx = c.context ? '<p class="context">' + markWord(c.context, c, side === "reverse") + "</p>" : "";
    if (side === "forward") {
      front.innerHTML = wordHtml(c);
      back.innerHTML = '<div class="translation">' + esc(c.translation) + "</div>" + (c.context ? '<p class="context">' + markWord(c.context, c) + "</p>" : "");
    } else {
      front.innerHTML = '<div class="translation">' + esc(c.translation) + "</div>" + ctx;
      back.innerHTML = wordHtml(c) + (c.context ? '<p class="context">' + markWord(c.context, c) + "</p>" : "");
    }
    badge.hidden = !(c.early || c.again);
    badge.textContent = c.again ? "Ещё раз" : "Проверка";
    badge.className = "card-badge " + (c.again ? "again" : "check");
    hint.textContent = "Нажмите, чтобы проверить себя · пробел";
    btnRight.disabled = btnWrong.disabled = true;
    updateProgress();
  }

  function flip() {
    if (!card || flipped) return;
    flipped = true;
    cardEl.classList.add("flipped");
    back.hidden = false;
    hint.textContent = "← не знаю  ·  знаю →";
    btnRight.disabled = btnWrong.disabled = false;
  }

  function updateProgress() {
    const n = total.length;
    $("progress-fill").style.width = (n ? (result.finished / n) * 100 : 100) + "%";
    $("count").textContent = Math.min(result.finished + 1, n) + " / " + n;
  }

  // ---------- Ответ ----------
  function sendAnswer(c, correct) {
    const url = root.dataset.answerUrl.replace("/0/", "/" + c.id + "/");
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": ee.csrf() },
      body: JSON.stringify({ correct, early: !!c.early }),
    }).then((r) => { if (!r.ok) throw new Error(r.status); })
      .catch(() => { $("count").textContent = "⚠ ответ не сохранён"; });
  }

  function answer(correct) {
    if (!card || busy) return;
    if (!flipped) { flip(); return; }
    busy = true;
    const c = card;
    sendAnswer(c, correct);
    if (correct) {
      if (!c.again) result.right++;
      result.finished++;
    } else {
      result.wrong.set(c.id, c);
      // Неверно — карточка возвращается в эту же сессию через несколько слов.
      // Слово теперь «на заучивании», поэтому следующий ответ — уже не внеплановая проверка.
      queue.splice(Math.min(AGAIN_GAP, queue.length), 0, Object.assign({}, c, { again: true, early: false }));
    }
    flyOut(correct ? 1 : -1, next);
  }

  function flyOut(dir, then) {
    cardEl.style.transition = "transform .28s ease-in, opacity .28s ease-in";
    cardEl.style.transform = `translateX(${dir * 120}vw) rotate(${dir * 18}deg)`;
    cardEl.style.opacity = "0";
    setTimeout(() => {
      cardEl.style.transition = "none";
      cardEl.style.transform = "";
      cardEl.style.opacity = "";
      cardEl.classList.remove("drag-left", "drag-right");
      cardEl.style.setProperty("--swipe", 0);
      busy = false;
      then();
    }, 280);
  }

  function next() {
    card = queue.shift() || null;
    if (!card) return finish();
    cardEl.classList.remove("enter");
    void cardEl.offsetWidth; // перезапуск анимации появления
    cardEl.classList.add("enter");
    show(card);
  }

  function finish() {
    $("stack").hidden = true;
    document.querySelector(".answer-row").hidden = true;
    document.querySelector(".review-bar select").hidden = true;
    updateProgress();
    $("count").textContent = "";
    const done = $("done");
    done.hidden = false;
    if (!total.length) {
      const empty = root.dataset.totalCards === "0";
      $("done-title").textContent = empty ? "Словарик пока пуст" : "Всё повторено 🎉";
      $("done-text").textContent = empty
        ? "Добавляйте слова во время чтения — кнопкой ☆ или закрепляя перевод над словом."
        : "Сейчас повторять нечего." + (root.dataset.nextDue ? " Следующее повторение — " + root.dataset.nextDue + "." : "") +
          " Можно проверить себя на случайных словах.";
      if (empty) done.querySelector(".btn-primary").hidden = true;
      return;
    }
    $("done-title").textContent = "Готово!";
    $("done-text").textContent = "Знал сразу: " + result.right + " из " + total.length +
      (result.wrong.size ? ". На заучивание: " + result.wrong.size + "." : ". Отличный результат!");
    $("done-words").innerHTML = [...result.wrong.values()]
      .map((c) => "<li><b>" + esc(c.word) + "</b> — " + esc(c.translation) + "</li>").join("");
  }

  // ---------- Свайп ----------
  let startX = null, dx = 0, pointerId = null;
  cardEl.addEventListener("pointerdown", (e) => {
    if (busy || e.button !== 0) return;
    startX = e.clientX; dx = 0; pointerId = e.pointerId;
    cardEl.setPointerCapture(pointerId);
    cardEl.style.transition = "none";
  });
  cardEl.addEventListener("pointermove", (e) => {
    if (startX === null || e.pointerId !== pointerId) return;
    dx = e.clientX - startX;
    cardEl.style.transform = `translateX(${dx}px) rotate(${dx / 18}deg)`;
    const k = Math.min(Math.abs(dx) / SWIPE_THRESHOLD, 1);
    cardEl.style.setProperty("--swipe", flipped ? k : k * 0.3);
    cardEl.classList.toggle("drag-right", dx > 0);
    cardEl.classList.toggle("drag-left", dx < 0);
  });
  function release() {
    if (startX === null) return;
    startX = null;
    if (Math.abs(dx) < 8) {           // тап
      snapBack();
      flip();
    } else if (flipped && Math.abs(dx) >= SWIPE_THRESHOLD) {
      answer(dx > 0);
    } else {
      snapBack();
      if (!flipped && Math.abs(dx) >= SWIPE_THRESHOLD) flip(); // сначала проверь себя
    }
  }
  function snapBack() {
    cardEl.style.transition = "transform .2s ease-out";
    cardEl.style.transform = "";
    cardEl.style.setProperty("--swipe", 0);
    cardEl.classList.remove("drag-left", "drag-right");
  }
  cardEl.addEventListener("pointerup", release);
  cardEl.addEventListener("pointercancel", () => { startX = null; snapBack(); });

  btnRight.addEventListener("click", () => answer(true));
  btnWrong.addEventListener("click", () => answer(false));

  // ---------- Произношение ----------
  const speakBtn = $("btn-speak");
  if (!("speechSynthesis" in window)) speakBtn.hidden = true;
  function speak() {
    if (!card || !("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance(card.word);
    u.lang = card.src;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }
  speakBtn.addEventListener("click", speak);

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "SELECT" || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); }
    if (e.key === "ArrowRight") { e.preventDefault(); answer(true); }
    if (e.key === "ArrowLeft") { e.preventDefault(); answer(false); }
    if (e.key === "v") speak();
  });

  next();
})();
