import {
  useEffect,
  useRef,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";

const API_SRC = "https://www.youtube.com/iframe_api";

function ensureAPI() {
  return new Promise((resolve) => {
    if (window.YT?.Player) return resolve(window.YT);
    const tag = document.createElement("script");
    tag.src = API_SRC;
    document.head.appendChild(tag);
    window.onYouTubeIframeAPIReady = () => resolve(window.YT);
  });
}

const YouTubePlayer = forwardRef(function YouTubePlayer(
  { videoId, onReady, onStateChange, onTime, volume = 80, playbackRate = 1 },
  ref
) {
  const hostRef = useRef(null);
  const playerRef = useRef(null);
  const tickerRef = useRef(null);
  const onTimeRef = useRef(onTime);
  const onStateChangeRef = useRef(onStateChange);
  const onReadyRef = useRef(onReady);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    onTimeRef.current = onTime;
  }, [onTime]);

  useEffect(() => {
    onStateChangeRef.current = onStateChange;
  }, [onStateChange]);

  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  useEffect(() => {
    let disposed = false;
    ensureAPI().then((YT) => {
      if (disposed) return;
      playerRef.current = new YT.Player(hostRef.current, {
        videoId,
        width: 0,
        height: 0,
        playerVars: {
          controls: 0,
          disablekb: 1,
          modestbranding: 1,
          rel: 0,
          playsinline: 1,
        },
        events: {
          onReady: (e) => {
            setReady(true);
            e.target.setVolume(volume);
            e.target.setPlaybackRate(playbackRate);
            onReadyRef.current?.(e, {
              duration: e.target.getDuration?.() || 0,
            });
            startTicker();
          },
          onStateChange: (e) => onStateChangeRef.current?.(e),
        },
      });
    });

    function startTicker() {
      stopTicker();
      tickerRef.current = setInterval(() => {
        const p = playerRef.current;
        if (!p) return;
        const t = p.getCurrentTime?.() || 0;
        const d = p.getDuration?.() || 0;
        onTimeRef.current?.(t, d);
      }, 120);
    }
    function stopTicker() {
      if (tickerRef.current) clearInterval(tickerRef.current);
      tickerRef.current = null;
    }

    return () => {
      disposed = true;
      stopTicker();
      try {
        playerRef.current?.destroy();
      } catch {}
    };
  }, [videoId]);

  useEffect(() => {
    if (ready) playerRef.current?.setVolume?.(volume);
  }, [volume, ready]);

  useEffect(() => {
    if (ready) playerRef.current?.setPlaybackRate?.(playbackRate);
  }, [playbackRate, ready]);

  useImperativeHandle(ref, () => ({
    play: () => playerRef.current?.playVideo?.(),
    pause: () => playerRef.current?.pauseVideo?.(),
    seek: (sec) => playerRef.current?.seekTo?.(sec, true),
    getTime: () => playerRef.current?.getCurrentTime?.() || 0,
    getDuration: () => playerRef.current?.getDuration?.() || 0,
    setVolume: (v) => playerRef.current?.setVolume?.(v),
    setRate: (r) => playerRef.current?.setPlaybackRate?.(r),
    state: () => playerRef.current?.getPlayerState?.(),
  }));

  return (
    <div
      ref={hostRef}
      style={{
        width: 0,
        height: 0,
        overflow: "hidden",
        position: "absolute",
        opacity: 0,
      }}
      aria-hidden
    />
  );
});

export default YouTubePlayer;
