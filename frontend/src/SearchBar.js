import { useRef, useState } from "react";
import "./App.css";

function SearchBar({
  onSearch,
  onAudioDrop,
  loading,
  children,
  introActive,
  dragOffset,
  onDragStart,
}) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [internalDragOffset, setInternalDragOffset] = useState({ x: 0, y: 0 });
  const pillRef = useRef(null);
  const dragStateRef = useRef({
    active: false,
    dragging: false,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
  });

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = value.trim();
      if (trimmed) onSearch(trimmed);
    }
  };

  const isAudioFile = (file) => {
    const audioTypes = [ 
      'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/flac', 
      'audio/aac', 'audio/ogg', 'audio/m4a', 'audio/webm'
    ];
    const audioExtensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.webm'];
    
    return audioTypes.includes(file.type) || 
           audioExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    const audioFile = files.find(isAudioFile);
    
    if (audioFile && onAudioDrop) {
      onAudioDrop(audioFile);
    }
  };

  const showPlaceholder = !introActive && !value && !focused;
  const resolvedDragOffset = dragOffset || internalDragOffset;
  const dragStyle = {
    transform: `translate3d(${resolvedDragOffset.x}px, ${resolvedDragOffset.y}px, 0)`,
  };

  const handlePointerDown = (event) => {
    if (event.button !== 0) return;
    dragStateRef.current = {
      active: true,
      dragging: false,
      startX: event.clientX,
      startY: event.clientY,
      originX: internalDragOffset.x,
      originY: internalDragOffset.y,
    };

    const handlePointerMove = (moveEvent) => {
      if (!dragStateRef.current.active) return;
      const dx = moveEvent.clientX - dragStateRef.current.startX;
      const dy = moveEvent.clientY - dragStateRef.current.startY;
      if (!dragStateRef.current.dragging) {
        if (Math.hypot(dx, dy) < 4) return;
        dragStateRef.current.dragging = true;
        document.body.style.userSelect = "none";
      }
      setInternalDragOffset({
        x: dragStateRef.current.originX + dx,
        y: dragStateRef.current.originY + dy,
      });
    };

    const handlePointerUp = () => {
      dragStateRef.current.active = false;
      dragStateRef.current.dragging = false;
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
  };

  const pointerDownHandler = onDragStart || handlePointerDown;

  return (
    <div className="pill-wrapper">
      <div className="pill-drag-shell" style={dragStyle}>
        <div 
          className={`pill-window ${dragOver ? 'drag-over' : ''}${introActive ? ' intro' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onPointerDown={pointerDownHandler}
          style={{ WebkitAppRegion: "drag" }}
          ref={pillRef}
        >
          {showPlaceholder && children}
          <input
            className="pill-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={introActive}
            style={{ WebkitAppRegion: "no-drag" }}
          />
        </div>
      </div>
    </div>
  );
}

export default SearchBar;
