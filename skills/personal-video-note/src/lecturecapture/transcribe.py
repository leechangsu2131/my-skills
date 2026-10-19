from __future__ import annotations

import inspect
import warnings
from pathlib import Path

from .models import TranscriptSegment


def _supports_hotwords(model: object) -> bool:
    try:
        params = inspect.signature(model.transcribe).parameters  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        return False
    return "hotwords" in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


def transcribe_video(
    video_path: Path,
    model_size: str = "large-v3",
    language: str | None = "ko",
    initial_prompt: str | None = None,
    hotwords: str | None = None,
) -> list[TranscriptSegment]:
    """Optional faster-whisper wrapper. Requires `pip install -e '.[transcribe]'`."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('전사 기능을 사용하려면 `pip install -e ".[transcribe]"`를 실행하세요.') from exc

    def run(model: object, device_name: str) -> list[TranscriptSegment]:
        transcribe_options = {"language": language, "vad_filter": True}
        if initial_prompt and initial_prompt.strip():
            transcribe_options["initial_prompt"] = initial_prompt.strip()
        if hotwords and hotwords.strip():
            # `hotwords` is re-applied to every 30 s window, whereas initial_prompt only
            # lives in the rolling previous-text context and fades on long lectures.
            if _supports_hotwords(model):
                transcribe_options["hotwords"] = hotwords.strip()
            else:
                warnings.warn("설치된 faster-whisper가 hotwords를 지원하지 않아 무시합니다. `pip install -U faster-whisper`로 업데이트하세요.", RuntimeWarning, stacklevel=2)
        raw_segments, _info = model.transcribe(str(video_path), **transcribe_options)
        result: list[TranscriptSegment] = []
        # Iteration triggers actual inference; keep it inside the fallback boundary.
        for segment in raw_segments:
            text = (segment.text or "").strip()
            if text:
                result.append(TranscriptSegment(float(segment.start), float(segment.end), text, source=device_name))
        return result

    try:
        model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        return run(model, "faster-whisper-cuda")
    except Exception as cuda_error:
        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            return run(model, "faster-whisper-cpu")
        except Exception as cpu_error:
            raise RuntimeError(
                "faster-whisper 전사에 실패했습니다. GPU/CUDA 라이브러리 또는 모델 설치 상태를 확인하세요. "
                f"GPU 오류: {cuda_error}; CPU 오류: {cpu_error}"
            ) from cpu_error
