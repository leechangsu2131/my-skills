#!/usr/bin/env python3
"""
test_grader.py - 채점 엔진 단위 테스트
"""

import json
import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from grader import normalize_answer, compare_answers, grade_student


class TestNormalizeAnswer(unittest.TestCase):
    """답안 정규화 테스트"""

    def setUp(self):
        self.config = {
            "case_sensitive": False,
            "strip_whitespace": True,
            "normalize_numbers": True,
        }

    def test_strip_whitespace(self):
        self.assertEqual(normalize_answer("  24  ", self.config), "24")

    def test_case_insensitive(self):
        self.assertEqual(normalize_answer("ABC", self.config), "abc")

    def test_case_sensitive(self):
        config = {**self.config, "case_sensitive": True}
        self.assertEqual(normalize_answer("ABC", config), "ABC")

    def test_normalize_number_unit(self):
        self.assertEqual(normalize_answer("24 cm", self.config), "24cm")

    def test_normalize_decimal(self):
        self.assertEqual(normalize_answer("24.0", self.config), "24")

    def test_fullwidth_to_halfwidth(self):
        """전각 문자 → 반각 변환"""
        self.assertEqual(normalize_answer("１２３", self.config), "123")

    def test_korean_whitespace(self):
        self.assertEqual(normalize_answer("  삼각형  ", self.config), "삼각형")


class TestCompareAnswers(unittest.TestCase):
    """답 비교 테스트"""

    def setUp(self):
        self.config = {
            "grading": {
                "case_sensitive": False,
                "strip_whitespace": True,
                "normalize_numbers": True,
                "descriptive_auto_grade": False,
            }
        }

    def test_exact_match(self):
        result = compare_answers("3", "3", [], "multiple_choice", self.config)
        self.assertTrue(result)

    def test_wrong_answer(self):
        result = compare_answers("2", "3", [], "multiple_choice", self.config)
        self.assertFalse(result)

    def test_alt_answer_match(self):
        result = compare_answers("24cm", "24", ["24cm", "24 cm"], "short_answer", self.config)
        self.assertTrue(result)

    def test_empty_answer(self):
        result = compare_answers("", "3", [], "multiple_choice", self.config)
        self.assertFalse(result)

    def test_descriptive_needs_review(self):
        result = compare_answers("긴 서술...", "정답", [], "descriptive", self.config)
        self.assertIsNone(result)

    def test_descriptive_auto_grade(self):
        config = {
            "grading": {**self.config["grading"], "descriptive_auto_grade": True}
        }
        result = compare_answers("정답 텍스트", "정답 텍스트", [], "descriptive", config)
        self.assertTrue(result)

    def test_case_insensitive_match(self):
        result = compare_answers("ABC", "abc", [], "short_answer", self.config)
        self.assertTrue(result)

    def test_number_normalization(self):
        result = compare_answers("24 cm", "24cm", [], "short_answer", self.config)
        self.assertTrue(result)


class TestGradeStudent(unittest.TestCase):
    """전체 채점 테스트"""

    def setUp(self):
        self.answer_key = {
            "exam_title": "수학 1단원",
            "total_points": 30,
            "questions": [
                {"q_num": 1, "type": "multiple_choice", "answer": "3", "alt_answers": [], "points": 10},
                {"q_num": 2, "type": "short_answer", "answer": "24", "alt_answers": ["24cm"], "points": 10},
                {"q_num": 3, "type": "descriptive", "answer": "풀이", "alt_answers": [], "points": 10, "rubric": "공식 적용"},
            ],
        }

    def test_perfect_score_auto(self):
        """객관식+단답형 모두 맞으면 서술형은 review"""
        student = {
            "student_name": "테스트",
            "answers": [
                {"q_num": 1, "answer": "3"},
                {"q_num": 2, "answer": "24cm"},
                {"q_num": 3, "answer": "풀이 내용"},
            ],
        }
        config = {
            "grading": {
                "case_sensitive": False,
                "strip_whitespace": True,
                "normalize_numbers": True,
                "descriptive_auto_grade": False,
            }
        }
        result = grade_student(student, self.answer_key, config)

        self.assertEqual(result["total_score"], 20)  # 10+10+0(review)
        self.assertEqual(result["correct_count"], 2)
        self.assertEqual(result["wrong_count"], 0)
        self.assertEqual(result["review_count"], 1)

    def test_partial_score(self):
        student = {
            "student_name": "부분정답",
            "answers": [
                {"q_num": 1, "answer": "2"},  # 틀림
                {"q_num": 2, "answer": "24"},  # 맞음
                {"q_num": 3, "answer": "서술"},  # review
            ],
        }
        config = {
            "grading": {
                "case_sensitive": False,
                "strip_whitespace": True,
                "normalize_numbers": True,
                "descriptive_auto_grade": False,
            }
        }
        result = grade_student(student, self.answer_key, config)

        self.assertEqual(result["total_score"], 10)
        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["wrong_count"], 1)
        self.assertEqual(result["review_count"], 1)
        self.assertEqual(result["accuracy"], 50.0)

    def test_missing_answers(self):
        """일부 문제 미응답"""
        student = {
            "student_name": "미응답",
            "answers": [
                {"q_num": 1, "answer": "3"},
                # 2번, 3번 미응답
            ],
        }
        config = {
            "grading": {
                "case_sensitive": False,
                "strip_whitespace": True,
                "normalize_numbers": True,
                "descriptive_auto_grade": False,
            }
        }
        result = grade_student(student, self.answer_key, config)

        self.assertEqual(result["total_score"], 10)
        self.assertEqual(result["correct_count"], 1)
        # 2번은 미응답(빈 문자열) → 오답, 3번은 서술형 → review
        self.assertEqual(result["wrong_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
