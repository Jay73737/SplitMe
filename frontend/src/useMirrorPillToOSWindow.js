import { useLayoutEffect } from "react";

export default function useMirrorPillToOSWindow(
  selector = ".pill-window",
  radius = 39,
  deps = []
) {
  const extraDeps = Array.isArray(deps) ? deps : [deps];
  useLayoutEffect(() => {
    if (!window?.electronAPI?.setPillGeometry) return;
    const el = document.querySelector(selector);
    if (!el) return;

    const send = () => {
      const r = el.getBoundingClientRect();
      window.electronAPI.setPillGeometry({
        x: r.left,
        y: r.top,
        w: r.width,
        h: r.height,
        r: radius,
      });
    };

    send();
    const ro = new ResizeObserver(send);
    ro.observe(el);
    window.addEventListener("resize", send);
    window.addEventListener("scroll", send, true);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", send);
      window.removeEventListener("scroll", send, true);
    };
  }, [selector, radius, ...extraDeps]);
}
