# femaktiv live chat

## Goal of the document

Define conversational assistance using private chat context, anonymous model processing, cited evidence and current local-care lookup.

## Scope

This contract extends the [bilingual platform](platform.md) with an explicitly configured live mode for a private prototype using fictional information. The initial acceptance scenarios are nutrition with hypertension, protein/fibre goals and dietary exclusions, and organising support for an older parent after an injury in Germany. General conversation remains available. Public examples keep their approved wording; live-state controls are authorised by the live-chat implementation request. This contract supersedes the platform's placeholder-only reply behavior when live mode is selected. It does not activate the historical recipe-catalogue or clinical-review gates of the initial nutrition build.

## Modes and configuration

`FEMAKTIV_AI_MODE` MUST be `placeholder` (default) or `live`. Live requests require server-only `ANYMIZE_API_KEY`, `ANYMIZE_MODEL`, `BRAVE_SEARCH_API_KEY`, and `ANYMIZE_ZDR_CONFIRMED=1`. The last setting records the operator's confirmation that Zero Data Retention is enabled in the Anymize account; it MUST NOT be described as remotely verified. Missing configuration MUST produce an explicit unavailable state, without unprotected provider or fixture fallback. Existing stored modes MUST remain unchanged.

The application MUST explain that selected text reaches its server and Anymize, that masking happens before the downstream model, and that useful health details remain sensitive. Neither provider metadata nor identifier replacement establishes complete anonymity or clinical correctness. Logs MUST exclude private content, raw provider exceptions, credentials, mappings, and search queries.

## Conversation and active context

The assistant SHOULD answer naturally and ask at most three questions when missing or ambiguous facts materially affect the answer. It MUST distinguish reported facts from assumptions, preferences from allergies, and information about the user from information about a parent. It MUST NOT infer absence of allergies from missing information. General guidance and practical next steps MAY accompany clarification. Mentioning a diagnosis alone MUST NOT cause an automatic refusal. The assistant MUST NOT invent diagnoses, treatment changes, supplement prescriptions or service eligibility.

Live chat MUST use an isolated context segment. The first live request in an existing chat MUST exclude its earlier placeholder conversation. Raw messages and active note copies within the current segment are available to intake. Account identifiers, other chats and unrelated notes MUST NOT be included. Bound the input to 60,000 characters; exceeding the bound MUST request a context reset or smaller note selection rather than silently discarding constraints. No rolling model summary is retained in this version.

Selecting notes on a live message pins immutable title/body copies in that chat, with at most five active notes in total. Later replies MUST reuse those copies. Editing or deleting the original MUST NOT silently update or remove a pinned copy. Per-message context snapshots MUST include the copies actually used. Owners can explicitly remove, refresh or clear active context. Remove/refresh/reset and replacing or clearing an established locality MUST begin a new segment, invalidate any in-flight reply, and exclude all earlier messages and derived content from future calls. Earlier messages remain visible. Setting a locality for the first time MUST preserve the current conversation so a location clarification does not erase its original question; it still invalidates any in-flight reply. New chats MUST start without inherited context.

Local lookup MUST use a separately supplied, editable city or five-digit German postcode, at most 80 characters. It MUST NOT extract and export an address or a location inferred from private prose. Search queries MUST be constructed by the server from this field and a fixed service category, never from free-form model-generated queries or transcripts.

## Provider and retrieval

Use `POST https://app.anymize.ai/api/v1/llm-anonymous/chat/completions`, with `stream=false`, the requested English/German language and JSON-schema output. An adapter MUST check `_anymize.anonymized` is exactly true, successful completion, bounded response size and the application schema. Do not request identity mappings or depend on de-anonymization. The configured model MUST be an actual account-accessible identifier; the explicit evaluation command checks it with `GET /api/v1/llm/models`. Model/schema support and preservation of useful facts require live evaluation.

One turn performs structured intake, then either returns relevant clarification or retrieves information and composes a cited answer. It MUST make at most two model calls, two searches and three public-page requests, including redirects, within a 60-second application deadline. The local server timeout MUST accommodate that deadline. There are no automatic paid retries, tool-execution loops or streaming replies. The private prototype permits at most 30 new reservations per account per hour.

The evidence library MUST contain versioned, source-checked paraphrases with stable ids, titles, organisations, exact HTTPS URLs, sections, nullable publication/update dates, checked dates, topic tags, population applicability and limitations. Source checks MUST be distinguished from human editorial approval and clinical review. Begin with DGE general food guidance, NHLBI DASH guidance, German federal discharge/care guidance and ZQP. Targeted NIH/EFSA entries MAY support nutrient questions; bulk cohort ingestion and model training are outside this change.

