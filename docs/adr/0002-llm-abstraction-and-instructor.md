# ADR 0002: Structured interpretation and narrative providers

## Status
Accepted

## Context
Quotation layouts vary. Deterministic CSV/XLSX parsers handle recognizable tables; unstructured PDFs and draft narratives may require a language-model provider. Provider selection must not change scoring mathematics or grant award authority.

## Decision
Extraction and narrative services share `completion_options`, Instructor/Pydantic response schemas and LiteLLM transport. JSON-mode responses are validated. Failed requests or invalid responses produce errors; they do not silently select mock behavior. Schema validation does not guarantee factual accuracy.

| `PROCUREFLOW_LLM_PROVIDER` | Configuration | Transport |
|---|---|---|
| `mock` | No credentials; development/test/demo only | Offline heuristics and narrative templates |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`) | `openai/<model>` |
| `anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`) | `anthropic/<model>` |
| `ollama` | Reachable `OLLAMA_BASE_URL`, installed `OLLAMA_MODEL` (default `llama3.1:8b`) | `ollama_chat/<model>`; no OpenAI key |

Model names are configurable defaults, not availability guarantees. Select a model available to your account/local server. `local` is not an alias; use `ollama`. Unsupported values are rejected.

Local processes default to `http://localhost:11434`. Inside Docker, localhost means the container. Compose defaults to `http://host.docker.internal:11434` for Docker Desktop; Linux may require a host-gateway mapping or another reachable hostname. Both backend and worker receive the provider settings. See `.env.example` at the repository root.

Structured CSV/XLSX and recognizable PDF tables require no model requests. For offline PDF interpretation select `mock`, which is prohibited in production mode.

## Data and authority boundaries
PDF interpretation sends extracted text and parser-generated evidence IDs. Narratives use a projection of procurement facts, expanded for local mode. Remote providers can receive commercially sensitive information; operators must select an appropriate data policy.

Providers have no tools for awarding suppliers. Scoring and confirmation are separate service paths. Narrative prompts and hashes are retained as runtime provenance.

## Verification and consequences
`tests/unit/test_provider_routing.py` verifies both service call paths, credentials and error handling with simulated transports and no paid calls. It does not certify live provider availability or quality. Local models may fail validation; generated content still requires buyer review.
