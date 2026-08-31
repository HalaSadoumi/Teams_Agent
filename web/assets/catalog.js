/* Course catalog: lists every course the pipeline has exported.
 * Reads data/courses.json, which web_export.py keeps up to date. */

const STORAGE_PREFIX = "s2m-course-progress:";

function progressFor(courseId, chapterCount) {
  if (!chapterCount) return 0;
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + courseId);
    if (!raw) return 0;
    const done = (JSON.parse(raw).completed || []).length;
    return Math.round((done / chapterCount) * 100);
  } catch {
    return 0;
  }
}

function courseCard(course) {
  const pct = progressFor(course.id, course.chapters);
  const thumb = course.thumbnail
    ? `<img src="data/${course.id}/${course.thumbnail}" alt="" />`
    : '<span class="placeholder">▶</span>';

  const pdfButton = course.pdf
    ? `<a class="btn small" href="data/${course.id}/${course.pdf}" target="_blank" rel="noopener">Support PDF</a>`
    : "";

  return `
    <article class="course-card">
      <div class="course-thumb">${thumb}</div>
      <div class="course-body">
        <h3>${course.title}</h3>
        <p>${course.description || ""}</p>
        <div class="course-stats">
          <span class="stat"><strong>${course.chapters}</strong> chapitres</span>
          <span class="stat"><strong>${course.duration_minutes}</strong> min</span>
          ${course.questions ? `<span class="stat"><strong>${course.questions}</strong> questions</span>` : ""}
          ${pct ? `<span class="stat"><strong>${pct}%</strong> suivi</span>` : ""}
        </div>
        <div class="course-actions">
          <a class="btn primary" href="course.html?course=${encodeURIComponent(course.id)}">
            ${pct ? "Reprendre" : "Commencer"}
          </a>
          ${pdfButton}
        </div>
      </div>
    </article>`;
}

async function init() {
  const root = document.getElementById("catalog");
  try {
    const response = await fetch("data/courses.json");
    if (!response.ok) throw new Error("catalogue indisponible");
    const { courses } = await response.json();

    if (!courses || !courses.length) {
      root.innerHTML = '<p class="muted">Aucune formation disponible pour le moment.</p>';
      return;
    }
    root.innerHTML = courses.map(courseCard).join("");
  } catch {
    root.innerHTML =
      '<p class="muted">Impossible de charger le catalogue. Lancez un serveur local depuis le dossier <code>web/</code>.</p>';
  }
}

init();
