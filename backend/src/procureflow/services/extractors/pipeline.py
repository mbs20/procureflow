import difflib
import re
from decimal import Decimal
from pathlib import Path

import structlog

from procureflow.config import get_settings
from procureflow.models.rfq import RFQ, RFQLineItem
from procureflow.services.extractors.base import ExtractedQuotationData
from procureflow.services.extractors.csv_extractor import CSVExtractor
from procureflow.services.extractors.excel_extractor import ExcelExtractor
from procureflow.services.extractors.pdf_extractor import PDFExtractor

logger = structlog.get_logger(__name__)
settings = get_settings()


def calculate_similarity(s1: str, s2: str) -> float:
    """Calculates normalized token-based string similarity between 0.0 and 1.0."""

    def clean(s: str) -> set[str]:
        words = re.findall(r"\w+", s.lower())
        return set(words)

    tokens1 = clean(s1)
    tokens2 = clean(s2)

    if not tokens1 or not tokens2:
        return difflib.SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()

    # Jaccard, Overlap coefficient (containment), and sequence ratio blend
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    jaccard = len(intersection) / len(union) if union else 0.0
    min_len = min(len(tokens1), len(tokens2))
    overlap = len(intersection) / min_len if min_len > 0 else 0.0
    seq = difflib.SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()
    return 0.4 * overlap + 0.3 * jaccard + 0.3 * seq


class ExtractionPipeline:
    """Orchestrates document parsing, RFQ matching, and validation warnings."""

    def __init__(self) -> None:
        self.csv_extractor = CSVExtractor()
        self.excel_extractor = ExcelExtractor()
        self.pdf_extractor = PDFExtractor()

    def process_document(
        self,
        file_path: Path,
        rfq: RFQ | None = None,
        reference_currency: str | None = None,
    ) -> ExtractedQuotationData:
        ext = file_path.suffix.lower()
        curr = reference_currency or (rfq.reference_currency if rfq else "USD")

        # 1. Dispatch to format extractor
        if ext == ".csv":
            result = self.csv_extractor.extract(file_path, reference_currency=curr)
        elif ext == ".xlsx":
            result = self.excel_extractor.extract(file_path, reference_currency=curr)
        elif ext == ".pdf":
            result = self.pdf_extractor.extract(file_path, reference_currency=curr)
        else:
            raise ValueError(f"Unsupported document extension '{ext}'.")

        # 2. RFQ Line Item Matching with threshold enforcement
        if rfq and rfq.line_items and result.line_items:
            self._match_rfq_line_items(result, rfq.line_items)

        return result

    def _match_rfq_line_items(
        self,
        result: ExtractedQuotationData,
        rfq_items: list[RFQLineItem],
    ) -> None:
        threshold = settings.rfq_match_threshold

        for item in result.line_items:
            best_match: RFQLineItem | None = None
            best_score = 0.0

            for rfq_item in rfq_items:
                score = calculate_similarity(item.description_raw, rfq_item.description)
                if score > best_score:
                    best_score = score
                    best_match = rfq_item

            item.match_confidence = Decimal(str(round(best_score, 4)))

            if best_score >= threshold and best_match:
                item.rfq_line_item_id = best_match.id
                logger.debug(
                    "Matched line item to RFQ item",
                    extracted=item.description_raw,
                    rfq_item=best_match.description,
                    score=best_score,
                )
            else:
                # Cautious matching: Leave unresolved for human review
                item.rfq_line_item_id = None
                warning = (
                    f"Uncertain match for '{item.description_raw}' "
                    f"(best similarity {best_score:.0%}); left unresolved for human review."
                )
                item.warnings.append(warning)
                result.validation_warnings.append(warning)


extraction_pipeline = ExtractionPipeline()
