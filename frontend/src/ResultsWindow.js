import { motion } from "framer-motion";
import VideoCard from "./VideoCard";
import "./App.css";

const spring = { type: "spring", stiffness: 220, damping: 24, mass: 0.9 };

export default function ResultsWindow({ results, onSelect }) {
  if (!results?.length) return null;

  return (
    <motion.div
      className="results-window"
      initial={{ height: 0, opacity: 0, y: -20 }}
      animate={{ height: 478, opacity: 1, y: 0 }}
      exit={{ height: 0, opacity: 0, y: -20 }}
      transition={spring}
      style={{ WebkitAppRegion: "drag" }}
    >
      <motion.div
        className="results-grid"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.18, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        style={{ WebkitAppRegion: "no-drag" }}
      >
        {results.map((video) => (
          <VideoCard key={video.id} video={video} onSelect={onSelect} />
        ))}
      </motion.div>
    </motion.div>
  );
}
