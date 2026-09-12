# femaktiv

A bilingual space for everyday questions, personal context and optional live AI assistance. The public website and private workspace run together in one Django application.

## Start locally

Python 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/) are required. From this repository:

```bash
./bin/setup
./bin/serve
```

Open **http://127.0.0.1:8000/** for English or **http://127.0.0.1:8000/de/** for German. Registration is closed by default; create tester accounts through Django admin as described below. There are no shared default credentials. Stop the foreground server with Ctrl+C. To use another local port, run `FEMAKTIV_PORT=8001 ./bin/serve`.

`bin/setup` installs the locked dependencies, compiles translations, applies migrations and collects static assets. `bin/serve` runs Gunicorn with WhiteNoise, `DEBUG=False`, and a stable signing key stored privately in `.local/secret_key`. It binds only to `127.0.0.1` and explicitly permits local HTTP. `./bin/dev` runs Django's development server with reload support.

## Share a preview through ngrok

Install [ngrok and configure your account's authtoken](https://ngrok.com/download/linux) once. After `./bin/setup`, open a terminal and start the tunnel:

```bash
ngrok http http://127.0.0.1:8000 --inspect=false
```

Copy the HTTPS URL from ngrok's `Forwarding` line. Stop any existing femaktiv server on port 8000, then run this in a second terminal from the repository, replacing the example URL with yours:

```bash
FEMAKTIV_PUBLIC_URL=https://your-domain.ngrok-free.app ./bin/serve
```

Open that public URL for English or append `/de/` for German. The launcher configures Django's exact allowed host and CSRF origin, keeps `DEBUG=False`, enables secure cookies and HTTPS redirects, and uses the existing private signing key and database. Gunicorn recognizes HTTPS forwarded by the loopback ngrok agent. HTTP traffic inspection is disabled by the [ngrok CLI flag](https://ngrok.com/docs/gateway/agent/cli#ngrok-http).

Keep both processes running while showing the site. If the ngrok URL changes, restart `bin/serve` with the new URL. The public URL must be an HTTPS origin without a path, credentials or wildcard. To return to local HTTP, stop the server and run `./bin/serve` without `FEMAKTIV_PUBLIC_URL`. The helper never starts ngrok itself. Password recovery still prints emails in the server terminal with the default console backend.

If the public URL returns **Bad Request (400)** while `http://127.0.0.1:8000/` works, check whether femaktiv is still running in local HTTP mode. Starting ngrok does not reconfigure an already running Django server. Stop that server, then restart it with `FEMAKTIV_PUBLIC_URL` set in the same command as `./bin/serve`, as shown above. The launcher's startup line should display your HTTPS public URL. An “address already in use” error means the previous server still needs to be stopped.

## What works

- Real email/password accounts, login/logout, account settings and password change/recovery; optional public registration.
- Private notes and preferences, with create/edit/delete controls.
- Persistent chats, history, renaming, deletion and explicit note attachments.
- Immutable copies of attached notes: changing a note does not rewrite a previous conversation.
- English and German navigation, forms, errors, account emails and example content. English is the first-visit default; an explicit language choice is remembered.
- Two read-only conversation examples and six public Q&A previews in three topics.

Chat defaults to visibly labelled **placeholder replies**, with no provider calls. Optional live mode adds Anymize intake and answers with a small local evidence library. Brave Search and local-contact lookup have been removed; there is no replacement search provider or simulated search. This is a private prototype for fictional information. Example answers are illustrative authored content, not personalised recommendations or reviewed medical guidance. Q&A posting and moderation are not implemented.

## Accounts and data

Accounts, chats, notes and sessions are stored in `.local/db.sqlite3`; they survive refreshes and server restarts. Logout does not delete stored data. Users can delete their notes and chats. Deleting a source note leaves saved copies in chats; remove an active copy using its chat’s context controls to stop sending it. Deleting a chat removes its messages, copies, citations and turn records. Independent content-free usage records remain, so deletion cannot reset an allowance or free a running request. Both `.local/` and secrets are ignored by Git.

Account settings offers **Delete my chats and notes** with a confirmation screen. It removes all of that owner's chats, notes, active copies, historical snapshots and pending turns atomically, preserving the account and usage counts. Late AI replies cannot recreate deleted chats. Deletion is from the application database; hosting backup retention and already-transmitted provider requests are separate. There is no custom field encryption or automatic content-expiry job. Saved text is accessible to authorised server/database operators. Use encrypted hosting storage/backups where available and document their retention before real-data use.

Password recovery prints an email and reset URL in the local server terminal. This console backend is for local development only; configure SMTP for a hosted site. Create an administrator when needed with:

```bash
.venv/bin/python manage.py createsuperuser
```

The admin URL is `/en/admin/` or `/de/admin/`. Private notes, chat messages and attachments are deliberately not registered in the admin interface.

Create each tester under **Users → Add**, then edit the account and explicitly enable **Live chat approved**. This flag defaults off for all new and existing accounts, including staff; public signup/profile forms cannot grant it. Keep `FEMAKTIV_SIGNUP_ENABLED=0` for an invited pilot. Setting it to `1` intentionally opens registration but still does not grant live access. Approvals can be revoked in admin; further external stages stop when revocation is observed, although a request already transmitted cannot be recalled.

## Verification

```bash
./bin/check
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

`bin/check` validates/compiles German translations, runs Ruff, Django checks and missing-migration checks, collects static assets, runs backend tests and executes the Playwright browser suite. Browser tests use an installed Google Chrome/Chromium automatically. Alternatively install Playwright's Chromium with `.venv/bin/python -m playwright install chromium`, or set `FEMAKTIV_BROWSER_EXECUTABLE` to a browser binary. Browser tests require permission to create local sockets and launch a browser. They use an isolated browser profile and temporary test database, never a live AI provider.

Screenshots from the browser suite are saved under `.local/screenshots/`. See [validation results](docs/VALIDATION.md) for actual commands and outcomes from this implementation.

## Project structure and extension points

- `accounts/`: custom email user, forms and standard Django authentication views.
- `notes/`: owner-restricted saved context.
- `chats/`: durable conversations, active context, request reservations, Anymize and cited evidence.
- `content/evidence.json`: versioned paraphrases, source dates, applicability and limitations.
- `pages/` and `content/examples.json`: public pages and bilingual static examples.
- `templates/`, `static/` and `locale/`: shared presentation, small JavaScript modules and translations.
- `config/`: settings, route prefixes, deployment entrypoint and cache controls.

The active requirements are in [the platform specification](specs/behavior/platform.md) and [live-chat extension](specs/behavior/live_chat.md). The original nutrition build specification is preserved as historical/future reference; its Next.js, English-only, no-account and no-database requirements do not govern this version. Development follows the project's Donna workflow and Depmesh ownership mappings.

### Configure live chat locally

Keep secrets in your server environment or secret manager. `.env.example` documents the settings; it is **not loaded automatically**. Live mode requires all of:

- `FEMAKTIV_AI_MODE=live`
- `ANYMIZE_API_KEY` and `ANYMIZE_MODEL`, using a model identifier accessible to your account.
- `ANYMIZE_ZDR_CONFIRMED=1`, **after enabling account-level Zero Data Retention in Anymize**. This records your confirmation; the app cannot remotely attest to the account setting.
- `ANYMIZE_FALLBACKS_DISABLED_CONFIRMED=1`, **after disabling provider-side fallback models in Anymize**. This is also your confirmation, not remote attestation.

Install dependencies/apply migrations with `./bin/setup`, then restart `./bin/serve` with these variables in its environment. Missing settings, rejected anonymization metadata and malformed replies produce errors; they never switch providers or return a placeholder as a live answer. Leave `FEMAKTIV_AI_MODE=placeholder` to use the default offline mode.

For an ngrok preview, create a minimal `.env.local` in the project folder with the following settings and your actual key. This file is ignored by Git. Do not copy the hosting settings from `.env.example` into it.

```dotenv
FEMAKTIV_AI_MODE=live
ANYMIZE_API_KEY='YOUR_ANYMIZE_KEY'
ANYMIZE_MODEL='openai/gpt-5.6-sol'
ANYMIZE_ZDR_CONFIRMED=1
ANYMIZE_FALLBACKS_DISABLED_CONFIRMED=1
FEMAKTIV_SIGNUP_ENABLED=0
```

The model identifier above is the operator's selected model; actual account access and structured-output compatibility still require the explicit evaluation below. Set the confirmation flags only after applying the corresponding account settings.

Keep ngrok running in its terminal using `ngrok http http://127.0.0.1:8000 --inspect=false`. Stop the existing femaktiv server. In the terminal used to run femaktiv, load the file and restart with your current ngrok HTTPS URL:

```bash
chmod 600 .env.local
set -a
source .env.local
set +a
FEMAKTIV_PUBLIC_URL=https://YOUR-NGROK-HOST ./bin/serve
```

Run these commands from the project folder. Restart the server whenever the environment or ngrok URL changes. Visit `https://YOUR-NGROK-HOST/en/admin/` to enable **Live chat approved** on the intended tester account, then use the chat at your public URL. If needed, create an administrator with `.venv/bin/python manage.py createsuperuser` before starting the server. No Brave account or key is needed.

Anymize receives the submitted message, current chat context and attached copies, then masks identifiers before the downstream model. The app uses Anymize's combined endpoint and consumes its returned LLM answer directly; it does not forward masked text to another model provider itself. Each of the two conversational model steps uses this same endpoint. The separate masking inspection below is a quality check, not another step in normal chats.

Masking should cover names, street addresses, exact birth dates, emails/phones, financial and identity numbers, and legal case/contract identifiers. Preserve roles, conditions, allergies versus preferences, practical/care needs and meaningful deadlines. Replies use roles and do not request restoration or guess masked identifiers. These are the intended policy and evaluation targets; provider metadata does not establish that every span was masked. Health and legal details remain sensitive. Anymize is the only runtime external service. No credentials or private payloads are written to application logs.

Notes stay active within their chat until removed. Source edits/deletion do not change a copy; refresh explicitly to replace it. Removing or refreshing a copy or resetting message context starts a new AI segment. Earlier messages stay visible but are no longer sent, including answers derived from removed notes. Resetting message context keeps active note copies; remove those individually if needed. Nothing carries into another chat automatically. An existing placeholder conversation starts a fresh context on its first live turn. The removed locality field is no longer sent to the model; legacy saved fields and citations remain for historical compatibility.

The message endpoint remains `POST /<language>/api/chats/<chat UUID>/messages/` with exactly `content`, `note_ids` and `client_request_id`. Session authentication and CSRF are required. Complete replies return both stored messages, actual mode, answer/clarification kind, paragraph citations, source snapshots and active context. The legacy `lookup_status` response field is `not_requested` for new replies. A duplicate reuses the saved reservation/result; a different payload with the same id conflicts. `GET .../turns/<request UUID>/` returns processing (202), a result or a terminal error. `POST .../context/` accepts `remove`/`refresh` with `note_id` or `reset` alone; the retired `locality` action is rejected.

Each turn permits at most two model calls within 60 seconds. It makes no search or public-page requests. Gunicorn's local timeout is 90 seconds; hosting proxies should allow at least that long. There is no streaming or automatic paid retry. Default allowances are 30 new reservations per user over the preceding hour and 100 across the whole app per UTC day. Configure positive integers with `FEMAKTIV_LIVE_USER_HOURLY_LIMIT` and `FEMAKTIV_LIVE_DAILY_LIMIT`. These limit requests, not euros. Admission is atomic across chats/accounts and permits one running request per account. Failed accepted requests count; duplicates reuse their allowance. Deleting chats/data retains the counts and any running lease until its worker finishes or its deadline expires. Existing turn usage is preserved by migration.

Context is limited to 60,000 characters; exceeding this asks for a reset or smaller note selection rather than dropping earlier restrictions. A timed-out reservation cannot resume or charge again on a duplicate; a deliberate new send uses a new request id. The browser stops waiting after 75 seconds while retaining the original id for recovery. If a context update cannot be confirmed, refresh before sending again.

### Evaluate the configured provider explicitly

After configuring live mode, run this separately when you intend to make paid calls:

```bash
.venv/bin/python manage.py evaluate_live_chat --allow-provider-calls
```

Run the command in a terminal with the same Anymize settings loaded; it does not use the ngrok tunnel and can run before starting the server. It uses four predefined fictional English/German cases and checks account model access, structured output, anonymization metadata, essential intake facts and citations. Maximum cost exposure is eight model calls; it stops on a failed case without retrying. The report is saved to ignored `.local/live-chat-evaluation.json` and includes fictional answers for human review. Metadata and keyword checks **do not prove anonymization accuracy, clinical correctness or answer quality**.

On failure, the terminal summary and report identify the case and stage (`model_access`, `intake`, `composition` or `scenario_checks`). When available, `provider_http_status` and a fixed `failure_reason` distinguish an HTTP rejection from connection, timeout, encoding or JSON failures. Raw provider error bodies, headers and credentials are excluded. `model_available: true` confirms that the key could list the selected model, but does not prove anonymous generation works. `masking.status: "not_evaluated"` is an optional inspection status and does not itself fail integration. Diagnose the reported failure before deliberately running another paid evaluation; there are no automatic retries.

`./bin/check` forces `FEMAKTIV_OFFLINE_CHECKS=1` and uses mocked live integrations even if real credentials are inherited. The opt-in evaluation refuses to run with this switch enabled. No live provider evaluation was performed as part of routine implementation checks.

Optional developer masking inspection is separate from normal chat and setup. Export fixed fictional inputs without any external calls:

```bash
.venv/bin/python manage.py evaluate_live_chat --export-masking-cases .local/masking-inputs.json
```

If you have actual anonymizer exports for those inputs, check them locally:

```bash
.venv/bin/python manage.py evaluate_live_chat --masking-only --masking-output .local/masking-export.json --output .local/masking-review.json
```

The artifact is JSON with `schema_version: 1`, `provenance: "operator-supplied-anymize-anonymizer-export"` and a `cases` array. Include one entry each for `privacy-en` and `privacy-de`, shaped as `{"case": "privacy-en", "anonymizer_export": {"status": "completed", "original_text": "EXACT fictional input from masking-inputs.json", "anonymized_text_raw": "ACTUAL anonymizer output"}}`. Actual job responses may include other fields; mappings and extra fields are never copied into the review report. Obtain the output through a provider-supported inspection/export method, not a generated chat echo. The [public API documentation](https://app.anymize.ai/api-docs/anonymization) and [status reference](https://developers.anymize.ai/) do not document inspection of the combined chat's masked input under ZDR. Keep production ZDR enabled; if no compatible export is available, leave this optional check unperformed.

Adding `--masking-output` to the live evaluation includes these checks in its result. Without it, integration checks can pass and the report explicitly says `masking.status: "not_evaluated"`. Export provenance is operator-supplied, not independently attested; a passing sample does not prove complete masking or clinical/legal correctness. The exported-text checks never add a step to the application's Anymize chat requests.

### Maintain evidence

The initial library covers ordinary DGE food choices, NHLBI DASH context, federal discharge/care advice and ZQP's directory. NIH/EFSA entries are selected from the local library only for the covered specific nutrient questions. Population limits and German versus US applicability travel with each passage. Unknown publication dates remain null; checked dates record an actual source read, not human clinical approval. Review changes against the linked page and increment the library version. Saved replies retain their original citation snapshots.

Care guidance can cite the existing directory and care-information records and help prepare a call. The application does not search for or verify current local contacts. It does not invent contact cards or ask for a location to run a search. Anymize's own chat product advertises [web search](https://anymize.ai/en/product/features/chat), but its [API function-calling documentation](https://app.anymize.ai/api-docs/chat) describes tools executed by the integrating application; it does not establish hosted web-search support for the anonymous endpoint and selected model. Native search is not enabled in this integration.

### Extend Q&A later

`pages/content.py` loads the current examples separately from page rendering. Later, Django topic/question/answer models can supply the same templates. Add authenticated posting, ownership checks and moderation together before accepting public contributions. No forum framework or separate service is needed for the initial read-only preview.

### Maintain translations

English source strings use Django gettext/template translation tags. German UI translations live in `locale/de/LC_MESSAGES/django.po`; long example content has English/German entries in `content/examples.json`. The product name remains `femaktiv` in both languages. User-authored notes and saved messages are never automatically translated.

Compilation has no system gettext dependency:

```bash
./bin/translations
```

To extract new messages, install GNU gettext (`xgettext`, `msgmerge`, `msgfmt`) and run:

```bash
.venv/bin/python manage.py makemessages -l de --ignore=.venv --ignore=.local --ignore=staticfiles --ignore=tests --ignore=.session --no-wrap
./bin/translations
```

The compiler rejects fuzzy/untranslated entries and changed interpolation placeholders. Review new German strings for the consistent friendly `du` tone.

## Prepare for hosting

This delivery is local; no public site has been published. `.env.example` lists production environment variables. It is a reference, not automatically loaded: configure these values in the host's environment/secret manager.

For hosting, set a unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, explicit allowed hosts and CSRF origins, PostgreSQL credentials and SMTP. Use HTTPS and leave `DJANGO_LOCAL_HTTP` unset. Set `DJANGO_TRUST_PROXY=1` only behind a trusted proxy that sanitizes `X-Forwarded-Proto`. Run migrations, translation compilation and `collectstatic` during deployment, then serve `config.wsgi:application` using Gunicorn. The `bin/serve` helper is intentionally for local use only.

Run `.venv/bin/python manage.py check --deploy` under the actual hosting configuration. Hosting decisions still include persistent database storage/backups, recovery email delivery, rate limits for account endpoints and operational monitoring. Application logs should contain operational status, not note text, message bodies or passwords. Broader health use requires further evaluation; a public user-generated forum remains separate future work.
