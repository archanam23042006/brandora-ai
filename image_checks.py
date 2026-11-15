from database import get_db

GENERIC = {"image", "photo", "picture", "img", "pic", "photograph", "graphic", "banner", "logo"}


def _finding(severity, flagged, why, fix):
    return {
        "rule_id": "IMG-01", "origin": "rule", "flagged_text": flagged,
        "explanation": why, "severity": severity, "confidence": 1.0,
        "suggested_fix": fix,
    }


def run_image_checks(item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT alt_text FROM item_images WHERE item_id = ? ORDER BY id DESC LIMIT 1",
        (item_id,)).fetchone()
    conn.close()
    if not row:
        return []
    alt = (row["alt_text"] or "").strip()
    words = alt.split()
    if not alt:
        return [_finding(
            "major", "Image has no alt text",
            "People who use screen readers cannot understand this image without alt text.",
            "Describe what the image shows, for example 'A cup of coffee on a wooden table'.")]
    if len(words) < 3 or alt.lower().strip(".") in GENERIC:
        return [_finding(
            "minor", "Alt text: " + alt,
            "This alt text is too short or too general to describe the image.",
            "Write a short sentence about what is in the image and why it matters.")]
    if len(alt) > 125:
        return [_finding(
            "minor", "Alt text is " + str(len(alt)) + " characters long",
            "Very long alt text is tiring for screen reader users.",
            "Keep alt text under 125 characters.")]
    return []