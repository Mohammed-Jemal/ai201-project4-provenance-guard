# Provinance Guard
An AI enginering pipeline built to analyze text submissions(such as poam, stories, blog post) evaluate them across structural and semantic signals and verifyable transparency labels alongside a robust appeals workflow.

## Architecture overview
The system operates as a decoupled, single-instance Flask REST API utilizing a modular, multi-signal grading engine. When a payload hits the server:
1. **Ingestion Layer:** Validates input strings and tracks client session telemetry.
2. **Analysis Engine Pipeline:** Dispatches incoming text concurrently across two local, deterministic python algorithms (Sentence Variance and Type-Token Ratio) and one external semantic evaluator (`llama-3.3-70b-versatile` via Groq Cloud API).

3. **Consolidation Layer:** Computes an ensemble weighted index ($20\%$ Heuristics, $60\%$ LLM Context) to map the payload against static fallback boundary arrays.
4. **Persistence & Response:** Appends a structured transactional metadata snapshot to a localized JSON datastore (`database.db`) before rendering JSON states back to the consumer client application.

```text
[POST /submit] ──► [Flask Ingestion] ──► [Sentence Variance (20%)] ──────┐
                                     ──► [Vocabulary Diversity (20%)] ──┼──► [Ensemble Score Builder] ──► [Update database.db] ──► [Client Payload]
                                     ──► [Groq Cloud API API (60%)] ────┘
                                     
[POST /appeal] ──► [Log Query Engine] ──► [Identify Target content_id] ──► [Mutate Status state: "under_review"] ──► [Append Appeal Meta]

## Detaction signals

* **signal 1:** Stylometric Heuristics(Sentence length variance)
* **signal 2:** Stylometric Heuristics(Vocabulary diversity/Type token ratio)
* **signal 3:** LLM semantic analysis(`llama-3.3-70b-versatile` via Groq api)

## Transparency labels
The system explicitly surfaces one of the following exact string responses based on calibrated confidence thresholds:


**High confidenc human (score < 0.40):**
`verified authentic: this content exhibits strong characteristics of original human writing

**Uncertain/Boarderline (0.4 < score <= 0.65)**
`Content unclear:The text contain mix of structural signals. Our automated system cannot detrmine its origin.

**High confidence AI(score > 0.65):**
`Automated generation likely: Significant patterns in this text allign closely with machine-generated structure

## Ratelimitting and production setting:
To secure ingension point from denial of service vulnerabilities the application is protected by flask-limiter utilizing local in memory tracking structure.
    *endpoint protected: POST/Submit
    *threshold maximum 5 requests per minutes per unique client IP address
    *Failure trapping behavior: excess trafic request immediately breach  security treashold, cuasing the server framework to drop the transmission and return  429 too many requests response.

## Audit log sample(GET/log)

[
    {
        "content_id": "f89e1f90-1da6-48c0-8fd4-8fd1603035a0",
        "creator_id": "creator-123",
        "timestamp": "2026-06-30T17:25:12.482Z",
        "attribution": "likely_ai",
        "confidence": 0.88,
        "stylometrics": {
            "sentence_variance_score": 0.90,
            "vocabulary_diversity_score": 0.75
        },
        "llm_score": 0.92,
        "status": "under_review",
        "appeal_reason": "This is standard conversational English, not AI!"
    }
]

## Reflection and AI tool usage
1. Conceptual Design & IterationDuring development, balancing statistical metrics with semantic intelligence was critical. Relying purely on sentence lengths failed to catch sophisticated AI styles. Weighting the model score from the llama-3.3-70b-versatile engine at 60% provided the necessary contextual depth to identify subtle patterns while keeping the faster, local calculations intact.

2. AI Collaboration Notes
AI assistance was utilized systematically to draft data tracking boilerplate structures, isolate string parser validation errors, and structure multi-signal logic equations. When encountering a complex platform execution issue under PowerShell involving mock API client payload strings, the AI collaborator successfully generated custom Python integration test blocks that successfully validated state changes across endpoints.