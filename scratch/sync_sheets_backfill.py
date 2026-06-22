import sys
import os
import re
import requests
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Add parent dir to path so we can import utils and pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from pipeline.places import geocode
from utils.sheets import append_leads_to_sheet
from utils.usage_tracker import get_run_history, get_leads, _headers, _supabase_ok

def run_backfill():
    if not _supabase_ok():
        print("Supabase is not configured.")
        return {"error": "Supabase not configured"}

    print("Fetching runs and leads from Supabase...")
    runs = get_run_history(1000)
    leads = get_leads(limit=10000)

    print(f"Loaded {len(runs)} runs and {len(leads)} leads.")
    
    # Resolve ZIP codes and build mapping
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_PLACES_API_KEY", "")
        except Exception:
            pass
            
    # Resolve locations for runs that are ZIP codes
    resolved_runs = {}
    updated_runs_count = 0
    updated_leads_count = 0
    
    # Map run ID -> run
    run_map = {r["id"]: r for r in runs if r.get("id")}
    
    # Group leads by run_id
    leads_by_run_id = {}
    for l in leads:
        rid = l.get("run_id")
        if rid:
            leads_by_run_id.setdefault(rid, []).append(l)

    # Resolve ZIP runs
    for run in runs:
        run_id = run.get("id")
        loc_str = run.get("location", "")
        if not loc_str:
            continue
        
        # Check if it's a zip code
        is_zip = re.match(r'^\d{5}(-\d{4})?$', loc_str.strip())
        if is_zip:
            print(f"Found ZIP code run: ID {run_id}, location: '{loc_str}'")
            # Try to resolve from leads addresses
            resolved = None
            run_leads = leads_by_run_id.get(run_id, [])
            for l in run_leads:
                addr = l.get("address", "")
                parts = [p.strip() for p in addr.split(",")]
                if len(parts) >= 2:
                    for i, p in enumerate(parts):
                        m = re.search(r'\b([A-Z]{2})\b\s+\d{5}', p)
                        if m:
                            state = m.group(1)
                            city = parts[i-1] if i > 0 else ""
                            if city and state:
                                resolved = f"{loc_str.strip()} ({city}, {state})"
                                break
                    if resolved:
                        break
            
            # If not resolved from leads, use Geocoding API
            if not resolved and api_key:
                try:
                    _, _, resolved = geocode(loc_str, api_key)
                except Exception as e:
                    print(f"Failed to geocode zip code '{loc_str}': {e}")
            
            if resolved:
                print(f"Resolved ZIP '{loc_str}' to '{resolved}'")
                # Update in Supabase
                supabase_url = os.getenv("SUPABASE_URL")
                headers = _headers(prefer="return=minimal")
                # Update run
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/runs?id=eq.{run_id}",
                    headers=headers,
                    json={"location": resolved},
                    timeout=8
                )
                if resp.ok:
                    run["location"] = resolved
                    resolved_runs[run_id] = resolved
                    updated_runs_count += 1
                else:
                    print(f"Failed to update run location in Supabase: {resp.status_code} {resp.text}")
                
                # Update all leads for this run
                resp_l = requests.patch(
                    f"{supabase_url}/rest/v1/leads?run_id=eq.{run_id}",
                    headers=headers,
                    json={"run_location": resolved},
                    timeout=8
                )
                if resp_l.ok:
                    for l in run_leads:
                        l["run_location"] = resolved
                    updated_leads_count += len(run_leads)
                else:
                    print(f"Failed to update leads run_location in Supabase: {resp_l.status_code} {resp_l.text}")

    print(f"Migration completed. Updated {updated_runs_count} runs and {updated_leads_count} leads in Supabase.")

    # Push all leads to Google Sheets tab-by-tab
    from utils.sheets import _parse_tab_name
    
    # We will build rows to append state by state
    leads_by_tab = {}
    
    for l in leads:
        # Reconstruct the lead dictionary to DataFrame row format
        rid = l.get("run_id")
        run_obj = run_map.get(rid) if rid else None
        radius = run_obj.get("radius_miles", 25) if run_obj else 25
        if not radius:
            radius = 25
            
        r_location = l.get("run_location") or (run_obj.get("location") if run_obj else "Unknown")
        tab_name = _parse_tab_name(r_location)
        
        # Prepare run date
        r_date = "Unknown"
        if run_obj and run_obj.get("timestamp"):
            try:
                r_date = datetime.fromisoformat(run_obj["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                r_date = run_obj["timestamp"]
        elif l.get("scored_at"):
            try:
                r_date = datetime.fromisoformat(l["scored_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                r_date = l["scored_at"]
                
        # Handle notes reconstruction
        rating = l.get("rating", "")
        tot_rev = l.get("total_reviews", 0)
        notes_parts = [f"Rating: {rating} ({tot_rev} reviews)"]
        depth = l.get("review_depth", "")
        if depth:
            notes_parts.append(depth)
            
        # Reconstruct Evidence
        evidence = "No direct evidence found"
        raw_rj = l.get("reviews_json")
        worst_snippet = ""
        if raw_rj:
            try:
                rj = json.loads(raw_rj) if isinstance(raw_rj, str) else raw_rj
                if rj:
                    worst = min(rj, key=lambda x: x.get("rating", 5))
                    worst_snippet = worst.get("text", "")
            except Exception:
                pass

        evidence_parts = []
        sig_str = l.get("signals", "")
        if "Hiring" in sig_str:
            evidence_parts.append("Hiring signal detected")
        if worst_snippet:
            evidence_parts.append(f'Review: "{worst_snippet[:200]}"')
        if evidence_parts:
            evidence = " | ".join(evidence_parts)
        
        row_data = {
            "City":                r_location,
            "Search Radius":       f"{radius} mi",
            "Run Date":            r_date,
            "Place ID":            l.get("place_id", ""),
            "Clinic Name":         l.get("name", ""),
            "Classification":      l.get("classification", ""),
            "Specialty":           l.get("specialty", ""),
            "Address":             l.get("address", ""),
            "Website":             l.get("website", ""),
            "Phone Number":        l.get("phone", ""),
            "Best Contact Found":  "Office Manager",
            "Contact Role":        "Office Manager",
            "Contact Email":       "",
            "LinkedIn":            "",
            "Number of Locations": 1,
            "Pain Signal Type":    l.get("signals") or "None detected",
            "Evidence / Source":   evidence,
            "Pain Score":          l.get("pain_score", 0),
            "Outreach Angle":      l.get("outreach_angle", ""),
            "Notes":               " | ".join(notes_parts),
            "Google Rating":       rating,
            "Total Reviews":       tot_rev,
            "Hours Summary":       "",
            "Extended Hours":      "Yes" if l.get("extended_hours") else "No",
            "Online Booking":      "Yes" if l.get("online_booking") else "No",
            "Review Data Depth":   depth,
            "reviews_json":        l.get("reviews_json") or "",
        }
        leads_by_tab.setdefault(tab_name, []).append(row_data)

    sync_results = {}
    for tab, tab_leads in leads_by_tab.items():
        print(f"Syncing {len(tab_leads)} leads for tab '{tab}'...")
        tab_df = pd.DataFrame(tab_leads)
        res = append_leads_to_sheet(tab_df, location=tab, run_date="")
        sync_results[tab] = res
        print(f"Result for '{tab}': {res}")

    return {
        "updated_runs": updated_runs_count,
        "updated_leads": updated_leads_count,
        "sync_results": sync_results
    }

if __name__ == "__main__":
    res = run_backfill()
    print("Backfill completed:", json.dumps(res, indent=2))
