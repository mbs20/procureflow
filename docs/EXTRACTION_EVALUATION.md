# Reproducible extraction evaluation

This small corpus contains only synthetic fixtures already present in `backend/tests/fixtures/quotations`. It compares source-transcribed expected fields with the actual extraction pipeline, without network requests or paid provider calls. It does not estimate accuracy on real supplier documents.

## Run

After installing the backend dependencies, activate its virtual environment and run from `backend/`:

```bash
python -m procureflow.scripts.evaluate_extraction
pytest tests/unit/test_extraction_evaluation.py -q
```

The command selects mock/test mode in its own process. It prints JSON to stdout and diagnostics to stderr. Use the default `RFQ_MATCH_THRESHOLD=0.80`. The test verifies repeatability and the recorded known discrepancy; a future intentional extraction improvement should update that expectation.

No database, Redis, Docker, Tesseract or external credentials are required for these four cases. This evaluates extraction/matching, not the full persisted upload/approval workflow. Binary PDF/XLSX fixture generators are in `backend/tests/fixtures/quotations/generate_fixtures.py`.

## Expected and observed results

All four files contain three items. The synthetic RFQ deliberately requests only the first two, so one unmatched item per file is expected. The JSON includes every description, quantity, unit price, currency and lead time, plus actual warnings and differences. Decimal formatting is normalized for comparison.

| Fixture | Expected / observed items | Field differences | Unmatched | Items below 0.80 confidence | Warnings |
|---|---|---|---|---|---|
| `clean_bearings.csv` | 3 / 3 | None | 1 | 0 | 1 |
| `clean_fasteners.xlsx` | 3 / 3 | None | 1 | 0 | 1 |
| `native_valves.pdf` | 3 / 3 | None; absent lead times stay absent | 1 | 3 | 2 |
| `edge_case_warnings.csv` | 3 / 3 | Third item's missing unit price becomes zero | 1 | 3 | 4 |

The imperfect case includes zero price, negative quantity and missing price. The parser preserves the negative quantity and flags it, flags zero/missing prices, and substitutes zero for the missing price. This is a known representation limitation, not a correct recovery of an unknown price. Review and correction are required before comparison.

All results require buyer review in the product workflow. `buyer_review_required` records that policy; it is not a computed quality metric. Unmatched items require manual resolution. The native PDF uses offline heuristics and carries a manual-review warning even when these sample fields match. Reported confidence values are parser heuristics, not calibrated probabilities.

## Boundaries

These fixtures cover a few known layouts only. They do not cover degraded scans, multilingual documents, merged spreadsheet cells, OCR quality or live provider behavior. Provider routing has separate simulated-transport tests; no remote-model accuracy claim follows from this evaluation.