Brave Search MUST receive only a fixed German service category and the explicitly supplied locality. Retrieved pages MUST identify the organisation, locality and relevant contact information before they become local-contact citations. Prefer government, insurer, established-directory and service-operator pages. Search snippets alone MUST NOT establish contact details. Unavailable pages or unverified results MUST produce an honest lookup limitation with existing guidance/directories, not invented contact details. Language support, appointment availability and eligibility MUST remain unknown unless supported; fetching a page does not verify capacity.

Remote content MUST remain untrusted input. Only public HTTP(S) URLs without credentials or unusual ports are fetchable. Validate each redirect and pin connections to validated public IP addresses to prevent DNS rebinding. Do not forward authentication, cookies or referrers to retrieved pages. Limit fetched content sizes and remove scripts/styles. The model MUST NOT choose arbitrary fetch URLs or follow instructions embedded in retrieved content.

Each answer paragraph MUST identify only supplied source ids. The server resolves URLs, validates ids and stores citation snapshots with the reply. Source names, URLs and public contact cards MUST come from source records rather than generated prose. Nutrition/care factual explanations require citations; practical suggestions and questions are distinguished from factual explanations. Source-backed prose is still subject to semantic evaluation and MUST NOT be represented as automatically proven correct.

## HTTP and persistence

The existing message POST retains exactly `content`, `note_ids` and `client_request_id` with the platform's limits. Placeholder behavior remains atomic and offline. Live note ids add new pinned copies; an existing pinned note requires an explicit refresh to replace its copy. The live response adds `kind`, `paragraphs`, `citations`, `lookup_status`, `active_context` and `status`; `mode` reflects the stored reply.

`GET /<language>/api/chats/<chat_id>/turns/<client_request_id>/` returns the owner's stored completed result, a 202 processing response, or a stored error. `POST /<language>/api/chats/<chat_id>/context/` accepts one action: `remove`/`refresh` with `note_id`, `locality` with `locality`, or `reset` without another property. It returns the current context. All private access MUST enforce ownership, CSRF on writes and no-store caching.

Before network activity, atomically create a durable request reservation, fingerprint the submission and capture its context. Database uniqueness MUST permit only one processing turn per chat. External calls MUST run outside database transactions. Recheck the reservation before each external stage and after intake; an invalidated/deleted turn MUST NOT proceed to later lookup or composition. An already transmitted request cannot be recalled. A repeated id with the same payload MUST reuse its reservation/result without another call; changed payload returns 409. Another request during processing returns 409. Completion MUST atomically save both messages and snapshots only if the reservation and context are still current. Deleting a chat MUST prevent late completion from recreating it.

Failed or expired reservations retain safe error metadata and the payload fingerprint, not private working copies. Unknown outcomes MUST NOT be retried automatically. The UI MUST retain a failed draft, poll a processing reservation, and offer an explicit new attempt after a terminal failure; a lost response first retries the same id. Context resets and navigation MUST suppress stale results. The browser MUST stop waiting after 75 seconds while retaining the recovery id and draft. Context updates have a 15-second browser deadline; if a write outcome cannot be confirmed, refresh the context before permitting further inference.

## Verification and operation

The [live-chat workflow](../../workflows/implement-live-chat.donna.md) owns implementation and offline verification. Routine checks MUST disable external traffic even when the process inherits real credentials. Unit tests MUST cover provider schemas/metadata/errors, safe query construction, network destination/redirect protections, citation integrity, bounded context, owner isolation, reservations, timeouts and context invalidation. Mocked multi-turn scenarios and browser checks MUST cover both languages and 390px/1440px.

`manage.py evaluate_live_chat --allow-provider-calls` is a separately invoked fictional evaluation. It MUST verify configuration/model access, structured output, anonymization metadata, meaningful intake facts and cited scenario results, and report safe measurements plus the fictional generated answers for human review. It MUST NOT run from ordinary checks or claim anonymization accuracy from metadata alone. Implementation can be complete with live evaluation explicitly unperformed.

## References

Provider behavior was checked against the [Anymize anonymous-chat documentation](https://app.anymize.ai/api-docs/anonymization) and [chat documentation](https://app.anymize.ai/api-docs/chat). [Brave's API documentation](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started) describes search parameters. The [EDPB explanation](https://www.edpb.europa.eu/topics/ai-and-technology/anonymisation-pseudonymisation_en) distinguishes anonymisation from pseudonymisation. These references explain integrations and terminology; they are not evidence of a successful live test.
