import { api } from "./api.js";
import { el, qs, formatBytes, posterThumb } from "./utils.js";
import { confirmModal } from "./modal.js";
import { t } from "./i18n.js";

let cachedShows = [];

async function trashEpisode(episode, onDone) {
  const confirmed = await confirmModal({
    title: t("series.trashEpisode"),
    danger: true,
    confirmLabel: t("movies.trashConfirm"),
    bodyNode: el("div", {}, [
      el("p", {}, episode.filename),
      el("p", {}, `${t("common.size")}: ${formatBytes(episode.size_bytes)}`),
      el("p", {}, `${t("common.video")}: ${episode.video_codec || "—"} ${episode.width ? `${episode.width}x${episode.height}` : ""}`),
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
    ? t("series.wholeSelection", { show: show.show })
    : season == null
      ? t("series.unknownSelection", { show: show.show })
      : t("series.seasonSelection", { season: String(season).padStart(2, "0"), show: show.show });

  const confirmed = await confirmModal({
    title: t(isWholeShow ? "series.trashShow" : "series.trashSeason"),
    danger: true,
    confirmLabel: t("movies.trashConfirm"),
    bodyNode: el("div", {}, [
      el("p", {}, t("series.trashSelection", { selection: selectionLabel })),
      el("p", {}, t("series.restoreEpisodes")),
      el("div", { class: "member-tags" }, [
        el("span", { class: "badge badge-danger" }, t("common.episodes", { count: episodeCount })),
        el("span", { class: "badge" }, formatBytes(totalSize)),
      ]),
    ]),
  });
  if (!confirmed) return;

  const result = await api.trashMoveSeries(show.show, scope, season);
  if (result.failed) {
    window.alert(
      t("series.moveResult", result)
    );
  }
  await renderSeriesView();
}

async function renderSeasonPanel(panelEl, show, season) {
  panelEl.innerHTML = `<div class="empty-state">${t("common.loading")}</div>`;
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
      el("thead", {}, el("tr", {}, [el("th", {}, t("common.episode")), el("th", {}, t("common.size")), el("th", {}, t("common.video")), el("th", {}, "")])),
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
              el("button", { class: "btn btn-danger btn-sm", onclick: () => trashEpisode(ep, renderSeriesView) }, t("common.trash"))
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
      posterThumb(show.poster_url, show.show, "poster-thumb-show"),
      el("span", { class: "show-name" }, show.show),
      el("span", { class: "badge" }, t("common.seasons", { count: show.seasons.length })),
      el("span", { class: "badge" }, formatBytes(show.total_size)),
      el(
        "button",
        {
          class: "btn btn-danger btn-sm",
          title: t("series.moveShowTitle", { show: show.show }),
          onclick: (event) => {
            event.preventDefault();
            event.stopPropagation();
            trashSeriesSelection(show);
          },
        },
        t("common.trash")
      ),
    ])
  );

  const seasons = show.seasons.slice().sort((a, b) => a.season - b.season);
  for (const season of seasons) {
    const row = el("div", { class: "season-row" }, [
      el(
        "span",
        { class: "season-name" },
        season.season == null ? t("series.unidentified") : t("series.season", { season: String(season.season).padStart(2, "0") })
      ),
      el("span", { class: "badge" }, t("common.episodes", { count: season.episode_count })),
      el("span", { class: "badge" }, formatBytes(season.total_size)),
      season.has_multiple_releases ? el("span", { class: "badge badge-warning" }, t("series.multiple")) : null,
      el(
        "button",
        {
          class: "btn btn-danger btn-sm",
          title: season.season == null
            ? t("series.moveUnknownTitle")
            : t("series.moveSeasonTitle", { season: season.season }),
          onclick: (event) => {
            event.stopPropagation();
            trashSeriesSelection(show, { scope: "season", season: season.season });
          },
        },
        t("common.trash")
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

  wrap.innerHTML = `<div class="empty-state">${t("common.loading")}</div>`;
  try {
    cachedShows = await api.series();
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${t("common.error", { error: err.message })}</div>`;
    return;
  }

  countEl.textContent = t("common.shows", { count: cachedShows.length });
  if (cachedShows.length === 0) {
    wrap.innerHTML = `<div class="empty-state">${t("series.empty")}</div>`;
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
