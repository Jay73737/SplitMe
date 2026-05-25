import React, { useLayoutEffect, useRef, useState } from "react";

export default function VibrancyMask({
  targetSelector = ".pill-window",
  radius = 39,
  inset = 2,
  overlayColor = "rgba(13,13,13,0.7)",
  zIndex = 0,
}) {
  const [dims, setDims] = useState({ vw: 0, vh: 0 });
  const [cut, setCut] = useState({ x: 0, y: 0, w: 0, h: 0, r: radius });

  useLayoutEffect(() => {
    const update = () => {
      const el = document.querySelector(targetSelector);
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      setDims({ vw, vh });
      if (!el) return;
      const b = el.getBoundingClientRect();
      const pad = Math.max(0, inset);
      setCut({
        x: Math.round(b.x + pad),
        y: Math.round(b.y + pad),
        w: Math.max(0, Math.round(b.width - pad * 2)),
        h: Math.max(0, Math.round(b.height - pad * 2)),
        r: Math.max(0, radius - pad),
      });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(document.documentElement);
    const mo = new MutationObserver(update);
    mo.observe(document.body, {
      attributes: true,
      childList: true,
      subtree: true,
    });
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      ro.disconnect();
      mo.disconnect();
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [targetSelector, radius, inset]);

  return (
    <svg
      className="vibrancy-mask"
      width={dims.vw}
      height={dims.vh}
      viewBox={`0 0 ${dims.vw} ${dims.vh}`}
      style={{
        position: "fixed",
        inset: 0,
        zIndex,
        pointerEvents: "none",
        shapeRendering: "crispEdges",
      }}
    >
      <defs>
        <mask id="vmask" maskUnits="userSpaceOnUse">
          <rect x="0" y="0" width={dims.vw} height={dims.vh} fill="white" />
          <rect
            x={cut.x}
            y={cut.y}
            width={cut.w}
            height={cut.h}
            rx={cut.r}
            ry={cut.r}
            fill="black"
          />
        </mask>
      </defs>

      <rect
        x="0"
        y="0"
        width={dims.vw}
        height={dims.vh}
        fill={overlayColor}
        mask="url(#vmask)"
      />
    </svg>
  );
}
