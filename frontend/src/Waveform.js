import { useRef, useState, useEffect, useCallback } from "react";
import WaveSurfer from "wavesurfer.js";
import "./App.css";

/**
 * Waveform component for rendering an audio waveform using WaveSurfer.js.
 *
 * Props:
 *  - progress: number 0..1 (from YouTube player)
 *  - duration: number seconds (YouTube duration; used by loop UI)
 *  - loop: {a:number,b:number}|null (loop start/end times in seconds)
 *  - onScrub(ratio 0..1): called when user scrubs the waveform; pass ratio to parent
 *  - onLoopChange(newLoop): called when loop markers are moved
 *  - videoId: string (YouTube ID)
 *  - onAudioLoaded?: (blob: Blob) => void  // called when a WAV blob is ready
 *  - youtubePlayer: reference to YouTube player for play state
 */
export default function Waveform({
  progress = 0,
  duration = 0,
  loop = null,
  onScrub,
  onLoopChange,
  videoId = null,
  onAudioLoaded,
  youtubePlayer = null,
}) {
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const wrapperRef = useRef(null);

  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [wsDuration, setWsDuration] = useState(0); // WaveSurfer's true duration
  const [isPlaying, setIsPlaying] = useState(false);

  // refs to hold latest callback references
  const onScrubRef = useRef(onScrub);
  const onAudioLoadedRef = useRef(onAudioLoaded);

  // Update callback refs on prop changes
  useEffect(() => {
    onScrubRef.current = onScrub;
  }, [onScrub]);
  useEffect(() => {
    onAudioLoadedRef.current = onAudioLoaded;
  }, [onAudioLoaded]);

  // Check if YouTube player is playing and update state
  useEffect(() => {
    const checkPlayState = () => {
      const playerState = youtubePlayer?.getPlayerState?.();
      const playing = playerState === 1;
      setIsPlaying(playing);
      
      // Add or remove playing class for CSS animation
      if (wrapperRef.current) {
        if (playing) {
          wrapperRef.current.classList.add('playing');
        } else {
          wrapperRef.current.classList.remove('playing');
        }
      }
    };

    const interval = setInterval(checkPlayState, 100);
    checkPlayState(); // Check immediately

    return () => clearInterval(interval);
  }, [youtubePlayer]);

  // Instantiate the WaveSurfer instance once when the component mounts
  useEffect(() => {
    // Only create a new instance if the container is ready and no instance exists
    if (!containerRef.current || wsRef.current) return;
    try {
      const ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: '#ffffff', // Use white, we'll apply gradient via CSS
        progressColor: 'rgba(255, 255, 255, 0.5)', // Semi-transparent white for progress
        height: 300,  // Increased waveform height
        normalize: false, // preserve original amplitudes
        interact: true,
        dragToSeek: true,
        partialRender: true,
        // Bars rendering options
        barWidth: 3,
        barGap: 1,
        barRadius: 3,
        barHeight: 1, // fill full height of the waveform
        cursorWidth: 0, // Hide cursor
        backend: 'WebAudio',
      });

      ws.on("ready", () => {
        // Save duration once the audio is ready
        setWsDuration(ws.getDuration() || 0);
        setLoadError(null);
      });
      
      ws.on("error", (e) => {
        console.error("WaveSurfer error:", e);
        setLoadError("Waveform render error.");
      });
      
      ws.on("seek", (ratio) => {
        // propagate seek events to parent
        onScrubRef.current?.(ratio);
      });

      wsRef.current = ws;
    } catch (e) {
      console.error("Failed to create WaveSurfer:", e);
      setLoadError("Audio renderer failed to initialize.");
    }

    // cleanup on unmount
    return () => {
      if (wsRef.current) {
        try {
          wsRef.current.destroy();
        } catch {
          /* ignore cleanup errors */
        }
        wsRef.current = null;
      }
      setWsDuration(0);
    };
  }, []);

  // Download and load audio when the videoId changes
  useEffect(() => {
    let cancelled = false;
    const ws = wsRef.current;
    if (!ws || !videoId) return;

    async function load() {
      setIsLoading(true);
      setLoadError(null);
      console.log("Loading waveform for video:", videoId);
      // If Electron API is available, use it to download audio into a Blob.
      if (window.audioAPI?.downloadAudioForVideo) {
        try {
          const { mime, data } = await window.audioAPI.downloadAudioForVideo(
            videoId
          );
          if (cancelled) return;
          const blob = new Blob([data], { type: mime || "audio/webm" });
          console.log(
            "Downloaded audio via Electron — size:",
            blob.size,
            "bytes"
          );
          ws.loadBlob(blob);
          onAudioLoadedRef.current?.(blob);
          setIsLoading(false);
          return;
        } catch (e) {
          console.error("Electron audioAPI failed:", e);
          setLoadError(`Failed to download audio: ${e.message || e}`);
          setIsLoading(false);
          return;
        }
      }
      // If no Electron API is present, inform the user rather than attempting a remote download
      setLoadError(
        "The desktop audio API is not available in this environment. Please run the application via Electron (npm run electron-dev or packaged build) so that audio can be downloaded locally."
      );
      setIsLoading(false);
      return;
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  // Sync the waveform playback cursor to the YouTube player's progress
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || !wsDuration || isDragging) return;
    const targetTime = (progress || 0) * wsDuration;
    const currentTime = ws.getCurrentTime?.() ?? 0;
    if (Math.abs(currentTime - targetTime) > 0.25) {
      ws.setTime(targetTime);
    }
  }, [progress, wsDuration, isDragging]);

  // Utility to convert mouse X coordinate into a ratio (0..1) across the waveform
  const toRatio = useCallback((clientX) => {
    const box = containerRef.current?.getBoundingClientRect();
    if (!box) return 0;
    const x = Math.min(Math.max(clientX - box.left, 0), box.width);
    return x / box.width;
  }, []);

  // Handle mouse down events for scrubbing and loop handle dragging
  const handleMouseDown = useCallback(
    (e, type) => {
      e.preventDefault();
      setIsDragging(true);
      setDragType(type);
      if (type === "scrub") {
        const r = toRatio(e.clientX);
        onScrub?.(r);
      }
    },
    [onScrub, toRatio]
  );

  // Handle mouse move events while dragging
  const handleMouseMove = useCallback(
    (e) => {
      if (!isDragging) return;
      const r = toRatio(e.clientX);
      if (dragType === "scrub") {
        onScrub?.(r);
      } else if (dragType === "start" || dragType === "end") {
        const ytTime = r * (duration || 0);
        onLoopChange?.(
          dragType === "start" ? { ...loop, a: ytTime } : { ...loop, b: ytTime }
        );
      }
    },
    [isDragging, dragType, toRatio, duration, loop, onScrub, onLoopChange]
  );

  // Handle mouse up events to end dragging
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragType(null);
  }, []);

  // Compute loop positions as ratios of the total duration
  const startPos = (loop?.a ?? 0) / (duration || 1);
  const endPos = (loop?.b ?? duration ?? 1) / (duration || 1);

  return (
    <div
      ref={wrapperRef}
      className={`waveform-wrapper waveform-gradient-wrapper ${isPlaying ? 'playing' : ''}`}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ position: "relative" }}
    >
      {/* Gradient overlay that will be masked by the waveform */}
      <div className="waveform-gradient-bg" />
      
      {/* The waveform container for WaveSurfer */}
      <div
        ref={containerRef}
        className="waveform-container"
        style={{
          width: "100%",
          height: "300px",  // Match the WaveSurfer height
          opacity: isLoading ? 0.5 : 1,
          transition: "opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1)",
          backgroundColor: "transparent",
          cursor: "pointer",
          position: "relative",
          zIndex: 2,
          borderRadius: "4px",
        }}
        onMouseDown={(e) => handleMouseDown(e, "scrub")}
      />

      {/* Loading indicator */}
      {isLoading && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "rgba(255,255,255,0.7)",
            fontSize: 14,
            fontFamily: "Inter, sans-serif",
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          Loading waveform...
        </div>
      )}

      {/* Error indicator */}
      {loadError && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "#ff6b6b",
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            textAlign: "center",
            pointerEvents: "none",
            backgroundColor: "rgba(0,0,0,0.8)",
            padding: "12px 16px",
            borderRadius: "8px",
            maxWidth: "80%",
            lineHeight: "1.4",
          }}
        >
          ⚠️ {loadError}
        </div>
      )}

      {/* Loop highlight */}
      {loop && duration > 0 && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: `${startPos * 100}%`,
            width: `${(endPos - startPos) * 100}%`,
            height: "100%",
            backgroundColor: "rgba(0,0,0,0.3)",
            pointerEvents: "none",
            zIndex: 5,
          }}
        />
      )}

      {/* Loop start handle */}
      <div
        className="waveform-clip-handle start"
        style={{ left: `${startPos * 100}%` }}
        onMouseDown={(e) => handleMouseDown(e, "start")}
      >
        <div className="clip-handle-cap" />
      </div>
      {/* Loop end handle */}
      <div
        className="waveform-clip-handle end"
        style={{ left: `${endPos * 100}%` }}
        onMouseDown={(e) => handleMouseDown(e, "end")}
      >
        <div className="clip-handle-cap" />
      </div>
    </div>
  );
}
