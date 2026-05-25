import { useRef, useState, useEffect, useCallback, useLayoutEffect } from "react";
import { motion } from "framer-motion";
import YouTubePlayer from "./YoutubePlayer";
import WaveformPlayer from "./components/WaveformPlayer";
import StemCardStack from "./components/StemCardStack";
import CustomDropdown from "./CustomDropdown";
import { downloadAudioBlob, API_BASE } from "./lib/downloadAudio";
import { startStemSplit, fetchStemSplitStatus } from "./lib/splitAudio";
import { audioAnalyzer } from "./audioAnalysis";
import "./App.css";

const DEFAULT_VOLUME = 20;
const DEFAULT_REACTIVITY = 1;
const DEFAULT_GRADIENT_TUNING = {
  targetPerSecond: 55,
  peakMix: 0.23,
  peakGamma: 0.76,
  ampBase: 0.75,
  ampReactive: 1.05,
  beatBase: 6.6,
  beatReactive: 1.4,
  beatThresholdBase: 1.1,
  beatThresholdReactive: 0.19,
  avgBase: 0.022,
  avgMin: 0.013,
  attackBase: 0.76,
  attackReactive: 0.05,
  attackMax: 0.993,
  releaseBase: 0.52,
  releaseReactive: 0.16,
  releaseMax: 0.75,
  maxShift: 0.49,
  maxOffset: 0.45,
};

