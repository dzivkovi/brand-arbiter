# VLM-First Text Extraction, No Dedicated OCR Pipeline

**Status:** accepted

**Date:** 2026-03-25

**Decision Maker(s):** Daniel

## Context

Brand Arbiter's Block 4 (lettercase/regex validation) requires extracting text from marketing images to validate rules like "Mastercard" not "MasterCard." The original spec assumed a dedicated OCR pipeline (PaddleOCR, Tesseract, or similar) feeding extracted text into regex matchers.

However, modern VLMs extract text from images as a side effect of their visual understanding — at comparable or superior accuracy to dedicated OCR on marketing creative, and at negligible marginal cost when a VLM call is already being made for semantic analysis.

## Decision

Text extraction is performed by the VLM as part of the unified perception call (see ADR-0005). No dedicated OCR library is added to the dependency chain.

The VLM's unified output schema includes an `extracted_text` field:
```json
{
  "extracted_text": [
    {"text": "Mastercard", "location": "upper_left", "context": "tagline"},
    {"text": "Priceless", "location": "center", "context": "headline"}
  ]
}
```

Regex validation logic (lettercase matching, trademark formatting) operates on this VLM-extracted text identically to how it would operate on OCR output. The regex engine doesn't care about the text source.

## Consequences

### Positive Consequences

- Zero additional dependencies for text extraction (no PaddleOCR, Tesseract, or their system-level dependencies)
- Simpler deployment — fewer libraries to version, audit, and approve in restricted environments
- Text extraction is contextualized — VLMs understand that "MC" in a tagline is different from "MC" in a legal footer, which pure OCR cannot distinguish
- Marginal cost is near-zero when the VLM call is already happening for localization + semantic judgment

### Negative Consequences

- VLM text extraction accuracy is not benchmarked on Brand Arbiter's specific use cases — may need validation
- No fallback path for text extraction (unlike object detection which has DINO fallback)
- VLM text extraction may struggle with stylized fonts, rotated text, or very small print that dedicated OCR handles better

## Alternatives Considered

- **Option:** PaddleOCR as dedicated OCR pipeline
- **Pros:** Proven on document OCR; GPU-accelerated; open-source
- **Cons:** Heavy dependency (C++ backend, CUDA optional); overkill for marketing text that VLMs handle natively; training data optimized for documents, not marketing creative
- **Status:** rejected

- **Option:** Tesseract as lightweight OCR fallback
- **Pros:** Mature, widely available, no GPU needed
- **Cons:** Poor accuracy on non-document images; additional system-level dependency; VLM-extracted text is already available
- **Status:** rejected

## Affects

- `specs/brand-compliance-confidence-sketch.md` (Block 4 — input is VLM text, not OCR)
- `src/vlm_perception.py` (`extracted_text` field in unified schema)
- `todos/003-pending-p3-phase4-lettercase-regex.md` (rewritten — VLM text extraction, not OCR)

## Related Debt

- `todos/003-pending-p3-phase4-lettercase-regex.md` — rewritten to use VLM-extracted text

## Research References

- Gemini Flash text extraction: documented at sub-cent cost per image with superior accuracy on varied image types
- VLM-first architecture trend: modern pipelines use VLMs for unified understanding rather than specialized per-task models
