from packages.answer_key_extraction.service import parse_answer_key_pdf


def test_parse_answer_key_pdf_uses_text_extraction_before_gemini(monkeypatch) -> None:
    monkeypatch.setattr(
        "packages.answer_key_extraction.service._extract_pdf_text_pages",
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

    monkeypatch.setattr("packages.answer_key_extraction.service._extract_first_page_words", lambda path: [])
    monkeypatch.setattr("packages.answer_key_extraction.service.run_gemini_ocr", fail)

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
    monkeypatch.setattr("packages.answer_key_extraction.service._extract_pdf_text_pages", lambda path: [""])

    monkeypatch.setattr(
        "packages.answer_key_extraction.service.run_gemini_ocr",
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


def test_parse_answer_key_pdf_uses_word_columns_for_pua_answers_and_visual_blanks(monkeypatch) -> None:
    monkeypatch.setattr(
        "packages.answer_key_extraction.service._extract_pdf_text_pages",
        lambda path: [
            "\n".join(
                [
                    "\ubc88\ud638",
                    "\uc815\ub2f5",
                    "\ubc30\uc810 \ubc0f \ucc44\uc810 \uae30\uc900",
                    "\ud3c9\uac00 \ub0b4\uc6a9",
                    "\ud3c9\uac00 \uc601\uc5ed",
                    "\ub09c\uc774\ub3c4",
                    "\ubc30\uc810",
                    "\ucc44\uc810 \uae30\uc900",
                    "1",
                    "\u2461",
                    "\ue038",
                    "2",
                    "\ue03b\uac1c",
                    "\ue038",
                    "3",
                    "\ue038",
                    "4",
                    "\ud574\uc124 \ucc38\uc870, \ue035cm",
                    "\ue038",
                    "\uc218\ud559(\ud55c) 3-1",
                ]
            ),
            "\n".join(
                [
                    "4. \uc815\uc0ac\uac01\ud615 \ud574\uc124",
                    "\ubc30\uc810",
                    "\ucc44\uc810 \uae30\uc900",
                    "\uc911",
                    "\ub2f5 \ue035cm\ub9cc \uc37c\uc74c.",
                ]
            ),
        ],
    )

    monkeypatch.setattr(
        "packages.answer_key_extraction.service._extract_first_page_words",
        lambda path: [
            (541.8, 170.1, 551.8, 180.1, "\ud558", 0, 0, 99),
            (47.9, 169.6, 54.3, 180.7, "1", 0, 0, 0),
            (125.8, 169.6, 136.8, 180.7, "\u2461", 0, 0, 1),
            (205.8, 169.2, 211.8, 181.2, "\ue038", 0, 0, 2),
            (47.9, 198.9, 54.3, 209.9, "2", 0, 1, 0),
            (122.8, 198.5, 140.4, 210.5, "\ue03b\uac1c", 0, 1, 1),
            (205.8, 198.5, 211.8, 210.5, "\ue038", 0, 1, 2),
            (47.9, 228.3, 54.3, 239.3, "3", 0, 2, 0),
            (205.8, 227.9, 211.8, 239.9, "\ue038", 0, 2, 1),
            (47.9, 257.6, 54.3, 268.6, "4", 0, 3, 0),
            (87.4, 257.6, 109.4, 268.6, "\ud574\uc124", 0, 3, 1),
            (114.8, 257.6, 139.3, 268.6, "\ucc38\uc870,", 0, 3, 2),
            (145.3, 257.6, 168.8, 268.6, "\ue035cm", 0, 3, 3),
            (205.8, 257.2, 211.8, 269.2, "\ue038", 0, 3, 4),
        ],
    )

    def fail(*args, **kwargs):
        raise AssertionError("Gemini fallback should not be used for structured text PDFs")

    monkeypatch.setattr("packages.answer_key_extraction.service.run_gemini_ocr", fail)

    result = parse_answer_key_pdf("answer.pdf")

    assert [question["q_num"] for question in result["questions"]] == [1, 2, 3, 4]
    assert result["questions"][1]["answer"] == "8\uac1c"
    assert result["questions"][1]["type"] == "short_answer"
    assert result["questions"][2]["answer"] == ""
    assert result["questions"][2]["type"] == "descriptive"
    assert result["questions"][3]["answer"] == "2cm"
    assert "\ud574\uc124 \ucc38\uc870, 2cm" in result["questions"][3]["alt_answers"]
    assert "\ub2f5 2cm\ub9cc \uc37c\uc74c." in result["questions"][3]["rubric"]
