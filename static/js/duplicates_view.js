import { api } from "./api.js";
import { el, qs, qsa, formatBytes } from "./utils.js";
import { confirmModal } from "./modal.js";

let currentType = "movie";

function memberBadges(m) {
  const badges = [];
  if (m.height) badges.push(`${m.height}p`);
  if (m.video_codec) badges.push(m.video_codec);
  if (m.hdr_type && m.hdr_type !== "SDR") badges.push(m.hdr_type);
  if (m.audio_codec) badges.push(`${m.audio_codec} ${m.audio_channels_label || ""}`.trim());
  if (m.container) badges.push(m.container.split(",")[0]);
  return badges.map((b) => el("span", { class: "badge" }, b));
}

function scoreDetailBody(m) {
  const breakdown = m.score_breakdown || {};
  const rows = [
    ["Archivo", m.filename],
    ["Ruta", m.dir_path],
    ["Tamaño", formatBytes(m.size_bytes)],
    ["Resolución", m.width && m.height ? `${m.width}x${m.height}` : "—"],
    ["Codec vídeo", m.video_codec || "—"],
    ["HDR", m.hdr_type || "—"],
    ["Audio", `${m.audio_codec || "—"} ${m.audio_channels_label || ""}`.trim()],
    ["Idiomas", (m.languages || []).join(", ") || "—"],
    ["Score total", m.quality_score],
    ["  · resolución", breakdown.resolution],
    ["  · fuente", breakdown.source],
    ["  · HDR", breakdown.hdr],
    ["  · audio", breakdown.audio],
    ["  · bitrate", breakdown.bitrate],
  ];
  const table = el("table", { class: "data-table" });
  rows.forEach(([k, v]) => {
    table.appendChild(el("tr", {}, [el("td", {}, k), el("td", {}, String(v ?? "—"))]));
  });
  return table;
}

async function trashMembers(members, onDone) {
  const list = el(
    "ul",
    {},
    members.map((m) => el("li", {}, `${m.filename} (${formatBytes(m.size_bytes)})`))
  );
  const confirmed = await confirmModal({
    title: `Mover ${members.length} archivo(s) a la papelera`,
    danger: true,
    confirmLabel: "Mover a papelera",
    bodyNode: el("div", {}, [
      el("p", {}, "Estos archivos se moverán a la papelera de la NAS. Podrás restaurarlos después."),
      list,
    ]),
  });
  if (!confirmed) return;
  await api.trashMove(members.map((m) => m.media_item_id));
  onDone();
}

function renderMemberRow(m, allMembersInBucket) {
  const row = el("div", { class: `member-row ${m.is_recommended_keep ? "is-keep" : ""}` }, [
    el("div", { class: "member-info" }, [
      el("div", { class: "member-filename" }, m.filename),
      el("div", { class: "member-tags" }, [
        ...memberBadges(m),
        el("span", { class: "badge" }, formatBytes(m.size_bytes)),
        m.is_recommended_keep ? el("span", { class: "badge badge-success" }, "Recomendado: mantener") : null,
      ]),
    ]),
    el("div", { class: "member-score" }, String(m.quality_score ?? "—")),
    el("div", { class: "member-actions" }, [
      el("button", { class: "btn btn-ghost btn-sm", onclick: () => showDetail(m) }, "Detalle"),
      el(
        "button",
        {
          class: "btn btn-danger btn-sm",
          onclick: () => trashMembers([m], () => refreshOpenGroup()),
        },
        "Papelera"
      ),
    ]),
  ]);
  return row;
}

async function showDetail(m) {
  await confirmModal({
    title: m.filename,
    confirmLabel: "Cerrar",
    bodyNode: scoreDetailBody(m),
  });
}

let refreshOpenGroup = () => {};

async function renderGroupBody(bodyEl, group, members) {
  bodyEl.innerHTML = "";

  const nonKeep = members.filter((m) => !m.is_recommended_keep);
  if (nonKeep.length) {
    bodyEl.appendChild(
      el(
        "button",
        {
          class: "btn btn-primary btn-sm",
          style: "margin-bottom: 12px;",
          onclick: () => trashMembers(nonKeep, () => refreshOpenGroup()),
        },
        `Aplicar recomendación (papelear ${nonKeep.length})`
      )
    );
  }

  if (group.media_type === "movie") {
    members
      .slice()
      .sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0))
      .forEach((m) => bodyEl.appendChild(renderMemberRow(m)));
    return;
  }

  const byEpisode = new Map();
  members.forEach((m) => {
    const key = m.episode_start ?? "?";
    if (!byEpisode.has(key)) byEpisode.set(key, []);
    byEpisode.get(key).push(m);
  });

  const episodeKeys = Array.from(byEpisode.keys()).sort((a, b) => a - b);
  for (const epKey of episodeKeys) {
    const epMembers = byEpisode.get(epKey).sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
    bodyEl.appendChild(el("div", { class: "toolbar-info", style: "margin: 8px 0 4px;" }, `Episodio ${epKey}`));
    epMembers.forEach((m) => bodyEl.appendChild(renderMemberRow(m)));
  }
}

async function toggleGroup(groupEl, group) {
  const body = qs(".dup-group-body", groupEl);
  const isOpen = !body.classList.contains("hidden");
  if (isOpen) {
    body.classList.add("hidden");
    return;
  }
  body.classList.remove("hidden");
  body.innerHTML = '<div class="empty-state">Cargando…</div>';
  refreshOpenGroup = async () => {
    const detail = await api.duplicateGroup(group.id);
    await renderGroupBody(body, detail.group, detail.members);
    await renderDuplicatesView();
  };
  const detail = await api.duplicateGroup(group.id);
  await renderGroupBody(body, detail.group, detail.members);
}

export async function renderDuplicatesView() {
  const listEl = qs("#duplicates-list");
  const summaryEl = qs("#duplicates-summary");
  listEl.innerHTML = '<div class="empty-state">Cargando…</div>';

  let groups;
  try {
    groups = await api.duplicates(currentType);
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    return;
  }

  if (groups.length === 0) {
    summaryEl.textContent = "";
    listEl.innerHTML = '<div class="empty-state">No se han detectado duplicados en esta categoría.</div>';
    return;
  }

  const totalWasted = groups.reduce((sum, g) => sum + (g.wasted_size || 0), 0);
  summaryEl.textContent = `${groups.length} grupos · ${formatBytes(totalWasted)} recuperables`;

  listEl.innerHTML = "";
  for (const group of groups) {
    const groupEl = el("div", { class: "dup-group" }, [
      el("div", { class: "dup-group-header" }, [
        el("div", { class: "dup-group-title" }, group.display_title),
        el("span", { class: "badge" }, `${group.member_count} copias`),
        el("span", { class: "badge badge-warning" }, `${formatBytes(group.wasted_size)} recuperables`),
      ]),
      el("div", { class: "dup-group-body hidden" }),
    ]);
    qs(".dup-group-header", groupEl).addEventListener("click", () => toggleGroup(groupEl, group));
    listEl.appendChild(groupEl);
  }
}

export function initDuplicatesView() {
  qsa(".subtab-btn", qs("#duplicates-subtabs")).forEach((btn) => {
    btn.addEventListener("click", () => {
      currentType = btn.dataset.dupType;
      qsa(".subtab-btn", qs("#duplicates-subtabs")).forEach((b) => b.classList.toggle("active", b === btn));
      renderDuplicatesView();
    });
  });
}
