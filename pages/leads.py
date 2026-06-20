import math
import os
import threading
import time
from datetime import datetime

import pandas as pd
import streamlit as st


def _get_secret(key: str) -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""


GOOGLE_PLACES_API_KEY = _get_secret("GOOGLE_PLACES_API_KEY")
ADZUNA_APP_ID         = _get_secret("ADZUNA_APP_ID")
ADZUNA_APP_KEY        = _get_secret("ADZUNA_APP_KEY")
OUTSCRAPER_API_KEY    = _get_secret("OUTSCRAPER_API_KEY")

from pipeline.places import geocode, search_clinics, get_clinic_details
from pipeline.jobs import fetch_adzuna_jobs, match_clinic_to_job
from pipeline.reviews import scan_reviews
from pipeline.outscraper_reviews import fetch_deep_reviews
from pipeline.classifier import classify_clinic
from pipeline.scorer import (
    detect_extended_hours,
    infer_specialty,
    calculate_pain_score,
    is_borderline,
    generate_outreach_angle,
)
from pipeline.website import check_website
from utils.helpers import extract_city, get_hours_summary
from utils.usage_tracker import (
    get_remaining_budget,
    record_usage,
    record_run,
    save_lead,
    OUTSCRAPER_MONTHLY_LIMIT,
)

dark = st.session_state.get("dark_mode", False)


def _pain_badge(val: float) -> str:
    if val >= 6:
        bg, color = ("#fef2f2", "#b91c1c") if not dark else ("#3d1515", "#f87171")
        label = f"🔴 {val}"
    elif val >= 4:
        bg, color = ("#fff7ed", "#c2410c") if not dark else ("#3d2210", "#fb923c")
        label = f"🟠 {val}"
    elif val >= 2:
        bg, color = ("#fefce8", "#854d0e") if not dark else ("#2d2510", "#fbbf24")
        label = f"🟡 {val}"
    else:
        bg, color = ("#f0fdf4", "#166534") if not dark else ("#0f2d1a", "#4ade80")
        label = f"🟢 {val}"
    return (
        f"<span style='background:{bg};color:{color};padding:2px 9px;"
        f"border-radius:20px;font-size:12px;font-weight:600'>{label}</span>"
    )


def highlight_pain_score(val):
    if val >= 6:
        return "background-color: #fef2f2; color: #b91c1c; font-weight: 700"
    elif val >= 4:
        return "background-color: #fff7ed; color: #c2410c; font-weight: 700"
    elif val >= 2:
        return "background-color: #fefce8; color: #854d0e; font-weight: 600"
    else:
        return "background-color: #f0fdf4; color: #166534"


# ── Pipeline state ─────────────────────────────────────────────────────────────
if "_pipeline" not in st.session_state:
    st.session_state["_pipeline"] = {
        "running": False,
        "stop_requested": False,
        "progress": 0,
        "messages": [],
        "leads_df": None,
        "error": None,
        "search_location": None,
    }

_p = st.session_state["_pipeline"]


