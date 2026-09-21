# 🛡️ Sentinel-RAG

**A self-correcting, multi-agent RAG system with prompt-injection defense, token-cost optimization, and full execution observability.**

Sentinel-RAG answers questions over live, continuously changing data (Notion, Gmail) using a pipeline of specialized agents — a planner, retriever, synthesizer, citation verifier, and critic — that collaborate, check each other's work, and iteratively self-correct before returning an answer. Every agent decision, retry, and token spent is traced and queryable.

<!-- OPTIONAL: drag a screenshot of the trace UI or homepage into GitHub's editor to get an image URL, then paste it here -->
<!-- ![Sentinel-RAG trace view](PASTE_IMAGE_URL_HERE) -->

---

## 💡 Why this exists

Most RAG demos answer a question by retrieving some text and asking an LLM to summarize it. That approach has no way to know if its own answer is actually correct, no defense against malicious content hiding inside retrieved documents, and no visibility into what it's costing to run.

Sentinel-RAG is built around a different premise:

> **An agent that can catch and correct its own mistakes, resist adversarial input, and account for every token it spends is a fundamentally more trustworthy system than one that just generates and returns.**

---

## 🏗️ Architecture

### Pipeline flow

```
┌─────────────────┐
│  Memory Reader   │  semantic search over long-term memory
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│   Input Guard    │  prompt-injection defense on the raw query
└────────┬─────────┘
         │
   ┌─────┴──────┐
   ▼            ▼
┌────────┐  ┌──────────┐
│ Blocked│  │ Planner  │  decomposes query into sub-questions
└────────┘  └────┬─────┘
                  │
                  ▼
            ┌──────────┐
            │Retriever │  pgvector similarity search + dedup
            └────┬─────┘
                  │
                  ▼
            ┌──────────┐
            │  Chunk    │  injection defense on RETRIEVED content
            │  Guard    │  (live data sources are untrusted too)
            └────┬─────┘
                  │
                  ▼
            ┌──────────┐
      ┌────▶│Synthesizer│  generates answer, cites chunk_id per claim
      │     └────┬─────┘
      │           │
      │           ▼
      │     ┌──────────────┐
      │     │  Citation     │  verifies each cited chunk actually
      │     │  Verifier     │  supports the claim attached to it
      │     └────┬─────────┘
      │           │
      │           ▼
      │     ┌──────────────┐
      │     │   Output      │  redacts PII before returning
      │     │  Guardrail    │
      │     └────┬─────────┘
      │           │
      │           ▼
      │     ┌──────────┐
      │     │  Critic   │  approves OR rejects with actionable reason
      │     └────┬─────┘
      │           │
      │   ┌───────┼────────────┐
      │   ▼        ▼            ▼
      │ ┌──────┐ ┌────────┐ ┌────────────┐
      └─┤retry │ │approve │ │ unresolved │
        └──────┘ └───┬────┘ │(retry limit│
                      │      │  reached)  │
                      ▼      └────────────┘
                ┌─────────────┐
                │Write Memory │
                └─────────────┘
```

Implemented as a **LangGraph state machine** — a graph rather than a linear chain, specifically because the retry loop (`critic → synthesizer`) requires cycles, not just sequential steps.

### Agent responsibilities

| Agent | Role |
|---|---|
| 🧠 **Memory Reader** | Semantic search over long-term memory for facts relevant to the current query, carried from prior sessions |
| 🚧 **Input Guard** | Prompt-injection defense on the user's query before any retrieval happens |
| 🗺️ **Planner** | Decomposes the query into focused sub-questions for better retrieval coverage |
| 🔍 **Retriever** | Vector similarity search (pgvector) across sub-questions, with over-fetch + deduplication |
| 🛡️ **Chunk Guard** | Applies injection defense to *retrieved* content — live data sources are untrusted input too |
| ✍️ **Synthesizer** | Generates the answer, citing the specific `chunk_id` behind every factual claim |
| ✅ **Citation Verifier** | Independently checks whether each cited chunk's content genuinely supports the specific claim attached to it |
| 🔒 **Output Guardrail** | Redacts PII from the generated answer before it's returned |
| ⚖️ **Critic** | Judges the answer; approves, or rejects with a specific, actionable reason fed back into the next retry |

### The retry loop

If the Critic rejects an answer, the reason is fed directly back into the Synthesizer, which **revises rather than starting over blind**. This repeats up to a fixed retry limit; if still unresolved, the pipeline stops cleanly with an explanation rather than looping indefinitely or returning a low-confidence guess.

