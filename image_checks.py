import io
from PIL import Image
from database import get_db

GENERIC = {"image", "photo", "picture", "img", "pic", "photograph", "graphic", "banner", "logo"}


def _finding(severity, flagged, why, fix):
    return {
        "rule_id": "IMG-01", "origin": "rule", "flagged_text": flagged,
        "explanation": why, "severity": severity, "confidence": 1.0,
        "suggested_fix": fix,
    }

def _luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(data):
    """Rough contrast of the image: lightest 5% vs darkest 5% of pixels (WCAG formula)."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((100, 100))
    lums = sorted(_luminance(p) for p in img.getdata())
    n = len(lums)
    k = max(1, n // 20)
    dark = sum(lums[:k]) / k
    light = sum(lums[-k:]) / k
    return (light + 0.05) / (dark + 0.05)

BRAND_COLOURS = {"Coffee brown": (75, 46, 30), "Cream": (245, 236, 215), "Green": (15, 118, 110)}


def brand_colour_share(data):
    """Share of pixels close to any approved brand colour (0 to 1)."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((100, 100))
    px = list(img.getdata())
    close = 0
    for r, g, b in px:
        for cr, cg, cb in BRAND_COLOURS.values():
            if (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2 < 60 ** 2:
                close += 1
                break
    return close / len(px)

def run_image_checks(item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT alt_text, data FROM item_images WHERE item_id = ? ORDER BY id DESC LIMIT 1",
        (item_id,)).fetchone()
    conn.close()
    if not row:
        return []
    out = []
    alt = (row["alt_text"] or "").strip()
    words = alt.split()
    if not alt:
        out.append(_finding(
            "major", "Image has no alt text",
            "People who use screen readers cannot understand this image without alt text.",
            "Describe what the image shows, for example 'A cup of coffee on a wooden table'."))
    elif len(words) < 3 or alt.lower().strip(".") in GENERIC:
        out.append(_finding(
            "minor", "Alt text: " + alt,
            "This alt text is too short or too general to describe the image.",
            "Write a short sentence about what is in the image and why it matters."))
    elif len(alt) > 125:
        out.append(_finding(
            "minor", "Alt text is " + str(len(alt)) + " characters long",
            "Very long alt text is tiring for screen reader users.",
            "Keep alt text under 125 characters."))
    try:
        ratio = contrast_ratio(row["data"])
        if ratio < 3:
            out.append(_finding(
                "major", "Low image contrast (ratio " + format(ratio, ".1f") + ":1)",
                "The lightest and darkest areas of this image are too similar, so text placed on it "
                "may be hard to read. WCAG asks for at least 3:1 for large text and 4.5:1 for normal text. "
                "This is an estimate for the whole image.",
                "Use a darker or lighter background, or add a solid panel behind the text."))
    except Exception:
        pass
    try:
        share = brand_colour_share(row["data"])
        if share < 0.05:
            out.append(_finding(
                "minor", "Image uses almost none of the approved brand colours",
                "Only " + format(share * 100, ".0f") + "% of this image is close to the approved palette "
                "(" + ", ".join(BRAND_COLOURS) + "). This is an estimate.",
                "Use the approved brand colours in the background or text, or ask a reviewer to allow an exception."))
    except Exception:
        pass   
    return out