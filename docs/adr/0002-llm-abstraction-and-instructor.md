# ADR 0002: LLM Abstraction and Structured Extraction Strategy

## Status
Accepted

## Context
Supplier quotations vary widely in layout, terminology, and structure. Relying on raw text prompting yields unpredictable JSON formatting, hallucinations, and parsing exceptions at runtime. Furthermore, open-source users have differing constraints: some mandate self-hosted local models (e.g. Ollama / Llama 3) for data privacy, while others prefer state-of-the-art commercial models (e.g. OpenAI GPT-4o).

## Decision
1. **Schema Enforcement via Pydantic & Instructor**:
   We will enforce strict JSON schemas at the model communication protocol layer using `instructor`. Validation errors are automatically caught and re-prompted up to 3 times before failing.
2. **Provider Agnostic via LiteLLM**:
   All model requests flow through an internal `LLMClient` backed by `litellm`. The active provider is configured via `PROCUREFLOW_LLM_PROVIDER` (defaulting to OpenAI for MVP, with drop-in support for Anthropic and Ollama).
3. **Deterministic Non-LLM Fallback**:
   Structured tabular formats (standard CSV and Excel files with identifiable headers) can be processed through rule-based extractors without invoking any LLM, ensuring zero API cost and full offline capability when documents are already structured.

## Consequences
- **Positive**: Guaranteed schema validity; resilient extraction; users can switch between cloud and local privacy-preserving models with a single environment variable change; deterministic test fixtures can mock LLM calls.
- **Negative**: Adds dependency on `instructor` and `litellm`; small local models may occasionally struggle with deeply nested Pydantic schemas compared to frontier models.