export default function DashboardView({ video, onBack }) {
  const ytRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loop] = useState(null);
  const [audioFormat, setAudioFormat] = useState("");
  const [aiModel, setAiModel] = useState("");
  const [stems, setStems] = useState({
    vocals: true,
    piano: false,
    guitar: false,
    bass: false,
    drums: false,
    other: false,
  });

  const [audioBlob, setAudioBlob] = useState(null);
  const [backendAudioUrl, setBackendAudioUrl] = useState(null);
  const [backendAudioId, setBackendAudioId] = useState(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const abortRef = useRef(null);
  const [waveformInstance, setWaveformInstance] = useState(null);
  const [waveformPlaying, setWaveformPlaying] = useState(false);
  const waveformTrackRef = useRef(null);
  const waveformScrollRef = useRef(null);
  const sidebarRef = useRef(null);
  const waveformContainerRef = useRef(null);
  const [waveformMask, setWaveformMask] = useState(null);
  const volume = DEFAULT_VOLUME;
  const reactivity = DEFAULT_REACTIVITY;
  const gradientTuning = DEFAULT_GRADIENT_TUNING;
  const gradientPeaksRef = useRef(null);
  const gradientAvgRef = useRef(0);
  const gradientBandsRef = useRef([]);
  const gradientCanvasRef = useRef(null);
  const gradientMaskImageRef = useRef(null);
  const gradientOffscreenRef = useRef(null);
  const gradientStripRef = useRef(null);
  const gradientDrawRef = useRef(0);
  const gradientTimeRef = useRef(null);
  const selectionInitializedRef = useRef(false);
  const [selectionStart, setSelectionStart] = useState(0);
  const [selectionEnd, setSelectionEnd] = useState(0);
  const selectionRef = useRef({ start: 0, end: 0 });
  const highlightRef = useRef({ start: 0, end: 0 });
  const highlightAnchorRef = useRef(0);
  const [highlightStart, setHighlightStart] = useState(0);
  const [highlightEnd, setHighlightEnd] = useState(0);
  const [highlightActive, setHighlightActive] = useState(false);
  const [clipReady, setClipReady] = useState(false);
  const [activeDrag, setActiveDrag] = useState(null);
  const audioContextRef = useRef(null);
  const decodedAudioRef = useRef(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [compactMode, setCompactMode] = useState(false);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [modelOverlap, setModelOverlap] = useState(0.25);
  const [modelShifts, setModelShifts] = useState(4);
  const [waveformZoomed, setWaveformZoomed] = useState(false);
  const waveformZoomRef = useRef(1);
  const zoomAnimRef = useRef(null);
  const mutedWaveformRef = useRef(null);
  const [saveFolderPath, setSaveFolderPath] = useState("");
  const [splitStatus, setSplitStatus] = useState("idle");
  const [splitError, setSplitError] = useState(null);
  const [splitResults, setSplitResults] = useState([]);
  const splitPollRef = useRef(null);
  const [expandedStems, setExpandedStems] = useState(false);
  const [downloadingAll, setDownloadingAll] = useState(false);
  const [advancedConsoleLines, setAdvancedConsoleLines] = useState([]);
  const electronAPI =
    typeof window !== "undefined" ? window.electronAPI : null;
  const canUseCompactMode = Boolean(electronAPI?.setCompactMode);

  // Load audio from backend for accurate waveform
  useEffect(() => {
    return () => {
      if (backendAudioUrl) URL.revokeObjectURL(backendAudioUrl);
    };
  }, [backendAudioUrl]);

  useEffect(() => {
    return () => {
      if (splitPollRef.current) {
        clearInterval(splitPollRef.current);
        splitPollRef.current = null;
      }
    };
  }, []);

  const updateAdvancedConsoleOffset = useCallback(() => {
    const sidebar = sidebarRef.current;
    const container = waveformContainerRef.current;
    if (!sidebar || !container) return;
    const sidebarRect = sidebar.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    if (!sidebarRect.height || !containerRect.height) return;
    const offset = Math.round(sidebarRect.bottom - containerRect.bottom);
    container.style.setProperty("--advanced-console-offset", `${offset}px`);
  }, []);

  useLayoutEffect(() => {
    const shouldShow = advancedMode && !compactMode;
    if (!shouldShow) {
      waveformContainerRef.current?.style.removeProperty(
        "--advanced-console-offset"
      );
      return;
    }

    updateAdvancedConsoleOffset();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateAdvancedConsoleOffset);
      return () => {
        window.removeEventListener("resize", updateAdvancedConsoleOffset);
      };
    }

    const observer = new ResizeObserver(() => {
      updateAdvancedConsoleOffset();
    });

    const sidebar = sidebarRef.current;
    const container = waveformContainerRef.current;
    if (sidebar) observer.observe(sidebar);
    if (container) observer.observe(container);

    window.addEventListener("resize", updateAdvancedConsoleOffset);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateAdvancedConsoleOffset);
    };
  }, [advancedMode, compactMode, updateAdvancedConsoleOffset]);

  useEffect(() => {
    if (!electronAPI?.getDefaultSaveFolder) return;
    electronAPI.getDefaultSaveFolder().then((path) => {
      if (path) setSaveFolderPath(path);
    });
  }, [electronAPI]);

  useEffect(() => {
    if (!electronAPI?.onCompactModeChanged) return;
    const unsubscribe = electronAPI.onCompactModeChanged((enabled) => {
      setCompactMode(Boolean(enabled));
    });
    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
    };
  }, [electronAPI]);

  const handleCompactToggle = useCallback(
    (forceValue) => {
      if (!electronAPI?.setCompactMode) return;
      setSettingsOpen(false);
      const next =
        typeof forceValue === "boolean" ? forceValue : !compactMode;
      setCompactMode(next);
      electronAPI.setCompactMode(next);
    },
    [compactMode, electronAPI]
  );

  useEffect(() => {
    const rafId = requestAnimationFrame(() => {
      window.dispatchEvent(new Event("resize"));
    });
    const timeoutId = setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 200);
    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(timeoutId);
    };
  }, [compactMode]);

  const handleCompactMinimize = useCallback(() => {
    electronAPI?.minimizeWindow?.();
  }, [electronAPI]);

  const handleCompactQuit = useCallback(() => {
    electronAPI?.quitApp?.();
  }, [electronAPI]);

  useEffect(() => {
    decodedAudioRef.current = null;
  }, [audioBlob]);

  const WAVEFORM_ZOOM_DEFAULT = 1;
  const WAVEFORM_ZOOM_IN = 140;
  const WAVEFORM_ZOOM_ANIM_MS = 320;
  const getFitZoom = useCallback((overrideDuration) => {
    const track = waveformTrackRef.current;
    const targetDuration =
      Number.isFinite(overrideDuration) && overrideDuration > 0
        ? overrideDuration
        : duration;
    if (!track || !targetDuration) return WAVEFORM_ZOOM_DEFAULT;
    const width = track.clientWidth;
    if (!width) return WAVEFORM_ZOOM_DEFAULT;
    return width / targetDuration;
  }, [duration, WAVEFORM_ZOOM_DEFAULT]);

  const setSelectionRange = useCallback((start, end) => {
    selectionRef.current = { start, end };
    setSelectionStart(start);
    setSelectionEnd(end);
  }, []);

  const setHighlightRange = useCallback((start, end) => {
    highlightRef.current = { start, end };
    setHighlightStart(start);
    setHighlightEnd(end);
  }, []);

  useEffect(() => {
    const clamped = Math.max(0, Math.min(100, volume));
    const normalized = clamped / 100;
    if (waveformInstance?.setVolume) {
      waveformInstance.setVolume(normalized);
    }
    if (video?.isLocalFile) {
      if (ytRef.current && typeof ytRef.current.volume === "number") {
        ytRef.current.volume = normalized;
      }
    } else if (ytRef.current?.setVolume) {
      ytRef.current.setVolume(clamped);
    }
  }, [volume, waveformInstance, video?.isLocalFile]);

  const gradientBandCount = 9;
  const {
    targetPerSecond,
    peakMix,
    peakGamma,
    ampBase,
    ampReactive,
    beatBase,
    beatReactive,
    beatThresholdBase,
    beatThresholdReactive,
    avgBase,
    avgMin,
    attackBase,
    attackReactive,
    attackMax,
    releaseBase,
    releaseReactive,
    releaseMax,
    maxShift,
    maxOffset,
  } = gradientTuning;

  const initGradientBands = useCallback(() => {
    if (gradientBandsRef.current.length === gradientBandCount) return;
    const center = (gradientBandCount - 1) / 2;
    gradientBandsRef.current = Array.from({ length: gradientBandCount }, (_, i) => {
      const distance = Math.abs(i - center) / Math.max(1, center);
      const weight = 0.85 + 0.25 * Math.cos(distance * Math.PI);
      return { value: 0.5, weight };
    });
  }, [gradientBandCount]);

  const resetGradientBands = useCallback((value = 0.5) => {
    if (!gradientBandsRef.current.length) return;
    gradientBandsRef.current.forEach((band) => {
      band.value = value;
    });
  }, []);

  const getPeakAtTime = useCallback(
    (time) => {
      const peaks = gradientPeaksRef.current;
      const total = duration || waveformInstance?.getDuration?.() || 0;
      if (!peaks || !total) return 0;
      const clamped = Math.max(0, Math.min(total, time));
      const ratio = clamped / total;
      const position = ratio * (peaks.length - 1);
      const index = Math.floor(position);
      const nextIndex = Math.min(peaks.length - 1, index + 1);
      const frac = position - index;
      const current = peaks[index] || 0;
      const next = peaks[nextIndex] ?? current;
      return current + (next - current) * frac;
    },
    [duration, waveformInstance]
  );

  const drawGradient = useCallback(() => {
    const canvas = gradientCanvasRef.current;
    const track = waveformTrackRef.current;
    const mask = gradientMaskImageRef.current;
    const bands = gradientBandsRef.current;
    if (!canvas || !track || !mask || !bands.length) return;
    const rect = track.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const logicalWidth = Math.max(1, Math.floor(rect.width));
    const width = Math.max(1, Math.floor(rect.width * dpr));
    const height = Math.max(1, Math.floor(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const offscreen =
      gradientOffscreenRef.current ||
      (gradientOffscreenRef.current = document.createElement("canvas"));
    const columns = Math.min(
      logicalWidth,
      Math.max(240, bands.length * 45)
    );
    if (offscreen.width !== columns || offscreen.height !== height) {
      offscreen.width = columns;
      offscreen.height = height;
    }
    const octx = offscreen.getContext("2d");
    if (!octx) return;
    octx.clearRect(0, 0, offscreen.width, offscreen.height);

    let stripCanvas = gradientStripRef.current;
    const span = Math.max(1, Math.round(height * 1.6));
    if (!stripCanvas || stripCanvas.height !== span) {
      stripCanvas = document.createElement("canvas");
      stripCanvas.width = 1;
      stripCanvas.height = span;
      const sctx = stripCanvas.getContext("2d");
      if (sctx) {
        const grad = sctx.createLinearGradient(0, 0, 0, span);
        grad.addColorStop(0, "#ff008f");
        grad.addColorStop(0.2, "#ff3ad1");
        grad.addColorStop(0.42, "#ff4ef5");
        grad.addColorStop(0.62, "#b73bff");
        grad.addColorStop(0.82, "#5f2bff");
        grad.addColorStop(1, "#ff008f");
        sctx.fillStyle = grad;
        sctx.fillRect(0, 0, 1, span);
      }
      gradientStripRef.current = stripCanvas;
    }

    const values = bands.map((band) =>
      typeof band.value === "number" ? band.value : 0.5
    );
    const smoothValues = new Array(values.length);
    for (let i = 0; i < values.length; i += 1) {
      const prev = values[i - 1] ?? values[i];
      const next = values[i + 1] ?? values[i];
      smoothValues[i] = (prev * 0.1 + values[i] * 0.8 + next * 0.1);
    }
    const baseStart = (height - span) / 2;
    const maxShiftPx = height * maxShift;
    const baseStops = [0, 0.18, 0.4, 0.6, 0.8, 1];
    const baseColors = [
      "#ff008f",
      "#ff3ad1",
      "#ff4ef5",
      "#b73bff",
      "#5f2bff",
      "#2b2158",
    ];
    const maxOffsetValue = maxOffset;
    for (let x = 0; x < columns; x += 1) {
      const t = columns <= 1 ? 0 : x / (columns - 1);
      const pos = t * (values.length - 1);
      const i0 = Math.floor(pos);
      const i1 = Math.min(values.length - 1, i0 + 1);
      const frac = pos - i0;
      const amp = smoothValues[i0] * (1 - frac) + smoothValues[i1] * frac;
      const shift = (amp - 0.5) * 2 * maxShiftPx;
      octx.drawImage(stripCanvas, x, baseStart + shift, 1, span);
      const offset = (amp - 0.5) * maxOffsetValue;
      const gradient = octx.createLinearGradient(0, 0, 0, height);
      let lastStop = 0;
      gradient.addColorStop(0, baseColors[0]);
      for (let i = 1; i < baseStops.length - 1; i += 1) {
        const stop = Math.min(0.92, Math.max(baseStops[i] + offset, lastStop + 0.06));
        gradient.addColorStop(stop, baseColors[i]);
        lastStop = stop;
      }
      gradient.addColorStop(1, baseColors[baseColors.length - 1]);
      octx.fillStyle = gradient;
      octx.fillRect(x, 0, 1, height);
    }

    ctx.clearRect(0, 0, width, height);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(offscreen, 0, 0, width, height);
    ctx.globalCompositeOperation = "destination-in";
    ctx.drawImage(mask, 0, 0, width, height);
    ctx.globalCompositeOperation = "source-over";
  }, [maxOffset, maxShift]);

  const scheduleGradientDraw = useCallback(() => {
    if (gradientDrawRef.current) return;
    gradientDrawRef.current = requestAnimationFrame(() => {
      gradientDrawRef.current = 0;
      drawGradient();
    });
  }, [drawGradient]);

  const resetGradientState = useCallback(() => {
    gradientPeaksRef.current = null;
    gradientAvgRef.current = 0;
    gradientBandsRef.current = [];
    gradientMaskImageRef.current = null;
    gradientOffscreenRef.current = null;
    gradientStripRef.current = null;
    gradientTimeRef.current = null;
    if (gradientDrawRef.current) {
      cancelAnimationFrame(gradientDrawRef.current);
      gradientDrawRef.current = 0;
    }
  }, []);

  const buildGradientPeaks = useCallback(
    (instance = waveformInstance) => {
      const buffer = instance?.getDecodedData?.();
      if (!buffer) return;
      const channelData = buffer.getChannelData(0);
      const samples = channelData.length;
      if (!samples) return;
      const durationSeconds =
        buffer.duration || samples / (buffer.sampleRate || 1) || 0;
      const rawBucketCount = durationSeconds
        ? Math.floor(durationSeconds * targetPerSecond)
        : Math.floor(samples / 256);
      const maxBuckets = Math.min(12000, samples);
      const bucketCount = Math.min(Math.max(300, rawBucketCount), maxBuckets);
      const bucketSize = Math.max(1, Math.floor(samples / bucketCount));
      const peaks = new Float32Array(bucketCount);
      let max = 0;
      for (let i = 0; i < bucketCount; i += 1) {
        const start = i * bucketSize;
        const end = Math.min(samples, start + bucketSize);
        let peak = 0;
        let sum = 0;
        for (let j = start; j < end; j += 1) {
          const sample = channelData[j];
          const abs = Math.abs(sample);
          sum += sample * sample;
          if (abs > peak) peak = abs;
        }
        const count = Math.max(1, end - start);
        const rms = Math.sqrt(sum / count);
        const amplitude = Math.max(rms, peak * peakMix);
        peaks[i] = amplitude;
        if (amplitude > max) max = amplitude;
      }
      if (max > 0) {
        for (let i = 0; i < peaks.length; i += 1) {
          peaks[i] = Math.pow(peaks[i] / max, peakGamma);
        }
      }
      gradientPeaksRef.current = peaks;
      initGradientBands();
      resetGradientBands(0.5);
      scheduleGradientDraw();
    },
    [
      initGradientBands,
      peakGamma,
      peakMix,
      resetGradientBands,
      scheduleGradientDraw,
      targetPerSecond,
      waveformInstance,
    ]
  );

  useEffect(() => {
    if (!waveformInstance) return;
    buildGradientPeaks(waveformInstance);
  }, [buildGradientPeaks, waveformInstance]);

  const updateGradientPulse = useCallback(
    (time) => {
      const peaks = gradientPeaksRef.current;
      const total = duration || waveformInstance?.getDuration?.() || 0;
      if (!peaks || !total) return;
      const reactivityScale = Math.max(0.5, Math.min(8, reactivity));
      initGradientBands();
      const baseAmp = getPeakAtTime(time);
      const avgPrev = gradientAvgRef.current || 0;
      const avgFactor = Math.max(avgMin, avgBase / reactivityScale);
      const avgNext = avgPrev + (baseAmp - avgPrev) * avgFactor;
      gradientAvgRef.current = avgNext;
      const beatThreshold = Math.max(
        0.45,
        beatThresholdBase - reactivityScale * beatThresholdReactive
      );
      const beat = Math.max(0, baseAmp - avgNext * beatThreshold);
      const bands = gradientBandsRef.current;
      const center = (bands.length - 1) / 2;
      const offsetStep = Math.min(
        0.6,
        Math.max(0.14, total / 1200) * (0.8 + reactivityScale * 0.5)
      );
      for (let i = 0; i < bands.length; i += 1) {
        const offset = (i - center) * offsetStep;
        const amp = getPeakAtTime(time + offset);
        const weight = bands[i].weight || 1;
        const target = Math.min(
          1.6,
          (amp * (ampBase + reactivityScale * ampReactive) +
            beat * (beatBase + reactivityScale * beatReactive)) *
            weight
        );
        const prev = typeof bands[i].value === "number" ? bands[i].value : 0.5;
        const attack = Math.min(attackMax, attackBase + reactivityScale * attackReactive);
        const release = Math.min(
          releaseMax,
          releaseBase + reactivityScale * releaseReactive
        );
        const next =
          target > prev
            ? prev + (target - prev) * attack
            : prev + (target - prev) * release;
        bands[i].value = next;
      }
      scheduleGradientDraw();
    },
    [
      ampBase,
      ampReactive,
      attackBase,
      attackMax,
      attackReactive,
      avgBase,
      avgMin,
      beatBase,
      beatReactive,
      beatThresholdBase,
      beatThresholdReactive,
      duration,
      getPeakAtTime,
      initGradientBands,
      reactivity,
      releaseBase,
      releaseMax,
      releaseReactive,
      scheduleGradientDraw,
      waveformInstance,
    ]
  );

  const pauseUnderlying = useCallback(() => {
    const target = ytRef.current;
    if (!target) return;
    if (video?.isLocalFile) {
      if (typeof target.pause === "function") target.pause();
      return;
    }
    target?.pause?.();
  }, [video?.isLocalFile]);

  useEffect(() => {
    if (!duration) return;
    if (!selectionInitializedRef.current) {
      setSelectionRange(0, duration);
      selectionInitializedRef.current = true;
      setHighlightActive(false);
      return;
    }
    if (selectionRef.current.end > duration) {
      const start = Math.min(selectionRef.current.start, duration);
      setSelectionRange(start, duration);
    }
  }, [duration, setSelectionRange]);

  const captureWaveformMask = useCallback(
    async (instance = waveformInstance) => {
      if (!instance?.exportImage) return;
      try {
        const image = await instance.exportImage("image/png", 1, "dataURL");
        const dataUrl = Array.isArray(image) ? image[0] : image;
        if (dataUrl) {
          setWaveformMask(dataUrl);
        }
      } catch (err) {
        console.warn("Unable to capture waveform mask:", err);
      }
    },
    [waveformInstance]
  );

  useEffect(() => {
    if (!waveformMask) {
      gradientMaskImageRef.current = null;
      return;
    }
    const img = new Image();
    img.onload = () => {
      gradientMaskImageRef.current = img;
      scheduleGradientDraw();
    };
    img.src = waveformMask;
    gradientMaskImageRef.current = img;
    return () => {
      img.onload = null;
    };
  }, [scheduleGradientDraw, waveformMask]);

  useEffect(() => {
    if (!waveformMask) return;
    scheduleGradientDraw();
  }, [maxOffset, maxShift, reactivity, scheduleGradientDraw, waveformMask]);

  const getTrackRatio = useCallback((clientX) => {
    const track = waveformTrackRef.current;
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    if (!rect.width) return 0;
    const x = Math.min(Math.max(clientX - rect.left, 0), rect.width);
    return x / rect.width;
  }, []);

  const updateDragPosition = useCallback(
    (clientX, type) => {
      if (!duration) return;
      const ratio = getTrackRatio(clientX);
      const time = ratio * duration;
      const minGap = Math.min(1, duration * 0.02);
      if (type === "start") {
        const next = Math.min(time, selectionRef.current.end - minGap);
        setSelectionRange(Math.max(0, next), selectionRef.current.end);
      } else if (type === "end") {
        const next = Math.max(time, selectionRef.current.start + minGap);
        setSelectionRange(selectionRef.current.start, Math.min(duration, next));
      } else if (type === "selection") {
        const anchor = highlightAnchorRef.current;
        const start = Math.max(0, Math.min(anchor, time));
        const end = Math.min(duration, Math.max(anchor, time));
        setHighlightRange(start, end);
      } else if (type === "playhead") {
        const next = Math.max(0, Math.min(duration, time));
        setCurrent(next);
        if (waveformInstance?.setTime) {
          waveformInstance.setTime(next);
        }
      }
    },
    [duration, getTrackRatio, setHighlightRange, setSelectionRange, waveformInstance]
  );

  const startSelectionDrag = useCallback(
    (event) => {
      if (!duration) return;
      if (event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      const ratio = getTrackRatio(event.clientX);
      const time = ratio * duration;
      highlightAnchorRef.current = time;
      setHighlightActive(true);
      setHighlightRange(time, time);
      setActiveDrag("selection");
    },
    [duration, getTrackRatio, setHighlightRange]
  );

  const startDrag = useCallback(
    (type) => (event) => {
      event.preventDefault();
      event.stopPropagation();
      setActiveDrag(type);
      updateDragPosition(event.clientX, type);
    },
    [updateDragPosition]
  );

  useEffect(() => {
    if (!activeDrag) return;
    const handleMove = (event) => updateDragPosition(event.clientX, activeDrag);
    const handleUp = () => setActiveDrag(null);
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    document.body.style.cursor = activeDrag === "selection" ? "crosshair" : "ew-resize";
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
      document.body.style.cursor = "";
    };
  }, [activeDrag, updateDragPosition]);

  useEffect(() => {
    if (splitPollRef.current) {
      clearInterval(splitPollRef.current);
      splitPollRef.current = null;
    }

    setSplitStatus("idle");
    setSplitError(null);
    setSplitResults([]);
    selectionInitializedRef.current = false;
    selectionRef.current = { start: 0, end: 0 };
    setSelectionStart(0);
    setSelectionEnd(0);
    highlightRef.current = { start: 0, end: 0 };
    setHighlightStart(0);
    setHighlightEnd(0);
    setHighlightActive(false);

    if (video?.isLocalFile) {
      // For local files, use the existing file URL
      setBackendAudioUrl(video.filePath);
      setAudioBlob(video.file);
      setAudioError(null);
      setBackendAudioId(null);
      setWaveformInstance(null);
      setWaveformPlaying(false);
      setWaveformMask(null);
      resetGradientState();
      return;
    }

    if (!video?.id) {
      setBackendAudioUrl(null);
      setAudioBlob(null);
      setAudioError(null);
      setBackendAudioId(null);
      setWaveformInstance(null);
      setWaveformPlaying(false);
      setWaveformMask(null);
      resetGradientState();
      return;
    }

    // Cancel any existing request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    const loadBackendAudio = async () => {
      setAudioLoading(true);
      setAudioError(null);
      setAudioBlob(null);
      setWaveformInstance(null);
      setWaveformPlaying(false);
      setWaveformMask(null);
      resetGradientState();
      try {
        const youtubeUrl = `https://www.youtube.com/watch?v=${video.id}`;
        const { objectUrl, blob, id } = await downloadAudioBlob(
          youtubeUrl,
          "mp3",
          abortRef.current.signal
        );
        setBackendAudioUrl(objectUrl);
        setAudioBlob(blob);
        setBackendAudioId(id);
      } catch (err) {
        if (err.name === "AbortError") {
          return;
        }
        console.error("Failed to load backend audio:", err);
        setBackendAudioUrl(null);
        setAudioError(err.message || "Failed to load waveform audio.");
        setBackendAudioId(null);
        setWaveformInstance(null);
        setWaveformPlaying(false);
      } finally {
        setAudioLoading(false);
      }
    };

    loadBackendAudio();

    return () => {
      abortRef.current?.abort();
    };
  }, [
    resetGradientState,
    video?.file,
    video?.filePath,
    video?.id,
    video?.isLocalFile,
  ]);

  const handleWaveformReady = useCallback(
    (instance) => {
      setWaveformInstance(instance);
      setPlaying(false);
      pauseUnderlying();
      buildGradientPeaks(instance);
      const nextDuration = instance?.getDuration?.() || 0;
      if (nextDuration) {
        setDuration(nextDuration);
        if (!selectionInitializedRef.current) {
          setSelectionRange(0, nextDuration);
          selectionInitializedRef.current = true;
          setHighlightActive(false);
        }
      }
      const targetZoom =
        advancedMode && waveformZoomed
          ? WAVEFORM_ZOOM_IN
          : getFitZoom(nextDuration);
      waveformZoomRef.current = targetZoom;
      if (instance?.zoom) {
        instance.zoom(targetZoom);
      }
    },
    [
      advancedMode,
      buildGradientPeaks,
      getFitZoom,
      pauseUnderlying,
      setSelectionRange,
      waveformZoomed,
      WAVEFORM_ZOOM_IN,
    ]
  );

  const handleMutedWaveformReady = useCallback(
    (instance) => {
      mutedWaveformRef.current = instance;
      const targetZoom =
        advancedMode && waveformZoomed ? WAVEFORM_ZOOM_IN : getFitZoom();
      if (instance?.zoom) {
        instance.zoom(targetZoom);
      }
    },
    [advancedMode, getFitZoom, waveformZoomed, WAVEFORM_ZOOM_IN]
  );

  const handleWaveformPlayStateChange = useCallback(
    (playingState) => {
      setWaveformPlaying(playingState);
      if (!playingState) {
        gradientAvgRef.current = 0;
        resetGradientBands(0.5);
        scheduleGradientDraw();
      }
      if (playingState) {
        setPlaying(false);
        pauseUnderlying();
      }
    },
    [pauseUnderlying, resetGradientBands, scheduleGradientDraw]
  );

  useEffect(() => {
    if (!waveformInstance) return;
    const handleReady = () => {
      const nextDuration = waveformInstance.getDuration?.() || 0;
      if (nextDuration) {
        setDuration(nextDuration);
        if (!selectionInitializedRef.current) {
          setSelectionRange(0, nextDuration);
          selectionInitializedRef.current = true;
          setHighlightActive(false);
        }
      }
    };
    const handleRedraw = () => {
      captureWaveformMask(waveformInstance);
    };
    const getTimeValue = (timeValue) =>
      typeof timeValue === "number"
        ? timeValue
        : waveformInstance.getCurrentTime?.() || 0;
    const handleTime = (timeValue) => {
      const nextTime = getTimeValue(timeValue);
      setCurrent(nextTime);
      if (!waveformInstance.isPlaying?.()) {
        updateGradientPulse(nextTime);
      }
    };
    const handlePlay = () => setWaveformPlaying(true);
    const handlePause = () => setWaveformPlaying(false);
    waveformInstance.on("ready", handleReady);
    waveformInstance.on("redrawcomplete", handleRedraw);
    waveformInstance.on("timeupdate", handleTime);
    waveformInstance.on("play", handlePlay);
    waveformInstance.on("pause", handlePause);
    waveformInstance.on("finish", handlePause);
    return () => {
      waveformInstance.un("ready", handleReady);
      waveformInstance.un("redrawcomplete", handleRedraw);
      waveformInstance.un("timeupdate", handleTime);
      waveformInstance.un("play", handlePlay);
      waveformInstance.un("pause", handlePause);
      waveformInstance.un("finish", handlePause);
    };
  }, [
    captureWaveformMask,
    setSelectionRange,
    updateGradientPulse,
    waveformInstance,
  ]);

  const beginSplitPolling = useCallback((jobId) => {
    const poll = async () => {
      try {
        const data = await fetchStemSplitStatus(jobId);
        if (!data) return;
        if (Array.isArray(data.logs)) {
          setAdvancedConsoleLines(data.logs.slice(-10));
        }
        if (data.status === "completed") {
          const results = (data.results || []).map((item) => ({
            ...item,
            streamUrl: `${API_BASE}${item.streamUrl}`,
          }));
          setSplitResults(results);
          setSplitStatus("completed");
          clearInterval(splitPollRef.current);
          splitPollRef.current = null;
        } else if (data.status === "error") {
          setSplitStatus("error");
          setSplitError(data.error || "Stem split failed.");
          clearInterval(splitPollRef.current);
          splitPollRef.current = null;
        } else {
          setSplitStatus(data.status || "processing");
        }
      } catch (err) {
        console.error("Stem split status error:", err);
        setSplitStatus("error");
        setSplitError(err.message || "Unable to retrieve stem split status.");
        clearInterval(splitPollRef.current);
        splitPollRef.current = null;
      }
    };

    poll();
    splitPollRef.current = window.setInterval(poll, 1000);
  }, []);

  const handleSplitAudio = useCallback(async () => {
    if (splitStatus === "processing" || splitStatus === "queued") return;

    const selectedStems = Object.entries(stems)
      .filter(([, enabled]) => enabled)
      .map(([name]) => name);

    if (!selectedStems.length) {
      setSplitError("Select at least one stem to split.");
      return;
    }

    if (!backendAudioId) {
      setSplitError(
        video?.isLocalFile
          ? "Stem splitting for local files is not yet available."
          : "Audio must finish downloading before splitting. Please wait for the waveform to load."
      );
      return;
    }

    try {
      if (splitPollRef.current) {
        clearInterval(splitPollRef.current);
        splitPollRef.current = null;
      }

      setSplitError(null);
      setSplitResults([]);
      setAdvancedConsoleLines([]);
      setSplitStatus("processing");

      const payload = {
        audioId: backendAudioId,
        stems: selectedStems,
        model: aiModel || "ht-demucs-v4",
        format: audioFormat || "mp3",
      };
      if (advancedMode) {
        payload.overlap = modelOverlap;
        payload.shifts = modelShifts;
      }
      const rangeStart = Math.min(selectionStart, selectionEnd);
      const rangeEnd = Math.max(selectionStart, selectionEnd);
      if (duration > 0 && rangeEnd > rangeStart) {
        payload.startSeconds = rangeStart;
        payload.endSeconds = rangeEnd;
      }

      const { jobId, status } = await startStemSplit(payload);
      setSplitStatus(status || "processing");
      beginSplitPolling(jobId);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Failed to start stem split:", err);
      setSplitStatus("error");
      setSplitError(err.message || "Unable to start stem splitting.");
    }
  }, [
    advancedMode,
    aiModel,
    audioFormat,
    backendAudioId,
    beginSplitPolling,
    duration,
    modelOverlap,
    modelShifts,
    selectionEnd,
    selectionStart,
    splitStatus,
    stems,
    video?.isLocalFile,
  ]);

  useEffect(() => {
    if (!advancedMode || compactMode) {
      setAdvancedConsoleLines([]);
    }
  }, [advancedMode, compactMode]);

  const showStemStack = splitStatus === "completed" && splitResults.length > 0;
  const isSplitRunning =
    splitStatus === "processing" || splitStatus === "queued";
  const showWaveform =
    !audioLoading &&
    !showStemStack &&
    !isSplitRunning &&
    !splitError &&
    backendAudioUrl &&
    !audioError;
  const waveformReady = Boolean(waveformInstance && duration > 0);
  const showTimeline = showWaveform && duration > 0 && selectionEnd > selectionStart;
  const showLoadingGlow =
    audioLoading ||
    isSplitRunning ||
    (!showStemStack && !audioError && !splitError && !waveformReady);
  const transportLoading =
    !showStemStack && !audioError && !splitError && !waveformReady;

  useEffect(() => {
    if (!showWaveform || !waveformInstance) return;
    let rafId = 0;
    const tick = () => {
      const nextTime = waveformInstance.getCurrentTime?.() || 0;
      const lastTime = gradientTimeRef.current;
      const timeMoved =
        lastTime == null || Math.abs(nextTime - lastTime) > 0.001;
      if (timeMoved || waveformPlaying) {
        gradientTimeRef.current = nextTime;
        updateGradientPulse(nextTime);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [showWaveform, updateGradientPulse, waveformInstance, waveformPlaying]);

  useEffect(() => {
    if (!showWaveform || !waveformInstance) return;
    let raf = requestAnimationFrame(() => {
      captureWaveformMask();
    });
    return () => cancelAnimationFrame(raf);
  }, [showWaveform, waveformInstance, backendAudioUrl, captureWaveformMask]);

  useEffect(() => {
    if (!showWaveform) return;
    const track = waveformTrackRef.current;
    if (!track || typeof ResizeObserver === "undefined") return;
    let raf = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        captureWaveformMask();
      });
    });
    observer.observe(track);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [showWaveform, captureWaveformMask]);

  useEffect(() => {
    if (!showStemStack) {
      setExpandedStems(false);
    }
  }, [showStemStack]);

  const handleDownloadAll = useCallback(async () => {
    if (!splitResults.length || downloadingAll) return;
    setDownloadingAll(true);
    setSplitError(null);
    try {
      const payload = {
        title: video?.title || "SplitMe Stems",
        targetDir: saveFolderPath || undefined,
        stems: splitResults.map((stem) => ({
          stem: stem.stem,
          streamUrl: stem.streamUrl,
          format: stem.format || "mp3",
        })),
      };

      if (electronAPI?.downloadStems) {
        const result = await electronAPI.downloadStems(payload);
        if (result && result.ok === false) {
          throw new Error(result.error || "Download failed");
        }
      } else {
        for (const item of payload.stems) {
          const response = await fetch(item.streamUrl);
          if (!response.ok) {
            throw new Error("Failed to download stem");
          }
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          const safeTitle = (payload.title || "Stem").replace(/[\\/:*?"<>|]+/g, "-");
          const filename = `${safeTitle}-${item.stem}.${item.format || "mp3"}`;
          link.href = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      }
    } catch (err) {
      console.error("Failed to download stems:", err);
      setSplitError(err.message || "Unable to download stems.");
    } finally {
      setDownloadingAll(false);
    }
  }, [downloadingAll, electronAPI, saveFolderPath, splitResults, video?.title]);

  const handleToggleExpanded = useCallback(() => {
    setExpandedStems((prev) => !prev);
  }, []);

  const formatTimeForFile = useCallback((seconds = 0) => {
    const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
    const total = Math.floor(safeSeconds);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${mins}-${secs.toString().padStart(2, "0")}`;
  }, []);

  const applyWaveformZoom = useCallback(
    (value) => {
      const nextValue =
        Number.isFinite(value) && value > 0 ? value : WAVEFORM_ZOOM_DEFAULT;
      if (waveformInstance?.zoom) {
        waveformInstance.zoom(nextValue);
      }
      if (mutedWaveformRef.current?.zoom) {
        mutedWaveformRef.current.zoom(nextValue);
      }
      waveformZoomRef.current = nextValue;
    },
    [waveformInstance, WAVEFORM_ZOOM_DEFAULT]
  );

  useEffect(() => {
    if (!waveformInstance || !duration) return;
    if (advancedMode && waveformZoomed) return;
    const targetZoom = getFitZoom();
    applyWaveformZoom(targetZoom);
  }, [
    advancedMode,
    applyWaveformZoom,
    duration,
    getFitZoom,
    waveformInstance,
    waveformZoomed,
  ]);

  const animateWaveformZoom = useCallback(
    (target) => {
      const from = waveformZoomRef.current ?? getFitZoom();
      if (zoomAnimRef.current) {
        cancelAnimationFrame(zoomAnimRef.current);
      }
      if (!waveformInstance && !mutedWaveformRef.current) {
        waveformZoomRef.current = target;
        return;
      }
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / WAVEFORM_ZOOM_ANIM_MS);
        const eased = 1 - Math.pow(1 - t, 3);
        const next = from + (target - from) * eased;
        applyWaveformZoom(next);
        if (t < 1) {
          zoomAnimRef.current = requestAnimationFrame(step);
        }
      };
      zoomAnimRef.current = requestAnimationFrame(step);
    },
    [applyWaveformZoom, waveformInstance, WAVEFORM_ZOOM_ANIM_MS, getFitZoom]
  );

  useEffect(() => {
    if (!advancedMode && waveformZoomed) {
      setWaveformZoomed(false);
      animateWaveformZoom(getFitZoom());
    }
  }, [advancedMode, waveformZoomed, animateWaveformZoom, getFitZoom]);

  const handleZoomToggle = useCallback(() => {
    const next = !waveformZoomed;
    setWaveformZoomed(next);
    const target = next ? WAVEFORM_ZOOM_IN : getFitZoom();
    animateWaveformZoom(target);
  }, [animateWaveformZoom, getFitZoom, waveformZoomed, WAVEFORM_ZOOM_IN]);

  const ensureDecodedAudio = useCallback(async () => {
    if (decodedAudioRef.current) return decodedAudioRef.current;
    if (!audioBlob) return null;
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioContextClass();
    }
    const buffer = await audioBlob.arrayBuffer();
    const decoded = await audioContextRef.current.decodeAudioData(buffer.slice(0));
    decodedAudioRef.current = decoded;
    return decoded;
  }, [audioBlob]);

  useEffect(() => {
    setClipReady(false);
    if (!audioBlob || !electronAPI) return;
    let cancelled = false;
    ensureDecodedAudio()
      .then((decoded) => {
        if (!cancelled && decoded) {
          setClipReady(true);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.warn("Failed to pre-decode audio for clip export:", err);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [audioBlob, electronAPI, ensureDecodedAudio]);

  const buildClipBuffer = useCallback((decoded, startSeconds, endSeconds) => {
    if (!decoded) return null;
    const sampleRate = decoded.sampleRate;
    const startSample = Math.max(0, Math.floor(startSeconds * sampleRate));
    const endSample = Math.min(decoded.length, Math.ceil(endSeconds * sampleRate));
    const frameCount = Math.max(0, endSample - startSample);
    if (!frameCount) return null;
    let context = audioContextRef.current;
    if (!context) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      context = new AudioContextClass();
      audioContextRef.current = context;
    }
    const clipBuffer = context.createBuffer(
      decoded.numberOfChannels,
      frameCount,
      sampleRate
    );
    for (let channel = 0; channel < decoded.numberOfChannels; channel += 1) {
      const channelData = decoded.getChannelData(channel).slice(startSample, endSample);
      clipBuffer.getChannelData(channel).set(channelData);
    }
    return clipBuffer;
  }, []);

  const buildSelectionWavBufferSync = useCallback(
    (startSeconds, endSeconds) => {
      const decoded = decodedAudioRef.current;
      const clipBuffer = buildClipBuffer(decoded, startSeconds, endSeconds);
      if (!clipBuffer) return null;
      return audioAnalyzer.audioBufferToWavArrayBuffer(clipBuffer);
    },
    [buildClipBuffer]
  );

  const resolveExportRange = useCallback(() => {
    const highlight = highlightRef.current;
    const highlightStartValue = Math.min(highlight.start, highlight.end);
    const highlightEndValue = Math.max(highlight.start, highlight.end);
    const hasHighlight =
      highlightActive && highlightEndValue > highlightStartValue;
    if (hasHighlight) {
      return { start: highlightStartValue, end: highlightEndValue };
    }
    const selection = selectionRef.current;
    return {
      start: Math.min(selection.start, selection.end),
      end: Math.max(selection.start, selection.end),
    };
  }, [highlightActive]);

  const handleSelectionDragStart = useCallback(
    (event) => {
      if (!electronAPI) return;
      const { start: rangeStart, end: rangeEnd } = resolveExportRange();
      if (!audioBlob || rangeEnd <= rangeStart) return;
      const baseTitle = video?.title || video?.id || "SplitMe Clip";
      const fileName = `${baseTitle} ${formatTimeForFile(rangeStart)}-${formatTimeForFile(
        rangeEnd
      )}.wav`;
      const displayName = `Clip ${formatTime(rangeStart)}-${formatTime(rangeEnd)}`;
      const syncBuffer = buildSelectionWavBufferSync(rangeStart, rangeEnd);
      if (!syncBuffer) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "copy";
      }
      electronAPI.dragWaveformClip({
        data: syncBuffer,
        fileName,
        displayName,
      });
    },
    [
      audioBlob,
      buildSelectionWavBufferSync,
      electronAPI,
      formatTimeForFile,
      resolveExportRange,
      video?.id,
      video?.title,
    ]
  );

  const handleSelectSaveFolder = useCallback(async () => {
    if (!electronAPI?.pickSaveFolder) return;
    try {
      const next = await electronAPI.pickSaveFolder();
      if (next) setSaveFolderPath(next);
    } catch (err) {
      console.error("Failed to open folder picker:", err);
    }
  }, [electronAPI]);

  const clearHighlight = useCallback(() => {
    setHighlightActive(false);
    setHighlightRange(0, 0);
  }, [setHighlightRange]);

  useEffect(() => {
    if (!showWaveform || !highlightActive) return;
    const handleDown = (event) => {
      const track = waveformTrackRef.current;
      if (!track || track.contains(event.target)) return;
      clearHighlight();
    };
    window.addEventListener("pointerdown", handleDown);
    return () => window.removeEventListener("pointerdown", handleDown);
  }, [clearHighlight, highlightActive, showWaveform]);

  useEffect(() => {
    if (showStemStack && waveformInstance?.pause) {
      try {
        waveformInstance.pause();
      } catch (err) {
        /* ignore pause errors */
      }
    }
  }, [showStemStack, waveformInstance]);

  const scrollWaveformToTime = useCallback(
    (time, behavior = "auto") => {
      if (!compactMode) return;
      const scrollEl = waveformScrollRef.current;
      if (!scrollEl || !duration) return;
      const scrollWidth = scrollEl.scrollWidth;
      const clientWidth = scrollEl.clientWidth;
      if (scrollWidth <= clientWidth) return;
      const ratio = Math.max(0, Math.min(1, time / duration));
      const target = ratio * (scrollWidth - clientWidth);
      if (typeof scrollEl.scrollTo === "function") {
        scrollEl.scrollTo({ left: target, behavior });
      } else {
        scrollEl.scrollLeft = target;
      }
    },
    [compactMode, duration]
  );

  if (!video) return null;

  const audioFormatOptions = [
    { value: "wav", label: "WAV" },
    { value: "aiff", label: "AIFF" },
    { value: "m4a", label: "M4A" },
    { value: "mp3", label: "MP3" },
  ];

  const aiModelOptions = [
    { value: "ht-demucs-v4", label: "HT Demucs v4" },
    { value: "mdxnet-hq", label: "MDXNet HQ" },
  ];

  const rate = 1;
  const waveformHeight = compactMode ? 140 : 200;
  const waveformScrollPxPerSec = compactMode ? 22 : 18;
  const allowWaveformScroll = advancedMode && waveformZoomed;
  const showAdvancedConsole = advancedMode && !compactMode;
  const advancedConsoleActive =
    showAdvancedConsole &&
    (splitStatus === "processing" || splitStatus === "queued");
  const advancedConsoleStatusLabel = !advancedConsoleActive
    ? "IDLE"
    : splitStatus === "queued"
      ? "QUEUED"
      : "LIVE";
  const waveformScrollWidth =
    allowWaveformScroll && duration
      ? Math.min(12000, Math.max(duration * waveformScrollPxPerSec, 0))
      : null;
  const waveformTrackStyle = {
    "--waveform-height": `${waveformHeight}px`,
    width: waveformScrollWidth ? `${Math.max(waveformScrollWidth, 1)}px` : "100%",
    minWidth: "100%",
  };
  const progress = duration ? Math.min(1, current / duration) : 0;
  const playheadPosition = Math.min(Math.max(progress, 0), 1);
  const gradientPlaying = waveformInstance ? waveformPlaying : playing;
  const normalizedStart = Math.min(selectionStart, selectionEnd);
  const normalizedEnd = Math.max(selectionStart, selectionEnd);
  const selectionStartPct = duration
    ? Math.min(1, Math.max(0, normalizedStart / duration))
    : 0;
  const selectionEndPct = duration
    ? Math.min(1, Math.max(0, normalizedEnd / duration))
    : 0;
  const highlightNormalizedStart = Math.min(highlightStart, highlightEnd);
  const highlightNormalizedEnd = Math.max(highlightStart, highlightEnd);
  const useHighlightForExport =
    activeDrag === "selection" ||
    (highlightActive && highlightNormalizedEnd > highlightNormalizedStart);
  const exportNormalizedStart = useHighlightForExport
    ? highlightNormalizedStart
    : normalizedStart;
  const exportNormalizedEnd = useHighlightForExport
    ? highlightNormalizedEnd
    : normalizedEnd;
  const exportStartPct = duration
    ? Math.min(1, Math.max(0, exportNormalizedStart / duration))
    : 0;
  const exportEndPct = duration
    ? Math.min(1, Math.max(0, exportNormalizedEnd / duration))
    : 0;
  const exportWidthPct = Math.max(0, exportEndPct - exportStartPct);
  const showSelectionOverlay =
    exportWidthPct > 0 &&
    exportWidthPct < 0.999 &&
    (useHighlightForExport || selectionEnd > selectionStart);
  const activeClip = showTimeline
    ? `inset(0 ${(1 - selectionEndPct) * 100}% 0 ${selectionStartPct * 100}%)`
    : "inset(0 0 0 0)";
  const seek = (s) => {
    const targetTime = Math.max(0, Math.min(duration, s));
    if (waveformInstance?.setTime) {
      waveformInstance.setTime(targetTime);
      setCurrent(targetTime);
      scrollWaveformToTime(targetTime, "smooth");
      return;
    }
    if (video.isLocalFile) {
      if (ytRef.current) {
        ytRef.current.currentTime = targetTime;
      }
    } else {
      ytRef.current?.seek(targetTime);
    }
    scrollWaveformToTime(targetTime, "smooth");
  };

  return (
    <motion.div
      className={`dashboard${compactMode ? " compact" : ""}${
        advancedMode ? " advanced" : ""
      }`}
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ type: "spring", stiffness: 160, damping: 22, mass: 0.95, delay: 0.06 }}
    >
      <div className={`dash-loading-glow${showLoadingGlow ? " active" : ""}`}>
        <span className="glow-orb orb-a">
          <span className="glow-orb-layer layer-one" />
          <span className="glow-orb-layer layer-two" />
          <span className="glow-orb-layer layer-three" />
        </span>
        <span className="glow-orb orb-b">
          <span className="glow-orb-layer layer-one" />
          <span className="glow-orb-layer layer-two" />
          <span className="glow-orb-layer layer-three" />
        </span>
        <span className="glow-orb orb-c">
          <span className="glow-orb-layer layer-one" />
          <span className="glow-orb-layer layer-two" />
          <span className="glow-orb-layer layer-three" />
        </span>
      </div>
      <div className="dash-header" style={{ WebkitAppRegion: "drag" }}>
        {video.thumbnail && (
          <img src={video.thumbnail} className="dash-thumbnail" alt="" />
        )}
        {!video.thumbnail && video.isLocalFile && (
          <div className="dash-thumbnail local-file-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <path
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        )}
        <div className="dash-info">
          <h2 className="dash-title">{video.title}</h2>
          <p className="dash-artist">{video.channel}</p>
        </div>
        {compactMode && canUseCompactMode && (
          <div
            className="compact-window-controls"
            style={{ WebkitAppRegion: "no-drag" }}
          >
            <button
              type="button"
              className="compact-window-btn"
              onClick={() => setSettingsOpen(true)}
              title="Settings"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 8.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7z"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
                <path
                  d="M19.4 15a1.6 1.6 0 00.32 1.76l.06.06a1.8 1.8 0 01-2.55 2.55l-.06-.06a1.6 1.6 0 00-1.76-.32 1.6 1.6 0 00-1 1.46V21a1.8 1.8 0 01-3.6 0v-.1a1.6 1.6 0 00-1-1.46 1.6 1.6 0 00-1.76.32l-.06.06a1.8 1.8 0 01-2.55-2.55l.06-.06A1.6 1.6 0 005 15a1.6 1.6 0 00-1.46-1H3.5a1.8 1.8 0 010-3.6h.1A1.6 1.6 0 005 8.94a1.6 1.6 0 00-.32-1.76l-.06-.06a1.8 1.8 0 012.55-2.55l.06.06A1.6 1.6 0 008.94 5a1.6 1.6 0 001-1.46V3.5a1.8 1.8 0 013.6 0v.1A1.6 1.6 0 0015 5a1.6 1.6 0 001.76-.32l.06-.06a1.8 1.8 0 012.55 2.55l-.06.06A1.6 1.6 0 0019 8.94a1.6 1.6 0 001.46 1h.1a1.8 1.8 0 010 3.6h-.1a1.6 1.6 0 00-1.46 1z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <button
              type="button"
              className="compact-window-btn"
              onClick={() => handleCompactToggle(false)}
              title="Expand view"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <button
              type="button"
              className="compact-window-btn"
              onClick={handleCompactMinimize}
              title="Minimize"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 12h14"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </button>
            <button
              type="button"
              className="compact-window-btn exit"
              onClick={handleCompactQuit}
              title="Exit SplitMe"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        )}
        <div className="dash-window-controls" style={{ WebkitAppRegion: "no-drag" }}>
          {canUseCompactMode && (
            <button
              className={`dash-compact-toggle${compactMode ? " active" : ""}`}
              onClick={() => handleCompactToggle()}
              style={{ WebkitAppRegion: "no-drag" }}
              title={compactMode ? "Exit compact mode" : "Enter compact mode"}
              type="button"
            >
              {compactMode ? (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <rect
                    x="5"
                    y="5"
                    width="14"
                    height="14"
                    rx="2.5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  />
                  <rect
                    x="9"
                    y="9"
                    width="6"
                    height="6"
                    rx="1.5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  />
                </svg>
              )}
            </button>
          )}
          <button
            className="dash-settings"
            onClick={() => setSettingsOpen(true)}
            style={{ WebkitAppRegion: "no-drag" }}
            type="button"
            title="Settings"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 8.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7z"
                stroke="currentColor"
                strokeWidth="1.8"
              />
              <path
                d="M19.4 15a1.6 1.6 0 00.32 1.76l.06.06a1.8 1.8 0 01-2.55 2.55l-.06-.06a1.6 1.6 0 00-1.76-.32 1.6 1.6 0 00-1 1.46V21a1.8 1.8 0 01-3.6 0v-.1a1.6 1.6 0 00-1-1.46 1.6 1.6 0 00-1.76.32l-.06.06a1.8 1.8 0 01-2.55-2.55l.06-.06A1.6 1.6 0 005 15a1.6 1.6 0 00-1.46-1H3.5a1.8 1.8 0 010-3.6h.1A1.6 1.6 0 005 8.94a1.6 1.6 0 00-.32-1.76l-.06-.06a1.8 1.8 0 012.55-2.55l.06.06A1.6 1.6 0 008.94 5a1.6 1.6 0 001-1.46V3.5a1.8 1.8 0 013.6 0v.1A1.6 1.6 0 0015 5a1.6 1.6 0 001.76-.32l.06-.06a1.8 1.8 0 012.55 2.55l-.06.06A1.6 1.6 0 0019 8.94a1.6 1.6 0 001.46 1h.1a1.8 1.8 0 010 3.6h-.1a1.6 1.6 0 00-1.46 1z"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <div className="dash-close-pill" style={{ WebkitAppRegion: "no-drag" }}>
            <button
              type="button"
              className="dash-close-action back"
              onClick={onBack}
              title="Back"
              style={{ WebkitAppRegion: "no-drag" }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path
                  d="M14 6l-6 6 6 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <button
              type="button"
              className="dash-close-action minimize"
              onClick={handleCompactMinimize}
              title="Minimize"
              style={{ WebkitAppRegion: "no-drag" }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 12h14"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
            <button
              className="dash-close"
              onClick={onBack}
              style={{ WebkitAppRegion: "no-drag" }}
              title="Close"
              type="button"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {settingsOpen && (
        <div
          className="settings-overlay"
          style={{ WebkitAppRegion: "no-drag" }}
          onClick={() => setSettingsOpen(false)}
        >
          <div
            className="settings-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="settings-panel-header">
              <h3>Settings</h3>
              <button
                className="settings-close"
                onClick={() => setSettingsOpen(false)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M18 6L6 18M6 6l12 12"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>
            <div className="settings-section">
              <div className="settings-label">Save Folder Location</div>
              <button
                type="button"
                className="settings-folder"
                onClick={handleSelectSaveFolder}
                title="Choose a folder"
              >
                <span className="settings-folder-icon" aria-hidden="true">
                  <svg width="26" height="20" viewBox="0 0 26 20" fill="none">
                    <path
                      d="M2.5 6.5a2 2 0 012-2h5.2l2 2h9.8a2 2 0 012 2v6.5a2 2 0 01-2 2H4.5a2 2 0 01-2-2v-8.5z"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="settings-folder-path">
                  {saveFolderPath || "Choose a folder"}
                </span>
              </button>
            </div>
            <div className="settings-section">
              <div className="settings-advanced-row">
                <div className="settings-label">Advanced Mode</div>
                <button
                  className={`settings-toggle${advancedMode ? " active" : ""}`}
                  onClick={() => setAdvancedMode((prev) => !prev)}
                >
                  {advancedMode ? "ON" : "OFF"}
                </button>
              </div>
              <p className="settings-description">
                This enables advanced customized features including fine tuning of AI model performance and rich control
                features. Follow the advanced mode guide before enabling this feature.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="dash-content" style={{ WebkitAppRegion: "no-drag" }}>
        <div className="dash-sidebar" ref={sidebarRef}>
          <div className="dash-controls">
            <div className="dash-select-row">
              <CustomDropdown
                options={audioFormatOptions}
                placeholder="Select audio format"
                value={audioFormat}
                onChange={setAudioFormat}
                pushContent={!advancedMode}
              />

              <CustomDropdown
                options={aiModelOptions}
                placeholder="Select AI Model"
                value={aiModel}
                onChange={setAiModel}
                pushContent={false}
              />
            </div>

            {advancedMode && (
              <div className="advanced-controls">
                <div className="advanced-slider overlap">
                  <label htmlFor="advanced-overlap">Overlap</label>
                  <input
                    id="advanced-overlap"
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={modelOverlap}
                    onChange={(event) => setModelOverlap(Number(event.target.value))}
                  />
                </div>
                <div className="advanced-slider shifts">
                  <label htmlFor="advanced-shifts">Shifts</label>
                  <input
                    id="advanced-shifts"
                    type="range"
                    min="0"
                    max="10"
                    step="1"
                    value={modelShifts}
                    onChange={(event) => setModelShifts(Number(event.target.value))}
                  />
                </div>
              </div>
            )}

            <div className="stem-list">
              {Object.entries(stems).map(([k, v]) => (
                <div
                  key={k}
                  className={`stem-item ${v ? "active" : ""}`}
                  onClick={() => setStems((s) => ({ ...s, [k]: !v }))}
                >
                  <span className="stem-dot" />
                  <span className="stem-label">
                    {k.charAt(0).toUpperCase() + k.slice(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button
            className="split-audio-btn"
            onClick={handleSplitAudio}
            disabled={
              splitStatus === "processing" ||
              splitStatus === "queued" ||
              audioLoading
            }
          >
            {splitStatus === "processing" || splitStatus === "queued"
              ? "SPLITTING..."
              : "SPLIT AUDIO"}
          </button>
        </div>

        <div
          className={`dash-waveform-container${
            showAdvancedConsole ? " has-advanced-console" : ""
          }`}
          ref={waveformContainerRef}
        >
          {/* New backend-powered accurate waveform */}
          <div className={`waveform-wrapper${showStemStack ? " stems" : ""}`}>
            {audioLoading && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#fff",
                  fontSize: "12px",
                }}
              >
                Loading accurate waveform...
              </div>
            )}

            {!audioLoading && showStemStack && (
              <StemCardStack
                stems={splitResults}
                artist={video.channel || video.title || ""}
                onDownloadAll={handleDownloadAll}
                onToggleExpand={handleToggleExpanded}
                expanded={expandedStems}
                downloading={downloadingAll}
              />
            )}

            {!audioLoading && !showStemStack && isSplitRunning && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#fff",
                  fontSize: "12px",
                }}
              >
                Splitting stems… this can take a minute.
              </div>
            )}

            {!audioLoading && splitStatus === "error" && splitError && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#ff6b6b",
                  fontSize: "10px",
                  textAlign: "center",
                  padding: "0 12px",
                }}
              >
                {splitError}
              </div>
            )}

            {showWaveform && (
              <>
                <div
                  className={`waveform-scroll${allowWaveformScroll ? " scrollable" : ""}`}
                  ref={waveformScrollRef}
                >
                  <div
                    className="waveform-track"
                    ref={waveformTrackRef}
                    style={waveformTrackStyle}
                  >
                    <div className="waveform-layer muted">
                      <WaveformPlayer
                        url={backendAudioUrl}
                        blob={audioBlob}
                        height={waveformHeight}
                        interact={false}
                        normalize
                        barHeight={1}
                        waveColor="rgba(255, 255, 255, 0.25)"
                        progressColor="rgba(255, 255, 255, 0.25)"
                        onWaveformReady={handleMutedWaveformReady}
                        onPlayStateChange={null}
                      />
                    </div>
                    <div
                      className={`waveform-layer active${waveformMask ? " gradient-active" : ""}`}
                      style={{ clipPath: activeClip }}
                    >
                      <WaveformPlayer
                        url={backendAudioUrl}
                        blob={audioBlob}
                        height={waveformHeight}
                        normalize
                        barHeight={1}
                        onWaveformReady={handleWaveformReady}
                        onPlayStateChange={handleWaveformPlayStateChange}
                      />
                      {waveformMask && (
                        <canvas
                          ref={gradientCanvasRef}
                          className={`waveform-gradient-canvas${
                            gradientPlaying ? " playing" : ""
                          }`}
                        />
                      )}
                    </div>
                    <div
                      className="waveform-selection-layer"
                      onPointerDown={startSelectionDrag}
                    >
                      {showSelectionOverlay && (
                        <div
                          className="waveform-selection"
                          style={{
                            left: `${exportStartPct * 100}%`,
                            width: `${exportWidthPct * 100}%`,
                          }}
                          draggable={Boolean(electronAPI && clipReady)}
                          onPointerDown={(event) => event.stopPropagation()}
                          onDragStart={handleSelectionDragStart}
                          onDragEnd={() => electronAPI?.dragWaveformEnd?.()}
                          title={
                            electronAPI
                              ? clipReady
                                ? "Drag to export WAV clip"
                                : "Preparing clip export..."
                              : "Clip export is available in the desktop app"
                          }
                        />
                      )}
                    </div>
                    {showTimeline && (
                      <>
                        <div
                          className="waveform-handle start"
                          style={{ left: `${selectionStartPct * 100}%` }}
                          onPointerDown={startDrag("start")}
                        >
                          <div className="waveform-handle-bracket" />
                          <div className="waveform-handle-time">
                            {formatTime(selectionStart)}
                          </div>
                        </div>
                        <div
                          className="waveform-handle end"
                          style={{ left: `${selectionEndPct * 100}%` }}
                          onPointerDown={startDrag("end")}
                        >
                          <div className="waveform-handle-bracket" />
                          <div className="waveform-handle-time">
                            {formatTime(selectionEnd)}
                          </div>
                        </div>
                        <div
                          className="waveform-playhead"
                          style={{ left: `${playheadPosition * 100}%` }}
                          onPointerDown={startDrag("playhead")}
                        >
                          <div className="waveform-playhead-label">
                            {formatTime(current)}
                          </div>
                          <div className="waveform-playhead-line" />
                        </div>
                      </>
                    )}
                  </div>
                </div>
                {advancedMode && (
                  <button
                    type="button"
                    className={`waveform-zoom-btn${waveformZoomed ? " active" : ""}`}
                    onClick={handleZoomToggle}
                    disabled={!waveformInstance}
                    title={waveformZoomed ? "Reset zoom" : "Zoom waveform"}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <circle
                        cx="11"
                        cy="11"
                        r="6.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                      />
                      <path
                        d="M16.5 16.5L21 21"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                      />
                      <path
                        d="M11 8.5v5M8.5 11h5"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                )}
              </>
            )}

            {!audioLoading && audioError && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#ff6b6b",
                  fontSize: "10px",
                  textAlign: "center",
                }}
              >
                {audioError}
              </div>
            )}

          </div>

          {!showStemStack && (
            <>
              <div className={`dash-transport${transportLoading ? " loading" : ""}`}>
                <button className="transport-btn" onClick={() => seek(current - 5)}>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M16 15V5l-3.5 2.5L9 10l3.5 2.5L16 15zm-7 0V5l-3.5 2.5L2 10l3.5 2.5L9 15z" />
                  </svg>
                </button>
                <button
                  className="transport-btn play"
                  onClick={() => {
                    if (waveformInstance) {
                      waveformInstance.playPause();
                    } else if (video.isLocalFile) {
                      playing ? ytRef.current?.pause() : ytRef.current?.play();
                    } else {
                      playing ? ytRef.current?.pause() : ytRef.current?.play();
                    }
                  }}
                >
                  {(waveformInstance ? waveformPlaying : playing) ? (
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <rect x="6" y="4" width="4" height="16" rx="1" />
                      <rect x="14" y="4" width="4" height="16" rx="1" />
                    </svg>
                  ) : (
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  )}
                </button>
                <button className="transport-btn" onClick={() => seek(current + 5)}>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M4 5v10l3.5-2.5L11 10l-3.5-2.5L4 5zm7 0v10l3.5-2.5L18 10l-3.5-2.5L11 5z" />
                  </svg>
                </button>
              </div>
            </>
          )}
          {showAdvancedConsole && (
            <div
              className={`advanced-console-shell${
                advancedConsoleActive ? " open" : ""
              }`}
            >
              <div className="advanced-console-pill" />
              <div className="advanced-console-panel">
                <div className="advanced-console-header">
                  <div className="advanced-console-title">
                    <span className="advanced-console-dot" />
                    Advanced Console
                  </div>
                  <div
                    className={`advanced-console-status${
                      advancedConsoleActive ? " live" : " idle"
                    }`}
                  >
                    {advancedConsoleStatusLabel}
                  </div>
                </div>
                <div className="advanced-console-body" aria-live="polite">
                  {advancedConsoleLines.map((line, index) => (
                    <div
                      key={`${line.time}-${index}`}
                      className="advanced-console-line"
                    >
                      <span className="advanced-console-time">{line.time}</span>
                      <span className="advanced-console-message">
                        {line.message}
                      </span>
                    </div>
                  ))}
                  {advancedConsoleActive && (
                    <span className="advanced-console-cursor" />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {video.isLocalFile ? (
        <audio
          ref={ytRef}
          src={video.filePath}
          volume={Math.max(0, Math.min(1, volume / 100))}
          onLoadedMetadata={(e) => {
            if (waveformInstance) return;
            setDuration(e.target.duration);
          }}
          onTimeUpdate={(e) => {
            if (waveformInstance) return;
            setCurrent(e.target.currentTime);
            if (
              loop?.a != null &&
              loop?.b != null &&
              e.target.currentTime >= loop.b
            ) {
              e.target.currentTime = loop.a;
            }
          }}
          onPlay={() => {
            if (waveformInstance) return;
            setPlaying(true);
          }}
          onPause={() => {
            if (waveformInstance) return;
            setPlaying(false);
          }}
          onEnded={() => {
            if (waveformInstance) return;
            setPlaying(false);
          }}
          style={{ display: "none" }}
        />
      ) : (
        <YouTubePlayer
          ref={ytRef}
          videoId={video.id}
          volume={volume}
          playbackRate={rate}
          onReady={(_, i) => {
            if (waveformInstance) return;
            setDuration(i.duration || ytRef.current?.getDuration() || 0);
          }}
          onStateChange={(e) => {
            if (waveformInstance) return;
            setPlaying(
              e.data === 1
                ? true
                : e.data === 0 || e.data === 2
                ? false
                : playing
            );
          }}
          onTime={(t, d) => {
            if (waveformInstance) return;
            setCurrent(t);
            if (d && d !== duration) setDuration(d);
            if (loop?.a != null && loop?.b != null && t >= loop.b) seek(loop.a);
          }}
        />
      )}

    </motion.div>
  );
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
