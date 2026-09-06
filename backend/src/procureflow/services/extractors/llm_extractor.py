import re
from typing import Any

import structlog
from pydantic import BaseModel, Field

from procureflow.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class LLMExtractedLineItem(BaseModel):
    description_raw: str
    quantity: float = 1.0
    unit: str = "units"
    unit_price: float = 0.0
    currency: str = "USD"
    total_price: float | None = None
    lead_time_days: int | None = None
    # Crucial: LLM references an authoritative evidence_id supplied in context; it does NOT invent coordinates
    evidence_id: str = Field(
        description="The exact [evidence_id] tag associated with the source line or chunk in the prompt"
    )


class LLMExtractedQuotation(BaseModel):
    supplier_name: str | None = None
    supplier_reference: str | None = None
    payment_terms: str | None = None
    validity_days: int | None = None
    line_items: list[LLMExtractedLineItem] = Field(default_factory=list)
    notes: str | None = None


class LLMExtractor:
    """
    LLM-assisted structured quotation parser.
    The LLM interprets complex text/tables and references authoritative parser-provided evidence IDs.
    """

    def __init__(self) -> None:
        self.provider = settings.llm_provider

    def extract_from_tagged_chunks(
        self,
        tagged_chunks: list[dict[str, Any]],
        reference_currency: str = "USD",
    ) -> LLMExtractedQuotation:
        """
        Takes parser-generated chunks containing [evidence_id] tags and text,
        and returns structured quotation data referencing those exact evidence IDs.
        """
        if self.provider == "mock" or not settings.openai_api_key:
            return self._mock_extract(tagged_chunks, reference_currency)

        try:
            return self._live_extract(tagged_chunks, reference_currency)
        except Exception as e:
            logger.warning(
                "Live LLM extraction failed; falling back to heuristic parsing", error=str(e)
            )
            return self._mock_extract(tagged_chunks, reference_currency)

    def _mock_extract(
        self,
        tagged_chunks: list[dict[str, Any]],
        reference_currency: str = "USD",
    ) -> LLMExtractedQuotation:
        """
        Deterministic, offline extraction that extracts line items from tagged chunks using
        pattern matching without calling external paid APIs. Perfect for CI and offline execution.
        """
        line_items: list[LLMExtractedLineItem] = []
        supplier_name = None
        supplier_ref = None
        payment_terms = None

        # Regex patterns to detect line items with numbers
        # e.g., "Ball Bearing 6204 | 500 pcs | 12.50 | 6250.00" or similar
        for chunk in tagged_chunks:
            ev_id = chunk["evidence_id"]
            text = chunk.get("text", "")
            lines = text.split("\n")

            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue

                # Check metadata
                if ":" in line_clean:
                    parts = line_clean.split(":", 1)
                    k, v = parts[0].strip().lower(), parts[1].strip()
                    if "supplier" in k or "vendor" in k:
                        supplier_name = v
                    elif "quote" in k or "ref" in k:
                        supplier_ref = v
                    elif "terms" in k or "payment" in k:
                        payment_terms = v

                # 1. First check for labeled invoice lines (common in OCR output)
                # e.g. "Heavy Duty Hydraulic Cylinder 50mm bore - Qty: 4 - Price: $320.00"
                qty_match = re.search(
                    r"(?:qty|quantity)[:\s]+(\d+(?:\.\d+)?)", line_clean, re.IGNORECASE
                )
                price_match = re.search(
                    r"(?:price|unit price|rate|\$)[:\s]*(\d+(?:\.\d+)?)", line_clean, re.IGNORECASE
                )
                if qty_match and price_match:
                    desc_part = re.split(
                        r"[-|;]|\bqty\b|\bquantity\b", line_clean, flags=re.IGNORECASE
                    )[0].strip()
                    if desc_part and not any(
                        h in desc_part.lower() for h in ["total", "subtotal", "terms"]
                    ):
                        try:
                            qty = float(qty_match.group(1))
                            price = float(price_match.group(1))
                            curr = reference_currency
                            if "€" in line_clean or "EUR" in line_clean:
                                curr = "EUR"
                            elif "£" in line_clean or "GBP" in line_clean:
                                curr = "GBP"
                            elif "$" in line_clean or "USD" in line_clean:
                                curr = "USD"

                            line_items.append(
                                LLMExtractedLineItem(
                                    description_raw=desc_part,
                                    quantity=qty,
                                    unit="pcs" if "pcs" in line_clean.lower() else "units",
                                    unit_price=price,
                                    total_price=qty * price,
                                    currency=curr,
                                    lead_time_days=14
                                    if any(w in line_clean.lower() for w in ["lead", "day"])
                                    else None,
                                    evidence_id=ev_id,
                                )
                            )
                            continue
                        except (ValueError, IndexError):
                            pass

                # 2. Otherwise check for delimiter-separated line items with numbers
                # e.g. "Bearing 6204 | 100 | 25.00" or tabular row
                numbers = re.findall(r"[-+]?\d*\.?\d+", line_clean)
                if len(numbers) >= 2:
                    # Clean words for description
                    words = [w for w in re.split(r"[\t,|;]", line_clean) if w.strip()]
                    if words:
                        desc = words[0].strip()
                        # Skip headers
                        if any(
                            h in desc.lower() for h in ["description", "item", "total", "subtotal"]
                        ):
                            continue

                        try:
                            qty = float(numbers[0])
                            price = float(numbers[1])
                            total = float(numbers[2]) if len(numbers) >= 3 else qty * price

                            # Detect currency symbols
                            curr = reference_currency
                            if "€" in line_clean or "EUR" in line_clean:
                                curr = "EUR"
                            elif "$" in line_clean or "USD" in line_clean:
                                curr = "USD"
                            elif "£" in line_clean or "GBP" in line_clean:
                                curr = "GBP"

                            line_items.append(
                                LLMExtractedLineItem(
                                    description_raw=desc,
                                    quantity=qty,
                                    unit="pcs" if "pcs" in line_clean.lower() else "units",
                                    unit_price=price,
                                    total_price=total,
                                    currency=curr,
                                    lead_time_days=14
                                    if "lead" in line_clean.lower() or "day" in line_clean.lower()
                                    else None,
                                    evidence_id=ev_id,
                                )
                            )
                        except (ValueError, IndexError):
                            pass

        return LLMExtractedQuotation(
            supplier_name=supplier_name or "Detected Supplier",
            supplier_reference=supplier_ref or "Q-REF-001",
            payment_terms=payment_terms,
            line_items=line_items,
            notes="Extracted via heuristic offline extractor.",
        )

    def _live_extract(
        self,
        tagged_chunks: list[dict[str, Any]],
        reference_currency: str,
    ) -> LLMExtractedQuotation:
        import instructor
        import litellm

        client = instructor.from_litellm(litellm.completion)

        prompt_text = "Extract quotation line items from the following document blocks. Each block has an [evidence_id]. "
        prompt_text += "You MUST return the exact matching [evidence_id] for each line item where the data was found.\n\n"

        for chunk in tagged_chunks:
            prompt_text += (
                f"--- [evidence_id: {chunk['evidence_id']}] (Page {chunk.get('page', 1)}) ---\n"
            )
            prompt_text += f"{chunk.get('text', '')}\n\n"

        response = client.chat.completions.create(
            model=settings.openai_model if settings.llm_provider == "openai" else "gpt-4o-mini",
            response_model=LLMExtractedQuotation,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert procurement quote extraction assistant. "
                        "Extract all line items, supplier information, and commercial terms. "
                        "Never guess or invent evidence IDs; always reference the exact evidence_id provided."
                    ),
                },
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.0,
        )
        return response


llm_extractor = LLMExtractor()
