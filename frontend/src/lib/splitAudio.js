import { API_BASE } from "./downloadAudio";

async function parseError(response, fallback) {
  try {
    const data = await response.clone().json();
    if (data?.detail) return data.detail;
    if (data?.error) return data.error;
  } catch (err) {
    /* swallow */
  }
  try {
    const text = await response.text();
    if (text) return text;
  } catch (err) {
    /* swallow */
  }
  return fallback;
}

export async function startStemSplit({
  audioId,
  stems,
  model,
  format,
  startSeconds,
  endSeconds,
  overlap,
  shifts,
  signal,
}) {
  const res = await fetch(`${API_BASE}/api/split-audio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      audioId,
      stems,
      model,
      format,
      startSeconds,
      endSeconds,
      overlap,
      shifts,
    }),
    signal,
  });

  if (!res.ok) {
    const message = await parseError(res, "Failed to start stem split");
    throw new Error(message);
  }

  return res.json();
}

export async function fetchStemSplitStatus(jobId, signal) {
  const res = await fetch(`${API_BASE}/api/split-audio/${jobId}`, { signal });
  if (!res.ok) {
    const message = await parseError(res, "Failed to fetch stem split status");
    throw new Error(message);
  }
  return res.json();
}
