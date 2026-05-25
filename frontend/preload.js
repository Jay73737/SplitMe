// preload.js — main window
const { contextBridge, ipcRenderer } = require("electron");

function addElectronClass() {
  const add = () => document.documentElement.classList.add("is-electron");
  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", add, { once: true });
  } else {
    add();
  }
}
addElectronClass();

contextBridge.exposeInMainWorld("electronAPI", {
  setPillGeometry: (bounds) => ipcRenderer.send("pill:set-geometry", bounds),
  onPillSubmit: (fn) => ipcRenderer.on("pill:submit", (_e, v) => fn(v)),
  resultsOpened: (height) => ipcRenderer.send("results-opened", height),
  resultsClosed: () => ipcRenderer.send("results-closed"),
  setCompactMode: (enabled) =>
    ipcRenderer.send("window:set-compact-mode", Boolean(enabled)),
  onCompactModeChanged: (fn) => {
    const handler = (_event, enabled) => fn(Boolean(enabled));
    ipcRenderer.on("window:compact-mode-changed", handler);
    return () => ipcRenderer.removeListener("window:compact-mode-changed", handler);
  },
  minimizeWindow: () => ipcRenderer.send("window:minimize"),
  quitApp: () => ipcRenderer.send("window:quit"),
  downloadStems: (payload) => ipcRenderer.invoke("stems:download-all", payload),
  dragStem: (payload) => ipcRenderer.send("stems:drag-file", payload),
  dragWaveformClip: (payload) => ipcRenderer.send("waveform:drag-clip", payload),
  dragWaveformEnd: () => ipcRenderer.send("waveform:drag-end"),
  pickSaveFolder: () => ipcRenderer.invoke("settings:pick-folder"),
  getDefaultSaveFolder: () => ipcRenderer.invoke("settings:get-default-folder"),
});
