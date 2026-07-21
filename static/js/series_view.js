import { api } from "./api.js";
import { el, qs, formatBytes } from "./utils.js";
import { confirmModal } from "./modal.js";

let cachedShows = [];

async function trashEpisode(episode, onDone) {
  const confirmed = await confirmModal({
    title: "Mover a la papelera",
    danger: true,
    confirmLabel: "Mover a papelera",
    bodyNode: el("div", {}, [
      el("p", {}, episode.filename),
      el("p", {}, `Tamaño: ${formatBytes(episode.size_bytes)}`),
      el("p", {}, `Vídeo: ${episode.video_codec || "—"} ${episode.width ? `${episode.width}x${episode.height}` : ""}`),
    ]),
  });
  if (!confirmed) return;
  await api.trashMove([episode.id]);
  onDone();
}

async function trashSeriesSelection(show, { scope = "show", season = null } = {}) {
  const isWholeShow = scope === "show";
  const selectedSeason = isWholeShow
    ? null
    : show.seasons.find((item) => item.season === season);
  const episodeCount = isWholeShow
    ? show.seasons.reduce((total, item) => total + item.episode_count, 0)
    : selectedSeason?.episode_count || 0;
  const totalSize = isWholeShow ? show.total_size : selectedSeason?.total_size;
  const selectionLabel = isWholeShow
    ? `la serie completa “${show.show}”`
    : season == null
      ? `los episodios sin temporada identificada de “${show.show}”`
      : `la temporada ${String(season).padStart(2, "0")} de “${show.show}”`;

  const confirmed = await confirmModal({
    title: isWholeShow ? "Mover serie a la papelera" : "Mover temporada a la papelera",
    danger: true,
    confirmLabel: "Mover a papelera",
    bodyNode: el("div", {}, [
      el("p", {}, `Se moverá ${selectionLabel} a la papelera de la NAS.`),
      el("p", {}, "Los episodios podrán restaurarse individualmente desde la papelera."),
      el("div", { class: "member-tags" }, [
        el("span", { class: "badge badge-danger" }, `${episodeCount} episodios`),
        el("span", { class: "badge" }, formatBytes(totalSize)),
      ]),
    ]),
  });
  if (!confirmed) return;

  const result = await api.trashMoveSeries(show.show, scope, season);
  if (result.failed) {
    window.alert(
      `${result.moved} de ${result.selected} archivos se movieron a la papelera. ` +
      `${result.failed} no pudieron moverse.`
    );
  }
  await renderSeriesView();
}

async function renderSeasonPanel(panelEl, show, season) {
  panelEl.innerHTML = '<div class="empty-state">Cargando…</div>';
  const episodes = await api.seasonDetail(show, season);

  const byRelease = new Map();
  episodes.forEach((ep) => {
    if (!byRelease.has(ep.dir_path)) byRelease.set(ep.dir_path, []);
    byRelease.get(ep.dir_path).push(ep);
  });

  panelEl.innerHTML = "";
  for (const [dirPath, eps] of byRelease.entries()) {
    const releaseName = dirPath.split("/").pop();
    panelEl.appendChild(el("div", { class: "toolbar-info", style: "margin: 8px 0 4px;" }, releaseName));
    const table = el("table", { class: "data-table" }, [
      el("thead", {}, el("tr", {}, [el("th", {}, "Episodio"), el("th", {}, "Tamaño"), el("th", {}, "Vídeo"), el("th", {}, "")])),
    ]);
    const tbody = el("tbody");
    eps
      .sort((a, b) => (a.episode_start || 0) - (b.episode_start || 0))
      .forEach((ep) => {
        tbody.appendChild(
          el("tr", {}, [
            el("td", { class: "filename-cell" }, ep.filename),
            el("td", {}, formatBytes(ep.size_bytes)),
            el("td", {}, `${ep.video_codec || "—"} ${ep.height ? ep.height + "p" : ""}`),
            el(
              "td",
              {},
              el("button", { class: "btn btn-danger btn-sm", onclick: () => trashEpisode(ep, renderSeriesView) }, "Papelera")
            ),
          ])
        );
      });
    table.appendChild(tbody);
    panelEl.appendChild(el("div", { class: "card table-scroll" }, table));
  }
}

function renderShowCard(show) {
  const details = el("details", { class: "show-card card" });
  details.appendChild(
    el("summary", {}, [
      el("span", { class: "show-name" }, show.show),
      el("span", { class: "badge" }, `${show.seasons.length} temporadas`),
      el("span", { class: "badge" }, formatBytes(show.total_size)),
      el(
        "button",
        {
          class: "btn btn-danger btn-sm",
          title: `Mover la serie completa ${show.show} a la papelera`,
          onclick: (event) => {
            event.preventDefault();
            event.stopPropagation();
            trashSeriesSelection(show);
          },
        },
        "Papelera"
      ),
    ])
  );

  const seasons = show.seasons.slice().sort((a, b) => a.season - b.season);
  for (const season of seasons) {
    const row = el("div", { class: "season-row" }, [
      el(
        "span",
        { class: "season-name" },
        season.season == null ? "Temporada sin identificar" : `Temporada ${String(season.season).padStart(2, "0")}`
      ),
      el("span", { class: "badge" }, `${season.episode_count} episodios`),
      el("span", { class: "badge" }, formatBytes(season.total_size)),
      season.has_multiple_releases ? el("span", { class: "badge badge-warning" }, "Varias versiones") : null,
      el(
        "button",
        {
          class: "btn btn-danger btn-sm",
          title: season.season == null
            ? "Mover los episodios sin temporada identificada a la papelera"
            : `Mover la temporada ${season.season} a la papelera`,
          onclick: (event) => {
            event.stopPropagation();
            trashSeriesSelection(show, { scope: "season", season: season.season });
          },
        },
        "Papelera"
      ),
    ]);
    const panel = el("div", { class: "hidden" });
    row.style.cursor = "pointer";
    row.addEventListener("click", () => {
      panel.classList.toggle("hidden");
      if (!panel.classList.contains("hidden")) renderSeasonPanel(panel, show.show, season.season);
    });
    details.appendChild(row);
    details.appendChild(panel);
  }
  return details;
}

export async function renderSeriesView() {
  const wrap = qs("#series-tree");
  const countEl = qs("#series-count");
  const sort = qs("#series-sort").value;

  wrap.innerHTML = '<div class="empty-state">Cargando…</div>';
  try {
    cachedShows = await api.series();
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    return;
  }

  countEl.textContent = `${cachedShows.length} series`;
  if (cachedShows.length === 0) {
    wrap.innerHTML = '<div class="empty-state">No hay series escaneadas todavía. Pulsa "Escanear".</div>';
    return;
  }

  const shows = cachedShows.slice().sort((a, b) => {
    if (sort === "size") return b.total_size - a.total_size;
    return a.show.localeCompare(b.show);
  });

  wrap.innerHTML = "";
  shows.forEach((show) => wrap.appendChild(renderShowCard(show)));
}

export function initSeriesView() {
  qs("#series-sort").addEventListener("change", renderSeriesView);
}
