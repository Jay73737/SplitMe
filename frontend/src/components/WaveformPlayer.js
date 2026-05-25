import { memo, useEffect, useState } from "react";
import WavesurferPlayer from "@wavesurfer/react";

function WaveformPlayer({
  url,
  height = 96,
  onWaveformReady,
  onPlayStateChange,
  className = "",
  interact = true,
  waveColor = "#ff2db2",
  progressColor = "#ff2db2",
  barWidth = 4,
  barGap = 2,
  barRadius = 6,
  barHeight = 1,
  normalize = false,
  cursorWidth = 0,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  useEffect(() => {
    setIsPlaying(false);
  }, [url]);

  return (
    <div
      className={`waveform-player${isPlaying ? " playing" : ""}${
        className ? ` ${className}` : ""
      }`}
      style={{
        position: "relative",
        width: "100%",
        alignSelf: "stretch",
        display: "flex",
        alignItems: "center",
        height,
        minHeight: height,
        flex: 1,
      }}
    >
      <WavesurferPlayer
        url={url ?? undefined}
        height={height}
        barWidth={barWidth}
        barGap={barGap}
        barRadius={barRadius}
        barHeight={barHeight}
        cursorWidth={cursorWidth}
        normalize={normalize}
        interact={interact}
        autoCenter={false}
        autoScroll={false}
        hideScrollbar={true}
        waveColor={waveColor}
        progressColor={progressColor}
        onReady={(instance) => {
          if (onWaveformReady) onWaveformReady(instance);
        }}
        onPlay={() => {
          setIsPlaying(true);
          if (onPlayStateChange) onPlayStateChange(true);
        }}
        onPause={() => {
          setIsPlaying(false);
          if (onPlayStateChange) onPlayStateChange(false);
        }}
        onFinish={() => {
          setIsPlaying(false);
          if (onPlayStateChange) onPlayStateChange(false);
        }}
        onError={(e) => console.error("WaveSurfer error:", e)}
      />
      {/* Play controls moved to main transport controls */}
    </div>
  );
}

export default memo(WaveformPlayer);
