// electron.js — main process
const path = require("path");
const {
  app,
  BrowserWindow,
  ipcMain,
  shell,
  nativeImage,
  dialog,
  screen,
} = require("electron");
const { spawn } = require("child_process");
const fetch = require("node-fetch");
const fs = require("fs");

function logMain(message, extra = null) {
  try {
    const base = app?.isReady?.() ? app.getPath("userData") : __dirname;
    const logFile = path.join(base, "splitme-main.log");
    const line = `[${new Date().toISOString()}] ${message}${
      extra ? ` ${JSON.stringify(extra)}` : ""
    }\n`;
    fs.appendFileSync(logFile, line, "utf8");
  } catch (err) {
    console.error("Failed to write main log", err);
  }
}

function sanitizeFileName(name, fallback = "SplitMe Stems") {
  const safe = (name || "")
    .toString()
    .replace(/[\\/:*?"<>|]+/g, "-")
    .replace(/\s+/g, " ")
    .trim();
  return safe.length ? safe : fallback;
}

function getAppDragIcon() {
  try {
    const iconPath = path.join(app.getAppPath(), "buildResources", "icon.png");
    if (fs.existsSync(iconPath)) {
      const icon = nativeImage.createFromPath(iconPath);
      if (!icon.isEmpty()) return icon;
    }
  } catch (error) {
    logMain("drag-icon-error", { message: error.message });
  }
  return nativeImage.createEmpty();
}

function getWaveformDragIcon() {
  const candidates = [
    path.join(app.getAppPath(), "buildResources", "drag-icon.png"),
    path.join(app.getAppPath(), "build", "logo192.png"),
    path.join(app.getAppPath(), "public", "logo192.png"),
  ];
  for (const iconPath of candidates) {
    try {
      if (!fs.existsSync(iconPath)) continue;
      const icon = nativeImage.createFromPath(iconPath);
      if (!icon.isEmpty()) return icon;
    } catch (error) {
      logMain("drag-icon-error", { message: error.message });
    }
  }
  return getAppDragIcon();
}

const isMac = process.platform === "darwin";
const isWin = process.platform === "win32";
const isDev = !app.isPackaged;

let mainWin = null;
let pillWin = null;
let backendProcess = null;
let pillDragState = null;
let waveformDragTimer = null;
let compactModeEnabled = false;
let mainWinBoundsBeforeCompact = null;

const BACKEND_HOST = process.env.SPLITME_BACKEND_HOST || "127.0.0.1";
const BACKEND_PORT = parseInt(process.env.SPLITME_BACKEND_PORT || "5050", 10);
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const MAIN_WINDOW_WIDTH = 1400;
const MAIN_WINDOW_HEIGHT = 900;
const COMPACT_WINDOW_WIDTH = 520;
const COMPACT_WINDOW_HEIGHT = 900;

function resourcePath(...segments) {
  if (!segments.length) {
    return isDev ? path.join(__dirname, "..") : process.resourcesPath;
  }
  const base = isDev ? path.join(__dirname, "..") : process.resourcesPath;
  return path.join(base, ...segments);
}

function resolveBundledBackend() {
  if (isDev) return null;

  const execName = isWin ? "SplitMeBackend.exe" : "SplitMeBackend";
  const candidate = resourcePath("backend", execName);
  if (fs.existsSync(candidate)) {
    return candidate;
  }
  return null;
}

// Backend server managemen
const RESULTS_H = 478;
async function startBackendServer() {
  console.log("Starting backend server...");

  try {
    // First check if backend is already running
    const healthCheck = await fetch(`${BACKEND_URL}/api/health`).catch(
      () => null
    );
    if (healthCheck && healthCheck.ok) {
      console.log("Backend server already running");
      return;
    }
  } catch (err) {
    // Backend not running, continue to start it
  }

  const backendRoot = resourcePath();
  const bundledExec = resolveBundledBackend();

  const userDataDir = app.getPath("userData");

  const spawnOptions = {
    cwd: bundledExec ? path.dirname(bundledExec) : backendRoot,
    env: {
      ...process.env,
      SPLITME_BACKEND_HOST: BACKEND_HOST,
      SPLITME_BACKEND_PORT: BACKEND_PORT.toString(),
      SPLITME_APP_ROOT: backendRoot,
      SPLITME_USER_DATA_DIR: userDataDir,
    },
    stdio: ["pipe", "pipe", "pipe"],
  };

  if (bundledExec) {
    console.log(`Launching bundled backend from ${bundledExec}`);
    backendProcess = spawn(bundledExec, [], spawnOptions);
  } else {
    console.log("Bundled backend not found; using development Python environment.");
    const venvDir = path.join(backendRoot, ".venv");
    const venvBin = path.join(venvDir, isWin ? "Scripts" : "bin");
    const uvicornInVenv = path.join(
      venvBin,
      isWin ? "uvicorn.exe" : "uvicorn"
    );
    const pythonInVenv = path.join(
      venvBin,
      isWin ? "python.exe" : "python3"
    );

    let command = null;
    let args = [];

    if (fs.existsSync(uvicornInVenv)) {
      command = uvicornInVenv;
      args = [
        "api.server:app",
        "--host",
        BACKEND_HOST,
        "--port",
        BACKEND_PORT.toString(),
      ];
      spawnOptions.env = {
        ...spawnOptions.env,
        VIRTUAL_ENV: venvDir,
        PATH: `${venvBin}${path.delimiter}${process.env.PATH}`,
      };
    } else {
      const pythonCandidates = [
        fs.existsSync(pythonInVenv) ? pythonInVenv : null,
        isWin ? "python" : "python3",
        "python",
      ].filter(Boolean);

      for (const candidate of pythonCandidates) {
        if (!candidate) continue;
        command = candidate;
        args = [
          "-m",
          "uvicorn",
          "api.server:app",
          "--host",
          BACKEND_HOST,
          "--port",
          BACKEND_PORT.toString(),
        ];
        break;
      }

      if (fs.existsSync(venvDir)) {
        spawnOptions.env = {
          ...spawnOptions.env,
          VIRTUAL_ENV: venvDir,
          PATH: `${venvBin}${path.delimiter}${process.env.PATH}`,
        };
      }
    }

    if (!command) {
      throw new Error(
        "Unable to locate Python/uvicorn to launch backend. Run setup first."
      );
    }

    backendProcess = spawn(command, args, spawnOptions);
  }

  backendProcess.stdout.on("data", (data) => {
    console.log(`Backend stdout: ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.log(`Backend stderr: ${data}`);
  });

  backendProcess.on("close", (code) => {
    console.log(`Backend process exited with code ${code}`);
    backendProcess = null;
  });

  backendProcess.on("error", (err) => {
    console.error("Failed to start backend server:", err);
    backendProcess = null;
  });

  // Wait for server to be ready
  await waitForBackend();
}

async function waitForBackend(maxAttempts = 30) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/health`);
      if (response.ok) {
        console.log("Backend server is ready!");
        return;
      }
    } catch (err) {
      // Server not ready yet
    }

    console.log(`Waiting for backend... (${attempt}/${maxAttempts})`);
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error("Backend server failed to start within timeout");
}

function stopBackendServer() {
  if (backendProcess) {
    console.log("Stopping backend server...");
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
}

function abs(p) {
  // robust preload resolution, works in dev & prod
  return path.join(app.getAppPath(), p);
}

function getCompactBounds() {
  if (!mainWin) return null;
  const current = mainWin.getBounds();
  const display = screen.getDisplayMatching(current);
  const workArea = display.workArea;
  const anchorRight = current.x + current.width;
  const nextWidth = COMPACT_WINDOW_WIDTH;
  const nextHeight = COMPACT_WINDOW_HEIGHT;
  let nextX = anchorRight - nextWidth;
  let nextY = current.y;

  if (nextX < workArea.x) nextX = workArea.x;
  if (nextX + nextWidth > workArea.x + workArea.width) {
    nextX = workArea.x + workArea.width - nextWidth;
  }
  if (nextY < workArea.y) nextY = workArea.y;
  if (nextY + nextHeight > workArea.y + workArea.height) {
    nextY = workArea.y + workArea.height - nextHeight;
  }

  return {
    x: Math.round(nextX),
    y: Math.round(nextY),
    width: nextWidth,
    height: nextHeight,
  };
}

function setCompactMode(enabled) {
  if (!mainWin || mainWin.isDestroyed()) return;
  const shouldEnable = Boolean(enabled);
  if (shouldEnable === compactModeEnabled) return;

  const notifyRenderer = () => {
    if (mainWin && !mainWin.isDestroyed()) {
      mainWin.webContents.send("window:compact-mode-changed", compactModeEnabled);
    }
  };

  if (shouldEnable) {
    mainWinBoundsBeforeCompact = mainWin.getBounds();
    const targetBounds = getCompactBounds();
    try {
      if (isMac) mainWin.setAlwaysOnTop(true, "floating");
      else mainWin.setAlwaysOnTop(true);
    } catch {}
    if (targetBounds) {
      mainWin.setBounds(targetBounds, false);
    }
  } else {
    if (mainWinBoundsBeforeCompact) {
      mainWin.setBounds(mainWinBoundsBeforeCompact, false);
      const restoreBounds = { ...mainWinBoundsBeforeCompact };
      setTimeout(() => {
        if (!mainWin || mainWin.isDestroyed()) return;
        mainWin.setBounds(restoreBounds, false);
      }, 120);
    } else {
      mainWin.setSize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT, false);
      setTimeout(() => {
        if (!mainWin || mainWin.isDestroyed()) return;
        mainWin.setSize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT, false);
      }, 120);
    }
    try {
      mainWin.setAlwaysOnTop(false);
    } catch {}
    mainWinBoundsBeforeCompact = null;
  }

  compactModeEnabled = shouldEnable;
  notifyRenderer();
}

function createMainWindow() {
  mainWin = new BrowserWindow({
    width: MAIN_WINDOW_WIDTH, // Reduced for better screen fit
    height: MAIN_WINDOW_HEIGHT, // Reduced for better screen fit
    resizable: false,

    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    titleBarStyle: "hidden",
    fullscreenWindowTitleVisibility: "hidden",

    webPreferences: {
      preload: abs("preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  try {
    mainWin.setHasShadow(false);
  } catch {}
  try {
    mainWin.setWindowButtonVisibility?.(false);
  } catch {}

  if (isDev) mainWin.loadURL("http://localhost:3000");
  else mainWin.loadFile(path.join(app.getAppPath(), "build", "index.html"));

  mainWin.webContents.on("render-process-gone", (_event, details) => {
    const info = {
      reason: details.reason,
      exitCode: details.exitCode,
    };
    console.error("Renderer process crashed", JSON.stringify(info));
    logMain("renderer-crashed", info);
  });

  mainWin.on("closed", () => {
    mainWin = null;
    if (pillWin && !pillWin.isDestroyed()) pillWin.close();
    pillWin = null;
    compactModeEnabled = false;
    mainWinBoundsBeforeCompact = null;
  });
}

function ensurePillWindow() {
  if (!mainWin) return;
  if (pillWin && !pillWin.isDestroyed()) return;

  pillWin = new BrowserWindow({
    width: 800,
    height: 65,
    frame: false,
    transparent: true,
    resizable: false,
    movable: false,
    hasShadow: false,
    focusable: true,
    parent: mainWin,
    show: true,
    backgroundColor: "#00000000",
    skipTaskbar: true,
    webPreferences: {
      preload: abs("pill-preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  try {
    pillWin.setHasShadow(false);
  } catch {}

  const pillHTML = `
<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:transparent}
  .wrap{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;cursor:grab}
  .wrap.dragging{cursor:grabbing}
  .pill-shell{
    position:absolute;left:50%;top:50%;width:100%;height:100%;
    transform:translate(-50%,-50%);border-radius:999px;overflow:hidden;
  }
  .wrap.intro .pill-shell{
    animation:pillIntroMorph 1.9s cubic-bezier(0.22,1.15,0.36,1) 5s forwards;
  }

  .intro-stars{
    position:absolute;inset:0;border-radius:inherit;overflow:hidden;
    z-index:1;pointer-events:none;animation:introStarsFade 1s ease 4s forwards;
  }
  .intro-stars::before,.intro-stars::after{
    content:"";position:absolute;left:50%;top:50%;border-radius:50%;
    transform-origin:60px 60px;
  }
  .intro-stars::before{
    width:2px;height:2px;background:rgba(255,255,255,0.9);
    filter:
      drop-shadow(8px 6px rgba(255,255,255,0.55))
      drop-shadow(-9px 4px rgba(255,255,255,0.45))
      drop-shadow(6px -8px rgba(255,255,255,0.4))
      drop-shadow(-10px -6px rgba(255,255,255,0.35));
    box-shadow:
      36px 44px rgba(255,255,255,0.85),
      19px 98px rgba(255,255,255,0.85),
      56px 67px rgba(255,255,255,0.85),
      25px 17px rgba(255,255,255,0.85),
      14px 8px rgba(255,255,255,0.85),
      57px 76px rgba(255,255,255,0.85),
      43px 108px rgba(255,255,255,0.85),
      103px 13px rgba(255,255,255,0.85),
      34px 72px rgba(255,255,255,0.85),
      74px 52px rgba(255,255,255,0.85),
      41px 105px rgba(255,255,255,0.85),
      28px 111px rgba(255,255,255,0.85),
      19px 39px rgba(255,255,255,0.85),
      33px 9px rgba(255,255,255,0.85),
      112px 88px rgba(255,255,255,0.85),
      109px 39px rgba(255,255,255,0.85),
      108px 40px rgba(255,255,255,0.85),
      30px 27px rgba(255,255,255,0.85),
      45px 43px rgba(255,255,255,0.85),
      86px 117px rgba(255,255,255,0.85),
      99px 115px rgba(255,255,255,0.85),
      114px 118px rgba(255,255,255,0.85),
      53px 17px rgba(255,255,255,0.85),
      114px 83px rgba(255,255,255,0.85),
      49px 91px rgba(255,255,255,0.85),
      55px 70px rgba(255,255,255,0.85),
      37px 28px rgba(255,255,255,0.85),
      37px 66px rgba(255,255,255,0.85),
      41px 17px rgba(255,255,255,0.85),
      110px 116px rgba(255,255,255,0.85),
      76px 113px rgba(255,255,255,0.85),
      44px 6px rgba(255,255,255,0.85),
      43px 79px rgba(255,255,255,0.85),
      96px 118px rgba(255,255,255,0.85),
      45px 114px rgba(255,255,255,0.85),
      103px 71px rgba(255,255,255,0.85),
      30px 58px rgba(255,255,255,0.85),
      60px 82px rgba(255,255,255,0.85),
      42px 61px rgba(255,255,255,0.85),
      63px 26px rgba(255,255,255,0.85),
      35px 45px rgba(255,255,255,0.85),
      39px 110px rgba(255,255,255,0.85),
      108px 11px rgba(255,255,255,0.85),
      16px 11px rgba(255,255,255,0.85),
      65px 86px rgba(255,255,255,0.85),
      41px 72px rgba(255,255,255,0.85),
      74px 88px rgba(255,255,255,0.85),
      66px 95px rgba(255,255,255,0.85),
      49px 24px rgba(255,255,255,0.85),
      92px 31px rgba(255,255,255,0.85),
      14px 58px rgba(255,255,255,0.85),
      31px 87px rgba(255,255,255,0.85),
      86px 62px rgba(255,255,255,0.85),
      41px 29px rgba(255,255,255,0.85),
      51px 61px rgba(255,255,255,0.85);
    animation:starSpin 2.4s linear infinite, starsWhiteFade 1.4s ease 0.6s forwards;
  }
  .intro-stars::after{
    width:1.5px;height:1.5px;color:rgba(255,79,79,0.9);background:currentColor;
    box-shadow:
      63px 82px currentColor,
      51px 38px currentColor,
      21px 27px currentColor,
      114px 90px currentColor,
      4px 47px currentColor,
      68px 63px currentColor,
      118px 81px currentColor,
      14px 46px currentColor,
      74px 82px currentColor,
      93px 9px currentColor,
      97px 52px currentColor,
      25px 94px currentColor,
      61px 96px currentColor,
      58px 24px currentColor,
      25px 34px currentColor,
      10px 18px currentColor,
      20px 68px currentColor,
      115px 79px currentColor,
      12px 103px currentColor,
      92px 53px currentColor,
      105px 99px currentColor,
      117px 17px currentColor,
      41px 30px currentColor,
      90px 32px currentColor,
      96px 105px currentColor,
      57px 117px currentColor,
      15px 102px currentColor,
      38px 120px currentColor,
      30px 54px currentColor,
      39px 47px currentColor,
      107px 9px currentColor,
      29px 94px currentColor,
      117px 4px currentColor,
      116px 56px currentColor,
      11px 118px currentColor,
      52px 112px currentColor,
      66px 21px currentColor,
      7px 34px currentColor,
      58px 98px currentColor,
      120px 112px currentColor;
    opacity:0;
    filter:
      hue-rotate(0deg)
      saturate(1.8)
      drop-shadow(7px 5px rgba(255,255,255,0.35))
      drop-shadow(-8px 4px rgba(255,255,255,0.28))
      drop-shadow(6px -7px rgba(255,255,255,0.24))
      drop-shadow(-9px -6px rgba(255,255,255,0.2));
    mix-blend-mode:screen;
    animation:starSpin 3.6s linear infinite, starsColorRise 1.6s ease 0.6s forwards, starsHueSpin 3.6s linear infinite;
  }

  .glass{
    position:absolute; inset:0; border-radius:inherit;
    background: rgba(0,0,0,0.7);
    border:2px solid transparent; background-clip:padding-box;
    backdrop-filter: blur(30px) saturate(180%) brightness(0.7);
    -webkit-backdrop-filter: blur(30px) saturate(180%) brightness(0.7);
    z-index:0;
  }

  .stroke{
    position:absolute; inset:0; border-radius:inherit; padding:2px;
    background: linear-gradient(90deg,#fe14a8,#1a00ff,#fe14a8);
    background-size:200% 100%;
    filter:
      drop-shadow(0 0 6px rgba(254,20,168,0.35))
      drop-shadow(0 0 10px rgba(26,0,255,0.25));
    animation: spin 4s linear infinite;
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude;
    pointer-events:none; z-index:2;
  }
  .wrap.intro .stroke{
    animation:
      spinFast 5s linear 0s 1 forwards,
      spin 4s linear 5s infinite,
      introGlow 5s ease forwards;
  }
  @keyframes spin { from{background-position:0 0} to{background-position:200% 0} }
  @keyframes spinFast { from{background-position:0 0} to{background-position:400% 0} }
  @keyframes introGlow {
    0% {
      filter:
        drop-shadow(0 0 22px rgba(254,20,168,0.75))
        drop-shadow(0 0 40px rgba(26,0,255,0.6));
    }
    100% {
      filter:
        drop-shadow(0 0 6px rgba(254,20,168,0.35))
        drop-shadow(0 0 10px rgba(26,0,255,0.25));
    }
  }

  .field{
    position:absolute; inset:0; display:flex; align-items:center;
    padding:0 28px; border-radius:inherit; z-index:3; color:#fff;
    font:500 18px/1.2 system-ui,-apple-system,Inter,sans-serif;
    transition: opacity .3s ease;
  }
  #q{
    flex:1; height:100%; border:none; outline:none; background:transparent; color:#fff;
    font:600 20px/65px system-ui,-apple-system,Inter,sans-serif; /* centers caret */
  }

  .ghost{
    position:absolute; left:28px; right:28px; top:50%;
    transform: translateY(-50%);
    font:600 22px/1 system-ui,-apple-system,Inter,sans-serif;
    color: rgba(255,255,255,0.70);
    pointer-events:none; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    opacity:0; transition:opacity .2s ease; z-index:3;
  }
  .ghost.show{ opacity:1; }
  .wrap.intro .field,
  .wrap.intro .ghost{ opacity:0; pointer-events:none; }

  @keyframes starSpin {
    0% { transform: translate(-62px, -62px) rotate(0deg) scale(1.08); }
    50% { transform: translate(-42px, -42px) rotate(360deg) scale(0.65); }
    100% { transform: translate(-62px, -62px) rotate(720deg) scale(1.08); }
  }
  @keyframes starsWhiteFade {
    0% { opacity:1; }
    100% { opacity:0; }
  }
  @keyframes starsColorRise {
    0% { opacity:0; }
    100% { opacity:1; }
  }
  @keyframes starsHueSpin {
    0% { filter: hue-rotate(0deg) saturate(1.6); }
    100% { filter: hue-rotate(320deg) saturate(1.6); }
  }
  @keyframes introStarsFade {
    0% { opacity:1; }
    100% { opacity:0; }
  }
  @keyframes pillIntroMorph {
    0% { width:140px; height:140px; border-radius:999px; transform:scale(1); }
    65% { width:104%; height:112%; border-radius:44px; transform:scale(1.02); }
    82% { width:99%; height:95%; border-radius:36px; transform:scale(0.995); }
    100% { width:100%; height:100%; border-radius:39px; transform:scale(1); }
  }
</style>

<div class="wrap intro">
  <div class="pill-shell">
    <div class="glass"></div>
    <div class="stroke"></div>

    <div class="field">
      <input id="q" type="text" autocomplete="off" spellcheck="false" />
    </div>

    <div id="ghost" class="ghost"></div>
  </div>
</div>

<script>
  const INTRO_DURATION = 5000;
  const msgs = ["Type in a search","Paste a link","Drop in a file"];
  const wrap = document.querySelector('.wrap');
  const ghost = document.getElementById('ghost');
  const q = document.getElementById('q');
  let idx = 0, loop = null, fade = null;

  function tick(){
    ghost.textContent = msgs[idx];
    ghost.classList.add('show');
    clearTimeout(fade);
    fade = setTimeout(()=>ghost.classList.remove('show'), 1600);
    idx = (idx + 1) % msgs.length;
  }
  function start(){ stop(); tick(); loop = setInterval(tick, 2400); }
  function stop(){ if(loop){ clearInterval(loop); loop=null; } ghost.classList.remove('show'); }
  function syncGhost(){
    const focused = document.activeElement === q;
    const hasText = q.value.trim().length > 0;
    if (focused || hasText){ stop(); ghost.style.display = 'none'; }
    else { ghost.style.display = ''; start(); }
  }

  q.disabled = true;
  setTimeout(() => {
    wrap.classList.remove('intro');
    q.disabled = false;
    syncGhost();
  }, INTRO_DURATION);

  q.addEventListener('focus', syncGhost);
  q.addEventListener('blur', syncGhost);
  q.addEventListener('input', syncGhost);

  document.addEventListener('mousedown', () => q.focus());

  const dragState = { active: false, started: false, startX: 0, startY: 0 };
  const dragThreshold = 4;

  wrap.addEventListener('pointerdown', (e) => {
    dragState.active = true;
    dragState.started = false;
    dragState.startX = e.screenX;
    dragState.startY = e.screenY;
  });

  window.addEventListener('pointermove', (e) => {
    if (!dragState.active) return;
    const dx = e.screenX - dragState.startX;
    const dy = e.screenY - dragState.startY;
    if (!dragState.started) {
      if (Math.hypot(dx, dy) < dragThreshold) return;
      dragState.started = true;
      wrap.classList.add('dragging');
      window.pillAPI?.dragStart?.({ x: dragState.startX, y: dragState.startY });
    }
    window.pillAPI?.dragMove?.({ x: e.screenX, y: e.screenY });
  });

  const endDrag = () => {
    if (!dragState.active) return;
    if (dragState.started) {
      window.pillAPI?.dragEnd?.();
    }
    dragState.active = false;
    dragState.started = false;
    wrap.classList.remove('dragging');
  };

  window.addEventListener('pointerup', endDrag);
  window.addEventListener('pointercancel', endDrag);

  // Enter -> send text to main
  q.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      window.pillAPI?.submit(q.value || "");
    }
  });
</script>
  `;
  pillWin.loadURL(
    "data:text/html;charset=utf-8," + encodeURIComponent(pillHTML)
  );

  pillWin.on("closed", () => {
    pillWin = null;
  });
}

ipcMain.on("pill:set-geometry", (_evt, g) => {
  if (!mainWin) return;
  ensurePillWindow();
  if (!pillWin) return;

  const content = mainWin.getContentBounds();
  const zoom = mainWin.webContents.getZoomFactor();

  const x = Math.round(content.x + g.x * zoom);
  const y = Math.round(content.y + g.y * zoom);
  const w = Math.max(10, Math.round(g.w * zoom));
  const h = Math.max(10, Math.round(g.h * zoom));

  pillWin.setBounds({ x, y, width: w, height: h }, false);
});

ipcMain.on("pill:drag-start", (_evt, payload = {}) => {
  if (!pillWin) return;
  const { x, y } = payload;
  if (typeof x !== "number" || typeof y !== "number") return;
  const bounds = pillWin.getBounds();
  const mainBounds =
    mainWin && !mainWin.isDestroyed() ? mainWin.getBounds() : null;
  pillDragState = {
    startX: x,
    startY: y,
    winX: bounds.x,
    winY: bounds.y,
    width: bounds.width,
    height: bounds.height,
    mainX: mainBounds?.x ?? null,
    mainY: mainBounds?.y ?? null,
    mainWidth: mainBounds?.width ?? null,
    mainHeight: mainBounds?.height ?? null,
  };
});

ipcMain.on("pill:drag-move", (_evt, payload = {}) => {
  if (!pillWin || !pillDragState) return;
  const { x, y } = payload;
  if (typeof x !== "number" || typeof y !== "number") return;
  const dx = x - pillDragState.startX;
  const dy = y - pillDragState.startY;
  const nextX = Math.round(pillDragState.winX + dx);
  const nextY = Math.round(pillDragState.winY + dy);
  pillWin.setBounds(
    {
      x: nextX,
      y: nextY,
      width: pillDragState.width,
      height: pillDragState.height,
    },
    false
  );
  if (
    mainWin &&
    !mainWin.isDestroyed() &&
    typeof pillDragState.mainX === "number" &&
    typeof pillDragState.mainY === "number" &&
    typeof pillDragState.mainWidth === "number" &&
    typeof pillDragState.mainHeight === "number"
  ) {
    const nextMainX = Math.round(pillDragState.mainX + dx);
    const nextMainY = Math.round(pillDragState.mainY + dy);
    mainWin.setBounds(
      {
        x: nextMainX,
        y: nextMainY,
        width: pillDragState.mainWidth,
        height: pillDragState.mainHeight,
      },
      false
    );
  }
});

ipcMain.on("pill:drag-end", () => {
  pillDragState = null;
});

// Child (Enter) -> main -> renderer
ipcMain.on("pill:submit", (_evt, value) => {
  // forward to the renderer
  if (mainWin) mainWin.webContents.send("pill:submit", value ?? "");
});

ipcMain.handle("stems:download-all", async (_event, payload = {}) => {
  if (!payload.stems || !Array.isArray(payload.stems) || payload.stems.length === 0) {
    return { ok: false, error: "No stems provided" };
  }

  try {
    const downloadsDir = app.getPath("downloads");
    const folderName = sanitizeFileName(payload.title, "SplitMe Stems");
    const baseDir = payload.targetDir ? path.resolve(payload.targetDir) : downloadsDir;
    const targetDir = path.join(baseDir, folderName);
    await fs.promises.mkdir(targetDir, { recursive: true });

    for (const stem of payload.stems) {
      if (!stem?.streamUrl) continue;
      const response = await fetch(stem.streamUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch stem: ${stem?.stem || "stem"}`);
      }
      const buffer = await response.buffer();
      const ext = sanitizeFileName(stem.format || "mp3", "mp3").toLowerCase();
      const basename = sanitizeFileName(stem.stem || "stem");
      const filePath = path.join(targetDir, `${basename}.${ext}`);
      await fs.promises.writeFile(filePath, buffer);
    }

    shell.showItemInFolder?.(targetDir);
    logMain("stems-downloaded", { targetDir, count: payload.stems.length });
    return { ok: true, path: targetDir };
  } catch (error) {
    logMain("stems-download-error", { message: error.message });
    return { ok: false, error: error.message };
  }
});

ipcMain.on("stems:drag-file", async (event, payload = {}) => {
  try {
    const { filePath, displayName, dragRect } = payload;
    if (!filePath) {
      throw new Error("Missing file path");
    }

    const resolved = path.resolve(filePath);
    if (!fs.existsSync(resolved)) {
      throw new Error("Stem file does not exist");
    }

    let icon = getAppDragIcon();
    if (
      dragRect &&
      Number.isFinite(dragRect.width) &&
      Number.isFinite(dragRect.height) &&
      dragRect.width > 0 &&
      dragRect.height > 0
    ) {
      try {
        const captureRect = {
          x: Math.max(0, Math.round(dragRect.x || 0)),
          y: Math.max(0, Math.round(dragRect.y || 0)),
          width: Math.round(dragRect.width),
          height: Math.round(dragRect.height),
        };
        const captured = await event.sender.capturePage(captureRect);
        if (captured && !captured.isEmpty()) {
          icon = captured;
        }
      } catch (error) {
        logMain("stems-drag-icon-error", { message: error.message });
      }
    }

    event.sender.startDrag({
      file: resolved,
      icon,
      title: typeof displayName === "string" ? displayName : undefined,
    });
    logMain("stems-drag", { path: resolved });
  } catch (error) {
    logMain("stems-drag-error", { message: error.message });
  }
});

ipcMain.on("waveform:drag-end", () => {
  if (!mainWin || mainWin.isDestroyed()) return;
  try {
    if (waveformDragTimer) {
      clearTimeout(waveformDragTimer);
      waveformDragTimer = null;
    }
    mainWin.setIgnoreMouseEvents(false);
  } catch (error) {
    logMain("waveform-drag-ignore-error", { message: error.message });
  }
});

ipcMain.on("window:set-compact-mode", (_event, enabled) => {
  setCompactMode(enabled);
});

ipcMain.on("window:minimize", () => {
  if (!mainWin || mainWin.isDestroyed()) return;
  mainWin.minimize();
});

ipcMain.on("window:quit", () => {
  app.quit();
});

ipcMain.handle("settings:get-default-folder", () => app.getPath("downloads"));

ipcMain.handle("settings:pick-folder", async () => {
  const window = BrowserWindow.getFocusedWindow() || mainWin;
  const result = await dialog.showOpenDialog(window, {
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || !result.filePaths?.length) return null;
  return result.filePaths[0];
});

ipcMain.on("waveform:drag-clip", (event, payload = {}) => {
  try {
    const { data, fileName, displayName } = payload;
    if (!data) {
      throw new Error("Missing clip data");
    }

    const tempDir = path.join(app.getPath("temp"), "splitme-clips");
    fs.mkdirSync(tempDir, { recursive: true });

    const safeName = sanitizeFileName(fileName || "SplitMe Clip.wav", "SplitMe Clip.wav");
    const basename = safeName.toLowerCase().endsWith(".wav") ? safeName : `${safeName}.wav`;
    const resolved = path.join(tempDir, basename);
    const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
    fs.writeFileSync(resolved, buffer);

    if (mainWin && !mainWin.isDestroyed()) {
      try {
        mainWin.setIgnoreMouseEvents(true, { forward: true });
        if (waveformDragTimer) clearTimeout(waveformDragTimer);
        waveformDragTimer = setTimeout(() => {
          try {
            if (mainWin && !mainWin.isDestroyed()) {
              mainWin.setIgnoreMouseEvents(false);
            }
          } catch (err) {
            logMain("waveform-drag-ignore-error", { message: err.message });
          }
          waveformDragTimer = null;
        }, 4000);
      } catch (error) {
        logMain("waveform-drag-ignore-error", { message: error.message });
      }
    }

    const icon = getWaveformDragIcon();
    event.sender.startDrag({
      file: resolved,
      icon,
      title: typeof displayName === "string" ? displayName : basename,
    });
    logMain("waveform-clip-drag", { path: resolved });
  } catch (error) {
    logMain("waveform-clip-drag-error", { message: error.message });
  }
});

// Toggle pill window visibility based on panel height
ipcMain.on("results-opened", (_evt, height) => {
  if (!mainWin) return;
  ensurePillWindow();
  if (!pillWin || pillWin.isDestroyed()) return;
  const numericHeight = typeof height === "number" ? height : null;
  const shouldHide = Number.isFinite(numericHeight) && numericHeight > RESULTS_H;
  if (shouldHide) {
    if (pillWin.isVisible()) pillWin.hide();
  } else {
    if (!pillWin.isVisible()) pillWin.show();
  }
});

ipcMain.on("results-closed", () => {
  if (!mainWin) return;
  ensurePillWindow();
  if (!pillWin || pillWin.isDestroyed()) return;
  if (!pillWin.isVisible()) pillWin.show();
});

app.whenReady().then(async () => {
  try {
    logMain("app-ready", { userData: app.getPath("userData") });

    // Start backend server first
    await startBackendServer();

    // Then create windows
    createMainWindow();
    ensurePillWindow();

    if (isMac) {
      app.on("activate", () => {
        if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
      });
    }
  } catch (error) {
    console.error("Failed to start backend server:", error);
    // Continue with app startup even if backend fails
    createMainWindow();
    ensurePillWindow();
  }
});

app.on("window-all-closed", () => {
  stopBackendServer();
  if (!isMac) app.quit();
});

app.on("before-quit", () => {
  stopBackendServer();
});
