const { app, BrowserWindow, Notification, ipcMain } = require("electron");
const fs = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");

const isDev = Boolean(process.env.ELECTRON_RENDERER_URL);
const remoteDebuggingPort = process.env.ELECTRON_REMOTE_DEBUGGING_PORT;
const rendererPort = Number.parseInt(process.env.ELECTRON_RENDERER_PORT ?? "5173", 10);
const appName = "Sentinel Intelligence";
const hasSingleInstanceLock = app.requestSingleInstanceLock();
let mainWindow = null;
let isQuitting = false;
let rendererServer = null;
let rendererUrlPromise = null;

if (!hasSingleInstanceLock) {
  app.quit();
}

if (isDev && remoteDebuggingPort) {
  app.commandLine.appendSwitch("remote-debugging-port", remoteDebuggingPort);
}

app.setName(appName);

function getContentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === ".html") return "text/html; charset=utf-8";
  if (extension === ".js") return "text/javascript; charset=utf-8";
  if (extension === ".css") return "text/css; charset=utf-8";
  if (extension === ".svg") return "image/svg+xml";
  if (extension === ".png") return "image/png";
  if (extension === ".jpg" || extension === ".jpeg") return "image/jpeg";
  if (extension === ".ico") return "image/x-icon";
  if (extension === ".json") return "application/json; charset=utf-8";
  return "application/octet-stream";
}

function resolveStaticPath(distDir, requestUrl) {
  const parsedUrl = new URL(requestUrl ?? "/", `http://localhost:${rendererPort}`);
  const requestPath = decodeURIComponent(parsedUrl.pathname);
  const relativePath = requestPath === "/" ? "index.html" : requestPath.slice(1);
  const staticPath = path.normalize(path.join(distDir, relativePath));
  const relativeToDist = path.relative(distDir, staticPath);

  if (relativeToDist.startsWith("..") || path.isAbsolute(relativeToDist)) {
    return null;
  }

  return staticPath;
}

async function sendStaticFile(response, filePath) {
  const data = await fs.readFile(filePath);
  response.writeHead(200, {
    "Content-Type": getContentType(filePath),
    "Cache-Control": filePath.endsWith("index.html") ? "no-cache" : "public, max-age=31536000, immutable",
  });
  response.end(data);
}

function startRendererServer() {
  if (rendererUrlPromise) return rendererUrlPromise;

  rendererUrlPromise = new Promise((resolve, reject) => {
    const distDir = path.normalize(path.join(app.getAppPath(), "dist"));
    const indexPath = path.join(distDir, "index.html");
    const server = http.createServer(async (request, response) => {
      try {
        const staticPath = resolveStaticPath(distDir, request.url);
        if (!staticPath) {
          response.writeHead(403);
          response.end("Forbidden");
          return;
        }

        try {
          await sendStaticFile(response, staticPath);
        } catch (error) {
          if (error?.code === "ENOENT") {
            await sendStaticFile(response, indexPath);
            return;
          }
          throw error;
        }
      } catch (error) {
        console.error("Failed to serve Electron renderer asset", error);
        response.writeHead(500);
        response.end("Internal server error");
      }
    });

    server.once("error", reject);
    server.listen(rendererPort, "localhost", () => {
      rendererServer = server;
      resolve(`http://localhost:${rendererPort}`);
    });
  });

  return rendererUrlPromise;
}

async function loadRenderer(window) {
  if (isDev) {
    await window.loadURL(process.env.ELECTRON_RENDERER_URL);
    return;
  }

  const rendererUrl = await startRendererServer();
  await window.loadURL(rendererUrl);
}

function createWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    focusMainWindow();
    return;
  }

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
      partition: "persist:sentinel-intelligence",
      backgroundThrottling: false,
    },
  });

  mainWindow.on("close", (event) => {
    if (isQuitting) return;

    event.preventDefault();
    mainWindow?.hide();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  loadRenderer(mainWindow).catch((error) => {
    console.error("Failed to load Electron renderer", error);
    mainWindow?.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`<h1>${appName}</h1><p>Failed to load the desktop renderer.</p>`)}`);
  });
}


function normalizeUnreadCount(value) {
  const count = Number(value);
  if (!Number.isFinite(count) || count < 0) return 0;
  return Math.min(Math.trunc(count), 999);
}

function focusMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    return;
  }

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

if (hasSingleInstanceLock) {
  app.on("second-instance", () => {
    focusMainWindow();
  });

  app.whenReady().then(() => {
    app.setName(appName);
    app.setAppUserModelId("com.sentinelintelligence.operatorconsole");
    createWindow();

    app.on("activate", () => {
      focusMainWindow();
    });
  });

  app.on("before-quit", () => {
    isQuitting = true;
    rendererServer?.close();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin" || isQuitting) {
      app.quit();
    }
  });
}