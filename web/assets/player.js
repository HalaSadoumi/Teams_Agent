/* Course player.
 *
 * Loads one course, selected via ?course=<id>, from data/<id>/. Each chapter
 * is its own video file so navigation is instant rather than seeking inside a
 * single long recording. Progress is kept per course in localStorage.
 */

const params = new URLSearchParams(location.search);
const COURSE_ID = params.get("course");
const BASE = `data/${COURSE_ID}`;
const STORAGE_KEY = `s2m-course-progress:${COURSE_ID}`;

let course = null;
let chapters = [];
let quizzes = {};
let current = 0;
let completed = new Set();

/* ---------- helpers ---------- */

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m} min ${String(s).padStart(2, "0")}`;
}

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    completed = new Set(saved.completed || []);
    current = typeof saved.current === "number" ? saved.current : 0;
  } catch {
    /* Fresh start when storage is unavailable or corrupt. */
  }
}

function saveProgress() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ completed: [...completed], current })
    );
  } catch {
    /* Progress is a convenience, not a requirement. */
  }
}

/* ---------- rendering ---------- */

function renderChapterList() {
  const list = document.getElementById("chapter-list");
  list.innerHTML = "";

  chapters.forEach((chapter, index) => {
    const li = document.createElement("li");
    li.className = "chapter-item";
    if (index === current) li.classList.add("active");
    if (completed.has(chapter.id)) li.classList.add("done");

    li.innerHTML = `
      <span class="chapter-num">${completed.has(chapter.id) ? "✓" : index + 1}</span>
      <span>
        <span class="chapter-text">${chapter.title}</span><br>
        <span class="chapter-dur">${formatDuration(chapter.duration)}</span>
      </span>`;
    li.addEventListener("click", () => selectChapter(index));
    list.appendChild(li);
  });
}

function renderProgress() {
  const pct = chapters.length ? Math.round((completed.size / chapters.length) * 100) : 0;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  document.getElementById("progress-label").textContent = `${pct} %`;
}

function renderQuiz(chapterId) {
  const container = document.getElementById("quiz-container");
  const questions = quizzes[chapterId] || [];
  container.innerHTML = "";

  if (!questions.length) {
    container.innerHTML = '<p class="empty">Aucune question pour ce chapitre.</p>';
    return;
  }

  questions.forEach((q, qi) => {
    const multiple = q.correct_letters.length > 1;
    const block = document.createElement("div");
    block.className = "question";

    block.innerHTML = `
      <h4>${qi + 1}. ${q.question}</h4>
      <p class="hint">${multiple ? "Plusieurs réponses possibles" : "Une seule réponse"}</p>
      ${q.options
        .map(
          (o) =>
            `<div class="option" data-letter="${o.letter}">
               <span class="letter">${o.letter}</span><span>${o.text}</span>
             </div>`
        )
        .join("")}
      <button class="btn small check-btn">Valider</button>
      <div class="feedback"></div>`;

    const selected = new Set();
    const optionEls = block.querySelectorAll(".option");
    const feedback = block.querySelector(".feedback");
    const checkBtn = block.querySelector(".check-btn");

    optionEls.forEach((el) => {
      el.addEventListener("click", () => {
        if (checkBtn.disabled) return;
        const letter = el.dataset.letter;
        if (multiple) {
          if (selected.has(letter)) {
            selected.delete(letter);
            el.classList.remove("selected");
          } else {
            selected.add(letter);
            el.classList.add("selected");
          }
        } else {
          selected.clear();
          optionEls.forEach((o) => o.classList.remove("selected"));
          selected.add(letter);
          el.classList.add("selected");
        }
      });
    });

    checkBtn.addEventListener("click", () => {
      if (!selected.size) return;
      const correct = new Set(q.correct_letters);
      const isRight =
        selected.size === correct.size && [...selected].every((l) => correct.has(l));

      optionEls.forEach((el) => {
        const letter = el.dataset.letter;
        el.classList.remove("selected");
        if (correct.has(letter)) el.classList.add("correct");
        else if (selected.has(letter)) el.classList.add("wrong");
      });

      feedback.className = `feedback show ${isRight ? "ok" : "ko"}`;
      feedback.textContent = isRight
        ? `Correct. ${q.explanation}`
        : `Réponse attendue : ${q.correct_letters.join(", ")}. ${q.explanation}`;
      checkBtn.disabled = true;
    });

    container.appendChild(block);
  });
}

function selectChapter(index) {
  current = Math.max(0, Math.min(chapters.length - 1, index));
  const chapter = chapters[current];

  document.getElementById("chapter-title").textContent = chapter.title;
  document.getElementById("chapter-time").textContent =
    `${chapter.timestamp} · ${formatDuration(chapter.duration)}`;
  document.getElementById("chapter-summary").textContent = chapter.summary;

  const points = document.getElementById("chapter-points");
  points.innerHTML = chapter.key_points.length
    ? chapter.key_points.map((p) => `<li>${p}</li>`).join("")
    : '<li class="empty">Aucun point clé.</li>';

  const player = document.getElementById("player");
  player.src = `${BASE}/videos/${chapter.id}.mp4`;
  player.load();

  renderQuiz(chapter.id);
  renderChapterList();

  document.getElementById("prev-btn").disabled = current === 0;
  document.getElementById("next-btn").disabled = current === chapters.length - 1;

  saveProgress();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ---------- init ---------- */

async function init() {
  if (!COURSE_ID) {
    location.replace("index.html");
    return;
  }

  try {
    const [coursesRes, chaptersRes, quizRes] = await Promise.all([
      fetch("data/courses.json"),
      fetch(`${BASE}/course_chapters.json`),
      fetch(`${BASE}/quiz.json`).catch(() => null),
    ]);

    const catalog = await coursesRes.json();
    course = (catalog.courses || []).find((c) => c.id === COURSE_ID) || null;
    chapters = await chaptersRes.json();
    quizzes = quizRes && quizRes.ok ? await quizRes.json() : {};
  } catch {
    document.getElementById("course-meta").textContent =
      "Impossible de charger ce cours.";
    return;
  }

  document.title = course ? `${course.title} — S2M` : "Cours — S2M";
  document.getElementById("course-title").textContent = course ? course.title : "Cours";

  const totalSeconds = chapters.reduce((acc, c) => acc + c.duration, 0);
  document.getElementById("course-meta").textContent =
    `${chapters.length} chapitres · ${Math.round(totalSeconds / 60)} minutes`;

  // The reading tab only appears when a support document was exported.
  if (course && course.pdf) {
    const url = `${BASE}/${course.pdf}`;
    document.getElementById("tab-read").hidden = false;
    document.getElementById("pdf-frame").src = url;
    document.getElementById("pdf-download").href = url;
  }

  loadProgress();
  selectChapter(current);
  renderProgress();

  const player = document.getElementById("player");
  player.addEventListener("timeupdate", () => {
    if (!player.duration) return;
    if (player.currentTime / player.duration > 0.9) {
      const id = chapters[current].id;
      if (!completed.has(id)) {
        completed.add(id);
        saveProgress();
        renderChapterList();
        renderProgress();
      }
    }
  });

  player.addEventListener("ended", () => {
    if (current < chapters.length - 1) selectChapter(current + 1);
  });

  document.getElementById("prev-btn").addEventListener("click", () => selectChapter(current - 1));
  document.getElementById("next-btn").addEventListener("click", () => selectChapter(current + 1));

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.panel).classList.add("active");
    });
  });
}

init();
