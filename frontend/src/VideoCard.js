import "./App.css";
import { useSelection } from "./store/selection";

function formatDuration(iso) {
  const match = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return "";
  const h = parseInt(match[1] || 0, 10);
  const m = parseInt(match[2] || 0, 10);
  const s = parseInt(match[3] || 0, 10);
  const parts = [];
  if (h) parts.push(h);
  parts.push(h ? String(m).padStart(2, "0") : m);
  parts.push(String(s).padStart(2, "0"));
  return parts.join(":");
}

function VideoCard({ video, onSelect }) {
  const { setSelected } = useSelection();
  
  const handleClick = () => {
    // Use the new backend selection system for YouTube videos
    const sourceUrl = `https://www.youtube.com/watch?v=${video.id}`;
    setSelected({
      title: video.title,
      sourceUrl: sourceUrl
    });
    
    // Also call the legacy onSelect for backwards compatibility
    if (onSelect) onSelect(video);
  };

  return (
    <div
      className="video-card"
      onClick={handleClick}
      style={{ WebkitAppRegion: "no-drag" }}
    >
      <img src={video.thumbnail} alt="thumbnail" className="thumbnail" />
      <div className="video-title">{video.title}</div>
      <div className="video-meta">
        <span>{formatDuration(video.duration)}</span>
        <span className="yt-badge">YT</span>
      </div>
    </div>
  );
}

export default VideoCard;
