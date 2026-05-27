from valuation_app.narrative_consistency import (
    build_narrative_explanation,
    get_company_narratives,
)


def test_get_company_narratives_samsung_electro_returns_six_stories():
    stories = get_company_narratives("009150")
    assert len(stories) == 5 # 5개로 수정되었음
    
    # 첫 번째 스토리가 MLCC 관련인지 확인
    assert "MLCC" in stories[0]["title"]


def test_narrative_structure_has_required_keys():
    stories = get_company_narratives("009150")
    required_keys = {
        "title",
        "description",
        "metrics_to_watch",
        "related_tabs",
        "bull_signal",
        "bear_signal",
    }
    for story in stories:
        assert required_keys.issubset(story.keys())
        assert isinstance(story["title"], str)
        assert isinstance(story["metrics_to_watch"], list)
        assert isinstance(story["related_tabs"], list)


def test_narratives_contain_key_themes():
    stories = get_company_narratives("009150")
    titles = [s["title"] for s in stories]

    # Check for the key themes
    assert any("MLCC" in t for t in titles)
    assert any("FC-BGA" in t for t in titles)
    assert any("실리콘 캐패시터" in t for t in titles)
    assert any("전장" in t for t in titles)
    assert any("카메라 모듈" in t for t in titles)


def test_build_narrative_explanation_is_not_empty():
    explanation = build_narrative_explanation("삼성전기")
    assert len(explanation) > 0
    assert "숫자" in explanation
    assert "스토리" in explanation
