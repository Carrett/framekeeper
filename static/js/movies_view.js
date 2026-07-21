import { api } from "./api.js";
import { el, qs, formatBytes, formatDate, posterThumb } from "./utils.js";
import { confirmModal } from "./modal.js";
import { t } from "./i18n.js";

function qualityBadges(m) {
  const badges = [];
  if (m.height) badges.push(`${m.height}p`);
  if (m.video_codec) badges.push(m.video_codec);
  if (m.hdr_type && m.hdr_type !== "SDR") badges.push(m.hdr_type);
  if (m.audio_codec) badges.push(`${m.audio_codec} ${m.audio_channels_label || ""}`.trim());
  return badges;
}

function detailBody(m) {
  const rows = [
    [t("common.file"), m.filename],
    [t("common.size"), formatBytes(m.size_bytes)],
    [t("common.resolution"), m.width && m.height ? `${m.width}x${m.height}` : "—"],
    [t("common.videoCodec"), m.video_codec || "—"],
    ["HDR", m.hdr_type || "—"],
    [t("common.audio"), `${m.audio_codec || "—"} ${m.audio_channels_label || ""}`.trim()],
    [t("common.languages"), (m.languages || []).join(", ") || "—"],
    [t("common.container"), m.container || "—"],
    [t("common.bitrate"), m.bitrate_total ? `${Math.round(m.bitrate_total / 1000)} kbps` : "—"],
  ];
  const table = el("table", { class: "data-table" });
  rows.forEach(([k, v]) => {
    table.appendChild(el("tr", {}, [el("td", {}, k), el("td", {}, String(v))]));
  });
  return table;
}

async function trashMovie(item, onDone) {
  const confirmed = await confirmModal({
    title: t("movies.trashTitle"),
    danger: true,
    confirmLabel: t("movies.trashConfirm"),
    bodyNode: el("div", {}, [
      el("p", {}, t("movies.trashMessage")),
      detailBody(item),
    ]),
  });
  if (!confirmed) return;
  await api.trashMove([item.id]);
  onDone();
}

export async function renderMoviesView() {
  const wrap = qs("#movies-table-wrap");
  const countEl = qs("#movies-count");
  const sort = qs("#movies-sort").value;
  const order = qs("#movies-order").value;

  wrap.innerHTML = `<div class="empty-state">${t("common.loading")}</div>`;
  let movies;
  try {
    movies = await api.movies(sort, order);
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${t("movies.loadError", { error: err.message })}</div>`;
    return;
  }

  countEl.textContent = t("common.movies", { count: movies.length });

  if (movies.length === 0) {
    wrap.innerHTML = `<div class="empty-state">${t("movies.empty")}</div>`;
    return;
  }

  const table = el("table", { class: "data-table" }, [
    el("thead", {}, [
      el("tr", {}, [
        el("th", { class: "poster-column" }, ""),
        el("th", {}, t("common.title")),
        el("th", {}, t("common.size")),
        el("th", {}, t("common.quality")),
        el("th", {}, t("common.status")),
        el("th", {}, ""),
      ]),
    ]),
  ]);

  const tbody = el("tbody");
  for (const m of movies) {
    const badges = qualityBadges(m).map((b) => el("span", { class: "badge" }, b));
    let statusBadge = "";
    if (m.group_id) {
      statusBadge = m.is_recommended_keep
        ? el("span", { class: "badge badge-success" }, t("movies.duplicateKeep"))
        : el("span", { class: "badge badge-warning" }, t("movies.duplicateDelete"));
    }
    const row = el("tr", {}, [
      el("td", { class: "poster-cell" }, posterThumb(m.poster_url, m.parsed_title)),
      el("td", { class: "filename-cell" }, `${m.parsed_title} ${m.parsed_year ? `(${m.parsed_year})` : ""}`),
      el("td", {}, formatBytes(m.size_bytes)),
      el("td", {}, el("div", { class: "member-tags" }, badges)),
      el("td", {}, statusBadge),
      el(
        "td",
        {},
        el("button", { class: "btn btn-danger btn-sm", onclick: () => trashMovie(m, renderMoviesView) }, t("common.trash"))
      ),
    ]);
    tbody.appendChild(row);
  }
  table.appendChild(tbody);

  wrap.innerHTML = "";
  wrap.appendChild(el("div", { class: "card table-scroll" }, table));
}

export function initMoviesView() {
  qs("#movies-sort").addEventListener("change", renderMoviesView);
  qs("#movies-order").addEventListener("change", renderMoviesView);
}
