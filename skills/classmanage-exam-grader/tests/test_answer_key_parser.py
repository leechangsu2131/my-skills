from answer_key_parser import parse_answer_key_pdf


def test_parse_answer_key_pdf_uses_text_extraction_before_gemini(monkeypatch) -> None:
    monkeypatch.setattr(
        "answer_key_parser._extract_pdf_text_pages",
        lambda path: [
            "\n".join(
                [
                    "번호",
                    "정답",
                    "배점 및 채점 기준",
                    "평가 내용",
                    "평가 영역",
                    "난이도",
                    "배점",
                    "채점 기준",
                    "1",
                    "②",
                    "선의 종류 알아보기",
                    "2",
                    "아린, 예진",
                    "선의 종류 알아보기",
                    "3",
                    "해설 참조, 37cm",
                    "정사각형 알아보기",
                    "수학(한) 3-1",
                    "기본 1회",
                ]
            ),
            "\n".join(
                [
                    "3. 정사각형은 네 변의 길이가 모두 같습니다.",
                    "배점",
                    "채점 기준",
                    "상",
                    "풀이와 답을 모두 바르게 씀.",
                    "중",
                    "답 37cm만 씀.",
                    "하",
                    "오답.",
                ]
            ),
        ],
    )

    def fail(*args, **kwargs):
        raise AssertionError("Gemini fallback should not be used for text PDFs")

    monkeypatch.setattr("answer_key_parser.run_gemini_ocr", fail)

    result = parse_answer_key_pdf("answer.pdf")

    assert [question["q_num"] for question in result["questions"]] == [1, 2, 3]
    assert result["questions"][0]["type"] == "multiple_choice"
    assert result["questions"][0]["answer"] == "②"
    assert result["questions"][1]["answer"] == "아린, 예진"
    assert result["questions"][2]["type"] == "descriptive"
    assert result["questions"][2]["answer"] == "37cm"
    assert "해설 참조, 37cm" in result["questions"][2]["alt_answers"]
    assert "채점 기준" in result["questions"][2]["rubric"]


def test_parse_answer_key_pdf_falls_back_to_gemini_for_image_only_pdf(monkeypatch) -> None:
    monkeypatch.setattr("answer_key_parser._extract_pdf_text_pages", lambda path: [""])

    monkeypatch.setattr(
        "answer_key_parser.run_gemini_ocr",
        lambda *args, **kwargs: {
            "exam_title": "Gemini Quiz",
            "questions": [
                {"q_num": 1, "type": "short_answer", "answer": "42", "points": 5}
            ],
        },
    )

    result = parse_answer_key_pdf("answer.pdf")

    assert result["exam_title"] == "Gemini Quiz"
    assert result["questions"][0]["answer"] == "42"
