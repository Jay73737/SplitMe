// pill-preload.js — child window
const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("pillAPI", {
  submit: (value) => ipcRenderer.send("pill:submit", value),
  dragStart: (payload) => ipcRenderer.send("pill:drag-start", payload),
  dragMove: (payload) => ipcRenderer.send("pill:drag-move", payload),
  dragEnd: () => ipcRenderer.send("pill:drag-end"),
});
