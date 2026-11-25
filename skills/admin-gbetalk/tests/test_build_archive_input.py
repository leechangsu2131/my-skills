"""scripts/build_archive_input.py 의 main() 시험 — 원본 캡처(JSONL) + 확인용 CSV → 검증된 JSONL·보관 Markdown.

    python -m pytest tests -v      (admin-gbetalk 폴더에서)

가짜 쪽지(발신자A·본문1 …)와 임시 폴더만 쓴다. 이 스크립트는 지비톡 화면이나 외부 서비스를 건드리지 않는다.
작은 도우미 함수(날짜 비교 등)는 test_archive_helpers.py 쪽에서 다루므로 여기서는 입력 검증과 파일 병합 흐름을 본다.
"""
import hashlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_archive_input as bai  # noqa: E402


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def raw_row(seq, body, **extra):
    return {"sequence": seq, "body": body, "body_sha256": sha(body), "row_sha256": f"행지문{seq}", **extra}


def write_raw(path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def write_csv(path, lines, header="sequence,title,received_date"):
    path.write_text(header + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def files(tmp_path):
    """기본 자료: 10월 쪽지 2개 + 9월 쪽지 1개(최신순)."""
    write_raw(tmp_path / "raw.jsonl", [raw_row(1, "본문1"), raw_row(2, "본문2"), raw_row(3, "본문3")])
    write_csv(tmp_path / "meta.csv", ["1,발신자A,2026-10-22", "2,발신자B,2026-10-21", "3,발신자C,2026-09-30"])
    return tmp_path


def run(files, *extra, month="2026-10", out="out.jsonl", raw="raw.jsonl", meta="meta.csv"):
    argv = ["build_archive_input.py", str(files / raw), str(files / meta), str(files / out), "--month", month, *extra]
    old = sys.argv
    sys.argv = argv
    try:
        return bai.main()
    finally:
        sys.argv = old


def out_rows(files, name="out.jsonl"):
    return [json.loads(line) for line in (files / name).read_text(encoding="utf-8").splitlines()]


# ───────────────────────── 정상 흐름 ─────────────────────────

def test_selects_only_target_month_and_keeps_newest_first(files, capsys):
    assert run(files) == 0
    rows = out_rows(files)
    assert [(r["received_date"], r["title"], r["body"], r["capture_sequence"]) for r in rows] == [
        ("2026-10-22", "발신자A", "본문1", 1), ("2026-10-21", "발신자B", "본문2", 2)]
    assert rows[0]["body_sha256"] == sha("본문1") and rows[0]["row_sha256"] == "행지문1"
    out = capsys.readouterr().out
    assert "Wrote 2 verified rows" in out and "2026-10-22 through 2026-10-21" in out


def test_output_digest_printed_matches_file(files, capsys):
    run(files)
    printed = capsys.readouterr().out.split("SHA-256 ")[1].strip()
    assert printed == hashlib.sha256((files / "out.jsonl").read_bytes()).hexdigest()


def test_timestamp_rows_are_kept_as_received_at(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22 11:20:00", "2,발신자B,2026-10-21T09:00:00", "3,발신자C,2026-09-30 08:00:00"],
              header="sequence,title,received_at")
    run(files)
    rows = out_rows(files)
    assert [r["received_at"] for r in rows] == ["2026-10-22T11:20:00", "2026-10-21T09:00:00"]
    assert "received_date" not in rows[0]


def test_date_can_come_from_raw_row_when_csv_cell_is_empty(files):
    write_raw(files / "raw.jsonl", [raw_row(1, "본문1", received_date="2026-10-22"), raw_row(2, "본문2", received_date="2026-10-21"),
                                    raw_row(3, "본문3", received_date="2026-09-30")])
    write_csv(files / "meta.csv", ["1,발신자A,", "2,발신자B,", "3,발신자C,"])
    run(files)
    assert [r["received_date"] for r in out_rows(files)] == ["2026-10-22", "2026-10-21"]


def test_title_whitespace_is_normalized(files):
    write_csv(files / "meta.csv", ['1,"발신자A\n안내",2026-10-22', "2,발신자B,2026-10-21", "3,발신자C,2026-09-30"])
    run(files)
    assert out_rows(files)[0]["title"] == "발신자A 안내"


def test_same_day_notes_are_not_treated_as_going_newer(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22", "2,발신자B,2026-10-22", "3,발신자C,2026-09-30"])
    assert run(files) == 0


# ───────────────────────── 원본 캡처(raw) 검증 ─────────────────────────

def test_raw_sequence_gap_is_error(files):
    write_raw(files / "raw.jsonl", [raw_row(1, "본문1"), raw_row(3, "본문3")])
    with pytest.raises(ValueError, match="does not follow"):
        run(files)
    assert not (files / "out.jsonl").exists()


def test_raw_body_hash_mismatch_is_error(files):
    bad = raw_row(2, "본문2")
    bad["body"] = "몰래 바뀐 본문"
    write_raw(files / "raw.jsonl", [raw_row(1, "본문1"), bad, raw_row(3, "본문3")])
    with pytest.raises(ValueError, match="invalid body SHA-256"):
        run(files)
    assert not (files / "out.jsonl").exists()


def test_raw_missing_row_fingerprint_or_field_is_error(files):
    no_fp = raw_row(1, "본문1")
    del no_fp["row_sha256"]
    write_raw(files / "raw.jsonl", [no_fp])
    with pytest.raises(ValueError, match="invalid body SHA-256 or row fingerprint"):
        run(files)
    (files / "raw.jsonl").write_text('{"sequence": 1}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid row"):
        run(files)


# ───────────────────────── 확인용 CSV 검증 ─────────────────────────

@pytest.mark.parametrize("lines,header,message", [
    (["1,발신자A,2026-10-22"], "sequence,received_date", "sequence and title"),
    (["1,발신자A,2026-10-22", "1,발신자B,2026-10-21", "3,발신자C,2026-09-30"], None, "duplicate sequence"),
    (["1,발신자A,2026-10-22", "9,발신자B,2026-10-21", "3,발신자C,2026-09-30"], None, "no raw sequence 9"),
    (["1,,2026-10-22", "2,발신자B,2026-10-21", "3,발신자C,2026-09-30"], None, "empty title"),
    (["1,발신자A,어제", "2,발신자B,2026-10-21", "3,발신자C,2026-09-30"], None, "invalid value"),
    (["1,발신자A,2026-10-21", "2,발신자B,2026-10-22", "3,발신자C,2026-09-30"], None, "move newer at sequence 2"),
    (["1,발신자A,2026-10-22", "3,발신자C,2026-09-30"], None, "contiguous prefix"),
    ([], None, "no message rows"),
])
def test_csv_problems_are_errors_and_write_nothing(files, lines, header, message):
    write_csv(files / "meta.csv", lines, **({"header": header} if header else {}))
    with pytest.raises(ValueError, match=message):
        run(files)
    assert not (files / "out.jsonl").exists()


def test_csv_cannot_mix_date_only_and_timestamp_rows(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22 11:00:00,", "2,발신자B,,2026-10-21", "3,발신자C,,2026-09-30"],
              header="sequence,title,received_at,received_date")
    with pytest.raises(ValueError, match="cannot mix"):
        run(files)


def test_csv_timestamp_with_utc_offset_is_error(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22T11:00:00+09:00", "2,발신자B,2026-10-21T09:00:00", "3,발신자C,2026-09-30T08:00:00"],
              header="sequence,title,received_at")
    with pytest.raises(ValueError, match="UTC offset"):
        run(files)


def test_csv_with_both_date_columns_filled_is_error(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22,2026-10-22 11:00:00", "2,발신자B,2026-10-21,", "3,발신자C,2026-09-30,"],
              header="sequence,title,received_date,received_at")
    with pytest.raises(ValueError, match="only one of"):
        run(files)


def test_target_month_without_notes_is_error(files):
    with pytest.raises(ValueError, match="no messages in target month 2026-08"):
        run(files, month="2026-08")


def test_bad_month_argument_exits(files):
    with pytest.raises(SystemExit) as exc:
        run(files, month="10월")
    assert exc.value.code == 2


# ───────────────────────── 인자 안전장치 ─────────────────────────

def test_output_must_differ_from_inputs(files):
    with pytest.raises(SystemExit):
        run(files, out="raw.jsonl")
    assert "본문1" in (files / "raw.jsonl").read_text(encoding="utf-8")          # 원본은 그대로


def test_only_one_markdown_mode_allowed(files):
    (files / "arch.md").write_text("## 2026-10-23 — 발신자Z\n\n본문Z\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        run(files, "--markdown-output", str(files / "new.md"), "--prepend-to", str(files / "arch.md"))


def test_markdown_output_never_overwrites_existing_file(files):
    (files / "new.md").write_text("기존", encoding="utf-8")
    with pytest.raises(SystemExit):
        run(files, "--markdown-output", str(files / "new.md"))
    assert (files / "new.md").read_text(encoding="utf-8") == "기존"


def test_markdown_output_writes_standalone_archive(files):
    run(files, "--markdown-output", str(files / "new.md"))
    assert (files / "new.md").read_text(encoding="utf-8") == (
        "## 2026-10-22 — 발신자A\n\n본문1\n\n## 2026-10-21 — 발신자B\n\n본문2\n")


# ───────────────────────── 기존 보관 파일에 이어 붙이기 ─────────────────────────

NEWER = "## 2026-10-25 08:00:00 — 발신자Z\n\n본문Z\n"


def make_archive(files, text, newline="\n"):
    path = files / "arch.md"
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def test_prepend_adds_newer_records_in_front_and_keeps_old_text(files):
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-27", "2,발신자B,2026-10-26", "3,발신자C,2026-09-30"])
    arch = make_archive(files, NEWER)
    run(files, "--prepend-to", str(arch))
    text = arch.read_text(encoding="utf-8")
    assert text == "## 2026-10-27 — 발신자A\n\n본문1\n\n## 2026-10-26 — 발신자B\n\n본문2\n\n" + NEWER
    assert not list(files.glob(".*.tmp"))                                        # 임시 파일이 남지 않는다


def test_prepend_refuses_records_not_newer_than_archive_head(files):
    arch = make_archive(files, NEWER)                                           # 머리 2026-10-25 보다 새롭지 않은 쪽지(10-22, 10-21)
    before = arch.read_bytes()
    with pytest.raises(ValueError, match="must be newer than existing archive head"):
        run(files, "--prepend-to", str(arch))
    assert arch.read_bytes() == before and not (files / "out.jsonl").exists()


def test_append_adds_older_records_at_the_end_and_keeps_crlf(files):
    older = "## 2026-10-23 10:00:00 — 발신자Z\n\n본문Z\n"
    arch = make_archive(files, older, newline="\r\n")
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22 11:20:00", "2,발신자B,2026-10-21 09:00:00", "3,발신자C,2026-09-30 08:00:00"],
              header="sequence,title,received_at")
    run(files, "--append-to", str(arch))
    data = arch.read_bytes().decode("utf-8")
    assert data.startswith("## 2026-10-23 10:00:00 — 발신자Z\r\n\r\n본문Z")
    assert "## 2026-10-22 11:20:00 — 발신자A\r\n\r\n본문1" in data
    assert "\n" not in data.replace("\r\n", "")                                  # 줄바꿈이 모두 CRLF 로 통일


def test_append_refuses_records_not_older_than_archive_tail(files):
    arch = make_archive(files, "## 2026-10-20 08:00:00 — 발신자Z\n\n본문Z\n")
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-22 11:20:00", "2,발신자B,2026-10-21 09:00:00", "3,발신자C,2026-09-30 08:00:00"],
              header="sequence,title,received_at")
    before = arch.read_bytes()
    with pytest.raises(ValueError, match="must be older than existing archive tail"):
        run(files, "--append-to", str(arch))
    assert arch.read_bytes() == before


def test_merge_refuses_unordered_or_unrecognized_archive_or_a_note_already_at_the_head(files):
    unordered = make_archive(files, "## 2026-10-20 — A\n\n가\n\n## 2026-10-25 — B\n\n나\n")
    with pytest.raises(ValueError, match="not ordered newest-to-oldest"):
        run(files, "--prepend-to", str(unordered))
    unordered.write_text("그냥 글\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no recognized records"):
        run(files, "--prepend-to", str(unordered))
    write_csv(files / "meta.csv", ["1,발신자A,2026-10-27", "2,발신자B,2026-10-26", "3,발신자C,2026-09-30"])
    # 이미 보관된 쪽지(같은 날짜)를 다시 앞에 붙이려 하면 '머리보다 새로워야 한다' 검사에서 먼저 거절된다
    dup = make_archive(files, "## 2026-10-26 — 발신자B\n\n본문2\n\n## 2026-10-20 — 발신자Y\n\n본문Y\n")
    before = dup.read_bytes()
    with pytest.raises(ValueError, match="must be newer than existing archive head"):
        run(files, "--prepend-to", str(dup))
    assert dup.read_bytes() == before


# ───────────────────────── 범위 기록(range manifest) ─────────────────────────

def test_range_manifest_describes_newest_and_oldest(files):
    run(files, "--range-manifest", str(files / "range.json"))
    info = json.loads((files / "range.json").read_text(encoding="utf-8"))
    assert info["month"] == "2026-10" and info["record_count"] == 2
    assert info["newest"]["sender"] == "발신자A" and info["oldest"]["sender"] == "발신자B"
    assert info["newest"]["body_preview"] == "본문1"
    assert info["verified_jsonl_sha256"] == hashlib.sha256((files / "out.jsonl").read_bytes()).hexdigest()


def test_range_manifest_existing_with_different_contents_is_refused_and_same_is_kept(files):
    run(files, "--range-manifest", str(files / "range.json"))
    first = (files / "range.json").read_bytes()
    run(files, "--range-manifest", str(files / "range.json"))                   # 같은 내용이면 그대로 통과
    assert (files / "range.json").read_bytes() == first
    (files / "range.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists with different contents"):
        run(files, "--range-manifest", str(files / "range.json"))


def test_range_manifest_must_not_be_an_input_file(files):
    with pytest.raises(SystemExit):
        run(files, "--range-manifest", str(files / "raw.jsonl"))
