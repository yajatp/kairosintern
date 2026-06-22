SIGNAL_LABELS = {
    "front_desk": "front desk",
    "phone": "phone",
    "scheduling": "scheduling",
    "insurance": "insurance",
    "paperwork": "paperwork",
    "digital_tools": "digital tools",
    "extended_hours": "extended hours",
    "active_marketing": "active marketing",
}

PAIN_KEYWORDS = {
    "phone": [
        "phone", "call", "answer", "voicemail", "hold", "callback", "busy signal",
        "rang", "picked up", "no one answers", "couldn't reach", "never answer",
        "hang up", "disconnected", "transfer", "re-dial", "dial", "machine", "line",
        "messages", "automated", "customer service", "operator", "voice mail", "ring",
    ],
    "scheduling": [
        "schedule", "appointment", "wait", "booking", "rescheduled", "cancelled",
        "no show", "overbooked", "long wait", "waiting room", "reschedule", "cancel",
        "book", "delay", "postpone", "slot", "time", "calendar", "wait list",
        "waiting time", "in lobby", "hour wait", "minutes late", "tardy", "no-show",
        "double book",
    ],
    "front_desk": [
        "front desk", "receptionist", "staff", "rude", "unhelpful", "unprofessional",
        "disorganized", "chaotic", "confused", "reception", "front office", "clerk",
        "desk staff", "secretary", "check in", "check-in", "attitude", "impolite",
        "abrupt", "dismissive", "unfriendly", "grouchy", "snarky",
    ],
    "insurance": [
        "insurance", "billing", "claim", "coverage", "verification", "denied",
        "charged", "incorrect bill", "overcharged", "pay", "cost", "copay",
        "co-pay", "price", "out of pocket", "out-of-pocket", "covered",
        "reimbursement", "estimate", "invoice", "fee", "charge", "payment",
        "statement", "deductible", "financial", "bill", "in-network",
        "out-of-network", "prior authorization",
    ],
    "paperwork": [
        "paperwork", "forms", "intake", "documents", "records", "fax",
        "sign", "fill out", "clipboard", "portal intake", "questionnaire",
        "medical history", "consent form", "registration",
    ],
    "digital_tools": [
        "online booking", "text", "website", "portal", "email", "online scheduler",
        "app", "link", "reminders", "weave", "dentrix", "ipad", "tablet", "confirmation text",
    ],
    "extended_hours": [
        "saturday", "weekend", "evening", "late", "after hours", "sunday", "hours", "open late",
    ],
    "active_marketing": [
        "ad", "marketing", "promotion", "referred", "google", "review", "stars", "recommend", "recommended",
    ],
}


def _normalize_review(raw: dict) -> dict:
    if "review_text" in raw or "review_rating" in raw or "author_title" in raw:
        return {
            "text": raw.get("review_text") or "",
            "rating": raw.get("review_rating") or 0,
            "author": raw.get("author_title") or "",
        }
    return {
        "text": raw.get("text") or "",
        "rating": raw.get("rating") or 0,
        "author": raw.get("author") or raw.get("author_name") or "",
    }


def expand_to_sentence(text: str, start: int, end: int) -> tuple[int, int]:
    """Find the sentence boundaries around the span [start, end) in text."""
    left = start
    while left > 0:
        char = text[left - 1]
        if char in ('.', '!', '?', '\n'):
            if left < len(text) and text[left].isspace():
                break
        left -= 1
        
    right = end
    while right < len(text):
        char = text[right]
        if char in ('.', '!', '?', '\n'):
            if right + 1 == len(text) or text[right + 1].isspace():
                right += 1  # Include the sentence terminator
                break
        right += 1
        
    # Trim leading/trailing whitespace
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
        
    return left, right


def _find_highlights(text: str, cat: str) -> list[dict]:
    """Return non-overlapping sentence-expanded highlights for all keywords of a category."""
    keywords = PAIN_KEYWORDS.get(cat, [])
    text_lower = text.lower()
    spans = []
    for kw in keywords:
        start = text_lower.find(kw)
        while start != -1:
            end = start + len(kw)
            
            # Expand the matched keyword to sentence boundaries
            sent_start, sent_end = expand_to_sentence(text, start, end)
            
            # Merge overlapping spans
            overlapped = False
            for s in spans:
                if not (sent_end <= s["start"] or sent_start >= s["end"]):
                    s["start"] = min(s["start"], sent_start)
                    s["end"] = max(s["end"], sent_end)
                    overlapped = True
                    break
            
            if not overlapped:
                spans.append({"start": sent_start, "end": sent_end, "category": cat})
                
            start = text_lower.find(kw, start + 1)
            
    return spans


def scan_reviews(reviews: list[dict]) -> dict:
    normalized = [_normalize_review(r) for r in reviews]

    pain_count = 0
    triggered_categories = set()
    complaint_categories = set()
    worst_snippet = ""
    worst_rating = 99
    matched_reviews = []

    for review in normalized:
        rating = review["rating"]
        full_text = review["text"]
        text_lower = full_text.lower()

        matched_cats = []
        for cat, keywords in PAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                # For complaints/pain points, only match in low-rating reviews (<= 3)
                if cat in ["front_desk", "phone", "scheduling", "insurance", "paperwork"]:
                    if rating <= 3:
                        matched_cats.append(cat)
                else:
                    # For positive/neutral signals, match in any review
                    matched_cats.append(cat)

        if matched_cats:
            has_complaint = any(c in ["front_desk", "phone", "scheduling", "insurance", "paperwork"] for c in matched_cats)
            if has_complaint:
                pain_count += 1
                if rating < worst_rating:
                    worst_rating = rating
                    worst_snippet = full_text[:200]
                # Keep track of complaint categories
                complaint_categories.update(
                    [c for c in matched_cats if c in ["front_desk", "phone", "scheduling", "insurance", "paperwork"]]
                )

            triggered_categories.update(matched_cats)

            # Build highlights across all matched categories
            all_highlights = []
            for cat in matched_cats:
                all_highlights.extend(_find_highlights(full_text, cat))

            matched_reviews.append({
                "text": full_text[:1000],
                "rating": rating,
                "author": review.get("author") or "",
                "matched_categories": matched_cats,
                "highlights": all_highlights,
            })

    cats = sorted(complaint_categories)
    evidence_parts = []
    if pain_count:
        evidence_parts.append(f"{pain_count} review(s) flagged: {', '.join(cats)}")
    if worst_snippet:
        evidence_parts.append(f'"{worst_snippet}"')

    return {
        "pain_review_count": pain_count,
        "pain_categories": cats,
        "worst_review_snippet": worst_snippet,
        "evidence_text": " | ".join(evidence_parts),
        "review_source": "places_sample",
        "matched_reviews": matched_reviews,
    }
