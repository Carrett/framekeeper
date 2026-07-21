import { api } from "./api.js";
import { el, qs, formatBytes, formatDate } from "./utils.js";
import { confirmModal } from "./modal.js";

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
    ["Archivo", m.filename],
    ["Tamaño", formatBytes(m.size_bytes)],
    ["Resolución", m.width && m.height ? `${m.width}x${m.height}` : "—"],
    ["Codec vídeo", m.video_codec || "—"],
    ["HDR", m.hdr_type || "—"],
    ["Audio", `${m.audio_codec || "—"} ${m.audio_channels_label || ""}`.trim()],
    ["Idiomas", (m.languages || []).join(", ") || "—"],
    ["Contenedor", m.container || "—"],
    ["Bitrate total", m.bitrate_total ? `${Math.round(m.bitrate_total / 1000)} kbps` : "—"],
  ];
  const table = el("table", { class: "data-table" });
  rows.forEach(([k, v]) => {
    table.appendChild(el("tr", {}, [el("td", {}, k), el("td", {}, String(v))]));
  });
  return table;
}

async function trashMovie(item, onDone) {
  const confirmed = await confirmModal({
    title: `Mover a la papelera`,
    danger: true,
    confirmLabel: "Mover a papelera",
    bodyNode: el("div", {}, [
      el("p", {}, "Se moverá este archivo a la papelera de la NAS. Podrás restaurarlo después."),
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

  wrap.innerHTML = '<div class="empty-state">Cargando…</div>';
  let movies;
  try {
    movies = await api.movies(sort, order);
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">Error cargando películas: ${err.message}</div>`;
    return;
  }

  countEl.textContent = `${movies.length} películas`;

  if (movies.length === 0) {
    wrap.innerHTML = '<div class="empty-state">No hay películas escaneadas todavía. Pulsa "Escanear".</div>';
    return;
  }

  const table = el("table", { class: "data-table" }, [
    el("thead", {}, [
      el("tr", {}, [
        el("th", {}, "Título"),
        el("th", {}, "Tamaño"),
        el("th", {}, "Calidad"),
        el("th", {}, "Estado"),
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
        ? el("span", { class: "badge badge-success" }, "Duplicado · mantener")
        : el("span", { class: "badge badge-warning" }, "Duplicado · candidato a borrar");
    }
    const row = el("tr", {}, [
      el("td", { class: "filename-cell" }, `${m.parsed_title} ${m.parsed_year ? `(${m.parsed_year})` : ""}`),
      el("td", {}, formatBytes(m.size_bytes)),
      el("td", {}, el("div", { class: "member-tags" }, badges)),
      el("td", {}, statusBadge),
      el(
        "td",
        {},
        el("button", { class: "btn btn-danger btn-sm", onclick: () => trashMovie(m, renderMoviesView) }, "Papelera")
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
