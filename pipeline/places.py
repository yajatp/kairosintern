from __future__ import annotations

import time
import requests
import logging

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_BASE = "https://places.googleapis.com/v1"


def geocode(location: str, api_key: str) -> tuple[float, float]:
    resp = requests.get(
        GEOCODE_URL,
        params={"address": location, "key": api_key},
        timeout=10,
    )
    data = resp.json()
    status = data.get("status")
    if status != "OK" or not data.get("results"):
        if status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "no detail provided")
            raise ValueError(
                f"Geocoding API request denied ({error_msg}). "
                "Make sure the 'Geocoding API' is enabled in your Google Cloud Console "
                "and the API key has no restrictions blocking it."
            )
        raise ValueError(
            f"Location not found: '{location}' (API status: {status}). "
            "Try a different city name or ZIP code."
        )
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def search_clinics(lat: float, lng: float, radius_miles: int, max_results: int, api_key: str) -> list[dict]:
    radius_meters = min(int(radius_miles * 1609.34), 50000)
    results = []
    next_page_token = None

    while len(results) < max_results:
        body: dict = {
            "textQuery": "dental clinic dentist",
            "includedType": "dentist",
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_meters),
                }
            },
            "maxResultCount": min(20, max_results - len(results)),
        }
        if next_page_token:
            body["pageToken"] = next_page_token

        resp = requests.post(
            f"{PLACES_BASE}/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.businessStatus,places.formattedAddress,nextPageToken",
            },
            json=body,
            timeout=10,
        )
        data = resp.json()

        if "error" in data:
            logger.warning(f"Places search error: {data['error']}")
            break

        for place in data.get("places", []):
            if place.get("businessStatus") != "OPERATIONAL":
                continue
            results.append({
                "place_id": place["id"],
                "name": place.get("displayName", {}).get("text", ""),
                "vicinity": place.get("formattedAddress", ""),
            })
            if len(results) >= max_results:
                break

        next_page_token = data.get("nextPageToken")
        if not next_page_token or len(results) >= max_results:
            break

    return results


def get_clinic_details(place_id: str, api_key: str) -> dict:
    try:
        resp = requests.get(
            f"{PLACES_BASE}/places/{place_id}",
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": (
                    "id,displayName,internationalPhoneNumber,websiteUri,"
                    "formattedAddress,regularOpeningHours,reviews,rating,"
                    "userRatingCount,businessStatus,types"
                ),
            },
            timeout=10,
        )
        time.sleep(0.3)
        data = resp.json()

        if "error" in data:
            logger.warning(f"Place details failed for {place_id}: {data['error']}")
            return {}

        # Normalize opening hours to old-API shape expected by the rest of the codebase
        opening_hours = None
        if "regularOpeningHours" in data:
            oh = data["regularOpeningHours"]
            opening_hours = {
                "weekday_text": oh.get("weekdayDescriptions", []),
                "open_now": oh.get("openNow", False),
                "periods": oh.get("periods", []),
            }

        # Normalize reviews
        reviews = []
        for r in data.get("reviews", []):
            reviews.append({
                "text": r.get("text", {}).get("text", ""),
                "rating": r.get("rating", 0),
                "author_name": r.get("authorAttribution", {}).get("displayName", ""),
            })

        result = {
            "name": data.get("displayName", {}).get("text", ""),
            "formatted_phone_number": data.get("internationalPhoneNumber", ""),
            "website": data.get("websiteUri", ""),
            "formatted_address": data.get("formattedAddress", ""),
            "opening_hours": opening_hours,
            "reviews": reviews,
            "rating": data.get("rating", 0),
            "user_ratings_total": data.get("userRatingCount", 0),
            "business_status": data.get("businessStatus", ""),
            "types": data.get("types", []),
        }

        if opening_hours and opening_hours.get("weekday_text"):
            result["hours_summary"] = "; ".join(opening_hours["weekday_text"])
        else:
            result["hours_summary"] = "Hours not available"

        return result
    except Exception as e:
        logger.warning(f"Error fetching details for {place_id}: {e}")
        return {}
