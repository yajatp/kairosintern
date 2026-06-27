from __future__ import annotations

from datetime import datetime

import pandas as pd
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


def _section_banner(title: str, subtitle: str, color: str, bg: str) -> None:
    st.markdown(
        f"<div style='background:{bg};border-left:5px solid {color};border-radius:10px;"
        f"padding:12px 16px;margin:22px 0 14px;'>"
        f"<div style='font-size:19px;font-weight:700;color:{color};letter-spacing:-0.02em;'>{title}</div>"
        f"<div style='font-size:12px;color:#6b6f76;margin-top:3px;'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _api_label(text: str, color: str) -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{color};"
        f"margin:14px 0 2px;text-transform:uppercase;letter-spacing:0.04em;'>{text}</div>",
        unsafe_allow_html=True,
    )


# Distinct accent per section so they read apart at a glance (brand palette).
_C_TOTAL = "#183e34"   # dark forest green
_C_LEADS = "#14756a"   # deep teal
_C_DONUT = "#b9692f"   # warm amber
_C_RECENT = "#475569"  # slate

total = stats["total"]
fl = stats["find_leads"]
dn = stats["donut"]

# ── Total ─────────────────────────────────────────────────────────────────────────
_section_banner("Total — All Tools", "Combined usage and spend across Find Leads and Donut Scraper.",
                _C_TOTAL, "rgba(24, 62, 53, 0.08)")

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

_api_label("Google Maps Platform", _C_TOTAL)
st.caption(
    f"Geocoding \\${GOOGLE_GEOCODE_COST}/call · "
    f"Text Search \\${GOOGLE_SEARCH_COST}/call · "
    f"Place Details \\${GOOGLE_DETAIL_COST}/call · "
    f"\\${GOOGLE_MONTHLY_CREDIT_USD:.0f}/month free credit (shared across both tools)"
)
_render_google(total["google"], show_credit_against=g_total_cost)

_api_label("Gemini — AI Extraction", _C_TOTAL)
st.caption(f"gemini-3.1-flash-lite · ~\\${GEMINI_CALL_COST}/call (estimate — tune GEMINI_CALL_COST if billing differs)")
_render_gemini(total["gemini"])

_api_label("Outscraper — Deep Reviews", _C_TOTAL)
st.caption(f"\\${OUTSCRAPER_REVIEW_COST}/review · includes \\${OUTSCRAPER_BILLING_OFFSET_USD:.2f} pre-tracking offset")
_render_outscraper(total["outscraper"], show_billed=True)

_api_label("Adzuna — Job Signals", _C_TOTAL)
_render_adzuna(total["adzuna"])

# ── Find Leads ─────────────────────────────────────────────────────────────────────
_section_banner("Find Leads", "Google (geocode + search + details), Gemini review scans, Outscraper deep reviews, Adzuna job signals.",
                _C_LEADS, "rgba(58, 189, 175, 0.14)")

_api_label("Google Maps Platform", _C_LEADS)
_render_google(fl["google"])
_api_label("Gemini — Review Scans", _C_LEADS)
_render_gemini(fl["gemini"])
_api_label("Outscraper — Deep Reviews", _C_LEADS)
_render_outscraper(fl["outscraper"])
_api_label("Adzuna — Job Signals", _C_LEADS)
_render_adzuna(fl["adzuna"])

# ── Donut Scraper ──────────────────────────────────────────────────────────────────
_section_banner("Donut Scraper", "Google Nearby/Text Search across the grid, plus Gemini dentist + email extraction per clinic.",
                _C_DONUT, "rgba(207, 124, 63, 0.12)")

_api_label("Google Maps Platform", _C_DONUT)
_render_google(dn["google"], search_only=True)
_api_label("Gemini — Dentist / Email Extraction", _C_DONUT)
_render_gemini(dn["gemini"])

# ── Recent runs ──────────────────────────────────────────────────────────────────
_FL_TINT = "rgba(58, 189, 175, 0.16)"
_DN_TINT = "rgba(207, 124, 63, 0.16)"


def _legend_chip(label: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;width:11px;height:11px;border-radius:3px;"
        f"background:{color};margin:0 5px 0 12px;vertical-align:middle;'></span>"
        f"<span style='vertical-align:middle;'>{label}</span>"
    )


_recent_subtitle = (
    "Last 20 runs across both tools — rows are tinted by source."
    + _legend_chip("Find Leads", _C_LEADS) + _legend_chip("Donut Scraper", _C_DONUT)
)
_section_banner("Recent Runs", _recent_subtitle, _C_RECENT, "rgba(71, 85, 105, 0.08)")

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

    df = pd.DataFrame(rows)

    def _tint_row(row):
        color = _DN_TINT if row["Page"] == "Donut" else _FL_TINT
        return [f"background-color: {color}"] * len(row)

    st.dataframe(
        df.style.apply(_tint_row, axis=1),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.caption(
    "Google cost estimates use published Maps Platform pricing. "
    "Outscraper estimated at $3/1,000 reviews. "
    "Gemini is a per-call estimate (gemini-3.1-flash-lite). "
    "Check your billing dashboards for actuals."
)
