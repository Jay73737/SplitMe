import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutGroup, motion } from "framer-motion";

export const STEM_COLORS = [
  "#6546FED6",
  "#0009FF47",
  "#0088FF52",
  "#5100FF80",
  "#7300FF80",
  "#BF00FF80",
  "#FF00B757",
];

export const STEM_LABELS = {
  vocals: "Vocal Stem Split",
  drums: "Drum Stem Split",
  bass: "Bass Stem Split",
  guitar: "Guitar Stem Split",
  piano: "Piano Stem Split",
  other: "Other Stem Split",
};

const MIME_TYPES = {
  mp3: "audio/mpeg",
  wav: "audio/wav",
  flac: "audio/flac",
  aiff: "audio/aiff",
  aif: "audio/aiff",
  m4a: "audio/mp4",
  opus: "audio/ogg",
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const formatTime = (seconds = 0) => {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const total = Math.floor(safeSeconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

export default function StemCardStack({
  stems,
  artist = "",
  onDownloadAll,
  onToggleExpand,
  downloading = false,
  expanded = false,
}) {
  const layoutTransition = {
    duration: 0.9,
    ease: [0.22, 1, 0.36, 1],
    type: "tween",
  };
  const decorated = useMemo(
    () =>
      stems.map((stem, index) => {
        const key = (stem.stem || "").toLowerCase();
        const title = STEM_LABELS[key] || `${key.charAt(0).toUpperCase()}${key.slice(1)} Stem Split`;
        return {
          ...stem,
          stem: key,
          title,
          color: STEM_COLORS[index % STEM_COLORS.length],
          duration: stem.duration ?? 0,
          format: stem.format,
          filePath: stem.filePath,
        };
      }),
    [stems]
  );

  const [activeIndex, setActiveIndex] = useState(0);
  const [playingIndex, setPlayingIndex] = useState(null);
  const [currentTimes, setCurrentTimes] = useState(() => decorated.map((stem) => stem.duration ?? 0));
  const [durations, setDurations] = useState(() => decorated.map((stem) => stem.duration ?? 0));
  const playerRef = useRef(null);
  const playingIndexRef = useRef(playingIndex);
  const wheelLockRef = useRef(false);
  const wasExpandedRef = useRef(expanded);
  const isExpanding = expanded && !wasExpandedRef.current;
  const isCollapsing = !expanded && wasExpandedRef.current;
  const expandStagger = 0.16;
  const collapseStagger = 0.12;

  useEffect(() => {
    playingIndexRef.current = playingIndex;
  }, [playingIndex]);

  useEffect(() => {
    wasExpandedRef.current = expanded;
  }, [expanded]);

  useEffect(() => {
    if (!playerRef.current && typeof window !== "undefined") {
      const audio = document.createElement("audio");
      audio.preload = "none";
      audio.style.display = "none";
      document.body.appendChild(audio);
      playerRef.current = audio;
    }

    const player = playerRef.current;
    if (!player) return undefined;

    const handleTimeUpdate = () => {
      const index = playingIndexRef.current;
      if (index == null) return;
      const value = player.currentTime || 0;
      setCurrentTimes((prev) => {
        if (prev[index] === value) return prev;
        const next = [...prev];
        next[index] = value;
        return next;
      });
    };

    const handleLoadedMetadata = () => {
      const index = playingIndexRef.current;
      if (index == null) return;
      const value = player.duration || decorated[index]?.duration || 0;
      setDurations((prev) => {
        if (prev[index] === value) return prev;
        const next = [...prev];
        next[index] = value;
        return next;
      });
    };

    const handleEnded = () => {
      setPlayingIndex(null);
    };

    player.addEventListener("timeupdate", handleTimeUpdate);
    player.addEventListener("loadedmetadata", handleLoadedMetadata);
    player.addEventListener("ended", handleEnded);

    return () => {
      player.removeEventListener("timeupdate", handleTimeUpdate);
      player.removeEventListener("loadedmetadata", handleLoadedMetadata);
      player.removeEventListener("ended", handleEnded);
    };
  }, [decorated]);

  useEffect(() => {
    const player = playerRef.current;
    player?.pause?.();
    setPlayingIndex(null);
    setCurrentTimes(decorated.map((stem) => stem.duration ?? 0));
    setDurations(decorated.map((stem) => stem.duration ?? 0));
    setActiveIndex((prev) => clamp(prev, 0, Math.max(decorated.length - 1, 0)));
  }, [decorated]);

  useEffect(() => () => {
    const player = playerRef.current;
    if (player) {
      player.pause();
      player.src = "";
      player.remove();
      playerRef.current = null;
    }
  }, []);

  const navigate = useCallback(
    (delta) => {
      if (!decorated.length) return;
      setActiveIndex((prev) => {
        const total = decorated.length;
        const next = (prev + delta + total) % total;
        return next;
      });
    },
    [decorated.length]
  );

  useEffect(() => {
    const handler = (event) => {
      if (decorated.length === 0) return;
      if (event.key === "ArrowUp") {
        event.preventDefault();
        navigate(-1);
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        navigate(1);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [decorated.length, navigate]);

  const handleWheel = useCallback(
    (event) => {
      if (expanded) return;
      if (!decorated.length || wheelLockRef.current) return;
      event.preventDefault();
      wheelLockRef.current = true;
      navigate(event.deltaY > 0 ? 1 : -1);
      setTimeout(() => {
        wheelLockRef.current = false;
      }, 250);
    },
    [navigate, decorated.length, expanded]
  );

  const togglePlayback = useCallback(
    async (index) => {
      const player = playerRef.current;
      if (!player) return;

      if (playingIndex === index) {
        player.pause();
        setPlayingIndex(null);
        return;
      }

      try {
        player.pause();
        const target = decorated[index];
        if (!target) return;
        if (player.src !== target.streamUrl) {
          player.src = target.streamUrl;
        }
        player.currentTime = 0;
        player.load();
        await player.play();
        setPlayingIndex(index);
      } catch (err) {
        console.error("Failed to play stem:", err);
        setPlayingIndex(null);
      }
    },
    [decorated, playingIndex]
  );

  const handleDragStart = useCallback((event, stem) => {
    if (!stem) return;
    event.stopPropagation?.();
    if (event?.dataTransfer) {
      event.dataTransfer.effectAllowed = "copy";
      const safeTitle = ((stem.title || stem.stem || "Stem").toString()).replace(/[\\/:*?"<>|]+/g, "-");
      try {
        event.dataTransfer.setData("text/plain", safeTitle);
      } catch (_) {
        /* ignore */
      }
      const dragTarget = event.currentTarget;
      if (dragTarget instanceof HTMLElement) {
        const rect = dragTarget.getBoundingClientRect();
        const clone = dragTarget.cloneNode(true);
        if (clone instanceof HTMLElement) {
          clone.style.width = `${rect.width}px`;
          clone.style.height = `${rect.height}px`;
          clone.style.position = "fixed";
          clone.style.top = "-1000px";
          clone.style.left = "-1000px";
          clone.style.margin = "0";
          clone.style.transform = "none";
          clone.style.pointerEvents = "none";
          clone.style.opacity = "0.95";
          clone.style.zIndex = "9999";
          document.body.appendChild(clone);
          event.dataTransfer.setDragImage(
            clone,
            Math.round(rect.width / 2),
            Math.round(rect.height / 2)
          );
          setTimeout(() => {
            clone.remove();
          }, 0);
        }
      }
      if (stem.streamUrl) {
        try {
          event.dataTransfer.setData("text/uri-list", stem.streamUrl);
        } catch (_) {
          /* ignore */
        }
        const format = (stem.format || "mp3").toLowerCase();
        const downloadName = `${safeTitle}.${format}`;
        try {
          const mime = MIME_TYPES[format] || `audio/${format}`;
          event.dataTransfer.setData("DownloadURL", `${mime}:${downloadName}:${stem.streamUrl}`);
        } catch (_) {
          /* ignore */
        }
      }
    }

    if (window?.electronAPI?.dragStem && stem.filePath) {
      const dragTarget = event.currentTarget;
      let dragRect = null;
      if (dragTarget instanceof HTMLElement) {
        const rect = dragTarget.getBoundingClientRect();
        if (rect.width && rect.height) {
          dragRect = {
            x: Math.round(rect.left + window.scrollX),
            y: Math.round(rect.top + window.scrollY),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        }
      }
      window.electronAPI.dragStem({
        filePath: stem.filePath,
        displayName: `${stem.title || stem.stem || "Stem"}.${(stem.format || "mp3").toLowerCase()}`,
        dragRect,
        pixelRatio: typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1,
      });
    }
  }, []);

  const gridRows = useMemo(() => {
    if (!expanded) return [];

    const rows = [];
    const total = decorated.length;
    if (total <= 3) {
      rows.push(decorated);
      return rows;
    }

    const firstRow = decorated.slice(0, Math.min(3, total));
    rows.push(firstRow);

    let remaining = decorated.slice(firstRow.length);

    if (total === 4) {
      rows.push(remaining);
      return rows;
    }

    if (total === 5) {
      rows.push(remaining);
      return rows;
    }

    while (remaining.length) {
      rows.push(remaining.slice(0, 3));
      remaining = remaining.slice(3);
    }

    return rows;
  }, [decorated, expanded]);

  if (!decorated.length) {
    return null;
  }

  return (
    <LayoutGroup id="stem-stack">
      <div className={`stem-stack${expanded ? " expanded" : ""}`} onWheel={handleWheel}>
        <div className={`stem-stack-inner${expanded ? " expanded" : ""}`}>
          {!expanded &&
            decorated.map((stem, index) => {
              const offset = ((index - activeIndex) + decorated.length) % decorated.length;
              const visible = offset <= 3;
              const translateY = offset * 24;
              const scale = 1 - offset * 0.06;
              const opacity = offset === 3 ? 0.4 : 1;
              const zIndex = decorated.length - offset;
              const isActive = index === activeIndex;
              const isPlaying = index === playingIndex;
              const timelineSeconds = isPlaying ? currentTimes[index] : durations[index];
              const delay = isCollapsing
                ? (decorated.length - 1 - index) * collapseStagger
                : 0;

              return (
                <motion.div
                  key={stem.stem}
                  className={`stem-card${isActive ? " active" : ""}${
                    isPlaying ? " playing" : ""
                  }`}
                  layout="position"
                  layoutId={`stem-card-${stem.stem}`}
                  transition={{
                    layout: { ...layoutTransition, delay },
                    scale: { ...layoutTransition, delay },
                    opacity: {
                      duration: 0.3,
                      ease: [0.22, 1, 0.36, 1],
                      delay,
                    },
                  }}
                  style={{
                    background: `linear-gradient(135deg, ${stem.color} 0%, rgba(15, 15, 35, 0.85) 100%)`,
                    top: translateY,
                    scale,
                    opacity: visible ? opacity : 0,
                    zIndex,
                  }}
                  draggable={Boolean(stem.filePath || stem.streamUrl)}
                  onDragStart={(event) => handleDragStart(event, stem)}
                >
                  <div className="stem-card-content">
                    <div className="stem-card-header">
                      <span className="stem-card-title">{stem.title}</span>
                      <span className="stem-card-artist">{artist}</span>
                    </div>
                    <div className="stem-card-footer">
                      <span className="stem-card-time">{formatTime(timelineSeconds)}</span>
                      <button
                        type="button"
                        className="stem-card-play"
                        onClick={() => togglePlayback(index)}
                      >
                        {isPlaying ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <rect x="7" y="5" width="3.5" height="14" rx="1.2" fill="white" />
                            <rect x="13.5" y="5" width="3.5" height="14" rx="1.2" fill="white" />
                          </svg>
                        ) : (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <path d="M8 5v14l11-7z" fill="white" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                </motion.div>
              );
            })}

          {expanded &&
            gridRows.map((row, rowIndex) => {
              const rowLength = row.length;
              const rowClass = `stem-grid-row ${rowLength === 3 ? "full" : "centered"}`;
              return (
                <div key={`row-${rowIndex}`} className={rowClass}>
                  {row.map((stem, index) => {
                    const globalIndex = rowIndex * 3 + index;
                    const delay = isExpanding ? globalIndex * expandStagger : 0;
                    const stackOffset =
                      ((globalIndex - activeIndex) + decorated.length) % decorated.length;
                    const stackVisible = stackOffset <= 3;
                    const stackOpacity = stackOffset === 3 ? 0.4 : 1;
                    const isActive = globalIndex === activeIndex;
                    const isPlaying = globalIndex === playingIndex;
                    const timelineSeconds = isPlaying
                      ? currentTimes[globalIndex]
                      : durations[globalIndex];

                    return (
                      <motion.div
                        key={stem.stem}
                        className={`stem-card expanded${isActive ? " active" : ""}${
                          isPlaying ? " playing" : ""
                        }`}
                        layout="position"
                        layoutId={`stem-card-${stem.stem}`}
                        initial={{ opacity: stackVisible ? stackOpacity : 0 }}
                        animate={{ opacity: 1 }}
                        transition={{
                          layout: { ...layoutTransition, delay },
                          opacity: {
                            duration: 0.45,
                            ease: [0.22, 1, 0.36, 1],
                            delay,
                          },
                        }}
                        style={{
                          background: `linear-gradient(135deg, ${stem.color} 0%, rgba(15, 15, 35, 0.85) 100%)`,
                        }}
                        draggable={Boolean(stem.filePath || stem.streamUrl)}
                        onDragStart={(event) => handleDragStart(event, stem)}
                      >
                        <div className="stem-card-content">
                          <div className="stem-card-header">
                            <span className="stem-card-title">{stem.title}</span>
                            <span className="stem-card-artist">{artist}</span>
                          </div>
                          <div className="stem-card-footer">
                            <span className="stem-card-time">{formatTime(timelineSeconds)}</span>
                            <button
                              type="button"
                              className="stem-card-play"
                              onClick={() => togglePlayback(globalIndex)}
                            >
                              {isPlaying ? (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                                  <rect x="7" y="5" width="3.5" height="14" rx="1.2" fill="white" />
                                  <rect x="13.5" y="5" width="3.5" height="14" rx="1.2" fill="white" />
                                </svg>
                              ) : (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                                  <path d="M8 5v14l11-7z" fill="white" />
                                </svg>
                              )}
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              );
            })}
        </div>
        {!expanded && (
          <div className="stem-stack-instructions">Use ↑↓ keys or scroll to navigate</div>
        )}
        <div className={`stem-stack-actions${expanded ? " expanded" : ""}`}>
          <div className={`stem-action-pill${downloading ? " disabled" : ""}`}>
            <button
              type="button"
              className="stem-pill-btn"
              onClick={() => onDownloadAll?.()}
              disabled={downloading}
              aria-label="Download all stems"
              title={downloading ? "Downloading…" : "Download all stems"}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 3v14" />
                <path d="M5 14l7 7 7-7" />
                <path d="M5 21h14" />
              </svg>
            </button>
            <span className="stem-pill-divider" aria-hidden="true" />
            <button
              type="button"
              className="stem-pill-btn"
              onClick={() => onToggleExpand?.()}
              aria-label={expanded ? "Collapse stem view" : "Expand stem view"}
              title={expanded ? "Collapse stem view" : "Expand stem view"}
            >
              {expanded ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="9 3 3 3 3 9" />
                  <polyline points="15 21 21 21 21 15" />
                  <line x1="3" y1="9" x2="10" y2="16" />
                  <line x1="21" y1="15" x2="14" y2="8" />
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="15 3 21 3 21 9" />
                  <polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" />
                  <line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              )}
            </button>
          </div>
          {downloading && <span className="stem-pill-status">Preparing downloads…</span>}
        </div>
      </div>
    </LayoutGroup>
  );
}
