from valuation_app.narrative_consistency import (
    build_narrative_explanation,
    get_samsung_electro_narratives,
)


def test_get_samsung_electro_narratives_returns_six_stories():
    stories = get_samsung_electro_narratives()
    assert len(stories) == 6


def test_narrative_structure_has_required_keys():
    stories = get_samsung_electro_narratives()
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
    stories = get_samsung_electro_narratives()
    titles = [s["title"] for s in stories]

    # Check for the 6 key themes outlined in PLANS.md
    assert any("MLCC" in t for t in titles)
    assert any("FC-BGA" in t for t in titles)
    assert any("실리콘 캐패시터" in t for t in titles)
    assert any("전장" in t for t in titles)
    assert any("카메라 모듈" in t for t in titles)
    assert any("환율" in t for t in titles)


def test_build_narrative_explanation_is_not_empty():
    explanation = build_narrative_explanation()
    assert len(explanation) > 0
    assert "숫자" in explanation
    assert "스토리" in explanation
