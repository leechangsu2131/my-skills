"""ISSUE-038(주간 정리 글의 학생 이름 가리기 한계) 재현 시험(S3). 고치지 않았고, 아직 안 고쳐진 증상은 xfail 로 표시한다.

    python -m pytest tests/test_weekly_report_issue038.py -v      (teacherlesson-assistant 폴더에서)

고치는 사람은 해당 시험의 xfail 표시를 지우고 통과시킨다(strict 라서 고쳐지면 XPASS 로 실패해 알려 준다).
이름은 모두 가짜(학생A 등)이고 임시 폴더만 쓴다. ①은 반 명단 없이는 고칠 수 없다(명단 위치 확인 필요).
"""
import json
import pathlib
import sys
from datetime import date

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import weekly_report as wr  # noqa: E402

DAY = date(2026, 11, 26)


def make(tmp_path, *memos_by_period):
    """memos_by_period: 교시마다 [(kind, text), ...]. 같은 날 같은 과목으로 저장하고 주간 글 본문을 돌려준다."""
    folder = tmp_path / "sessions" / DAY.isoformat()
    folder.mkdir(parents=True)
    for period, memos in enumerate(memos_by_period, start=1):
        rec = {"date": DAY.isoformat(), "subject": "수학", "publisher": "가출판", "title": "분수",
               "memos": [{"kind": k, "text": t} for k, t in memos]}
        (folder / f"{period}교시_수학.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    path, _count, _broken = wr.make_report(tmp_path, DAY)
    return path.read_text(encoding="utf-8")


def outside_students(text):
    """학생별 절을 뺀 나머지(과목·출판사별 + 주의점 후보)."""
    return text.split("## 🙋 학생별 발표 메모")[0]


def test_baseline_name_written_in_student_memo_is_masked_elsewhere(tmp_path):
    """지금 되는 것: 🙋 에 적힌 이름은 다른 절에서 (학생)으로 가려진다."""
    text = make(tmp_path, [("student", "학생A 발표를 잘함"), ("fix", "학생A 자리를 바꿔야 함")])
    assert "학생A" not in outside_students(text)
    assert "(학생)" in outside_students(text)


@pytest.mark.xfail(strict=True, reason="ISSUE-038 ①: 🙋 에 한 번도 안 적힌 이름은 가려지지 않는다(반 명단을 읽지 않음).")
def test_name_never_written_in_student_memo_is_masked(tmp_path):
    text = make(tmp_path, [("student", "학생A 발표를 잘함"), ("fix", "학생B 가 자꾸 떠들어 활동이 끊김")])
    assert "학생B" not in outside_students(text)


@pytest.mark.xfail(strict=True, reason="ISSUE-038 ②: 🙋 메모의 첫 낱말이 이름이 아니면 그 낱말이 가려진다.")
def test_first_word_that_is_not_a_name_is_not_masked(tmp_path):
    text = make(tmp_path, [("student", "발표를 아주 잘함"), ("fix", "발표를 준비할 시간이 모자랐음")])
    assert "발표를 준비할 시간이 모자랐음" in outside_students(text)


@pytest.mark.xfail(strict=True, reason="ISSUE-038 ③: '학생A가'·'학생A' 가 학생별 절에서 다른 사람으로 따로 묶인다.")
def test_same_student_with_josa_is_one_section(tmp_path):
    text = make(tmp_path, [("student", "학생A 발표를 잘함")], [("student", "학생A가 질문을 함")])
    sections = text.split("## 🙋 학생별 발표 메모")[1].count("\n### ")
    assert sections == 1


@pytest.mark.xfail(strict=True, reason="ISSUE-038 ④: 띄어 쓴 이름은 첫 토막만 이름으로 보아 절 제목이 '홍' 만 된다.")
def test_spaced_name_is_not_cut_to_first_piece(tmp_path):
    text = make(tmp_path, [("student", "홍 길동 발표를 잘함")])
    assert "\n### 홍\n" not in text
