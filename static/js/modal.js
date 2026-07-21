import { el, qs } from "./utils.js";

export function confirmModal({ title, bodyNode, message, danger = false, confirmLabel = "Confirmar" }) {
  return new Promise((resolve) => {
    const root = qs("#modal-root");

    function close(result) {
      root.innerHTML = "";
      resolve(result);
    }

    const content = bodyNode || el("p", {}, message || "");

    const backdrop = el(
      "div",
      { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) close(false); } },
      [
        el("div", { class: "modal" }, [
          el("h3", { class: danger ? "modal-danger-text" : "" }, title),
          content,
          el("div", { class: "modal-actions" }, [
            el("button", { class: "btn btn-ghost", onclick: () => close(false) }, "Cancelar"),
            el(
              "button",
              { class: danger ? "btn btn-danger" : "btn btn-primary", onclick: () => close(true) },
              confirmLabel
            ),
          ]),
        ]),
      ]
    );

    root.appendChild(backdrop);
  });
}
