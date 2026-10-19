from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .ingest import youtube_video_id


def _timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _video_link(video_url: str | None, seconds: float) -> str | None:
    if not video_url:
        return None
    parsed = urlparse(video_url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {"youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}:
        return None
    video_id = youtube_video_id(video_url)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}&t={max(0, int(seconds))}s"


def write_report(project_data: dict, project_dir: Path) -> Path:
    project_dir = Path(project_dir)
    summary_link = '<p><a href="summary.md">강의 요약 및 슬라이드별 정리 보기 ↗</a></p>' if (project_dir / "summary.md").is_file() else ""
    slides = project_data.get("slides", [])
    cards: list[str] = []
    for idx, slide in enumerate(slides, 1):
        image_rel = Path("slides") / Path(slide["image_path"]).name
        image_src = html.escape(image_rel.as_posix(), quote=True)
        start = float(slide.get("start_time", slide.get("first_seen", 0.0)))
        end = float(slide.get("end_time", start))
        best = float(slide.get("best_frame_time", start))
        url = _video_link(project_data.get("source_url"), best)
        link = f'<a href="{url}" target="_blank" rel="noopener">YouTube { _timestamp(best) }에서 열기 ↗</a>' if url else f'<span class="muted">대표 프레임 { _timestamp(best) }</span>'
        texts = slide.get("transcript", [])
        transcript_html = "\n".join(
            f'<li><span class="time">{_timestamp(float(seg["start"]))}–{_timestamp(float(seg["end"]))}</span> {html.escape(str(seg["text"]))}</li>'
            for seg in texts
        ) or '<li class="muted">이 구간에 연결된 자막이 없습니다.</li>'
        duplicate = f'<span class="tag">중복 후보: {html.escape(str(slide["duplicate_of"]))}</span>' if slide.get("duplicate_of") else ""
        cards.append(f'''<article class="slide">
          <div class="preview"><img loading="lazy" src="{image_src}" alt="슬라이드 {idx}"></div>
          <div class="body"><div class="topline"><h2>슬라이드 {idx:04d}</h2>{duplicate}</div>
          <p class="times">구간 {_timestamp(start)}–{_timestamp(end)} · 처음 관찰 {_timestamp(float(slide.get('first_seen', start)))} · 안정 확인 {_timestamp(float(slide.get('stable_from', start)))} · 대표 이미지 {_timestamp(best)}</p>
          <p>{link}</p><ul class="transcript">{transcript_html}</ul></div>
        </article>''')
    warnings = project_data.get("warnings", [])
    warning_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings)
    title = html.escape(str(project_data.get("project_id", "LectureCapture 프로젝트")))
    source = html.escape(str(project_data.get("source_video", "")))
    page = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - LectureCapture</title>
<style>
:root{{--bg:#f4f6f8;--panel:#fff;--ink:#19212b;--muted:#596575;--line:#dce2e8;--accent:#245c8f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
header{{padding:28px max(20px,calc((100vw - 1200px)/2));background:#152b42;color:white}}header h1{{margin:0 0 8px;font-size:1.7rem}}header p{{margin:4px 0;color:#dce8f3;overflow-wrap:anywhere}}
main{{max-width:1200px;margin:22px auto;padding:0 16px}}.notice{{background:#fff8e6;border:1px solid #e8d59b;padding:12px 16px;border-radius:10px;margin-bottom:18px}}
.slide{{display:grid;grid-template-columns:minmax(280px,42%) 1fr;gap:20px;background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:0 0 18px;box-shadow:0 2px 6px #1b2d3d0a}}
.preview{{background:#111;display:flex;align-items:center;justify-content:center;min-height:180px}}.preview img{{display:block;max-width:100%;max-height:440px;object-fit:contain}}
.body{{padding:18px 20px;min-width:0}}.topline{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}h2{{font-size:1.12rem;margin:0}}.times{{font-size:.9rem;color:var(--muted)}}a{{color:var(--accent);font-weight:600}}.muted{{color:var(--muted)}}.tag{{font-size:.78rem;background:#f7e8ca;color:#6d4b0d;padding:3px 8px;border-radius:5px}}.transcript{{padding-left:20px}}.transcript li{{margin:7px 0}}.time{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:.85rem}}
footer{{max-width:1200px;margin:24px auto;padding:0 16px 40px;color:var(--muted);font-size:.85rem}}
@media(max-width:760px){{.slide{{grid-template-columns:1fr}}.preview img{{max-height:320px}}}}
</style></head><body><header><h1>{title}</h1><p>LectureCapture v{__version__} · 자동 추출 결과 검토</p><p>원본: {source}</p><p>슬라이드 후보: {len(slides)}개</p>{summary_link}</header><main>
<div class="notice"><strong>검토 안내:</strong> 화면 변화 감지와 자막 연결은 자동 추정입니다. 특히 애니메이션, 화면 속 작은 변화, 반복 슬라이드는 원본 영상과 대조해 주세요.</div>
<ul>{warning_html}</ul>{''.join(cards) if cards else '<p>추출된 슬라이드가 없습니다. crop 영역 또는 임계값을 조정해 다시 실행하세요.</p>'}
</main><footer>이 보고서는 로컬에서 생성된 정적 HTML입니다. 결과 원본과 처리 설정은 project.json에 저장됩니다.</footer></body></html>'''
    output = project_dir / "report.html"
    output.write_text(page, encoding="utf-8")
    return output
