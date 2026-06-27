from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.usage_tracker import (
    get_monthly_stats_by_source,
    get_run_history,
    estimated_google_cost,
    estimated_outscraper_cost,
    estimated_gemini_cost,
    using_supabase,
    GOOGLE_MONTHLY_CREDIT_USD,
    GOOGLE_GEOCODE_COST,
    GOOGLE_SEARCH_COST,
    GOOGLE_DETAIL_COST,
    OUTSCRAPER_REVIEW_COST,
    OUTSCRAPER_BILLING_OFFSET_USD,
    GEMINI_CALL_COST,
    ADZUNA_DAILY_LIMIT,
)

# ── Page header ─────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='page-header-linear'>"
    "<span class='bc-parent'>Kairos</span>"
    "<span class='bc-sep'>›</span>"
    "<span class='bc-current'>API Usage</span>"
    "</div>",
    unsafe_allow_html=True,
)

if using_supabase():
    st.success("Connected to Supabase — usage data is shared across all machines.")

stats = get_monthly_stats_by_source()
month_label = datetime.strptime(stats["year_month"], "%Y-%m").strftime("%B %Y")
st.caption(f"Showing data for {month_label} · Resets automatically each calendar month")


# ── Per-API render helpers ───────────────────────────────────────────────────────
def _render_google(g: dict, *, search_only: bool = False, show_credit_against: float | None = None) -> float:
    gc = g.get("geocode_calls", 0)
    sc = g.get("search_calls", 0)
    dc = g.get("detail_calls", 0)
    cost = estimated_google_cost(gc, sc, dc)

    if search_only:
        c1, c2 = st.columns(2)
        c1.metric("Text Search Calls", sc, help=f"${sc * GOOGLE_SEARCH_COST:.3f} est.")
        c2.metric("Est. Cost", f"${cost:.2f}")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Geocode Calls", gc, help=f"${gc * GOOGLE_GEOCODE_COST:.3f} est.")
        c2.metric("Text Search Calls", sc, help=f"${sc * GOOGLE_SEARCH_COST:.3f} est.")
        c3.metric("Place Detail Calls", dc, help=f"${dc * GOOGLE_DETAIL_COST:.3f} est.")
        c4.metric("Est. Cost", f"${cost:.2f}")

    if show_credit_against:
        pct = min(show_credit_against / GOOGLE_MONTHLY_CREDIT_USD, 1.0)
        st.progress(
            pct,
            text=f"${show_credit_against:.2f} / ${GOOGLE_MONTHLY_CREDIT_USD:.0f} free credit used ({pct * 100:.1f}%)",
        )
    return cost


def _render_gemini(gm: dict) -> float:
    calls = gm.get("calls", 0)
    cost = estimated_gemini_cost(calls)
    c1, c2 = st.columns(2)
    c1.metric("Gemini Calls", calls, help="gemini-3.1-flash-lite")
    c2.metric("Est. Cost", f"${cost:.4f}")
    return cost


def _render_outscraper(o: dict, *, show_billed: bool = False) -> float:
    reviews = o.get("reviews_used", 0)
    cost = estimated_outscraper_cost(reviews)
    if show_billed:
        c1, c2, c3 = st.columns(3)
        c1.metric("Reviews Pulled (Tracked)", reviews, help=f"${cost:.3f} est.")
        c2.metric("Est. Cost", f"${cost:.2f}")
        c3.metric(
            "Actual Billed This Period",
            f"${OUTSCRAPER_BILLING_OFFSET_USD:.2f}",
            help="From app.outscraper.cloud/billing — update OUTSCRAPER_BILLING_OFFSET_USD when this changes",
        )
    else:
        c1, c2 = st.columns(2)
        c1.metric("Reviews Pulled (Tracked)", reviews)
        c2.metric("Est. Cost", f"${cost:.2f}")
    return cost


def _render_adzuna(a: dict) -> None:
    calls = a.get("job_fetch_calls", 0)
    c1, c2 = st.columns(2)
    c1.metric("Job Fetch Calls This Month", calls)
    c2.metric("Daily Limit", f"~{ADZUNA_DAILY_LIMIT}/day", help="Evaluation-use limit")


total = stats["total"]
fl = stats["find_leads"]
dn = stats["donut"]

# ── Total ─────────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown("## Total — All Tools")

g_total_cost = estimated_google_cost(
    total["google"]["geocode_calls"],
    total["google"]["search_calls"],
    total["google"]["detail_calls"],
)
gem_total_cost = estimated_gemini_cost(total["gemini"]["calls"])
o_total_cost = estimated_outscraper_cost(total["outscraper"]["reviews_used"])

# Outscraper has no free tier — actual billed = tracked-review estimate + pre-tracking offset.
outscraper_billed = OUTSCRAPER_BILLING_OFFSET_USD + o_total_cost
# Full cost of all usage at list price (Google's free credit not yet applied).
total_list = g_total_cost + gem_total_cost + outscraper_billed
# Google's monthly free credit covers its usage until exhausted; only the overage leaves the bank.
google_covered = min(g_total_cost, GOOGLE_MONTHLY_CREDIT_USD)
total_actual = total_list - google_covered

