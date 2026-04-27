const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("sentinelDesktop", {
  platform: process.platform,
  setUnreadCount(count) {
    ipcRenderer.send("sentinel:set-unread-count", count);
  },
  notify(payload) {
    ipcRenderer.send("sentinel:notify", payload);
  },
  onOpenIncident(callback) {
    const listener = (_event, incidentId) => callback(incidentId);
    ipcRenderer.on("sentinel:open-incident", listener);

    return () => {
      ipcRenderer.removeListener("sentinel:open-incident", listener);
    };
  },
});