import { api } from "./api.js";
import { qs, qsa } from "./utils.js";
import { initMoviesView, renderMoviesView } from "./movies_view.js";
import { initSeriesView, renderSeriesView } from "./series_view.js";
import { initDuplicatesView, renderDuplicatesView } from "./duplicates_view.js";
import { initTrashView, renderTrashView } from "./trash_view.js";
import { initScanProgress } from "./scan_progress.js";

const RENDERERS = {
  movies: renderMoviesView,
  series: renderSeriesView,
  duplicates: renderDuplicatesView,
  trash: renderTrashView,
};

let activeTab = "movies";

const VIEW_COPY = {
  movies: ["PELÍCULAS", "Tu colección de películas", "Explora, compara y mantén tu filmoteca perfectamente organizada."],
  series: ["SERIES", "Historias que continúan", "Navega por tus series, temporadas y episodios desde un solo lugar."],
  duplicates: ["DUPLICADOS", "Recupera espacio con criterio", "Compara cada versión y conserva siempre la de mejor calidad."],
  trash: ["PAPELERA", "Nada desaparece por accidente", "Revisa y restaura archivos antes de eliminarlos definitivamente."],
};

function switchTab(tab) {
  activeTab = tab;
  qsa(".tab-btn", qs("#main-tabs")).forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  qsa(".view").forEach((section) => section.classList.toggle("hidden", section.id !== `view-${tab}`));
  qsa(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${tab}`));
  const [eyebrow, title, description] = VIEW_COPY[tab];
  qs("#view-eyebrow").textContent = eyebrow;
  qs("#view-title").textContent = title;
  qs("#view-description").textContent = description;
  RENDERERS[tab]();
}

async function checkMount() {
  const status = await api.mountStatus();
  const banner = qs("#mount-banner");
  const scanBtn = qs("#scan-btn");
  if (status.mounted) {
    banner.classList.add("hidden");
    scanBtn.disabled = false;
  } else {
    banner.classList.remove("hidden");
    banner.textContent = "NAS no montada — reintentando…";
    scanBtn.disabled = true;
    try {
      const retry = await api.mountRetry();
      if (retry.mounted) {
        banner.classList.add("hidden");
        scanBtn.disabled = false;
      } else {
        banner.textContent = `NAS no montada: ${retry.error || "error desconocido"}`;
      }
    } catch (err) {
      banner.textContent = `NAS no montada: ${err.message}`;
    }
  }
}

function init() {
  qsa(".tab-btn", qs("#main-tabs")).forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  initMoviesView();
  initSeriesView();
  initDuplicatesView();
  initTrashView();
  initScanProgress(() => RENDERERS[activeTab]());

  checkMount();
  RENDERERS[activeTab]();
}

init();
