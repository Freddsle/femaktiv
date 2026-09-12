# femaktiv validation

Implementation review on 12 September 2026. This report records the local Django prototype governed by [the platform specification](../specs/behavior/platform.md) and [live-chat extension](../specs/behavior/live_chat.md). Startup and extension instructions are in [README](../README.md). The latest results are in [Anymize-only live chat](#anymize-only-live-chat); earlier sections preserve historical checks and requirements that were subsequently changed.

## Environment

Python 3.14.5, Django 5.2.17, Gunicorn 23.0.0, WhiteNoise 6.12.0, Playwright 1.62.0 and Google Chrome 151.0.7922.137 on Linux. Application dependencies are pinned in `uv.lock`; local persistence uses SQLite.

## Automated verification

The integration check is `./bin/check`: translation validation/compilation, Ruff lint/format, Django system checks, missing-migration checks, static-file collection, backend tests and browser journeys. Donna runs this command followed by Depmesh verification, workflow validation and `git diff --check`.

Donna's verification step completed successfully:

| Check | Observed result |
| --- | --- |
| German translations | 260 translated entries, no fuzzy/untranslated entries; compilation passed |
| Ruff lint and formatting | Passed; 60 Python files formatted |
| Django system and migration checks | No issues; no missing migrations |
| Static collection | Passed; versioned CSS, JavaScript and image assets generated |
| Backend tests | 58 passed |
| Playwright browser tests | 4 passed |
| Depmesh | 114 files, 256 directed relations; all 15 source/test fixture pairs and exclusions passed |
| Donna workflow validation | All artifacts valid |
| Whitespace check | `git diff --check` passed |

Backend coverage includes registration, recovery tokens/emails, CSRF enforcement, owner isolation including staff accounts, note edits/deletion, immutable message context, durable chats, atomic rollback, idempotent retries and conflicting request identifiers. Localization checks include a German browser on an English page and a language cookie that differs from the current page.

The four browser journeys cover account creation through note attachment and saved history; a failed request with draft retention and a keyboard skip link; a delayed response after navigation; and public examples/topic filtering in both languages. They assert no unexpected JavaScript or HTTP errors and no horizontal overflow in the checked layouts.

## Local deployment and review

`./bin/serve` starts Gunicorn with `DEBUG=False`, WhiteNoise assets and a loopback-only HTTP listener. English is at `http://127.0.0.1:8000/`; German is at `http://127.0.0.1:8000/de/`. A stable private signing key and the local database live in ignored `.local/`.

Browser screenshots are written to `.local/screenshots/`. The review covers 1440px desktop and 390px mobile layouts, both languages, and the signup, private-note, attachment, conversation-history and logout/login journey.

Reviewed `home-en-desktop.png`, `home-de-desktop.png`, `home-de-mobile.png`, `community-en-mobile.png`, `chat-en-desktop.png` and `chat-de-mobile.png`. Decorative hero rings were adjusted to remove mobile/tablet overflow. Additional browser measurements passed for 12 English/German public and account pages at 390px and the German homepage at 360, 390, 700, 720, 768, 900, 1024 and 1440px.

A separate production-mode browser smoke check used an isolated temporary SQLite database and actual Gunicorn/WhiteNoise. Registration, a private note, a message with an attached snapshot, English-to-German switching, private no-store headers and collected CSS all passed. Restarting the server preserved the session, both messages and the attachment snapshot. The temporary database was removed afterwards.

`manage.py check --deploy` passed with a generated secret, explicit host/CSRF origin, `DEBUG=False` and the local-HTTP override disabled. The local helper rejects additional bind arguments and ignores `GUNICORN_CMD_ARGS`; its intended listener is loopback only.

## ngrok preview follow-up

On 12 September 2026, `bin/serve` gained the opt-in `FEMAKTIV_PUBLIC_URL` HTTPS preview mode described in [README](../README.md#share-a-preview-through-ngrok). The full `./bin/check` run passed: 260 German translations, Ruff lint and formatting for 62 Python files, Django system/migration checks, static collection, 63 backend tests and four browser scenarios. Depmesh specification/link/graph checks, all 15 isolated relation fixtures, Donna validation and `git diff --check` also passed.

The five new launcher tests cover the default loopback HTTP mode and stable private key, exact public host and CSRF origin, secure cookies, HTTPS forwarding, rejection of foreign hosts/origins, URL normalization, and invalid URL/port/bind inputs. Depmesh resolves `bin/run_local.py` and `tests/unit/bin/test_run_local.py` in both directions through the existing Python convention.

A separate smoke check started the actual `./bin/serve` process on temporary loopback ports in both modes. Local HTTP, English/German pages, collected CSS and logo assets, HTTPS redirects, exact host validation, secure CSRF cookies and same-origin/foreign-origin form handling passed. The check simulated ngrok's `Host` and `X-Forwarded-Proto` headers; it created no accounts and stopped both test servers. No external tunnel or provider request was made.

At that implementation review, the ngrok CLI was not installed in the inspected environment, so the checks above did not exercise a public endpoint. The subsequent live tunnel check is recorded below.

### Live tunnel access repair

Later on 12 September 2026, the user's existing `https://unlocked-fabric-nearness.ngrok-free.dev` tunnel returned HTTP 400 from Gunicorn while local HTTP returned 200. The running Django server still had `DJANGO_LOCAL_HTTP=1` and allowed only loopback hosts. Sending the public Host header directly to the local server reproduced the same 400 response.

Restarted the identified femaktiv server with `FEMAKTIV_PUBLIC_URL=https://unlocked-fabric-nearness.ngrok-free.dev ./bin/serve`. The existing launcher required no code change. The restart preserved the signing key and database configuration; the user's existing ngrok process remained running with traffic inspection disabled.

Live HTTPS checks passed for the root redirect to English, `/en/`, `/de/`, both language versions of the login page, the collected CSS and the rounded logo. The CSRF cookie was secure; an empty same-origin login submission reached normal form validation (200), and a foreign-origin submission was rejected (403). Local requests confirmed rejection of a foreign hostname (400) and redirecting HTTP to the exact configured HTTPS origin (301). The probes used ngrok's browser-warning bypass header and did not create accounts or access private content.

Public browser checks also passed for English and German at 1440px and 390px: pages returned 200, the logo loaded at its expected resolution, there was no horizontal overflow, and no JavaScript or HTTP errors were observed. Screenshots are saved as `.local/screenshots/ngrok-{en,de}-{desktop,mobile}.png`; the English desktop and German mobile screenshots were visually reviewed.

A separate `./bin/check` run during concurrent homepage/translation edits passed translation compilation, lint/format, Django system/migration checks, static collection and all 63 backend tests. Three browser journeys passed; the responsive bilingual journey initially failed its German mobile overflow assertion. After the concurrent task finished, a focused rerun of `tests.e2e.test_platform.PlatformBrowserTests.test_public_examples_and_responsive_bilingual_layouts` passed without any source/test edits for this access repair. The initial failure was not reproduced by the live public browser checks. Depmesh (117 files, 264 directed edges and 15 isolated fixture pairs), Donna validation and `git diff --check` passed. The shared Donna session advanced externally during this repair and was idle at the final status check; it was not reset. Final public requests to both language pages still returned 200.

## Prototype boundaries

Chat persistence and account ownership are real. Placeholder replies remain the default. Optional live chat is implemented as described below; live provider evaluation has not been performed. Q&A and the two public conversations contain authored examples. Public posting, moderation, file uploads and clinical review remain future work.

The application is accessible through the user's temporary ngrok preview while both processes are running; no hosting-provider deployment was performed. HTTPS forwarding was exercised by the live tunnel check above. PostgreSQL, external SMTP delivery and a hosting provider remain untested. Password recovery uses the local console email backend. The browser suite uses fictional data and a disposable test database.

## Homepage headline update

On 12 September 2026, the homepage's emphasized headline changed to “Find trusted health answers faster.” in English and “Finde schneller verlässliche Antworten auf deine Gesundheitsfragen.” in German. The existing typography and surrounding copy are retained.

`./bin/check` passed through Donna: 260 translations validated and compiled, Ruff and Django checks passed, static collection succeeded, and all 63 backend tests and four browser journeys passed. Depmesh verification, Donna validation and `git diff --check` also passed. The first browser attempt was blocked by sandbox socket restrictions; the rerun with local socket/browser access passed.

Additional production-browser checks confirmed the exact headlines, correct language and no horizontal overflow at 390px and 1440px in both languages. Reviewed all four `headline-{en,de}-{desktop,mobile}.png` screenshots in `.local/screenshots/`. The existing preview workers were reloaded, and both updated headlines were verified through loopback requests using its configured preview headers. The temporary production-check server was stopped; the existing preview remains running. No external tunnel or provider request was made. The existing README startup instructions remain applicable.

## Rounded logo refinement

On 12 September 2026, the user authorized retaining only the soft central cross, preserving its central artwork, and improving resolution. The website uses [the rounded PNG](../static/img/femaktiv-logo-rounded.png); [the original image](../static/img/femaktiv-logo.png) remains unchanged.

The built-in image_gen tool produced the higher-resolution artwork. Its two outputs contained an opaque checkerboard, so the user explicitly authorized programmatic background removal. Pillow removed only the connected neutral exterior, refined the silhouette edge, and exported a 2048×2048 RGBA PNG. The generated artwork's central RGB pixels and full opacity were checked before final resampling. The exported corner pixels have alpha zero, with a full alpha range of 0–255. This is an actual transparent asset.

All logo consumers use the new asset, including the favicon, standalone error page, and new assistant messages. Intrinsic dimensions are square, and the former rectangular shadow and corner clipping have been removed.

The existing four browser journeys passed after the update. Desktop/mobile chat screenshots showed clean cutouts. Additional production-browser checks verified the 2048px image, transparent corner pixels, English/German pages and no horizontal overflow at 1440px and 390px.

### Image generation prompts

Built-in image_gen was used; the CLI/API fallback was not used. The following prompts record the generation inputs. Final transparency was completed with the separately authorized local processing described above.

First edit, using the original supplied logo:

```text
Use case: background-extraction / precise-object-edit.
Asset type: the existing femaktiv brand logo, cleaned up for use as a transparent website logo.
Image 1 is the EDIT TARGET and the only authority for the design. This is a careful restoration of this existing logo, not a redesign.

Primary request: extract just the central soft four-lobed rounded cross/clover emblem from the pink square screenshot. Remove all pale-pink rectangular background outside that four-lobed silhouette, the thin black screenshot edges, and any exterior artifacts. The resulting PNG must have a genuinely transparent alpha background, NOT a white or pink square and NOT a checkerboard drawn into the image.

Keep the center design exactly recognizable and unchanged: lowercase white serif word "femaktiv" across the middle; the small exact white tagline "- lifecycle essentials -" below it; the delicate white radial sun above the word; the group of white horizontal waves below. Preserve their relative placement, sizes, original letterforms, proportions, and spacing. Preserve the emblem's existing left-purple, middle-mauve/rose, right-coral/orange smooth gradient, with no invented colors. Do not change the central artwork, do not simplify it, do not remove the tagline or symbols.

Improve only edge quality and source resolution: smooth, clean, slightly rounder balanced lobes, softly curved joins, faithful to the supplied rounded cross. It should remain a four-lobed cross, not become a circle or a many-petaled flower. Crisp typography and graceful thin sun/wave lines, polished high-resolution rendering, preferably 2048x2048 PNG. Flat graphic, no bevel, no 3D, no lighting, no added shadow, no outline.
Composition: one emblem, centered, upright, occupying about 90% of a square canvas, equal minimal transparent padding. No alternate versions, no presentation board, no added words or decorative elements.
```

Background-only follow-up, using the first generated image:

```text
Use case: background-extraction.
Image 1 is the EDIT TARGET: an already finished femaktiv logo. Perform ONLY precise background removal. Preserve the colored four-lobed cross and ALL pixels, typography, sun, waves and gradient inside its outer silhouette as closely as possible. Do not redesign, recolor, retype, regenerate or reshape the emblem.

The existing gray checkerboard OUTSIDE the colored cross is an unwanted opaque background, not transparency. Remove every pixel of that checkerboard and its scratches and lines. Replace the outside with actual alpha=0 transparency in the saved PNG. The required output is an RGBA PNG file with a real transparency channel, not an RGB image showing a transparency grid. No painted grid, no white/gray/black/pink backdrop, no halo, no square panel, no shadow. Clean antialiased edge around the single existing rounded cross. Center it with the same canvas and orientation, retaining the existing high resolution.

Keep the exact center text "femaktiv" and "- lifecycle essentials -", the white sun above, the white waves below, and the purple-to-mauve-to-coral gradient unchanged. Only the exterior background changes. Deliver one genuinely transparent PNG cutout.
```

## Login heading update

On 12 September 2026, the shared account-page heading changed to “More clarity.” and emphasized “More time for you.” German uses “Mehr Klarheit.” and “Mehr Zeit für dich.” The footer retains “A little more room for you.” and its existing German translation, as requested in the user's follow-up.

`./bin/check` passed: 260 translations, Ruff lint/format, Django system/migration checks, static collection, 63 backend tests and four browser journeys. The initial browser run encountered sandbox socket restrictions; the rerun with local socket/browser access passed. Depmesh verification, Donna validation and `git diff --check` also passed. After restoring the original footer, translation compilation passed again.

Production-browser checks verified the final login heading, emphasis, original footer, correct language and absence of horizontal overflow or browser errors at 390px and 1440px in both languages. All four `.local/screenshots/login-copy-{en,de}-{desktop,mobile}.png` screenshots were visually reviewed. The temporary production server was stopped, and the existing preview worker was gracefully reloaded. Local requests then confirmed the final English and German copy on the existing preview. No accounts, private data, external tunnels or provider requests were created by these copy checks. The separate example-content review remains pending in Donna.


## Live chat implementation

On 12 September 2026, implemented the user-approved nutrition and family-care chat plan under the scoped live-chat specification and `workflows/implement-live-chat.donna.md`. Approved public examples and their wording remain unchanged. The existing local database received the additive chat migration, and the identified preview workers were gracefully reloaded. English/German login pages and private no-store responses passed through loopback; the preview remains in placeholder mode. Enabling live mode requires restarting with the documented environment settings and updated launcher.

The implementation adds Anymize anonymous structured intake/composition, active note copies and context boundaries, durable turn reservations, a versioned evidence library, constrained Brave queries, public-destination page fetching and saved paragraph/source citations. The first locality entry preserves the question being clarified; replacing an established locality resets the AI segment. Removing or refreshing a note excludes both its copy and all earlier derived chat text from later requests. Cancellation is checked before external stages as well as before saving a reply. Already transmitted requests cannot be recalled.

The final Donna verification completed successfully:

| Check | Observed result |
| --- | --- |
| German translations | 303 entries validated and compiled |
| Ruff lint/format | Passed |
| Django system and missing-migration checks | Passed; no missing migrations |
| Static asset collection | Passed |
| Backend tests | 109 passed, including 62 chat tests |
| Browser journeys | 12 passed, including eight live-chat journeys with mocked services |
| Depmesh | Six specifications, 146 files, 442 directed edges; all 16 isolated source/test fixture pairs passed |
| Donna validation | All artifacts valid |
| Whitespace | `git diff --check` passed |

Backend checks exercise anonymous-route metadata and schema failures, source-id tampering, unsafe destinations and redirects, DNS pinning, response limits, safe search payloads, source applicability, owner/staff isolation, CSRF, atomic rollback, duplicate and concurrent submissions, expired reservations, chat deletion, and cancellation between intake, lookup and composition. Context tests verify persistent copies, explicit refresh/removal, original-note deletion, no cross-chat carry-over and exclusion of historical placeholder messages. The original 16 chat tests continue to pass.

Browser checks cover both scenarios in English and German, keyboard controls, 390px/1440px layouts, saved citations, note removal, locality entry, German call preparation, status polling, terminal failures and explicit retries, retained drafts/recovery ids, navigation during a pending reply, the 75-second browser deadline, and uncertain context writes. Routine checks force `FEMAKTIV_OFFLINE_CHECKS=1`; every model/search boundary is mocked. A stale-static-assets failure in the first focused browser run was resolved by collecting the updated JavaScript. The stalled-connection test was changed to a deterministic fetch fixture to avoid an intercepted-route cleanup warning. The final full run has neither failure.

Reviewed `.local/screenshots/live-chat-{en,de}-{desktop,mobile}.png` and the local-care mobile view. German UI and German newly generated fixture replies display correctly; saved English messages retain their original language. Contact cards show page-check dates and explicitly unconfirmed availability, language support and eligibility.

An isolated Gunicorn/WhiteNoise smoke check used a temporary SQLite database and generated signing key with `DEBUG=False`. Migrations, registration, a note containing escaped HTML, an attached placeholder turn, no-store headers and collected assets passed. Restarting preserved the session, messages and historical labels. The live UI was checked in both languages at both widths. Missing live configuration returned an explicit error and retained the draft, with no fallback. The temporary server and database were removed; no real account or private content was used. Production screenshots are `.local/screenshots/live-production-{en,de}-{390,1440}.png`.

### Source and live-service readiness

The ten records in `content/evidence.json` contain original paraphrases, organisations, exact URLs/sections, checked dates, available update dates, applicability and limitations. Primary pages were read on 12 September 2026: DGE food guidance, NHLBI DASH, federal German discharge/care advice, ZQP's care-advice directory, and targeted NIH/EFSA nutrient material. NIH/EFSA entries are retrieved only for the covered nutrient questions. Cohort bulk ingestion is deferred. These source reads are neither human editorial approval nor clinical validation.

**At this stage, actual Anymize inference and Brave API integration were untested. No provider credits were consumed.** The configuration then required `ANYMIZE_API_KEY`, an account-accessible `ANYMIZE_MODEL`, `BRAVE_SEARCH_API_KEY`, `FEMAKTIV_AI_MODE=live` and `ANYMIZE_ZDR_CONFIRMED=1` after enabling account-level ZDR. The Brave requirement and contact checks described here were subsequently removed; see [Anymize-only live chat](#anymize-only-live-chat). The updated local launcher allows 90 seconds, accommodating the 60-second application deadline. `.env.example` is documentation and is not automatically loaded.

The separately invoked `manage.py evaluate_live_chat --allow-provider-calls` checks model availability and four fictional English/German cases, including structured output, anonymization metadata, essential intake terms, citations and current contact lookup. It stops on failure without automatic paid retries and saves an ignored report for human review. Its guard and failure behavior were tested with mocks. Metadata and keyword checks do not establish anonymization accuracy, preservation of every nuance, clinical correctness or answer quality. Real model/schema compatibility, latency and contact-extraction success must be evaluated after configuration. Conservative page extraction can miss valid services; source citations alone do not establish that a generated claim is supported.

## Prototype privacy fixes — 12 September 2026

Implemented the user-approved small prototype changes: registration closed by default, explicit operator approval for live access, durable content-free hourly/user and daily/global allowances, and one pending request per account. Chat deletion cannot reset either usage or the running lease. Account settings now provides confirmed deletion of all owned chats, notes and attached copies. Concurrent profile edits preserve operator revocation; concurrent note edits cannot reinsert deleted content.

Normal inference still uses Anymize's combined anonymous-chat endpoint and consumes its returned LLM answer directly. No masked-text forwarding stage or new end-user workflow was introduced. Account-level ZDR and disabled provider fallbacks require operator configuration; their environment flags are confirmations, not remote verification. Optional developer checks inspect supplied actual anonymizer exports for fixed fictional EN/DE identifier/fact cases. The integration check remains usable without those exports and explicitly reports masking as untested. Custom encryption and automated retention remain deferred.

Observed application verification: 317 German translations compiled, Ruff passed (92 files), Django checks passed, no missing migrations, static collection passed, **147 backend tests passed**, and **15 browser tests passed**. Tests include deletion/approval races, concurrent allowance admission, deletion-resistant accounting, UTC/rolling limits, mocked provider errors and masking-export checks. Browser coverage includes English/German, keyboard controls, 390px/1440px, confirmation/cancel, ownership isolation and retained drafts. An earlier launcher test expected open registration; its optional-signup fixture was aligned with the new default. The concurrency test now recognises the existing safe SQLite contention-recovery response while still requiring exactly one paid reservation/call.

An isolated Gunicorn/WhiteNoise HTTP smoke passed with DEBUG=False, a temporary database/signing key, empty provider keys and the offline guard. It exercised migrations, closed signup, approved tester login, CSRF/confirmation failures, complete owner-only content deletion, retained account/session/usage, restart persistence and static assets. Temporary resources were removed. Evidence is ignored `.session/donna/live-chat/privacy-production-report.json`; browser screenshots are `.local/screenshots/privacy-{en,de}-{390,1440}.png`.

Both additive migrations were applied to the local prototype database. The existing preview workers were refreshed without changing their environment or approving accounts; signup returned 403 as intended. Fictional masking inputs were exported locally without external calls. Real Anymize/Brave inference, actual masking exports, account settings, hosting encryption and backup retention remain unverified. No provider credits were consumed.

Depmesh's current graph passed with 155 files and 550 directed edges; its isolated fixture expectation was updated to reflect account files' additional live-chat governance. Final repository validation is recorded in the Donna verification output.

## Anymize-only live chat

On 12 September 2026, removed Brave Search following the user's explicit preference to delete it rather than replace it with generated examples or simulated results. The adapter, search tests, required API key, search budgets, locality form/action and associated translations are removed. Live chat uses Anymize and the existing local evidence library. Care questions still receive cited guidance and call preparation. Existing database fields and historical citation snapshots are retained; saved locality values no longer enter active context or model input, and new replies use the legacy `lookup_status: "not_requested"` value.

Donna's complete offline verification passed: **142 backend tests and 15 browser tests**, 309 German translations, Ruff lint/format (90 files), Django system and missing-migration checks, static collection, Depmesh (six specifications, 153 files, 540 directed edges and 16 isolated fixture pairs), workflow validation and `git diff --check`. Focused provider/service/transport checks (17 tests), context/turn checks (21 tests), evaluation-command checks (eight tests) and live browser journeys (eight tests) also passed. The evaluation command now permits at most eight Anymize model calls and has no search requirement. Ordinary checks used mocks and the offline guard; no provider credits were consumed.

An isolated Gunicorn/WhiteNoise smoke passed with `DEBUG=False`, a temporary database/signing key, an approved fictional tester, empty provider credentials and the offline guard. English/German views at 390px and 1440px had no horizontal overflow or JavaScript errors. The locality control and Brave disclosure were absent; context serialization excluded legacy locality. CSRF-protected resets preserved active note copies in both locales, private responses used no-store, collected CSS loaded, and missing configuration returned an explicit error while retaining the draft. All four `.local/screenshots/brave-removal-production-{en,de}-{390,1440}.png` views were visually reviewed. The temporary server/database were cleaned up; the user's ngrok tunnel and running preview were not restarted.

The [ngrok setup instructions](../README.md#configure-live-chat-locally) now use only Anymize settings, explicit `.env.local` loading and `FEMAKTIV_PUBLIC_URL` when restarting `./bin/serve`. The user selected `openai/gpt-5.6-sol` and reported enabling account ZDR and disabling fallbacks. Those account settings are user confirmations, not remote verification. No secret was read or copied into tracked files.

Current primary documentation distinguishes Anymize's consumer-chat [web search feature](https://anymize.ai/en/product/features/chat) from its [API function-calling interface](https://app.anymize.ai/api-docs/chat), whose search example requires the integrating application to execute a tool. No documented hosted-search contract for the selected model through the anonymous endpoint was found. This change does not claim Anymize web search is connected or fabricate current contact results. Optional masking inspection remains unperformed and separate from integration checks.

### Operator evaluation and failure diagnostics

The operator separately ran the opt-in live evaluation at 19:18:59 UTC on 12 September 2026. Its saved report confirms `model_available: true` for `openai/gpt-5.6-sol`; the first `nutrition-en` case failed with `provider_unavailable` and integration did not pass. The old report did not retain the underlying HTTP status or failure stage, so it cannot establish whether the provider rejected request parameters or encountered another failure. `masking.status: "not_evaluated"` was not the reason integration failed. This command calls Anymize directly and does not traverse ngrok. No further live calls were made by the implementation checks.

The transport and evaluation command now retain only validated numeric HTTP status, a fixed application-defined failure reason and the failed stage. Terminal output provides a concise diagnostic and relevant next check; provider bodies, headers, exception text and credentials are excluded. Ordinary website errors remain generic and translated. Actual successful anonymous generation and schema compatibility remain unverified pending a deliberate operator evaluation with these diagnostics.

A subsequent operator run reported `nutrition-en`, `intake`, `provider_http_status: 400` and `failure_reason: "http_error"`, confirming that Anymize rejected the generation request. Review against the [official Structured Outputs subset](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) identified string-length and uniqueness keywords in the outgoing schema beyond its documented supported-property list. The adapter now omits those keywords from the transmitted schema while preserving all original checks locally, including duplicate citation/topic rejection and text limits. This addresses a request-compatibility issue; the precise original provider rejection and successful live generation are not established by the HTTP status alone. Anymize's documented `max_tokens` parameter is retained instead of assuming support for a different gateway parameter.

Final verification after the diagnostics and schema changes passed: **151 backend tests and 15 browser journeys**, Ruff lint/format, Django checks, translation/static generation, Depmesh and Donna validation. Provider regressions inspect both transmitted schemas and confirm that outputs violating the retained length/uniqueness rules are rejected locally. Evaluation regressions cover HTTP status, intake/composition failures and invalid intake that must stop before a second model call. The original operator reports were not rewritten by automated checks; no additional live provider call was made by the agents. The next operator evaluation remains the live-readiness check.

The operator's 19:33:18 UTC evaluation subsequently passed the English nutrition case, including anonymization metadata, structured output, essential facts and citations. The German nutrition intake then failed local validation with `invalid_reply`; provider logs showed HTTP200 responses. Successful English generation is therefore observed, while the complete bilingual evaluation remains incomplete. A small follow-up reports fixed reasons for truncation, unexpected completion/tools, malformed message/JSON, invalid prose, inconsistent intake and schema validation. Schema failures include only the fixed rule name, without response text or paths. Focused mocked checks passed; no validation rule or model setting was relaxed, and no further paid request was made by the agents.

Final verification of the small validation-diagnostic follow-up passed: 152 backend tests, 15 browser tests, application checks, Depmesh, Donna validation and whitespace checks. Live evaluation remains a separate operator action.