On each retry, chunks already cited in the previous attempt are **compressed to a placeholder** rather than resent in full — reducing token cost on retries without reducing what the model has access to.

---

## 🧪 Example run

A real trace from `test_graph_pipeline.py`, run end-to-end against live Gmail data.

**Query:**
> *"What internships have I received and what's blocking Project Alpha?"*

### ┌─ Pipeline events ─────────────────────────────────────────┐

```
Memory Reader     → found 1 relevant memory (similarity 0.703)
Input Guard       → CLEAN (passed all security layers)
Planner           → decomposed into 2 sub-questions
Retriever         → 5 chunks pulled via match_chunks (pgvector)
Chunk Guard       → scanned 5 chunks, excluded 0 poisoned chunks
Synthesizer #1    → answer generated  (in: 5,901 · out: 446 tokens)
Output Guardrail  → 0 PII items redacted
Critic #1         → ❌ REJECT — citations not verified as accurate
Synthesizer #2    → answer revised    (in: 6,081 · out: 402 tokens)
Output Guardrail  → 0 PII items redacted
Critic #2         → ✅ APPROVE — both parts of the question answered,
                     citations verified
Write Memory      → skipped (no new durable fact to store)
```

> **Note the Groq `429` retries in the raw log** — the pipeline transparently absorbed three rate-limit backoffs (1s, 9s, 17s, 38s, 51s) via the client's built-in retry, without failing the run. This is reflected in the elevated latency figures below, not in token cost.

### ┌─ Retrieval — what actually came back ────────────────────┐

The retriever pulled from a **live, unfiltered Gmail inbox**, and the result set is a good illustration of why `chunk_guard` and `citation_verifier` exist as separate steps:

| # | Chunk | Similarity | Relevant? |
|---|---|---|---|
| 1 | Internshala promotional email listing two internships | 0.286 | ✅ Used |
| 2 | "Sign in with Google" security notice | 0.092 | ❌ Noise |
| 3 | Project Alpha status update | 0.074 | ✅ Used |
| 4 | Google Terms of Service update notice | 0.131 | ❌ Noise |
| 5 | BBC tech newsletter (surveillance / self-flying planes) | 0.112 | ❌ Noise |

Three of five retrieved chunks were irrelevant marketing/newsletter noise — the Synthesizer and Citation Verifier correctly ignored them rather than fabricating a citation to make the answer look more complete.

### ┌─ Final answer ────────────────────────────────────────────┐

> Based on the retrieved documents, you have two internship opportunities listed: a Junior Manual Tester/QA position at Jarvis Technology & Strategy Consulting in Delhi, and a Database Analyst position at TSTEPS PRIVATE LIMITED in Keralapuram, Andhra `[0a5c3941…]`. Project Alpha is currently blocked by a delay from a third-party API provider `[12a4cd66…]`.

| Field | Value |
|---|---|
| Verdict | `approve` |
| Retry count | 1 |
| Blocked (input guard)? | No |
| Citations verified | ✅ True |
| Total attempts | 2 |
| Final status | `resolved` |

### ┌─ Node-by-node trace ──────────────────────────────────────┐

```
 memory_reader        tokens=0      latency=   592ms
 input_guard          tokens=0      latency=   485ms
 planner              tokens=149    latency=   626ms
 retriever            tokens=0      latency=   977ms
 chunk_guard          tokens=0      latency=   858ms
 synthesizer          tokens=6347   latency= 40777ms  ◄ retry 1 (incl. 38s backoff)
 citation_verifier    tokens=0      latency= 18267ms
 output_guardrail     tokens=0      latency=     4ms
 critic               tokens=370    latency=  1789ms  ◄ REJECT
 synthesizer          tokens=6483   latency= 53799ms  ◄ retry 2 (incl. 51s backoff)
 citation_verifier    tokens=0      latency= 10130ms
 output_guardrail     tokens=0      latency=     1ms
 critic               tokens=376    latency=  1944ms  ◄ APPROVE
 write_memory         tokens=0      latency=   802ms
 ────────────────────────────────────────────────────
 Total events:   14
 Total tokens:   13,725
 Total latency:  131,051ms (131.1s)
```

### ┌─ Token breakdown by agent role ───────────────────────────┐

| Agent | Tokens | Share |
|---|---:|---:|
| Synthesizer | 12,830 | 72.0% |
| Retriever (embeddings) | 4,093 | 23.0% |
| Critic | 746 | 4.2% |
| Planner | 149 | 0.8% |

