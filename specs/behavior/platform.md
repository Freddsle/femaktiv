# femaktiv bilingual platform

## Goal of the document

Define the approved first implementation of femaktiv: an English/German public website and private AI-chat workspace with a replaceable placeholder backend.

## Scope

This contract governs the Django application, accounts, personal notes, chat history, example conversations and public Q&A previews. The user approved implementation through Donna. Delivery is local with hosting preparation; live AI, real community posting, file uploads and external publication are deferred.

## Authority and migration

The user's revised plan supersedes the scope, architecture, screens, English-only setting, no-account/no-database restrictions and completion gates of [the initial nutrition prototype](../../00_initial/FEMAKTIV_BUILD_SPEC.md) for this implementation. That document remains a historical/future nutrition reference. Do not claim clinical content review, live inference or forum participation from placeholder examples. Existing repository-process requirements remain applicable.

## Product and language

Product-facing branding MUST be lowercase `femaktiv`. Use the supplied logo palette: purple, mauve, coral and blush, with dark plum text. The responsive interface MUST work at 390px and 1440px with keyboard-operable controls, visible focus and labelled errors.

English and German MUST be fully supported. Use `/en/` and `/de/` URL prefixes and an English default independent of browser language. An explicit language choice MAY persist in a language cookie. Translate UI, validation messages, placeholder replies, account emails and example content. User-authored text and already saved messages MUST NOT be automatically translated. German uses friendly `du`. Language switching retains the current saved object/page.

## Accounts and private data

Use Django email/password registration and a public display name, with a custom user model in the initial migration. Include login, POST logout, password change and token-based password recovery; local email is console-backed and hosting email is configurable. Chats and notes persist after logout and restart.

Notes MUST have an owner, UUID identifier, title and text body. Owners can create, edit and delete notes. Chats MUST have an owner and UUID identifier, support creation, reopening, renaming and deletion, and store ordered user/assistant messages. Every private lookup or mutation MUST enforce ownership; an inaccessible object returns 404. Staff moderation privileges MUST NOT confer private data access.

On each message the owner explicitly selects up to five notes. Save immutable title/body snapshots with the user message. Editing or deleting a source note does not alter prior snapshots; explain this at deletion. Deleting a chat removes its messages/snapshots. Inputs are plain text, validated and escaped; request bodies and private content MUST NOT appear in operational logs or public previews. All mutations use CSRF protection and private responses use no-store cache controls.

## Chat interface contract

`POST /<language>/api/chats/<chat_id>/messages/` accepts exactly `content` (1–4000 non-whitespace characters), `note_ids` (up to five distinct UUIDs), and `client_request_id` (UUID). The authenticated owner and reply language come from the server session/URL. Reject inaccessible notes before saving any part of a turn.

The response includes `mode: "placeholder"`, `user_message`, `assistant_message`, and `chat` metadata. Serialized messages have `id`, `role`, `content`, `created_at`, `mode`, and `context` (title/body snapshots). Errors use `error: {code, message}` with 400 validation, 401 unauthenticated, 403 CSRF and 404 inaccessible/not-found responses. A repeated client request identifier in the same chat MUST return the existing turn without duplication. Save the turn atomically.

The deterministic response service MUST make no external requests and clearly say AI replies are not connected. Persist the placeholder mode so historic replies stay honestly labelled. The UI MUST retain a failed draft, disable duplicate sends, and prevent a late response from rendering in a different chat or after logout/navigation.

## Example content

Provide two read-only conversation previews for wellbeing/nutrition and family care. Demonstrate summaries and practical planning steps without pretending to use private data or inventing medical sources. Public Q&A is six static bilingual example discussions in wellbeing/nutrition, family care and everyday organisation. Support category filtering and detail pages; show example/preview labels. No posting, voting, reporting or moderation backend is required. Load fixtures separately from templates so later database-backed discussions can reuse the view structure.

## Implementation boundaries

Use a single Django 5.2 LTS application, Python 3.14, `uv`, SQLite locally, reusable Django templates, CSS tokens and small JavaScript modules. Domain modules are `accounts`, `notes`, `chats` and `pages`; project configuration is `config`. GNU gettext or compatible PO/MO tooling compiles translation catalogues. Use Django's built-in auth/session/password features. Prepare environment-based production settings and static serving; no external deployment occurs in this phase.

## Acceptance

Automated verification MUST cover accounts/recovery, durable chat/note state, cross-account isolation, snapshot semantics, atomic/idempotent submissions, localization and honest examples. Browser checks MUST exercise the primary workflow and both widths. Run Django checks, missing-migration checks, tests, translation compilation, static collection, local production smoke checks, Donna validation and Depmesh verification. Record actual results and startup commands in the handoff. No check may consume provider credits.
