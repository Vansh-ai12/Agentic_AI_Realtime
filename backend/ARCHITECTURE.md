# Sentinel-RAG

**A self-correcting, multi-agent RAG system with prompt-injection defense, token-cost optimization, and full execution observability.**

Sentinel-RAG answers questions over live, continuously changing data (Notion, Gmail) using a pipeline of specialized agents — a planner, retriever, synthesizer, citation verifier, and critic — that collaborate, check each other's work, and iteratively self-correct before returning an answer. Every agent decision, retry, and token spent is traced and queryable.

---

## Why this exists

Most RAG demos answer a question by retrieving some text and asking an LLM to summarize it. That approach has no way to know if its own answer is actually correct, no defense against malicious content hiding inside retrieved documents, and no visibility into what it's costing to run. Sentinel-RAG is built around a different premise: **an agent that can catch and correct its own mistakes, resist adversarial input, and account for every token it spends, is a fundamentally more trustworthy system than one that just generates and returns.**

---

## Architecture

### Pipeline

```
memory_reader → input_guard → (blocked | planner) → retriever → chunk_guard
   → synthesizer → citation_verifier → output_guardrail → critic
   → (write_memory | retry synthesizer | unresolved)
```

This is implemented as a LangGraph state machine — a graph rather than a linear chain, specifically because the retry loop (`critic → synthesizer`) requires cycles, not just sequential steps.

### Agent responsibilities

| Agent | Role |
|---|---|
| **Memory Reader** | Semantic search over long-term memory for facts relevant to the current query, carried from prior sessions |
| **Input Guard** | 3-layer prompt-injection defense on the user's query itself (regex heuristics → ML classifier → LLM fallback) before any retrieval happens |
| **Planner** | Decomposes the query into focused sub-questions, so retrieval covers what a single vague query would miss |
| **Retriever** | Vector similarity search (pgvector) across sub-questions, with over-fetch + deduplication to avoid returning near-identical chunks |
| **Chunk Guard** | Applies the same 3-layer injection defense to *retrieved* content — since live data sources (an email, a Notion page) are untrusted input just as much as a user's prompt is |
| **Synthesizer** | Generates the answer, citing the specific chunk_id behind every factual claim |
| **Citation Verifier** | Independently re-checks each citation — not "is this chunk topically relevant," but "does this specific chunk's content actually support this specific claim" |
| **Output Guardrail** | Redacts PII from the generated answer before it's returned |
| **Critic** | Judges the answer against the query and the citation-verification result; approves, or rejects with a specific, actionable reason |

### The retry loop

If the Critic rejects an answer, the reason is fed directly back into the Synthesizer, which revises rather than starting over blind. This repeats up to a fixed retry limit. If the Critic is still unsatisfied after the limit, the pipeline stops cleanly with an `unresolved` status and an explanation — rather than looping indefinitely or returning a low-confidence guess dressed up as a final answer.

On each retry, chunks that were already cited in the previous attempt are compressed to a placeholder rather than resent in full — the model doesn't need to re-read evidence it already used; what it needs is the specific feedback on what was wrong. This measurably reduces token cost on retries without reducing what the model has access to.

---

## Security

Retrieved content is treated as untrusted input, not just the user's own prompt. A malicious instruction embedded inside a Notion page or email thread is a real attack surface for any RAG system that blindly trusts what it retrieves — Chunk Guard exists specifically to catch this before that content ever reaches the Synthesizer.

- **Input Guard**: regex heuristics catch obvious injection patterns instantly with no API call; an ML classifier catches subtler attempts; an LLM fallback handles ambiguous cases
- **Chunk Guard**: the same layered defense applied to every retrieved chunk before synthesis
- **Output Guardrail**: PII redaction on the generated answer before it's returned to the user
- **Citation Verifier**: a structural defense against hallucination — even if nothing malicious is present, this catches the Synthesizer citing a chunk that doesn't actually support what it's claiming

---

## Observability & cost tracking

Every node execution is logged — input, output, tokens used, latency — independent of whether that node calls an LLM at all. This makes it possible to answer concrete questions after any run:

- Which node was the bottleneck?
- How many tokens did this specific retry cost, versus the first attempt?
- Which agent role consumes the most tokens across a run?
- Did the retry-compression optimization actually reduce cost, and by how much?

A FastAPI endpoint exposes full per-run traces; a Next.js frontend renders them as an execution timeline with a token/cost breakdown by agent role.

---

## Data model (Supabase / Postgres + pgvector)

| Table | Purpose |
|---|---|
| `connections` | Source credentials for live data connectors (Notion, Gmail) |
| `documents` | Raw ingested content per source |
| `chunks` | Chunked, embedded content — the retrieval unit |
| `memory_short_term` / `memory_long_term` | Session-scoped vs. persistent semantic memory, with deduplication on write |
| `agent_runs` / `agent_attempts` | Run-level and attempt-level execution records |
| `trace_events` | Full node-by-node execution log |
| `token_logs` | Per-call token usage, attributable to a specific agent role and model |
| `embedding_cache` | Content-hash-keyed cache to avoid re-embedding unchanged text |
| `eval_cases` / `eval_results` | Structured evaluation suite and results |

Vector search runs natively in Postgres via `pgvector` — chosen deliberately over a standalone vector database, since retrieval results need to join against `documents`/`connections` for citation and access control, and the data volume here doesn't approach the scale where a dedicated vector store would outperform an indexed Postgres column.

---

## Token and cost optimization

- **Model routing by task**: cheaper, faster models are used for judgment/classification tasks (planning, critique, guardrails); a larger model is reserved for the one task where output quality matters most — synthesis
- **Retry-context compression**: previously-cited chunks are replaced with placeholders on retry rather than resent in full
- **Embedding cache**: identical text (a re-synced unchanged document, repeated boilerplate) is embedded once, not on every encounter
- **Retrieval deduplication**: near-duplicate chunks are filtered out before reaching the Synthesizer, reducing both token spend and redundant context

---

## Known limitations

Being direct about these is part of the engineering, not an afterthought:

- **Memory deduplication is summary-level**, not fact-level — two memories with partial factual overlap but different phrasing may not be caught as duplicates. Acceptable trade-off for the added cost of fact-level dedup at this stage.
- **Output guardrail's risky-action detection is a stub** — PII redaction is implemented; broader risky-action detection (e.g. flagging generated instructions for destructive operations) is scoped as future work.
- **Sequential processing, no job queue** — ingestion and query handling run synchronously; background job processing for ingestion is a natural next step at higher data volume.
- **Citation-to-claim mapping in the verifier relies on sentence-level text matching**, which can lose precision when a single sentence cites multiple chunks. A structured claim-citation output from the Synthesizer (rather than inferring the mapping from bracket positions in prose) would be a more robust version of this.

---

## Stack

FastAPI · LangGraph · Groq · Supabase (Postgres + pgvector) · Next.js · sentence-transformers (local embeddings)