import { api } from "./api.js";
import { qs } from "./utils.js";

let pollTimer = null;
let onCompleteCallback = () => {};

function renderProgress(status) {
  const wrap = qs("#scan-progress");
  const fill = qs("#progress-fill");
  const label = qs("#progress-label");
  const scanBtn = qs("#scan-btn");

  if (status.status === "running") {
    wrap.classList.remove("hidden");
    scanBtn.disabled = true;
    const pct = status.total_files ? Math.round((status.processed_files / status.total_files) * 100) : 0;
    fill.style.width = `${pct}%`;
    label.textContent = `${status.processed_files}/${status.total_files} · ${status.current_file || ""}`;
  } else {
    wrap.classList.add("hidden");
    scanBtn.disabled = false;
  }
}

async function poll() {
  const status = await api.scanStatus();
  renderProgress(status);
  if (status.status === "running") {
    pollTimer = setTimeout(poll, 1500);
  } else {
    clearTimeout(pollTimer);
    onCompleteCallback(status);
  }
}

export function initScanProgress(onComplete) {
  onCompleteCallback = onComplete || (() => {});

  qs("#scan-btn").addEventListener("click", async () => {
    try {
      await api.scanStart();
      poll();
    } catch (err) {
      alert(`No se pudo iniciar el escaneo: ${err.message}`);
    }
  });

  qs("#scan-cancel-btn").addEventListener("click", async () => {
    await api.scanCancel();
  });

  poll();
}
