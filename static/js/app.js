import { api } from "./api.js";
import { qs, qsa } from "./utils.js";
import { initMoviesView, renderMoviesView } from "./movies_view.js";
import { initSeriesView, renderSeriesView } from "./series_view.js";
import { initDuplicatesView, renderDuplicatesView } from "./duplicates_view.js";
import { initTrashView, renderTrashView } from "./trash_view.js";
import { initScanProgress } from "./scan_progress.js";
import { localizeDocument, t } from "./i18n.js";

const RENDERERS = {
  movies: renderMoviesView,
  series: renderSeriesView,
  duplicates: renderDuplicatesView,
  trash: renderTrashView,
};

let activeTab = "movies";

function switchTab(tab) {
  activeTab = tab;
  qsa(".tab-btn", qs("#main-tabs")).forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  qsa(".view").forEach((section) => section.classList.toggle("hidden", section.id !== `view-${tab}`));
  qsa(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${tab}`));
  qs("#view-eyebrow").textContent = t(`view.${tab}.eyebrow`);
  qs("#view-title").textContent = t(`view.${tab}.title`);
  qs("#view-description").textContent = t(`view.${tab}.description`);
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
    banner.textContent = t("mount.retrying");
    scanBtn.disabled = true;
    try {
      const retry = await api.mountRetry();
      if (retry.mounted) {
        banner.classList.add("hidden");
        scanBtn.disabled = false;
      } else {
        banner.textContent = t("mount.error", { error: retry.error || t("error.unknown") });
      }
    } catch (err) {
      banner.textContent = t("mount.error", { error: err.message });
    }
  }
}

function init() {
  localizeDocument();
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
