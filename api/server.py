import os
import math
import random
import uuid
import shutil
import tempfile
import threading
import time
import logging
import inspect
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp  # pip install yt-dlp
from demucs import pretrained
from demucs.separate import apply_model, save_audio, load_track
from demucs.apply import BagOfModels, TensorChunk
import torch

PROJECT_ROOT = Path(os.environ.get("SPLITME_APP_ROOT", Path(__file__).resolve().parents[1]))
logger = logging.getLogger("splitme.api")

STORAGE_BASE = Path(
    os.environ.get("SPLITME_STORAGE_DIR")
    or os.environ.get("SPLITME_USER_DATA_DIR")
    or (PROJECT_ROOT / "data")
).expanduser().resolve()

# Where we cache downloaded/converted audio
DATA_DIR = (STORAGE_BASE / "audio_cache").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

STEMS_DIR = (STORAGE_BASE / "stem_cache").resolve()
STEMS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_FORMATS = {
    "mp3": ".mp3",
    "opus": ".opus",
    "wav": ".wav",
    "m4a": ".m4a",
}

SUPPORTED_STEM_FORMATS = {
    "mp3": ".mp3",
    "wav": ".wav",
    "flac": ".flac",
    "aiff": ".aiff",
    "m4a": ".m4a",
}

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".m4a": "audio/mp4",
}

MODEL_MAP = {
    "ht-demucs-v4": "htdemucs_6s",
    "mdxnet-hq": "mdx_extra_q",
}

split_jobs: Dict[str, Dict[str, Any]] = {}
split_jobs_lock = threading.Lock()
split_executor = ThreadPoolExecutor(max_workers=1)
LOG_MAX_ENTRIES = 60

app = FastAPI(title="SplitMe Audio API")

# DEV CORS (lock down origins in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadReq(BaseModel):
    sourceUrl: str
    format: Optional[str] = "mp3"  # "mp3" | "opus" | "wav" | "m4a"


class SplitAudioReq(BaseModel):
    audioId: str
    stems: List[str]
    model: Optional[str] = "ht-demucs-v4"
    format: Optional[str] = "mp3"
    startSeconds: Optional[float] = None
    endSeconds: Optional[float] = None
    overlap: Optional[float] = None
    shifts: Optional[int] = None


