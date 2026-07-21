import { api } from "./api.js";
import { el, qs, formatBytes } from "./utils.js";
import { confirmModal } from "./modal.js";
import { locale, t } from "./i18n.js";

export async function renderTrashView() {
  const listEl = qs("#trash-list");
  const countEl = qs("#trash-count");
  listEl.innerHTML = `<div class="empty-state">${t("common.loading")}</div>`;

  let items;
  try {
    items = await api.trashList();
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state">${t("common.error", { error: err.message })}</div>`;
    return;
  }

  const totalSize = items.reduce((sum, i) => sum + i.size_bytes, 0);
  countEl.textContent = t("trash.count", { count: items.length, size: formatBytes(totalSize) });

  if (items.length === 0) {
    listEl.innerHTML = `<div class="empty-state">${t("trash.empty")}</div>`;
    return;
  }

  const table = el("table", { class: "data-table" }, [
    el(
      "thead",
      {},
      el("tr", {}, [el("th", {}, t("common.file")), el("th", {}, t("common.size")), el("th", {}, t("common.moved")), el("th", {}, "")])
    ),
  ]);
  const tbody = el("tbody");
  items.forEach((item) => {
    tbody.appendChild(
      el("tr", {}, [
        el("td", { class: "filename-cell" }, item.original_path.split("/").pop()),
        el("td", {}, formatBytes(item.size_bytes)),
        el("td", {}, new Date(item.moved_at).toLocaleString(locale)),
        el(
          "td",
          { class: "member-actions" },
          el(
            "button",
            {
              class: "btn btn-sm",
              onclick: async () => {
                await api.trashRestore([item.id]);
                renderTrashView();
              },
            },
            t("common.restore")
          )
        ),
      ])
    );
  });
  table.appendChild(tbody);
  listEl.innerHTML = "";
  listEl.appendChild(el("div", { class: "card table-scroll" }, table));
}

export function initTrashView() {
  qs("#empty-trash-btn").addEventListener("click", async () => {
    const confirmed = await confirmModal({
      title: t("trash.emptyTitle"),
      danger: true,
      confirmLabel: t("trash.emptyConfirm"),
      message: t("trash.emptyMessage"),
    });
    if (!confirmed) return;
    await api.trashEmpty({ all: true });
    renderTrashView();
  });
}