**Takeaway:** synthesis dominates cost, as expected — it's the only step running the larger model on the full context. This is exactly what the token/cost breakdown view in the trace UI is meant to surface at a glance.

---

## 🔒 Security

Retrieved content is treated as **untrusted input**, not just the user's own prompt — a malicious instruction embedded inside a Notion page or email thread is a real attack surface for any RAG system that blindly trusts what it retrieves. The example run above shows this in practice: a live Gmail inbox returned promotional emails and newsletters riddled with tracking links and HTML noise, and the pipeline correctly kept them out of the final answer.

| Layer | Defense |
|---|---|
| **Input Guard** | Layered defense against prompt injection in the user's query |
| **Chunk Guard** | The same defense applied to every retrieved chunk before synthesis |
| **Output Guardrail** | PII redaction on the generated answer |
| **Citation Verifier** | A structural defense against hallucination — catches the Synthesizer citing a chunk that doesn't actually support what it's claiming |

---

## 📊 Observability & cost tracking

Every node execution is logged — input, output, tokens used, latency — regardless of whether that node calls an LLM. This makes it possible to answer, after any run:

- Which node was the bottleneck?
- How many tokens did a specific retry cost, versus the first attempt?
- Which agent role consumes the most tokens across a run?
- Did retry-compression actually reduce cost, and by how much?

A FastAPI endpoint exposes full per-run traces; a Next.js frontend renders them as an execution timeline with a token/cost breakdown by agent role.

<!-- PASTE a screenshot of the /trace/[runId] page here once styled -->

---

## 🗄️ Data model (Supabase / Postgres + pgvector)

| Table | Purpose |
|---|---|
| `connections` | Source credentials for live data connectors (Notion, Gmail) |
| `documents` | Raw ingested content per source |
| `chunks` | Chunked, embedded content — the retrieval unit |
| `memory_short_term` / `memory_long_term` | Session-scoped vs. persistent semantic memory, deduplicated on write |
| `agent_runs` / `agent_attempts` | Run-level and attempt-level execution records |
| `trace_events` | Full node-by-node execution log |
| `token_logs` | Per-call token usage, attributable to a specific agent role and model |
| `embedding_cache` | Content-hash-keyed cache to avoid re-embedding unchanged text |
| `eval_cases` / `eval_results` | Structured evaluation suite and results |

Vector search runs natively in Postgres via `pgvector`, chosen over a standalone vector database since retrieval needs to join against `documents`/`connections` for citation and access control, and data volume here doesn't approach the scale where a dedicated vector store would outperform an indexed Postgres column.

---

## 💰 Token and cost optimization

- **Model routing by task** — cheaper, faster models for judgment/classification tasks (planning, critique, guardrails); a larger model reserved for synthesis, where output quality matters most
- **Retry-context compression** — previously-cited chunks replaced with placeholders on retry
- **Embedding cache** — identical text is embedded once, not on every encounter
- **Retrieval deduplication** — near-duplicate chunks filtered before reaching the Synthesizer
- **Batched guardrail/verification calls** — chunk guardrail and citation verification evaluate multiple items in a single LLM call rather than one call per item

<!-- PASTE your real measured numbers here once available, e.g.:
- X% token reduction from retry-compression (measured across N runs)
- X% fewer API calls from batching (before/after)
-->

---

## ✅ Evaluation

<!-- PASTE your D25 eval results here once complete:
- Overall accuracy: X%
- Citation correctness: X%
- Retry-resolution rate: X% resolved within 3 attempts
- Average tokens/query: X
- Category breakdown: normal / adversarial / missing-data / edge-case
-->

---

## ⚠️ Known limitations

- **Memory deduplication is summary-level**, not fact-level — two memories with partial factual overlap but different phrasing may not be caught as duplicates
- **Output guardrail's risky-action detection is a stub** — PII redaction is implemented; broader risky-action detection is scoped as future work
- **Sequential processing, no job queue** — ingestion and query handling run synchronously
- **Citation-to-claim mapping relies on sentence-level text matching**, which can lose precision when a single sentence cites multiple chunks

---

## 🧰 Stack

`FastAPI` · `LangGraph` · `Groq` · `Supabase (Postgres + pgvector)` · `Next.js` · `sentence-transformers` (local embeddings)

---

## 🚀 Setup

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # or source venv/bin/activate on Mac/Linux
pip install -r requirements.txt
# Fill in .env.local with SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
