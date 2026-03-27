Date: 2026-03-27 at 18:47:12 EDT

# Golden Dataset Sources — Actionable Checklist

Research agent found URLs for building TODO-021's golden dataset. Organized by effort level.

## Phase A: Zero Effort (download + screenshot)

These give you ~20 pre-labeled images in minutes:

### FAIL ground truth (brand "don'ts")

| # | Source | URL | What you get |
|---|--------|-----|-------------|
| 1 | **MC Brand Mark Standards v6.1 PDF** | `https://feskov.ua/wp-content/uploads/2020/10/mastercard_brandmark.pdf` | 12+ labeled violations in "Common Mistakes" section (wrong colors, wrong sizing, crowded logos) |
| 2 | **MC Brand Mark Guidelines v8.3 PDF** | `https://digicelvipcard.com/pdf/mc_brandmark_guidelines_v8,3.pdf` | Clear space rules + incorrect spacing examples. Key quote: "size, color, and frequency parity with all other brands" |
| 3 | **Visa Brand Standards PDF (Sept 2025)** | `https://corporate.visa.com/content/dam/VCOM/corporate/about-visa/documents/visa-brand-standards-sept2025.pdf` | "DO NOT" callouts on pages 3, 6-7: disproportionate display, crowding, old marks |

**Action:** Download all 3 PDFs. Screenshot every "Common Mistakes" / "DO NOT" page. Each screenshot is a labeled FAIL image.

### PASS ground truth (official correct usage)

| # | Source | URL | What you get |
|---|--------|-----|-------------|
| 4 | **MC Brand Center** | `https://www.mastercard.com/brandcenter/us/en/brand-requirements/mastercard.html` | Interactive page with correct configurations, correct clear space, correct co-branding |
| 5 | **MC Download Artwork** | `https://www.mastercard.com/brandcenter/us/en/download-artwork.html` | Official SVG/PNG logos with correct proportions built in |
| 6 | **Visa E-commerce Standards PDF** | `https://corporate.visa.com/content/dam/VCOM/corporate/about-visa/documents/visa-ecommerce-brand-standards-sept2025.pdf` | Mobile/web checkout mockups showing compliant payment mark display |

## Phase B: Quick Wins (~30 min, screenshots for co-brand)

| # | Source | URL | Rule | Label |
|---|--------|-----|------|-------|
| 7 | **Xbox Mastercard Press Release** | `https://newsroom.mastercard.com/news/press/2023/september/xbox-to-launch-the-xbox-mastercard-its-first-ever-credit-card-in-the-us-issued-by-barclays/` | BC-DOM-001 | PASS |
| 8 | **GM Rewards Mastercard (Barclays)** | `https://home.barclays/news/press-releases/2025/05/gm-enhances-loyalty-program-and-unveils-new-gm-rewards-mastercar/` | BC-DOM-001 | PASS |

## Phase C: Controlled Mockups (1-2 hours, highest value)

Download payment icons, create images with exact known measurements:

**Icon sources (free):**
- Figma: `https://www.figma.com/community/file/880472656109554171/credit-cards-and-payment-methods-icons`
- Pixelbag: `https://pixelbag.net/payment-icons-pack-visa-mastercard-amex-paypal-apple-pay-google-pay-download/`
- Speckyboy roundup: `https://speckyboy.com/free-payment-method-credit-card-icon-sets/`

**Mockups to create (6 images, all rules covered):**

| Filename | What | Rule | Label | How |
|----------|------|------|-------|-----|
| `PASS-parity-001.png` | 3 logos at equal height (64px each) | MC-PAR-001 | PASS | Equal sizing |
| `FAIL-parity-001.png` | MC 64px, Visa 48px, AmEx 32px | MC-PAR-001 | FAIL | Deliberate 25-50% size difference |
| `PASS-clearspace-001.png` | MC logo with 1/2 circle height clear space | MC-CLR-002 | PASS | Adequate spacing |
| `FAIL-clearspace-001.png` | MC logo with text invading exclusion zone | MC-CLR-002 | FAIL | Crowded |
| `PASS-dominance-001.png` | "Barclays" at 2x MC mark size | BC-DOM-001 | PASS | Subject brand dominant |
| `FAIL-dominance-001.png` | MC mark equal to or larger than "Barclays" | BC-DOM-001 | FAIL | Network mark too large |

Export at 1200x800px with bounding box coordinates recorded in `ground_truth.yaml`.

## Phase D: Real-World Supplement (ongoing)

Free stock photos for human labeling:
- `https://www.needpix.com/photo/413528/credit-card-master-card-visa-card` (public domain)
- `https://www.pickpik.com/credit-card-master-card-visa-card-credit-paying-plastic-12746` (royalty-free)
- `https://pixabay.com/photos/ecommerce-shopping-credit-card-2607114/` (Pixabay license)

## Priority Recommendation

**Start with Phase A + Phase C.** Phase A gives you 20 pre-labeled images from brand owners (highest authority ground truth). Phase C gives you controlled images where you know the exact pixel math. Together that's 25+ images — more than enough for TODO-021's "5-10" requirement.
