const { app, BrowserWindow, Notification, ipcMain } = require("electron");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const isDev = Boolean(process.env.ELECTRON_RENDERER_URL);
const remoteDebuggingPort = process.env.ELECTRON_REMOTE_DEBUGGING_PORT;
const appName = "Sentinel Intelligence";
let mainWindow = null;

if (isDev && remoteDebuggingPort) {
  app.commandLine.appendSwitch("remote-debugging-port", remoteDebuggingPort);
}

app.setName(appName);

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    title: appName,
    backgroundColor: "#f6f8fb",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  if (isDev) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    const indexUrl = pathToFileURL(path.join(app.getAppPath(), "dist", "index.html"));
    mainWindow.loadURL(indexUrl.toString());
  }
}

function normalizeUnreadCount(value) {
  const count = Number(value);
  if (!Number.isFinite(count) || count < 0) return 0;
  return Math.min(Math.trunc(count), 999);
}

function focusMainWindow() {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

ipcMain.on("sentinel:set-unread-count", (_event, value) => {
  const count = normalizeUnreadCount(value);
  app.setBadgeCount(count);

  if (process.platform === "darwin") {
    app.dock?.setBadge(count > 0 ? String(count) : "");
  }
});

ipcMain.on("sentinel:notify", (_event, payload) => {
  if (!Notification.isSupported()) return;
  if (!payload || typeof payload !== "object") return;

  const title = typeof payload.title === "string" ? payload.title.slice(0, 120) : appName;
  const body = typeof payload.body === "string" ? payload.body.slice(0, 240) : "New incident update.";
  const incidentId = typeof payload.incidentId === "string" ? payload.incidentId.slice(0, 256) : undefined;

  const notification = new Notification({
    title,
    body,
    silent: false,
  });

  notification.on("click", () => {
    focusMainWindow();
    if (incidentId) {
      mainWindow?.webContents.send("sentinel:open-incident", incidentId);
    }
  });

  notification.show();
});

app.whenReady().then(() => {
  app.setName(appName);
  app.setAppUserModelId("com.sentinelintelligence.operatorconsole");
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});