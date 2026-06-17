"""
Watan Sehat — Companion Engine Test Script
Tests both rule matching (instant) and Ollama fallback.
Run: python test_companion.py
"""

from companion_engine import get_companion_response, _match_rules

def test_rule_matching():
    """Test that rule matching works instantly without Ollama."""
    print("=" * 60)
    print("TEST 1: Rule Matching (Instant, No Ollama needed)")
    print("=" * 60)

    test_cases = [
        # (query, season, age_mode, expected_source)
        ("بزرگوں کو سردی میں کیا احتیاط کرنی چاہیے؟", "chilla_kalan", "buzurg", "rule"),
        ("کانگڑی کا محفوظ استعمال بتائیں", "chilla_kalan", "jawaan", "rule"),
        ("سردی میں کیا کھائیں", "chilla_kalan", "jawaan", "rule"),
        ("ہاک کے فائدے بتائیں", "grind", "jawaan", "rule"),
        ("ورزش کرنی چاہیے", "chilla_kalan", "jawaan", "rule"),
        ("السلام علیکم", "grind", "jawaan", "rule"),
        ("hello", "grind", "jawaan", "rule"),
    ]

    passed = 0
    for query, season, age_mode, expected in test_cases:
        match = _match_rules(query, season, age_mode)
        source = "rule" if match else "none"
        status = "✓" if source == expected else "✗"
        if status == "✓":
            passed += 1
        print(f"  {status} Query: {query[:40]:<42} → {source} (rule_id: {match.get('id', 'N/A') if match else 'N/A'})")

    print(f"\n  Results: {passed}/{len(test_cases)} passed\n")


def test_full_companion():
    """Test the full companion flow — rules first, then Ollama fallback."""
    print("=" * 60)
    print("TEST 2: Full Companion (Rule + Ollama Fallback)")
    print("=" * 60)
    print("  NOTE: This requires Ollama to be running (`ollama serve`)")
    print("        and `qwen2.5:0.5b` model to be pulled.\n")

    test_queries = [
        # Should match rules (instant)
        ("بزرگوں کو سردی میں احتیاط", "jawaan", "srinagar", "chilla_kalan"),
        # Should fall through to Ollama (no rule match)
        ("What vitamins should I take during winter in Kashmir?", "jawaan", "srinagar", "chilla_kalan"),
    ]

    for query, age_mode, district, season in test_queries:
        print(f"  Query: {query}")
        result = get_companion_response(query, age_mode, district, season)
        print(f"  Source:     {result.get('source')}")
        print(f"  Confidence: {result.get('confidence')}")
        print(f"  Response:   {result.get('response_text', '')[:120]}...")
        if result.get('tip'):
            print(f"  Tip:        {result.get('tip')}")
        print()


if __name__ == "__main__":
    print()
    print("  وطن صحت — Companion Engine Tests")
    print()
    test_rule_matching()
    try:
        test_full_companion()
    except Exception as e:
        print(f"  ⚠ Ollama test skipped: {e}")
        print("  Make sure Ollama is running: ollama serve")
    print("Done.\n")
