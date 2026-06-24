"""
Standalone A/B test runner for review analysis methods.

Usage:
    python scratch/review_ab_test.py                          # Method A only
    python scratch/review_ab_test.py --gemini-key YOUR_KEY    # Method A + B comparison
    python scratch/review_ab_test.py --gemini-key YOUR_KEY --verbose
"""

import argparse
import json
import os
import sys

# Make pipeline importable from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.review_scanner_ab import SAMPLE_REVIEWS, run_ab_comparison


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _sep(char: str = "-", width: int = 72) -> str:
    return char * width


def _header(title: str) -> str:
    return f"\n{_sep('=')}\n  {title}\n{_sep('=')}"


def _section(title: str) -> str:
    return f"\n{_sep('-')}\n  {title}\n{_sep('-')}"


def _fmt_categories(cats: list) -> str:
    return ", ".join(cats) if cats else "(none)"


def _truncate(text: str, n: int = 100) -> str:
    return text[:n] + "..." if len(text) > n else text


def _print_method_result(label: str, result: dict, time_s: float, verbose: bool = False) -> None:
    print(_section(f"{label}  [{result.get('method', 'unknown')}]"))

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return

    print(f"  Time:              {time_s:.3f}s")
    print(f"  Pain reviews:      {result.get('pain_review_count', 0)}")
    print(f"  Pain categories:   {_fmt_categories(result.get('pain_categories', []))}")

    matched = result.get("matched_reviews", [])
    if not matched:
        print("  No matched reviews.")
        return

    print(f"\n  Matched reviews ({len(matched)}):")
    for i, mr in enumerate(matched):
        rating_stars = "*" * int(mr.get("rating", 0))
        print(f"\n    [{i+1}] {mr.get('author', 'Unknown')} — {rating_stars} ({mr.get('rating')}/5)")
        print(f"         Categories: {_fmt_categories(mr.get('matched_categories', []))}")

        if verbose:
            print(f"         Text: {_truncate(mr.get('text', ''), 120)}")

        highlights = mr.get("highlights", [])
        if highlights:
            text = mr.get("text", "")
            for h in highlights[:2]:  # show up to 2 highlights
                s, e = h.get("start", 0), h.get("end", 0)
                snippet = text[s:e]
                print(f"         Highlight ({h.get('category', '?')}): \"{_truncate(snippet, 80)}\"")


def _print_comparison(comp: dict) -> None:
    print(_section("Side-by-Side Comparison"))

    in_both = comp.get("in_both", [])
    only_a  = comp.get("only_in_a", [])
    only_b  = comp.get("only_in_b", [])

    print(f"  Found by BOTH methods ({len(in_both)}):")
    for item in in_both:
        print(f"    - {item['author']}: \"{_truncate(item['snippet'], 70)}\"")
    if not in_both:
        print("    (none)")

    print(f"\n  Found by A ONLY — not in B ({len(only_a)}):")
    for item in only_a:
        print(f"    - {item['author']}: \"{_truncate(item['snippet'], 70)}\"")
    if not only_a:
        print("    (none)")

    print(f"\n  Found by B ONLY — A's keywords MISSED these ({len(only_b)}):")
    for item in only_b:
        print(f"    - {item['author']}: \"{_truncate(item['snippet'], 70)}\"")
    if not only_b:
        print("    (none)")

    print(_section("Tricky Review Analysis"))
    tricky = comp.get("tricky_caught_by_b", [])
    if not tricky:
        print("  No tricky review analysis available (Method B not run).")
    else:
        for t in tricky:
            a_icon = "CAUGHT" if t["caught_by_a"] else "MISSED"
            b_icon = "CAUGHT" if t["caught_by_b"] else "MISSED"
            gap = " *** KEYWORD GAP ***" if t["missed_by_a_caught_by_b"] else ""
            print(
                f"  Review #{t['review_index']} ({t['author']}): "
                f"A={a_icon}  B={b_icon}{gap}"
            )

    print(_section("Accuracy Estimate"))
    acc = comp.get("accuracy_estimate", {})
    print(f"  Method A: {acc.get('method_a', 'N/A')}")
    print(f"  Method B: {acc.get('method_b', 'N/A')}")
    print(f"  (Based on 8 true positives: 5 clear pain reviews + 3 tricky reviews)")

    print(_section("Recommendation"))
    print(f"  {comp.get('recommendation', 'N/A')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Kairos review analysis A/B test")
    parser.add_argument(
        "--gemini-key",
        default=os.getenv("GEMINI_API_KEY", ""),
        help="Gemini API key (or set GEMINI_API_KEY env var). If omitted, only Method A runs.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full review texts in output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Dump raw comparison dict as JSON instead of formatted report",
    )
    args = parser.parse_args()

    gemini_key = args.gemini_key.strip()

    print(_header("Kairos Review Analysis A/B Test"))
    print(f"\n  Sample size:  {len(SAMPLE_REVIEWS)} reviews")
    print(f"    - 5 clear pain signal reviews (ratings 1–2)")
    print(f"    - 5 borderline reviews (ratings 3–4, keywords present but not complaints)")
    print(f"    - 5 positive reviews (ratings 4–5, no pain signals)")
    print(f"    - 3 tricky reviews (ratings 1–2, pain signal with unusual phrasing)")
    print(f"\n  Gemini key:   {'provided — running both methods' if gemini_key else 'NOT provided — Method A only'}")

    print("\nRunning comparison...")

    comparison = run_ab_comparison(SAMPLE_REVIEWS, gemini_key=gemini_key)

    if args.output_json:
        print(json.dumps(comparison, indent=2, default=str))
        return

    # Method A results
    _print_method_result(
        "Method A — Pattern Matching",
        comparison["method_a"]["result"],
        comparison["method_a"]["time_s"],
        verbose=args.verbose,
    )

    # Method B results
    if comparison["method_b"]["result"] is not None:
        _print_method_result(
            "Method B — Full Gemini AI",
            comparison["method_b"]["result"],
            comparison["method_b"]["time_s"],
            verbose=args.verbose,
        )
    else:
        print(_section("Method B — Full Gemini AI"))
        print("  Skipped (no Gemini API key provided).")
        print("  Run with --gemini-key YOUR_KEY to enable.")

    # Comparison
    if comparison["method_b"]["result"] is not None:
        _print_comparison(comparison["comparison"])
    else:
        print(_section("Comparison"))
        print("  Cannot compare — Method B was not run.")
        print("  Provide --gemini-key to see the full A/B analysis.")

    # Performance summary
    print(_section("Performance Summary"))
    print(f"  Method A time: {comparison['method_a']['time_s'] * 1000:.1f} ms")
    if comparison["method_b"]["time_s"] is not None:
        print(f"  Method B time: {comparison['method_b']['time_s']:.2f}s")
        ratio = comparison["method_b"]["time_s"] / max(comparison["method_a"]["time_s"], 0.001)
        print(f"  B is {ratio:.0f}x slower than A")
        print(f"  Estimated cost per clinic (Method B): ~$0.001–$0.002 (Gemini Flash pricing)")
        print(f"  Estimated cost per 50-clinic scan (Method B): ~$0.05–$0.10")

    print(f"\n{_sep('=')}\n")


if __name__ == "__main__":
    main()
