"""
Generate golden dataset images for Brand Arbiter evaluation (TODO-021).

Creates controlled test images with exact known measurements so ground truth
is mathematically provable — no human labeling ambiguity on these images.

Uses PIL to draw simplified payment mark representations. These are NOT
official brand artwork (we don't redistribute trademarked logos). They're
colored rectangles with text labels that a VLM can identify as representing
payment brands. The ground truth is in the GEOMETRY, not the artwork.

IMPORTANT: "area" throughout this file means BOUNDING BOX area, consistent
with how Brand Arbiter's DetectedEntity computes area:
    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
This creates a systematic property: circular logos (MC) have lower pixel-fill
density than rectangular logos (Visa) within the same bounding box. This is
a known property of bounding-box-based measurement, not a defect.

Output: golden/ folder with PNG images + ground_truth.yaml manifest.

v2 — Fixed area ratio calculations (height ratio != area ratio for non-square logos).
     Added coverage gap images (color treatment, clearspace borderline, vertical stacking).
     Reviewed by 3rd-party AI, bugs corrected.
"""

from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent / "golden"
OUTPUT_DIR.mkdir(exist_ok=True)

# Brand colors (simplified representations)
MC_RED = (204, 0, 0)
MC_YELLOW = (255, 153, 0)
VISA_BLUE = (26, 35, 126)
AMEX_BLUE = (0, 111, 207)
WHITE = (255, 255, 255)
LIGHT_GRAY = (245, 245, 245)
DARK_GRAY = (100, 100, 100)
BLACK = (0, 0, 0)

CANVAS_W, CANVAS_H = 1200, 800


# ============================================================================
# Drawing helpers
# ============================================================================


def _mc_bbox_dims(size: int) -> tuple[int, int]:
    """Compute MC logo bounding box dimensions for a given circle diameter.

    Returns (width, height). Width > height because of overlapping circles.
    """
    offset = int(size * 0.6)
    return size + offset, size


def _mc_bbox_area(size: int) -> int:
    """Compute MC logo bounding box area for a given circle diameter."""
    w, h = _mc_bbox_dims(size)
    return w * h