def _looks_like_audio(header: bytes) -> bool:
    """Best-effort sniffing of common audio container headers."""

    if not header:
        return False

    sample = header[:16]

    if sample.startswith(b"ID3"):
        return True
    if sample[:2] in (b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"):
        return True

    if sample.startswith(b"RIFF"):
        return True

    if sample.startswith(b"OggS"):
        return True

    if sample.startswith(b"fLaC"):
        return True

    if len(sample) >= 12 and sample[4:8] == b"ftyp":
        return True

    return False


def _is_broken_pipe_error(exc: Exception) -> bool:
    if isinstance(exc, BrokenPipeError):
        return True
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == 32:
        return True
    message = str(exc).lower()
    return "broken pipe" in message or "epipe" in message


def _normalize_output_format(fmt: Optional[str]) -> str:
    normalized = (fmt or "mp3").strip().lower()
    if normalized in ("aif", "aiff"):
        normalized = "aiff"
    if normalized not in SUPPORTED_STEM_FORMATS:
        raise ValueError(f"Unsupported stem format '{normalized}'.")
    return normalized


def _mime_type_for_suffix(suffix: str) -> str:
    return MIME_TYPES.get((suffix or "").lower(), "application/octet-stream")


def _convert_audio_with_ffmpeg(src_path: Path, dest_path: Path, fmt: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to export this audio format.")
    cmd = [ffmpeg, "-y", "-i", str(src_path)]
    if fmt == "m4a":
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    elif fmt == "aiff":
        cmd += ["-c:a", "pcm_s16be"]
    cmd.append(str(dest_path))
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr.strip()}")


def _download_audio_to_cache(src_url: str, fmt: str) -> Path:
    fmt = (fmt or "mp3").lower()
    if fmt not in SUPPORTED_FORMATS:
        raise RuntimeError(f"Unsupported audio format '{fmt}'.")

    expected_suffix = SUPPORTED_FORMATS[fmt]
    ext = expected_suffix.lstrip(".")

    for attempt in range(2):
        uid = str(uuid.uuid4())
        final_path = DATA_DIR / f"{uid}{expected_suffix}"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                outtmpl = str(Path(tmpdir) / f"%(id)s.%(ext)s")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "quiet": True,
                    "noprogress": True,
                    "retries": 3,
                    "fragment_retries": 3,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": ext,
                            "preferredquality": "192",
                        }
                    ],
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(src_url, download=True)
                    produced = None
                    if "requested_downloads" in info and info["requested_downloads"]:
                        produced = info["requested_downloads"][0].get("filepath")
                    if not produced:
                        for p in Path(tmpdir).glob(f"*.{ext}"):
                            produced = str(p)
                            break
                    if not produced or not os.path.exists(produced):
                        raise RuntimeError("Audio conversion failed; no output found.")

                    produced_path = Path(produced)
                    try:
                        with produced_path.open("rb") as fh:
                            header = fh.read(32)
                    except OSError:
                        header = b""

                    if not _looks_like_audio(header):
                        produced_path.unlink(missing_ok=True)
                        raise RuntimeError(
                            "Downloaded data is not an audio stream. The video may have audio downloads disabled."
                        )

                    actual_suffix = produced_path.suffix.lower()
                    if actual_suffix != expected_suffix:
                        produced_path.unlink(missing_ok=True)
                        raise RuntimeError(
                            "Audio conversion did not produce the requested format. "
                            "Ensure FFmpeg is installed and accessible."
                        )

                    shutil.move(str(produced_path), final_path)

            return final_path
        except Exception as exc:  # noqa: BLE001
            if _is_broken_pipe_error(exc) and attempt < 1:
                logger.warning("Broken pipe during download; retrying once.")
                time.sleep(0.4)
                continue
            raise


VALID_STEMS = {"vocals", "drums", "bass", "guitar", "piano", "other"}


def _normalize_stems(stems: List[str]) -> List[str]:
    cleaned: List[str] = []
    for stem in stems:
        if not stem:
            continue
        name = stem.strip().lower()
        if not name or name not in VALID_STEMS:
            continue
        if name not in cleaned:
            cleaned.append(name)
    return cleaned


def _locate_audio_file(audio_id: str) -> Path:
    matches = list(DATA_DIR.glob(f"{audio_id}.*"))
    if not matches:
        raise FileNotFoundError(f"Cached audio with id '{audio_id}' not found.")
    return matches[0]


def _set_job_state(job_id: str, **updates: Any) -> None:
    with split_jobs_lock:
        job = split_jobs.get(job_id)
        if not job:
            job = {}
            split_jobs[job_id] = job
        job.update(updates)


def _append_job_log(job_id: str, message: str) -> None:
    with split_jobs_lock:
        job = split_jobs.get(job_id)
        if not job:
            return
        started_at = job.get("started_at")
        if started_at is None:
            started_at = time.time()
            job["started_at"] = started_at
        elapsed = time.time() - started_at
        logs = job.setdefault("logs", [])
        logs.append({"time": f"+{elapsed:.2f}s", "message": message})
        if len(logs) > LOG_MAX_ENTRIES:
            del logs[:-LOG_MAX_ENTRIES]