_t1, _t2 = st.columns(2)
_t1.metric(
    "Total API Cost (list price)", f"${total_list:.2f}",
    help="Full cost of all usage this period: Google + Gemini + Outscraper (incl. pre-tracking offset). "
         "Adzuna is evaluation-tier (no per-call charge).",
)
_t2.metric(
    "Actually Paying (out-of-pocket)", f"${total_actual:.2f}",
    help=f"Money leaving the bank after free limits. Google's first ${GOOGLE_MONTHLY_CREDIT_USD:.0f}/mo is "
         f"free credit (${google_covered:.2f} covered). Outscraper has no free tier; Gemini billed as used.",
)

st.markdown("**Google Maps Platform**")
st.caption(
    f"Geocoding \\${GOOGLE_GEOCODE_COST}/call · "
    f"Text Search \\${GOOGLE_SEARCH_COST}/call · "
    f"Place Details \\${GOOGLE_DETAIL_COST}/call · "
    f"\\${GOOGLE_MONTHLY_CREDIT_USD:.0f}/month free credit (shared across both tools)"
)
_render_google(total["google"], show_credit_against=g_total_cost)

st.markdown("**Gemini — AI Extraction**")
st.caption(f"gemini-3.1-flash-lite · ~\\${GEMINI_CALL_COST}/call (estimate — tune GEMINI_CALL_COST if billing differs)")
_render_gemini(total["gemini"])

st.markdown("**Outscraper — Deep Reviews**")
st.caption(f"\\${OUTSCRAPER_REVIEW_COST}/review · includes \\${OUTSCRAPER_BILLING_OFFSET_USD:.2f} pre-tracking offset")
_render_outscraper(total["outscraper"], show_billed=True)

st.markdown("**Adzuna — Job Signals**")
_render_adzuna(total["adzuna"])

st.markdown("---")

# ── Find Leads ─────────────────────────────────────────────────────────────────────
st.markdown("## Find Leads")
st.caption("Google (geocode + search + details), Gemini review scans, Outscraper deep reviews, Adzuna job signals.")

st.markdown("**Google Maps Platform**")
_render_google(fl["google"])
st.markdown("**Gemini — Review Scans**")
_render_gemini(fl["gemini"])
st.markdown("**Outscraper — Deep Reviews**")
_render_outscraper(fl["outscraper"])
st.markdown("**Adzuna — Job Signals**")
_render_adzuna(fl["adzuna"])

st.markdown("---")

# ── Donut Scraper ──────────────────────────────────────────────────────────────────
st.markdown("## Donut Scraper")
st.caption("Google Nearby/Text Search across the grid, plus Gemini dentist + email extraction per clinic.")

st.markdown("**Google Maps Platform**")
_render_google(dn["google"], search_only=True)
st.markdown("**Gemini — Dentist / Email Extraction**")
_render_gemini(dn["gemini"])

st.markdown("---")

# ── Recent runs ──────────────────────────────────────────────────────────────────
st.markdown("### Recent Runs")
st.caption("Last 20 runs")

history = get_run_history(20)

if not history:
    st.caption("No runs recorded yet.")
else:
    rows = []
    for r in history:
        ts = r.get("timestamp", "")
        try:
            ts_fmt = datetime.fromisoformat(ts).strftime("%b %d %H:%M")
        except Exception:
            ts_fmt = ts

        g_cost = estimated_google_cost(
            r.get("geocode_calls", 0),
            r.get("search_calls", 0),
            r.get("detail_calls", 0),
        )
        o_cost = estimated_outscraper_cost(r.get("outscraper_reviews", 0))
        gem_cost = estimated_gemini_cost(r.get("gemini_calls", 0))
        page = "Donut" if r.get("source") == "donut" else "Find Leads"
        rows.append({
            "Time":               ts_fmt,
            "Page":               page,
            "Location":           r.get("location", ""),
            "Clinics Found":      r.get("clinics_found", 0),
            "Leads Output":       r.get("leads_found", 0),
            "Geocodes":           r.get("geocode_calls", 0),
            "Searches":           r.get("search_calls", 0),
            "Details":            r.get("detail_calls", 0),
            "Gemini Calls":       r.get("gemini_calls", 0),
            "Outscraper Reviews": r.get("outscraper_reviews", 0),
            "Google Cost":        f"${g_cost:.3f}",
            "Gemini Cost":        f"${gem_cost:.4f}",
            "Outscraper Cost":    f"${o_cost:.3f}",
            "Total Cost":         f"${g_cost + o_cost + gem_cost:.3f}",
            "Stopped Early":      "Yes" if r.get("stopped_early") else "—",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    "Google cost estimates use published Maps Platform pricing. "
    "Outscraper estimated at $3/1,000 reviews. "
    "Gemini is a per-call estimate (gemini-3.1-flash-lite). "
    "Check your billing dashboards for actuals."
)