def _bbox_area(bbox: list[int]) -> int:
    """Compute bounding box area from [x1, y1, x2, y2]."""
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def draw_mc_logo(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> list[int]:
    """Draw a simplified Mastercard logo (two overlapping circles + text).
    Returns bounding box [x1, y1, x2, y2]."""
    r = size // 2
    # Red circle
    draw.ellipse([x, y, x + size, y + size], fill=MC_RED)
    # Yellow circle (overlapping)
    offset = int(size * 0.6)
    draw.ellipse([x + offset, y, x + offset + size, y + size], fill=MC_YELLOW)
    # Overlap blend (orange)
    for px in range(x + offset, x + size):
        for py in range(y, y + size):
            in_red = (px - x - r) ** 2 + (py - y - r) ** 2 <= r * r
            in_yellow = (px - x - offset - r) ** 2 + (py - y - r) ** 2 <= r * r
            if in_red and in_yellow:
                draw.point((px, py), fill=(255, 102, 0))
    # Label
    try:
        font = ImageFont.truetype("arial.ttf", max(12, size // 5))
    except OSError:
        font = ImageFont.load_default()
    draw.text((x + offset // 2, y + size + 4), "mastercard", fill=BLACK, font=font)
    return [x, y, x + offset + size, y + size]


def draw_mc_logo_grayscale(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> list[int]:
    """Draw a grayscale Mastercard logo (for color treatment violation tests).
    Returns bounding box [x1, y1, x2, y2]."""
    r = size // 2
    draw.ellipse([x, y, x + size, y + size], fill=(120, 120, 120))
    offset = int(size * 0.6)
    draw.ellipse([x + offset, y, x + offset + size, y + size], fill=(180, 180, 180))
    for px in range(x + offset, x + size):
        for py in range(y, y + size):
            in_left = (px - x - r) ** 2 + (py - y - r) ** 2 <= r * r
            in_right = (px - x - offset - r) ** 2 + (py - y - r) ** 2 <= r * r
            if in_left and in_right:
                draw.point((px, py), fill=(150, 150, 150))
    try:
        font = ImageFont.truetype("arial.ttf", max(12, size // 5))
    except OSError:
        font = ImageFont.load_default()
    draw.text((x + offset // 2, y + size + 4), "mastercard", fill=DARK_GRAY, font=font)
    return [x, y, x + offset + size, y + size]


def draw_visa_logo(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> list[int]:
    """Draw a simplified Visa logo (blue rectangle + white text).
    Returns bounding box [x1, y1, x2, y2]."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=VISA_BLUE)
    try:
        font = ImageFont.truetype("arial.ttf", max(12, h // 2))
    except OSError:
        font = ImageFont.load_default()
    bbox = font.getbbox("VISA")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2), "VISA", fill=WHITE, font=font)
    return [x, y, x + w, y + h]


def draw_amex_logo(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> list[int]:
    """Draw a simplified AmEx logo (blue rectangle + white text).
    Returns bounding box [x1, y1, x2, y2]."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=AMEX_BLUE)
    try:
        font = ImageFont.truetype("arial.ttf", max(12, h // 3))
    except OSError:
        font = ImageFont.load_default()
    bbox = font.getbbox("AMEX")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2), "AMEX", fill=WHITE, font=font)
    return [x, y, x + w, y + h]


def draw_bank_logo(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, name: str) -> list[int]:
    """Draw a simplified bank logo (teal rectangle + white text).
    Returns bounding box [x1, y1, x2, y2]."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=(0, 114, 178))
    try:
        font = ImageFont.truetype("arial.ttf", max(12, h // 3))
    except OSError:
        font = ImageFont.load_default()
    bbox = font.getbbox(name)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2), name, fill=WHITE, font=font)
    return [x, y, x + w, y + h]


def add_title(draw: ImageDraw.ImageDraw, text: str, subtitle: str = "") -> None:
    """Add title text at top of canvas."""
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        sub_font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
    draw.text((40, 30), text, fill=BLACK, font=title_font)
    if subtitle:
        draw.text((40, 70), subtitle, fill=DARK_GRAY, font=sub_font)


# ============================================================================
# Image generators
# ============================================================================

ground_truth = []

# Reference: Visa logo dimensions used consistently
VISA_W, VISA_H = 160, 100
VISA_AREA = VISA_W * VISA_H  # 16,000


def gen_pass_parity_equal():
    """Three payment logos at exactly equal bbox area — PASS for parity."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Payment Options", "We accept all major credit cards")

    # MC size=100: bbox 160x100 = 16,000 = same as Visa 160x100
    mc_size = 100
    y = 350
    gap = 80

    entities = {}
    entities["mastercard"] = draw_mc_logo(draw, 200, y, mc_size)
    entities["visa"] = draw_visa_logo(draw, 200 + _mc_bbox_dims(mc_size)[0] + gap, y, VISA_W, VISA_H)
    entities["amex"] = draw_amex_logo(
        draw, 200 + _mc_bbox_dims(mc_size)[0] + gap + VISA_W + gap, y, VISA_W, VISA_H
    )

    mc_area = _mc_bbox_area(mc_size)
    ratio = mc_area / VISA_AREA

    path = OUTPUT_DIR / "PASS-parity-equal.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "PASS",
        "difficulty": "easy",
        "reasoning": f"MC bbox {_mc_bbox_dims(mc_size)[0]}x{mc_size} area={mc_area}, "
                     f"Visa 160x100 area={VISA_AREA}. Area ratio {ratio:.4f}. Equal bbox area.",
        "area_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_fail_parity_mc_small():
    """MC logo much smaller than Visa — clear FAIL for parity."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Accepted Payment Methods", "Checkout securely")

    # MC size=60: bbox 96x60 = 5,760. Visa 200x120 = 24,000. Ratio 0.24
    mc_size = 60
    visa_w, visa_h = 200, 120
    visa_area = visa_w * visa_h
    y = 350

    entities = {}
    entities["mastercard"] = draw_mc_logo(draw, 200, y + 30, mc_size)
    entities["visa"] = draw_visa_logo(draw, 500, y, visa_w, visa_h)

    mc_area = _mc_bbox_area(mc_size)
    ratio = mc_area / visa_area

    path = OUTPUT_DIR / "FAIL-parity-mc-small.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "FAIL",
        "difficulty": "easy",
        "reasoning": f"MC bbox {_mc_bbox_dims(mc_size)[0]}x{mc_size} area={mc_area}, "
                     f"Visa {visa_w}x{visa_h} area={visa_area}. Area ratio {ratio:.4f} << 0.95 threshold.",
        "area_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_fail_parity_subtle():
    """MC noticeably smaller — area ratio ~0.85. Subtle FAIL."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Pay with confidence", "Multiple payment options available")

    # MC size=92: bbox 147x92 = 13,524. Visa 160x100 = 16,000. Ratio 0.8453
    mc_size = 92
    y = 350

    entities = {}
    entities["mastercard"] = draw_mc_logo(draw, 200, y + 4, mc_size)
    entities["visa"] = draw_visa_logo(draw, 500, y, VISA_W, VISA_H)

    mc_area = _mc_bbox_area(mc_size)
    ratio = mc_area / VISA_AREA

    path = OUTPUT_DIR / "FAIL-parity-subtle.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "FAIL",
        "difficulty": "hard",
        "reasoning": f"MC bbox {_mc_bbox_dims(mc_size)[0]}x{mc_size} area={mc_area}, "
                     f"Visa {VISA_W}x{VISA_H} area={VISA_AREA}. Area ratio {ratio:.4f} < 0.95 threshold. "
                     f"Visually subtle — MC is only 8px shorter — but bbox area difference is significant.",
        "area_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_pass_clearspace_adequate():
    """MC logo with generous clear space — PASS."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), LIGHT_GRAY)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Mastercard Accepted Here")

    mc_size = 120
    entities = {}
    mc_bbox = draw_mc_logo(draw, 450, 300, mc_size)
    entities["mastercard"] = mc_bbox
    visa_bbox = draw_visa_logo(draw, 850, 320, 140, 80)
    entities["visa"] = visa_bbox

    mc_right = mc_bbox[2]
    visa_left = visa_bbox[0]
    gap = visa_left - mc_right
    mc_w = mc_bbox[2] - mc_bbox[0]
    ratio = gap / mc_w

    path = OUTPUT_DIR / "PASS-clearspace-adequate.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-CLR-002",
        "verdict": "PASS",
        "difficulty": "easy",
        "reasoning": f"MC right edge at x={mc_right}, Visa left edge at x={visa_left}. "
                     f"Gap={gap}px, MC width={mc_w}px. Ratio {ratio:.4f} >> 0.25 threshold.",
        "clearspace_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_fail_clearspace_crowded():
    """MC logo crowded by Visa logo and text — FAIL."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Pay Now!")

    mc_size = 100
    entities = {}
    mc_bbox = draw_mc_logo(draw, 300, 350, mc_size)
    entities["mastercard"] = mc_bbox

    # Visa right next to MC (8px gap)
    mc_right = mc_bbox[2]
    visa_x = mc_right + 8
    visa_bbox = draw_visa_logo(draw, visa_x, 350, 140, 100)
    entities["visa"] = visa_bbox

    gap = visa_bbox[0] - mc_bbox[2]
    mc_w = mc_bbox[2] - mc_bbox[0]
    ratio = gap / mc_w

    # Promotional text crowding from the left
    try:
        promo_font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        promo_font = ImageFont.load_default()
    draw.text((100, 370), "SALE! 50% OFF!", fill=(255, 0, 0), font=promo_font)

    path = OUTPUT_DIR / "FAIL-clearspace-crowded.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-CLR-002",
        "verdict": "FAIL",
        "difficulty": "easy",
        "reasoning": f"MC right edge at x={mc_bbox[2]}, Visa left edge at x={visa_bbox[0]}. "
                     f"Gap={gap}px, MC width={mc_w}px. Ratio {ratio:.4f} << 0.25 threshold. "
                     f"Also crowded by promo text from the left.",
        "clearspace_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_pass_dominance_bank_larger():
    """Bank (Barclays) logo dominant over MC — PASS for BC-DOM-001."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Barclays Premier Rewards Card")

    mc_size = 80
    entities = {}
    bank_bbox = draw_bank_logo(draw, 200, 280, 360, 150, "BARCLAYS")
    entities["barclays"] = bank_bbox
    mc_bbox = draw_mc_logo(draw, 700, 330, mc_size)
    entities["mastercard"] = mc_bbox

    bank_area = _bbox_area(bank_bbox)
    mc_area = _bbox_area(mc_bbox)
    dominance = bank_area / mc_area

    path = OUTPUT_DIR / "PASS-dominance-bank-larger.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "BC-DOM-001",
        "verdict": "PASS",
        "difficulty": "easy",
        "reasoning": f"Barclays area={bank_area}, MC area={mc_area}. "
                     f"Dominance ratio {dominance:.2f}x. Bank clearly dominant.",
        "dominance_ratio": round(dominance, 2),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_fail_dominance_mc_too_large():
    """MC logo same size as bank logo — FAIL for BC-DOM-001."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Barclays Credit Card")

    mc_size = 100
    entities = {}
    bank_bbox = draw_bank_logo(draw, 200, 320, 200, 100, "BARCLAYS")
    entities["barclays"] = bank_bbox
    mc_bbox = draw_mc_logo(draw, 500, 320, mc_size)
    entities["mastercard"] = mc_bbox

    bank_area = _bbox_area(bank_bbox)
    mc_area = _bbox_area(mc_bbox)
    dominance = bank_area / mc_area

    path = OUTPUT_DIR / "FAIL-dominance-mc-equal.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "BC-DOM-001",
        "verdict": "FAIL",
        "difficulty": "medium",
        "reasoning": f"Barclays area={bank_area}, MC area={mc_area}. "
                     f"Dominance ratio {dominance:.2f}x. Network mark too prominent for co-brand.",
        "dominance_ratio": round(dominance, 2),
        "entities": {k: v for k, v in entities.items()},
    })


def gen_ambiguous_parity_near_threshold():
    """MC bbox area ratio ~0.956 — just above 0.95 threshold. AMBIGUOUS case."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Secure Checkout", "All major cards accepted")

    # MC size=98: bbox 156x98 = 15,288. Visa 160x100 = 16,000. Ratio 0.9555
    mc_size = 98
    y = 350

    entities = {}
    entities["mastercard"] = draw_mc_logo(draw, 300, y + 1, mc_size)
    entities["visa"] = draw_visa_logo(draw, 560, y, VISA_W, VISA_H)

    mc_area = _mc_bbox_area(mc_size)
    ratio = mc_area / VISA_AREA

    path = OUTPUT_DIR / "AMBIGUOUS-parity-threshold.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "PASS",
        "difficulty": "hard",
        "reasoning": f"MC bbox {_mc_bbox_dims(mc_size)[0]}x{mc_size} area={mc_area}, "
                     f"Visa {VISA_W}x{VISA_H} area={VISA_AREA}. Area ratio {ratio:.4f}, "
                     f"just above 0.95 threshold. Technically passes but borderline. "
                     f"VLMs may disagree — ESCALATED is acceptable.",
        "area_ratio": round(ratio, 4),
        "acceptable_verdicts": ["PASS", "ESCALATED"],
        "entities": {k: v for k, v in entities.items()},
    })


# ============================================================================
# Coverage gap images (added after 3rd-party review)
# ============================================================================


def gen_fail_parity_color_treatment():
    """MC in grayscale while Visa in full color — parity violation via color, not size."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "We Accept", "Payment options at checkout")

    mc_size = 100
    y = 350

    entities = {}
    # MC in grayscale — same size but reduced visual prominence
    entities["mastercard"] = draw_mc_logo_grayscale(draw, 200, y, mc_size)
    # Visa in full color
    entities["visa"] = draw_visa_logo(draw, 500, y, VISA_W, VISA_H)

    mc_area = _mc_bbox_area(mc_size)
    ratio = mc_area / VISA_AREA

    path = OUTPUT_DIR / "FAIL-parity-color-treatment.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "FAIL",
        "difficulty": "hard",
        "reasoning": f"MC and Visa have equal bbox area (ratio {ratio:.4f}) but MC is displayed in grayscale "
                     f"while Visa is full color. This is a parity violation via color treatment, not size. "
                     f"Track A would say PASS (equal area), Track B should say FAIL (unequal prominence). "
                     f"Tests semantic judgment beyond pixel math.",
        "area_ratio": round(ratio, 4),
        "note": "This tests Track B (semantic) vs Track A (deterministic) disagreement. "
                "A VLM that only counts pixels would miss this.",
        "entities": {k: v for k, v in entities.items()},
    })


def gen_ambiguous_clearspace_borderline():
    """MC logo with clearspace ratio near 0.25 threshold — borderline case."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Payment Methods")

    mc_size = 100
    entities = {}
    mc_bbox = draw_mc_logo(draw, 300, 350, mc_size)
    entities["mastercard"] = mc_bbox

    # Place Visa so gap/mc_width is ~0.27 (just above 0.25 threshold)
    mc_w = mc_bbox[2] - mc_bbox[0]
    target_gap = int(mc_w * 0.27)
    visa_x = mc_bbox[2] + target_gap
    visa_bbox = draw_visa_logo(draw, visa_x, 350, 140, 100)
    entities["visa"] = visa_bbox

    actual_gap = visa_bbox[0] - mc_bbox[2]
    ratio = actual_gap / mc_w

    path = OUTPUT_DIR / "AMBIGUOUS-clearspace-borderline.png"
    img.save(path)
    ground_truth.append({
        "file": path.name,
        "rule": "MC-CLR-002",
        "verdict": "PASS",
        "difficulty": "hard",
        "reasoning": f"MC right edge at x={mc_bbox[2]}, Visa left at x={visa_bbox[0]}. "
                     f"Gap={actual_gap}px, MC width={mc_w}px. Ratio {ratio:.4f}, just above 0.25 threshold. "
                     f"Borderline — ESCALATED is acceptable.",
        "clearspace_ratio": round(ratio, 4),
        "acceptable_verdicts": ["PASS", "ESCALATED"],
        "entities": {k: v for k, v in entities.items()},
    })


def gen_pass_parity_vertical():
    """Three logos stacked vertically at equal size — PASS. Tests non-horizontal layout."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), WHITE)
    draw = ImageDraw.Draw(img)
    add_title(draw, "Accepted Here")

    mc_size = 80
    gap = 30
    x_center = 500

    entities = {}
    entities["mastercard"] = draw_mc_logo(draw, x_center, 200, mc_size)
    entities["visa"] = draw_visa_logo(draw, x_center, 200 + mc_size + gap + 20, VISA_W - 32, VISA_H - 20)
    entities["amex"] = draw_amex_logo(draw, x_center, 200 + (mc_size + gap + 20) * 2, VISA_W - 32, VISA_H - 20)

    path = OUTPUT_DIR / "PASS-parity-vertical.png"
    img.save(path)

    mc_area = _mc_bbox_area(mc_size)
    visa_area = (VISA_W - 32) * (VISA_H - 20)
    ratio = mc_area / visa_area

    ground_truth.append({
        "file": path.name,
        "rule": "MC-PAR-001",
        "verdict": "PASS",
        "difficulty": "medium",
        "reasoning": f"Vertical stacking layout. MC area={mc_area}, Visa area={visa_area}. "
                     f"Ratio {ratio:.4f}. Tests whether VLM handles non-horizontal logo arrangement.",
        "area_ratio": round(ratio, 4),
        "entities": {k: v for k, v in entities.items()},
    })


# ============================================================================
# Generate all images
# ============================================================================

if __name__ == "__main__":
    print("Generating golden dataset images (v2 — area-corrected)...\n")

    gen_pass_parity_equal()
    gen_fail_parity_mc_small()
    gen_fail_parity_subtle()
    gen_pass_clearspace_adequate()
    gen_fail_clearspace_crowded()
    gen_pass_dominance_bank_larger()
    gen_fail_dominance_mc_too_large()
    gen_ambiguous_parity_near_threshold()
    # Coverage gap additions (3rd-party review)
    gen_fail_parity_color_treatment()
    gen_ambiguous_clearspace_borderline()
    gen_pass_parity_vertical()

    # Write ground truth manifest
    manifest_path = OUTPUT_DIR / "ground_truth.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(ground_truth, f, default_flow_style=False, sort_keys=False)

    print(f"Generated {len(ground_truth)} images in {OUTPUT_DIR}/")
    print(f"Ground truth manifest: {manifest_path}\n")
    for entry in ground_truth:
        ratio_key = "area_ratio" if "area_ratio" in entry else ("clearspace_ratio" if "clearspace_ratio" in entry else "dominance_ratio")
        ratio_val = entry.get(ratio_key, "n/a")
        print(f"  {entry['file']:45s} {entry['rule']:12s} {entry['verdict']:10s} ({entry['difficulty']:6s})  {ratio_key}={ratio_val}")