def _run_split_job(
    job_id: str,
    audio_path: Path,
    requested_stems: List[str],
    model_alias: str,
    model_key: str,
    output_format: Optional[str],
    start_seconds: Optional[float],
    end_seconds: Optional[float],
    overlap: Optional[float],
    shifts: Optional[int],
) -> None:
    _set_job_state(job_id, status="processing", stage="loading_model")
    _append_job_log(job_id, f"Loading model {model_key} ({model_alias})")
    try:
        # Load the pretrained model
        model = pretrained.get_model(model_key)
        source_names = ", ".join(getattr(model, "sources", []) or [])
        if source_names:
            _append_job_log(job_id, f"Model ready: sources={source_names}")

        job_dir = STEMS_DIR / audio_path.stem / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Load the audio track
        _set_job_state(job_id, stage="loading_audio")
        _append_job_log(job_id, "Decoding audio track")
        wav = load_track(str(audio_path), model.audio_channels, model.samplerate)

        total_samples = wav.shape[-1]
        sample_rate = model.samplerate
        total_seconds = total_samples / sample_rate if sample_rate else 0
        _append_job_log(
            job_id,
            f"Audio ready: {total_seconds:.2f}s @ {sample_rate}Hz",
        )

        if start_seconds is not None or end_seconds is not None:
            start = 0.0 if start_seconds is None else float(start_seconds)
            end = total_seconds if end_seconds is None else float(end_seconds)
            start = max(0.0, start)
            end = min(max(start, end), total_seconds)
            start_idx = int(start * sample_rate)
            end_idx = int(end * sample_rate)
            if end_idx <= start_idx:
                raise ValueError("Invalid split range: start must be before end.")
            wav = wav[:, start_idx:end_idx]
            _append_job_log(job_id, f"Using range {start:.2f}s-{end:.2f}s")

        # Apply the model
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        apply_kwargs = {
            "device": "cpu",
            "progress": False,
        }
        overlap_value = None
        if overlap is not None:
            try:
                overlap_value = float(overlap)
            except (TypeError, ValueError):
                overlap_value = None
            if overlap_value is not None:
                overlap_value = max(0.0, min(0.99, overlap_value))
                apply_kwargs["overlap"] = overlap_value
        effective_overlap = (
            overlap_value if overlap_value is not None else apply_kwargs.get("overlap", 0.25)
        )
        shifts_value = None
        if shifts is not None:
            try:
                shifts_value = int(shifts)
            except (TypeError, ValueError):
                shifts_value = None
            if shifts_value is not None:
                shifts_value = max(0, min(20, shifts_value))
                apply_kwargs["shifts"] = shifts_value
        effective_shifts = shifts_value if shifts_value is not None else 1

        allowed_args = set(inspect.signature(apply_model).parameters)
        supports_callback = "callback" in allowed_args
        apply_kwargs = {k: v for k, v in apply_kwargs.items() if k in allowed_args}
        if isinstance(model, BagOfModels):
            segment_seconds = getattr(model, "max_allowed_segment", None)
        else:
            segment_seconds = getattr(model, "segment", None)
        if segment_seconds is not None:
            try:
                segment_seconds = float(segment_seconds)
            except (TypeError, ValueError):
                segment_seconds = None
        if not segment_seconds or segment_seconds <= 0:
            segment_seconds = 8.0
        segment_length = int(sample_rate * segment_seconds) if sample_rate else 0
        if segment_length <= 0:
            segment_length = max(1, wav.shape[-1])
        stride = int((1 - effective_overlap) * segment_length) if segment_length else 0
        if stride <= 0:
            stride = max(1, segment_length)
        offsets = list(range(0, wav.shape[-1], stride)) if stride else [0]
        segments = max(1, len(offsets))
        models_count = len(model.models) if isinstance(model, BagOfModels) else 1
        shifts_count = max(1, int(effective_shifts))
        segment_unit_weight = models_count
        segment_units = segments * segment_unit_weight * shifts_count
        total_units = segment_units + len(requested_stems)
        progress_state = {"segments_done": 0, "saves_done": 0}
        progress_lock = threading.Lock()

        def _update_progress(stage: str, done_override: Optional[int] = None) -> None:
            done = (
                done_override
                if done_override is not None
                else progress_state["segments_done"] + progress_state["saves_done"]
            )
            progress = done / total_units if total_units else 0.0
            _set_job_state(
                job_id,
                stage=stage,
                progress=progress,
                progress_done=done,
                progress_total=total_units,
            )

        _update_progress("separating")
        _append_job_log(
            job_id,
            f"Separating {segments} segments (shifts={shifts_count}, overlap={effective_overlap:.2f})",
        )

        seen_segments = set()

        def progress_callback(info: Dict[str, Any]) -> None:
            if info.get("state") != "end":
                return
            shift_idx = int(info.get("shift_idx", 0))
            model_idx = int(info.get("model_idx_in_bag", 0))
            segment_offset = int(info.get("segment_offset", 0))
            key = (model_idx, shift_idx, segment_offset)
            with progress_lock:
                if key in seen_segments:
                    return
                seen_segments.add(key)
                progress_state["segments_done"] = len(seen_segments)
                done = progress_state["segments_done"] + progress_state["saves_done"]
            segment_index = segment_offset // stride + 1 if stride else progress_state["segments_done"]
            if segment_index > segments:
                segment_index = segments
            message = f"Segment {segment_index}/{segments}"
            if shifts_count > 1:
                message += f" (shift {shift_idx + 1}/{shifts_count})"
            if models_count > 1:
                message += f" model {model_idx + 1}/{models_count}"
            _append_job_log(job_id, message)
            _update_progress("separating", done)

        if supports_callback:
            sources = apply_model(
                model,
                wav[None],
                **apply_kwargs,
                callback=progress_callback,
                callback_arg={"job_id": job_id},
            )[0]
        else:
            _append_job_log(
                job_id,
                "Demucs build lacks progress callbacks; using segment-level updates.",
            )
            manual_kwargs = dict(apply_kwargs)
            if "split" in allowed_args:
                manual_kwargs["split"] = False
            if "progress" in allowed_args:
                manual_kwargs["progress"] = False
            if "shifts" in allowed_args:
                manual_kwargs["shifts"] = 0
            if "segment" in allowed_args:
                manual_kwargs["segment"] = segment_seconds
            mix = wav[None]
            batch, channels, length = mix.shape
            weight = torch.cat(
                [
                    torch.arange(1, segment_length // 2 + 1, device=mix.device),
                    torch.arange(segment_length - segment_length // 2, 0, -1, device=mix.device),
                ]
            )
            weight = (weight / weight.max()) ** 1.0

            def run_segmented(
                mix_chunk,
                segments_total: int,
                shift_idx: Optional[int] = None,
            ) -> torch.Tensor:
                base_chunk = mix_chunk if isinstance(mix_chunk, TensorChunk) else TensorChunk(mix_chunk)
                total_len = base_chunk.length
                local_offsets = list(range(0, total_len, stride)) if stride else [0]
                out = torch.zeros(
                    batch, len(model.sources), channels, total_len, device=mix.device
                )
                sum_weight = torch.zeros(total_len, device=mix.device)
                for seg_idx, offset in enumerate(local_offsets):
                    chunk = TensorChunk(base_chunk, offset, segment_length)
                    chunk_out = apply_model(model, chunk, **manual_kwargs)
                    chunk_length = chunk_out.shape[-1]
                    out[..., offset:offset + segment_length] += (
                        weight[:chunk_length] * chunk_out
                    ).to(mix.device)
                    sum_weight[offset:offset + segment_length] += weight[:chunk_length].to(
                        mix.device
                    )
                    with progress_lock:
                        progress_state["segments_done"] += segment_unit_weight
                        done = progress_state["segments_done"] + progress_state["saves_done"]
                    message = f"Segment {seg_idx + 1}/{segments_total}"
                    if shift_idx is not None and shifts_count > 1:
                        message += f" (shift {shift_idx + 1}/{shifts_count})"
                    _append_job_log(job_id, message)
                    _update_progress("separating", done)
                out /= sum_weight
                return out

            if shifts_count > 1:
                max_shift = int(0.5 * sample_rate)
                mix_chunk = TensorChunk(mix)
                padded_mix = mix_chunk.padded(length + 2 * max_shift)
                shift_offsets = [random.randint(0, max_shift) for _ in range(shifts_count)]
                shift_lengths = [length + max_shift - offset for offset in shift_offsets]
                shift_segments = [
                    max(1, math.ceil(shift_length / stride)) for shift_length in shift_lengths
                ]
                total_units = (
                    sum(shift_segments) * segment_unit_weight + len(requested_stems)
                )
                out = torch.zeros(
                    batch, len(model.sources), channels, length, device=mix.device
                )
                for shift_idx, offset in enumerate(shift_offsets):
                    shifted = TensorChunk(padded_mix, offset, length + max_shift - offset)
                    shift_out = run_segmented(shifted, shift_segments[shift_idx], shift_idx)
                    out += shift_out[..., max_shift - offset:]
                out /= shifts_count
                sources = out[0]
            else:
                segments_total = max(1, math.ceil(length / stride)) if stride else 1
                sources = run_segmented(mix, segments_total)[0]
        _append_job_log(job_id, "Stitching segments + overlap blend")
        _update_progress("saving")

        output_format = _normalize_output_format(output_format)
        output_suffix = SUPPORTED_STEM_FORMATS[output_format]
        _append_job_log(job_id, f"Output format set to {output_format.upper()}")

        # Get the sample rate from the model
        sample_rate = model.samplerate

        # Map tensor indices to stem names based on model type
        stem_mapping = {
            'htdemucs_6s': ['drums', 'bass', 'other', 'vocals', 'guitar', 'piano'],
            'mdx_extra_q': ['drums', 'bass', 'other', 'vocals']
        }

        stem_names = stem_mapping.get(model_key, ['drums', 'bass', 'other', 'vocals'])

        results = []
        for i, stem_name in enumerate(stem_names):
            if stem_name not in requested_stems:
                continue
            if i >= sources.shape[0]:
                continue

            output_path = job_dir / f"{stem_name}{output_suffix}"

            _append_job_log(job_id, f"Saving stem {stem_name}")
            if output_format in ("mp3", "wav", "flac"):
                save_audio(
                    sources[i],
                    str(output_path),
                    sample_rate,
                    bitrate=192,
                    preset=4,
                    clip="rescale",
                )
            else:
                temp_wav = job_dir / f"{stem_name}__temp.wav"
                save_audio(
                    sources[i],
                    str(temp_wav),
                    sample_rate,
                    clip="rescale",
                )
                try:
                    _convert_audio_with_ffmpeg(temp_wav, output_path, output_format)
                finally:
                    temp_wav.unlink(missing_ok=True)
            with progress_lock:
                progress_state["saves_done"] += 1
                done = progress_state["segments_done"] + progress_state["saves_done"]
            _update_progress("saving", done)

            duration_seconds = float(sources[i].shape[-1] / sample_rate)
            results.append(
                {
                    "stem": stem_name,
                    "duration": duration_seconds,
                    "path": str(output_path),
                    "format": output_path.suffix.lstrip("."),
                }
            )

        if not results:
            raise RuntimeError(
                "Requested stems were not produced by the selected model. Try different stem choices or a different model."
            )

        _set_job_state(
            job_id,
            status="completed",
            results=results,
            output_dir=str(job_dir),
            model=model_alias,
            model_key=model_key,
            stage="completed",
            progress=1.0,
            progress_done=total_units,
            progress_total=total_units,
        )
        _append_job_log(job_id, "Split completed")
    except Exception as exc:  # noqa: BLE001
        _set_job_state(job_id, status="error", error=str(exc), stage="error")
        _append_job_log(job_id, f"Error: {exc}")


def _submit_split_job(
    audio_id: str,
    stems: List[str],
    model_alias: str,
    output_format: Optional[str],
    start_seconds: Optional[float],
    end_seconds: Optional[float],
    overlap: Optional[float],
    shifts: Optional[int],
) -> str:
    requested_stems = _normalize_stems(stems)
    if not requested_stems:
        raise ValueError("No valid stems selected for splitting.")

    audio_path = _locate_audio_file(audio_id)
    model_key = MODEL_MAP.get(model_alias, MODEL_MAP.get("ht-demucs-v4", "htdemucs_6s"))
    output_format = _normalize_output_format(output_format)

    job_id = str(uuid.uuid4())
    with split_jobs_lock:
        split_jobs[job_id] = {
            "status": "queued",
            "stage": "queued",
            "audio_id": audio_path.stem,
            "audio_path": str(audio_path),
            "requested_stems": requested_stems,
            "model": model_alias,
            "model_key": model_key,
            "output_format": output_format or "mp3",
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "overlap": overlap,
            "shifts": shifts,
            "progress": 0.0,
            "progress_done": 0,
            "progress_total": 0,
            "logs": [],
            "started_at": time.time(),
        }

    _append_job_log(job_id, "Queued split job")

    split_executor.submit(
        _run_split_job,
        job_id,
        audio_path,
        requested_stems,
        model_alias,
        model_key,
        output_format,
        start_seconds,
        end_seconds,
        overlap,
        shifts,
    )
    return job_id


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/download-audio")
def download_audio(req: DownloadReq):
    try:
        audio_path = _download_audio_to_cache(req.sourceUrl, req.format or "mp3")
        return {
            "id": audio_path.stem,
            "filename": audio_path.name,
            "mime": _mime_type_for_suffix(audio_path.suffix),
            "streamUrl": f"/api/audio/{audio_path.stem}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audio/{audio_id}")
def stream_audio(audio_id: str):
    matches = list(DATA_DIR.glob(f"{audio_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Audio not found")
    p = matches[0]
    return FileResponse(
        path=str(p),
        media_type=_mime_type_for_suffix(p.suffix),
        filename=p.name,
    )


@app.post("/api/split-audio")
def split_audio(req: SplitAudioReq):
    try:
        job_id = _submit_split_job(
            req.audioId,
            req.stems,
            req.model or "ht-demucs-v4",
            req.format or "mp3",
            req.startSeconds,
            req.endSeconds,
            req.overlap,
            req.shifts,
        )
        return {"jobId": job_id, "status": "queued"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/split-audio/{job_id}")
def split_audio_status(job_id: str):
    job = split_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Split job not found")

    response: Dict[str, Any] = {
        "jobId": job_id,
        "status": job.get("status", "unknown"),
        "audioId": job.get("audio_id"),
        "model": job.get("model"),
        "startSeconds": job.get("start_seconds"),
        "endSeconds": job.get("end_seconds"),
        "stage": job.get("stage"),
        "progress": job.get("progress"),
        "progressDone": job.get("progress_done"),
        "progressTotal": job.get("progress_total"),
        "logs": list(job.get("logs", [])),
    }

    status = response["status"]
    if status == "completed":
        results = []
        for item in job.get("results", []):
            results.append(
                {
                    "stem": item.get("stem"),
                    "duration": item.get("duration"),
                    "format": item.get("format", "mp3"),
                    "filePath": item.get("path"),
                    "streamUrl": f"/api/split-audio/{job_id}/stems/{item.get('stem')}",
                }
            )
        response["results"] = results
    elif status == "error":
        response["error"] = job.get("error", "Unknown error")

    return response


@app.get("/api/split-audio/{job_id}/stems/{stem_name}")
def get_split_stem(job_id: str, stem_name: str):
    job = split_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Split job not found")

    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Split job not completed yet")

    target_name = (stem_name or "").strip().lower()
    for item in job.get("results", []):
        if item.get("stem") == target_name:
            path_str = item.get("path")
            if not path_str:
                break
            path = Path(path_str)
            if not path.exists():
                raise HTTPException(status_code=404, detail="Stem file not found")
            return FileResponse(
                path=str(path),
                media_type=_mime_type_for_suffix(path.suffix),
                filename=path.name,
            )

    raise HTTPException(status_code=404, detail="Stem not available")


@app.delete("/api/audio/{audio_id}")
def delete_audio(audio_id: str):
    matches = list(DATA_DIR.glob(f"{audio_id}.*"))
    if not matches:
        return JSONResponse(status_code=200, content={"deleted": False})
    for p in matches:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    return {"deleted": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
