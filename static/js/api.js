async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `GET ${url} -> ${res.status}`);
  }
  return res.json();
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `POST ${url} -> ${res.status}`);
  }
  return data;
}

export const api = {
  mountStatus: () => getJSON("/api/mount/status"),
  mountRetry: () => postJSON("/api/mount/retry"),

  scanStart: () => postJSON("/api/scan/start"),
  scanStatus: () => getJSON("/api/scan/status"),
  scanCancel: () => postJSON("/api/scan/cancel"),

  movies: (sort, order) => getJSON(`/api/movies?sort=${sort}&order=${order}`),

  series: () => getJSON("/api/series"),
  seasonDetail: (show, season) =>
    getJSON(`/api/series/${encodeURIComponent(show)}/seasons/${season == null ? "unidentified" : season}`),

  duplicates: (type) => getJSON(`/api/duplicates?type=${type}`),
  duplicateGroup: (id) => getJSON(`/api/duplicates/${id}`),

  trashList: () => getJSON("/api/trash?status=trashed"),
  trashMove: (mediaItemIds) => postJSON("/api/trash/move", { media_item_ids: mediaItemIds, confirm: true }),
  trashMoveSeries: (show, scope, season = null) =>
    postJSON("/api/trash/move-series", { show, scope, season, confirm: true }),
  trashRestore: (trashItemIds) => postJSON("/api/trash/restore", { trash_item_ids: trashItemIds, confirm: true }),
  trashEmpty: (opts) => postJSON("/api/trash/empty", { ...opts, confirm: true }),
};