def _run_pipeline(p: dict, location: str, radius_miles: int, max_results: int) -> None:
    p["running"] = True
    p["stop_requested"] = False
    p["progress"] = 0
    p["messages"] = []
    p["leads_df"] = None
    p["error"] = None
    p["search_location"] = location

    _calls = {"geocode": 0, "search": 0, "detail": 0, "adzuna": 0, "outscraper_reviews": 0}
    leads = []

    def log(msg: str) -> None:
        p["messages"].append(msg)

    try:
        log("📍 Geocoding location...")
        try:
            lat, lng = geocode(location, GOOGLE_PLACES_API_KEY)
            _calls["geocode"] += 1
        except ValueError as e:
            p["error"] = str(e)
            return
        p["progress"] = 10

        if p["stop_requested"]:
            log("🛑 Stopped by user.")
            return

        log("🗺️ Searching for dental clinics...")
        raw_clinics = search_clinics(lat, lng, radius_miles, max_results, GOOGLE_PLACES_API_KEY)
        _calls["search"] += math.ceil(max_results / 20)
        if not raw_clinics:
            p["error"] = "No dental clinics found in that area. Try expanding the search radius."
            return
        p["progress"] = 20

        if p["stop_requested"]:
            log("🛑 Stopped by user.")
            return

        log("💼 Fetching job postings from Adzuna...")
        jobs = fetch_adzuna_jobs(location, ADZUNA_APP_ID, ADZUNA_APP_KEY)
        _calls["adzuna"] += 1
        p["progress"] = 30

        borderline_queue = []
        total = len(raw_clinics)

        for i, clinic in enumerate(raw_clinics):
            if p["stop_requested"]:
                log(f"🛑 Stopped by user after {i} of {total} clinics.")
                break

            p["progress"] = 30 + int((i / total) * 40)
            log(f"📋 Fetching clinic details... ({i + 1}/{total})")

            details = get_clinic_details(clinic["place_id"], GOOGLE_PLACES_API_KEY)
            _calls["detail"] += 1
            if not details:
                continue

            website_data  = check_website(details.get("website"))
            job_match     = match_clinic_to_job(details.get("name", ""), jobs)
            review_data   = scan_reviews(details.get("reviews", []))
            review_data["review_source"] = "places_sample"
            extended      = detect_extended_hours(details.get("opening_hours"))
            specialty     = infer_specialty(details.get("name", ""), details.get("types", []))

            clinic_data = {
                "has_hiring_signal":  job_match is not None,
                "hiring_job_url":     job_match["job_url"]   if job_match else None,
                "hiring_job_title":   job_match["job_title"] if job_match else None,
                "pain_review_count":  review_data["pain_review_count"],
                "pain_categories":    review_data["pain_categories"],
                "worst_review_snippet": review_data["worst_review_snippet"],
                "review_source":      "places_sample",
                "num_locations":      1,
                "extended_hours":     extended,
                "uses_digital_tools": website_data["uses_digital_tools"],
                "has_online_booking": website_data["has_online_booking"],
                "has_hiring_banner":  website_data["has_hiring_banner"],
                "detected_tools":     website_data["detected_tools"],
                "rating":             details.get("rating", 0),
                "user_ratings_total": details.get("user_ratings_total", 0),
            }

            pain_score, signals = calculate_pain_score(clinic_data)
            classification = classify_clinic(details.get("name", ""), num_locations=1)

            leads.append({
                "place_id":       clinic["place_id"],
                "details":        details,
                "clinic_data":    clinic_data,
                "specialty":      specialty,
                "pain_score":     pain_score,
                "signals":        signals,
                "job_match":      job_match,
                "review_data":    review_data,
                "classification": classification,
            })

            if is_borderline(pain_score):
                borderline_queue.append(len(leads) - 1)

        p["progress"] = 70

        if not p["stop_requested"]:
            log(f"🔬 Deep review scans on borderline clinics ({len(borderline_queue)}, budget-permitting)...")
            OUTSCRAPER_REVIEWS_PER_CALL = 10
            calls_made = 0

            for idx in borderline_queue:
                if p["stop_requested"]:
                    log("🛑 Stopped by user during deep scans.")
                    break
                if calls_made >= 15:
                    leads[idx]["clinic_data"]["enrichment_note"] = "Per-run cap reached — Places sample only"
                    continue
                if not OUTSCRAPER_API_KEY:
                    leads[idx]["clinic_data"]["enrichment_note"] = "Outscraper not configured — Places sample only"
                    continue
                if get_remaining_budget() < OUTSCRAPER_REVIEWS_PER_CALL:
                    leads[idx]["clinic_data"]["enrichment_note"] = "Monthly budget reached — Places sample only"
                    continue

                deep_reviews = fetch_deep_reviews(leads[idx]["place_id"], OUTSCRAPER_API_KEY, OUTSCRAPER_REVIEWS_PER_CALL)
                calls_made += 1
                if not deep_reviews:
                    leads[idx]["clinic_data"]["enrichment_note"] = "Outscraper returned no data — Places sample only"
                    continue

                record_usage(len(deep_reviews))
                _calls["outscraper_reviews"] += len(deep_reviews)

                dr = scan_reviews(deep_reviews)
                dr["review_source"] = "outscraper_deep"
                leads[idx]["clinic_data"].update({
                    "pain_review_count":    dr["pain_review_count"],
                    "pain_categories":      dr["pain_categories"],
                    "worst_review_snippet": dr["worst_review_snippet"],
                    "review_source":        "outscraper_deep",
                    "enrichment_note":      f"Deep review scan via Outscraper (n={len(deep_reviews)})",
                })
                leads[idx]["review_data"] = dr
                new_score, new_signals = calculate_pain_score(leads[idx]["clinic_data"])
                leads[idx]["pain_score"] = new_score
                leads[idx]["signals"]    = new_signals

        p["progress"] = 90
        log("⚡ Building results table...")

        if not leads:
            p["error"] = "No leads could be processed. The run may have been stopped too early."
            return

        final_leads = []
        for lead in leads:
            details        = lead["details"]
            clinic_data    = lead["clinic_data"]
            signals        = lead["signals"]
            job_match      = lead["job_match"]
            review_data    = lead["review_data"]
            specialty      = lead["specialty"]
            pain_score     = lead["pain_score"]
            classification = lead["classification"]

            outreach_angle = generate_outreach_angle(signals, details.get("name", ""), specialty)

            evidence_parts = []
            if job_match:
                evidence_parts.append(f"Hiring: {job_match['job_title']} → {job_match['job_url']}")
            if review_data.get("worst_review_snippet"):
                src = "deep scan" if review_data.get("review_source") == "outscraper_deep" else "Places sample"
                evidence_parts.append(f'Review ({src}): "{review_data["worst_review_snippet"]}"')
            evidence = " | ".join(evidence_parts) or "No direct evidence found"

            notes_parts = [f"Rating: {details.get('rating','N/A')}★ ({details.get('user_ratings_total',0)} reviews)"]
            if clinic_data.get("enrichment_note"):
                notes_parts.append(clinic_data["enrichment_note"])
            if clinic_data.get("has_hiring_banner"):
                notes_parts.append("Website shows a hiring banner")

            review_depth_label = "Deep scan" if review_data.get("review_source") == "outscraper_deep" else "Places sample (5 max)"

            final_leads.append({
                "Clinic Name":        details.get("name", ""),
                "Classification":     classification,
                "Specialty":          specialty,
                "City":               extract_city(details.get("formatted_address", "")),
                "Address":            details.get("formatted_address", ""),
                "Website":            details.get("website", ""),
                "Phone Number":       details.get("formatted_phone_number", ""),
                "Best Contact Found": "Office Manager",
                "Contact Role":       "Office Manager",
                "Contact Email":      "",
                "LinkedIn":           "",
                "Number of Locations": 1,
                "Pain Signal Type":   " | ".join(signals) if signals else "None detected",
                "Evidence / Source":  evidence,
                "Pain Score":         pain_score,
                "Outreach Angle":     outreach_angle,
                "Notes":              " | ".join(notes_parts),
                "Google Rating":      details.get("rating", ""),
                "Total Reviews":      details.get("user_ratings_total", 0),
                "Hours Summary":      get_hours_summary(details.get("opening_hours")),
                "Extended Hours":     "Yes" if clinic_data.get("extended_hours") else "No",
                "Online Booking":     "Yes" if clinic_data.get("has_online_booking") else "No",
                "Review Data Depth":  review_depth_label,
            })

            save_lead(
                place_id=lead["place_id"],
                run_location=location,
                name=details.get("name", ""),
                address=details.get("formatted_address", ""),
                phone=details.get("formatted_phone_number", ""),
                website=details.get("website", ""),
                specialty=specialty,
                classification=classification,
                pain_score=pain_score,
                signals=" | ".join(signals) if signals else "",
                outreach_angle=outreach_angle,
                rating=float(details.get("rating", 0) or 0),
                total_reviews=int(details.get("user_ratings_total", 0) or 0),
                extended_hours=bool(clinic_data.get("extended_hours")),
                online_booking=bool(clinic_data.get("has_online_booking")),
                review_depth=review_depth_label,
            )

        p["leads_df"] = pd.DataFrame(final_leads)
        p["progress"] = 100
        log(f"✅ Done — {len(final_leads)} leads collected.")

    except Exception as e:
        p["error"] = f"An unexpected error occurred: {e}"
    finally:
        try:
            record_run(
                location=location,
                geocode_calls=_calls["geocode"],
                search_calls=_calls["search"],
                detail_calls=_calls["detail"],
                adzuna_calls=_calls["adzuna"],
                outscraper_reviews=_calls["outscraper_reviews"],
                clinics_found=len(leads),
                leads_found=len(p["leads_df"]) if p.get("leads_df") is not None else 0,
                stopped_early=p.get("stop_requested", False),
            )
        except Exception:
            pass
        p["running"] = False


# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("LOCATION")
    location = st.text_input(
        "Location",
        placeholder="City, State or ZIP (e.g. Dallas, TX)",
        label_visibility="collapsed",
        disabled=_p["running"],
    )

    st.markdown("SEARCH RADIUS")
    radius_miles = st.select_slider(
        "Radius",
        options=[10, 25, 50],
        value=25,
        label_visibility="collapsed",
        disabled=_p["running"],
        format_func=lambda x: f"{x} mi",
    )

    st.markdown("MAX RESULTS")
    max_results = st.select_slider(
        "Max Results",
        options=[20, 35, 50],
        value=50,
        label_visibility="collapsed",
        disabled=_p["running"],
    )

    st.markdown("SPECIALTY")
    all_specialties = ["General", "Orthodontic", "Pediatric", "Endodontic", "Oral Surgery", "Periodontic"]
    specialty_filter = st.multiselect(
        "Specialties",
        options=all_specialties,
        default=all_specialties,
        label_visibility="collapsed",
    )

    st.markdown("MIN PAIN SCORE")
    min_pain_score = st.slider(
        "Min Score",
        min_value=0,
        max_value=8,
        value=0,
        label_visibility="collapsed",
    )

    st.markdown("")
    find_leads = st.button(
        "Find Leads",
        use_container_width=True,
        type="primary",
        disabled=_p["running"],
    )

    if _p["running"]:
        if st.button("Stop Run", use_container_width=True, type="secondary"):
            _p["stop_requested"] = True

    st.markdown("---")

    st.markdown(
        """
        <div style='font-size:12px;line-height:1.8'>
            <div style='font-size:11px;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px'>Pain Score Guide</div>
            <div><span style='background:#fef2f2;color:#b91c1c;padding:1px 7px;border-radius:12px;font-size:11px;font-weight:600'>6+</span> &nbsp;High Priority</div>
            <div style='margin-top:4px'><span style='background:#fff7ed;color:#c2410c;padding:1px 7px;border-radius:12px;font-size:11px;font-weight:600'>4–5</span> &nbsp;Strong Signal</div>
            <div style='margin-top:4px'><span style='background:#fefce8;color:#854d0e;padding:1px 7px;border-radius:12px;font-size:11px;font-weight:600'>2–3</span> &nbsp;Moderate</div>
            <div style='margin-top:4px'><span style='background:#f0fdf4;color:#166534;padding:1px 7px;border-radius:12px;font-size:11px;font-weight:600'>0–1</span> &nbsp;Low Priority</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    remaining_budget = get_remaining_budget()
    pct_used = 1.0 - remaining_budget / OUTSCRAPER_MONTHLY_LIMIT
    if remaining_budget == 0:
        st.error("Outscraper monthly limit reached — deep scans disabled.")
    elif pct_used >= 0.8:
        st.warning(f"Outscraper: {remaining_budget} reviews left ({int(pct_used*100)}% used)")
    else:
        st.caption(f"Outscraper: {remaining_budget}/{OUTSCRAPER_MONTHLY_LIMIT} reviews remaining")


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>Find Leads</h1>
        <p>AI-powered dental clinic prospecting — identify front-desk automation opportunities</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not GOOGLE_PLACES_API_KEY:
    st.error("Google Places API key not configured. Add `GOOGLE_PLACES_API_KEY` to your `.env` file or Streamlit secrets.")
if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    st.warning("Adzuna API not configured — hiring signals will be skipped.")
if not OUTSCRAPER_API_KEY:
    st.info("Outscraper not configured — deep review scans will be skipped.")

# ── Pipeline trigger ──────────────────────────────────────────────────────────
if find_leads:
    if not location.strip():
        st.error("Enter a location before searching.")
        st.stop()
    if not GOOGLE_PLACES_API_KEY:
        st.error("Google Places API key not configured.")
        st.stop()
    threading.Thread(
        target=_run_pipeline,
        args=(_p, location, radius_miles, max_results),
        daemon=True,
    ).start()
    st.rerun()

# ── Running state ─────────────────────────────────────────────────────────────
if _p["running"]:
    st.progress(_p["progress"] / 100, text=f"Scanning... {_p['progress']}%")
    for msg in _p["messages"][-10:]:
        st.caption(msg)
    time.sleep(0.6)
    st.rerun()

if _p["error"] and not _p["running"]:
    st.error(_p["error"])

# ── Results ───────────────────────────────────────────────────────────────────
leads_df = _p.get("leads_df")

if leads_df is not None and not _p["running"]:
    df = leads_df.copy()
    if specialty_filter and len(specialty_filter) < len(all_specialties):
        df = df[df["Specialty"].isin(specialty_filter)]
    df = df[df["Pain Score"] >= min_pain_score]
    df = df.sort_values("Pain Score", ascending=False).reset_index(drop=True)

    if df.empty:
        st.warning("No leads matched the current filters.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Leads", len(df))
        c2.metric("High Priority", len(df[df["Pain Score"] >= 6]))
        c3.metric("Strong Signal", len(df[(df["Pain Score"] >= 4) & (df["Pain Score"] < 6)]))
        c4.metric("Avg Score", round(df["Pain Score"].mean(), 1))
        c5.metric("Deep Scans", len(df[df["Review Data Depth"] == "Deep scan"]))

        st.markdown("---")

        st.dataframe(
            df.style.map(highlight_pain_score, subset=["Pain Score"]),
            use_container_width=True,
            height=480,
        )

        loc = _p.get("search_location", "unknown")
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name=f"kairos_leads_{loc.replace(' ','_').replace(',','')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Top Leads")

        for _, row in df.head(5).iterrows():
            with st.expander(f"{row['Clinic Name']}  ·  Score {row['Pain Score']}", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Phone** &nbsp; {row['Phone Number'] or '—'}")
                    st.markdown(f"**Website** &nbsp; {row['Website'] or '—'}")
                    st.markdown(f"**City** &nbsp; {row['City']}")
                    st.markdown(f"**Specialty** &nbsp; {row['Specialty']}")
                    st.markdown(f"**Extended Hours** &nbsp; {row['Extended Hours']}")
                with col_b:
                    st.markdown(f"**Online Booking** &nbsp; {row['Online Booking']}")
                    st.markdown(f"**Rating** &nbsp; {row['Google Rating']}★ ({row['Total Reviews']} reviews)")
                    st.markdown(f"**Review Depth** &nbsp; {row['Review Data Depth']}")
                    st.markdown(f"**Hours** &nbsp; {row['Hours Summary']}")

                st.markdown(_pain_badge(row["Pain Score"]), unsafe_allow_html=True)

                signals = [s for s in row["Pain Signal Type"].split(" | ") if s and s != "None detected"]
                if signals:
                    st.markdown("**Pain Signals**")
                    for sig in signals:
                        st.markdown(f"- {sig}")

                st.markdown(f"**Outreach Angle** — {row['Outreach Angle']}")
                if row["Evidence / Source"] != "No direct evidence found":
                    st.markdown(f"**Evidence** — {row['Evidence / Source']}")

elif leads_df is None and not _p["running"] and not _p["error"]:
    st.markdown(
        """
        <div style='text-align:center;padding:4rem 2rem'>
            <div style='font-size:40px;margin-bottom:16px'>⏳</div>
            <div style='font-size:20px;font-weight:700;letter-spacing:-0.02em;margin-bottom:8px'>Ready to find leads</div>
            <div style='font-size:14px;color:#6b7280;max-width:420px;margin:0 auto;line-height:1.7'>
                Enter a city, state, or ZIP in the sidebar and click <strong>Find Leads</strong> to scan dental clinics for front-desk pain signals.
            </div>
            <div style='margin-top:2.5rem;text-align:left;max-width:360px;margin-left:auto;margin-right:auto'>
                <div style='font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;color:#9ca3af;margin-bottom:12px'>How it works</div>
                <div style='font-size:13.5px;color:#6b7280;margin-bottom:8px'>1. &nbsp; Scans Google Places for dental clinics near you</div>
                <div style='font-size:13.5px;color:#6b7280;margin-bottom:8px'>2. &nbsp; Cross-references hiring activity on job boards</div>
                <div style='font-size:13.5px;color:#6b7280;margin-bottom:8px'>3. &nbsp; Scans reviews for admin and front-desk complaints</div>
                <div style='font-size:13.5px;color:#6b7280'>4. &nbsp; Scores and ranks clinics by pain signal strength</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
