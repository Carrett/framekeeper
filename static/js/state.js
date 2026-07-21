export function createStore(initial) {
  let state = { ...initial };
  const listeners = new Set();

  return {
    getState: () => state,
    setState(patch) {
      state = { ...state, ...patch };
      listeners.forEach((fn) => fn(state));
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

export const store = createStore({
  activeTab: "movies",
  moviesSort: "size",
  moviesOrder: "desc",
  duplicatesType: "movie",
  mounted: true,
  scanStatus: "idle",
});
