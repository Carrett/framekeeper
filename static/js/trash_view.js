import { api } from "./api.js";
import { el, qs, formatBytes } from "./utils.js";
import { confirmModal } from "./modal.js";

export async function renderTrashView() {
  const listEl = qs("#trash-list");
  const countEl = qs("#trash-count");
  listEl.innerHTML = '<div class="empty-state">Cargando…</div>';

  let items;
  try {
    items = await api.trashList();
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
    return;
  }

  const totalSize = items.reduce((sum, i) => sum + i.size_bytes, 0);
  countEl.textContent = `${items.length} archivos · ${formatBytes(totalSize)}`;

  if (items.length === 0) {
    listEl.innerHTML = '<div class="empty-state">La papelera está vacía.</div>';
    return;
  }

  const table = el("table", { class: "data-table" }, [
    el(
      "thead",
      {},
      el("tr", {}, [el("th", {}, "Archivo"), el("th", {}, "Tamaño"), el("th", {}, "Movido"), el("th", {}, "")])
    ),
  ]);
  const tbody = el("tbody");
  items.forEach((item) => {
    tbody.appendChild(
      el("tr", {}, [
        el("td", { class: "filename-cell" }, item.original_path.split("/").pop()),
        el("td", {}, formatBytes(item.size_bytes)),
        el("td", {}, new Date(item.moved_at).toLocaleString("es-ES")),
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
            "Restaurar"
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
      title: "Vaciar papelera",
      danger: true,
      confirmLabel: "Borrar permanentemente",
      message: "Esto borrará PERMANENTEMENTE todos los archivos de la papelera de la NAS. No se puede deshacer.",
    });
    if (!confirmed) return;
    await api.trashEmpty({ all: true });
    renderTrashView();
  });
}
