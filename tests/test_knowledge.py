"""Knowledge module + market-aware prompt builders (no LLM calls)."""
from app import knowledge
from app.analyzer import _build_system_prompt, _build_fit_system_prompt


def test_all_markets_have_guides_and_labels():
    for code in knowledge.MARKETS:
        assert code in knowledge.MARKET_GUIDES
        assert code in knowledge.MARKET_LABELS
        assert knowledge.MARKET_GUIDES[code].strip()
    assert knowledge.DEFAULT_MARKET in knowledge.MARKETS


def test_system_prompt_injects_the_right_market_guide():
    uk = _build_system_prompt("uk")
    assert "CV" in uk and "British English" in uk
    assert '"uk"' in uk  # instructed to echo the market code back
    # UK guide should not be bleeding India-specific notice-period rules.
    india = _build_system_prompt("india_modern")
    assert "NOTICE PERIOD" in india
    assert "notice period" not in uk.lower()


def test_traditional_india_keeps_conventions():
    trad = _build_system_prompt("india_traditional")
    assert "declaration" in trad.lower()
    assert "traditional" in trad.lower()


def test_prompts_include_shared_rubric_and_myth_correction():
    p = _build_system_prompt("us_global")
    assert "XYZ" in p                      # RESUME_PRINCIPLES + XYZ_RULE
    assert "auto-reject" in p              # myth correction present
    assert "defensibility_flags" in p      # new fields instructed


def test_unknown_market_falls_back_to_default():
    # Defensive: builder should not KeyError on an unexpected code.
    p = _build_system_prompt("nonexistent")
    assert p  # falls back to the default guide/label
    fit = _build_fit_system_prompt("nonexistent")
    assert fit


def test_fit_prompt_is_market_aware():
    fit = _build_fit_system_prompt("uk")
    assert "British English" in fit
    assert '"uk"' in fit
