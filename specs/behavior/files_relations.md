# Project file relations

## Goal of the document

This document defines how femaktiv connects files to their governing specifications and tests, and how Depmesh exposes those connections for change planning and verification.

## Scope

The contract covers repository file identity, ownership rules, dependency queries, helper tools, and maintenance checks. Package dependencies, language import graphs, Donna session state, and relationships among runtime option/claim/source identifiers are outside this file graph.

## Dictionary

- **Artifact:** a repository file identified by its project-root path.
- **Relation:** a named, directed connection from a queried artifact to another artifact.
- **Governing specification:** the document that owns requirements applying to a file.
- **Prospective artifact:** a file path queried before that file exists.

## Identity and project boundaries

`depmesh.toml` MUST remain at the repository root. Artifact ids MUST use the root-anchored form `@/relative/path` with `/` separators. Commands SHOULD use these ids so queries have the same meaning from any subdirectory. An explicit `--config` path MAY select the repository when a command runs outside it.

File relations MUST stay within the selected repository. Symlinks that point outside it MUST NOT be used as relation targets. Directory symlinks MUST NOT serve as discovery roots or alternate artifact namespaces; discovery traverses real directories without following directory symlinks. URLs and Markdown heading fragments are not file artifact ids. A Donna operation id such as `@/workflows/example.donna.md:review` identifies an operation, not a separate file; file queries use only the workflow file path.

Tracked and untracked nonignored project files MAY participate. Git's staging state MUST NOT change a relation's meaning. Files that are merely mentioned in prose MUST NOT automatically acquire a governance or testing relationship.

## Relation vocabulary

| Relation | Returned files for the queried artifact | Reverse relation |
| --- | --- | --- |
| `governed_by` | Specifications whose requirements apply to that file. | `governs` |
| `governs` | Existing files subject to the queried specification. | `governed_by` |
| `tested_by` | Existing unit tests and explicitly assigned browser tests for the queried source file. | `tests` |
| `tests` | Existing source files assigned to the queried test. | `tested_by` |

These names and directions MUST remain stable. Descriptions in `depmesh.toml` MUST explain the returned set. Relations MUST return direct edges, deduplicated as a set; consumers MUST NOT assume output order is significant. They MUST NOT imply recursive impact analysis, actual test execution, or complete import/call coverage.

For two existing, eligible files, `A governed_by B` MUST have the inverse `B governs A`, and `A tested_by B` MUST have the inverse `B tests A`. Self-edges MUST NOT be returned. Multiple governing specifications are allowed when their responsibilities differ.

## Specification ownership

The following table defines the current ownership map. Directory families refer to files recursively beneath the named directories, subject to the exclusions below.

| Owning specification | Governed artifacts |
| --- | --- |
| [Specification authoring requirements](../meta/general.md) | Every Markdown file under `specs/` except the authoring specification itself; root `AGENTS.md` for its specification-handling instructions. |
| [File relations](files_relations.md) | `depmesh.toml`, files under `bin/depemesh/`, and root `AGENTS.md` for its relation-query instructions. |
| [Workflow requirements](../general/workflows.md) | `donna.toml`, permanent `workflows/**/*.donna.md` files, and root `AGENTS.md` for workflow/session instructions. |
| [Bilingual platform](platform.md) | `README.md`, `manage.py`, `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`; files under `accounts/`, `notes/`, `chats/`, `pages/`, `config/`, `templates/`, `static/`, `locale/`, `content/`, `docs/`, `tests/` and `bin/`, with the tooling and historical-test exceptions below. |
| [Live chat](live_chat.md) | Additional ownership of `chats/`, `tests/unit/chats/`, `templates/chats/`, `content/evidence.json`, live-chat browser tests, chat JavaScript, shared site CSS for live controls, AI settings and the local launcher. |
| [Initial nutrition build reference](../../00_initial/FEMAKTIV_BUILD_SPEC.md) | Historical TypeScript families `app/`, `src/`, `components/`, `lib/`, `public/`; their mirrored unit tests and `tests/e2e/**/*.spec.ts`/`.tsx`/`.js`/`.jsx`; `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `tsconfig.json`, `next-env.d.ts`; root `next.config.*`, `postcss.config.*`, `tailwind.config.*`, `eslint.config.*`, `vitest.config.*`, `playwright.config.*`. |

Directory and configuration conventions do not claim that every prospective file exists. Files under `bin/depemesh/` and `tests/unit/bin/depemesh/` remain governed by this file-relation specification instead of the platform contract. Historical test families in the final row retain historical ownership rather than platform ownership.

The index inventories specifications; it does not automatically govern all implementation files. The current platform contract owns the approved Django implementation; the build specification and overview in `00_initial/` retain historical/future-reference and background roles. Formatting requirements for `specs/` documents MUST NOT be retroactively applied to preserved sources.

Root `.gitignore` and historical background documents have no declared governing edge at present. An empty result for such files is intentional. An empty result for a newly introduced artifact family requires review of this table and the rules; it is not evidence that the file is unconstrained.

## Source and test paths

For preserved application TypeScript conventions, unit tests MUST mirror the complete source path beneath `tests/unit/`, inserting `.test` before the original extension. Both `.ts` and `.tsx` are supported, and the original extension MUST be preserved to keep the mapping unambiguous.

| Source example | Unit-test example |
| --- | --- |
| `lib/contracts.ts` | `tests/unit/lib/contracts.test.ts` |
| `components/question-form.tsx` | `tests/unit/components/question-form.test.tsx` |
| `src/app/api/intake/route.ts` | `tests/unit/src/app/api/intake/route.test.ts` |
| `app/(demo)/page.tsx` | `tests/unit/app/(demo)/page.test.tsx` |

This automatic convention applies to source under `app/`, `src/`, `components/`, and `lib/`. Colocated `*.test.*` and `*.spec.*` files MUST NOT be mistaken for application source. A source file does not require a new unit test merely because a predictable path exists: test selection follows the product acceptance requirements and the significance of the change.

Python unit tests MUST mirror the source directory beneath `tests/unit/`, prefixing the source basename with `test_`. This applies recursively under `accounts/`, `notes/`, `chats/`, `pages/`, `config/` and `bin/`, including Depmesh helper tests. For example, `chats/services.py` maps to `tests/unit/chats/test_services.py`, and `bin/depemesh/check.py` maps to `tests/unit/bin/depemesh/test_check.py`. Root `manage.py` maps explicitly to `tests/unit/test_manage.py`. Existing `test_*.py` files MUST NOT be treated as source requiring `test_test_*.py` tests.

Browser/integration tests SHOULD live under `tests/e2e/` or `tests/integration/`. Their many-to-many coverage MUST use explicit paired rules; filename similarity alone is not enough to infer coverage. The platform browser suite `tests/e2e/test_platform.py` explicitly tests `accounts/views.py`, `notes/views.py`, `chats/views.py`, `pages/views.py`, `static/js/chat.js` and `templates/base.html`. The live-chat browser suite additionally covers `chats/turns.py`, `chats/context.py`, `chats/service.py`, chat templates and the shared CSS. These lists identify directly exercised boundaries rather than every transitive dependency. Current configuration MUST NOT invent an edge for a missing source or test file.

## Exclusions and missing files

All relation inputs and outputs MUST exclude any path containing these directory segments: `.git`, `.session`, `.agents`, `.codex`, `node_modules`, `.next`, `dist`, `build`, `coverage`, `playwright-report`, `test-results`, `.venv`, `__pycache__`, `.cache`, `.local`, `.ruff_cache`, `.pytest_cache`, or `staticfiles`. These exclusions apply at any depth, including nested generated directories under a source root.

Files named `.env` or beginning `.env.`, and files ending `.pyc`, `.pem`, `.key`, `.mo`, `.sqlite`, `.sqlite3` or `.db`, including database `-wal`, `-shm` and `-journal` companions, MUST be excluded. An example environment file also has no file-relation edge under this convention. Other hidden files and directories MAY participate and MUST follow the same forward/reverse rules as visible paths. Secrets and runtime state MUST NOT be introduced as artifact dependencies. Additional repository ignore patterns do not automatically alter Depmesh's rules; a new generated/private location requires an explicit exclusion update.

Every emitted dependency MUST exist and be a regular in-repository file. Querying a prospective source path MAY return existing governing specifications and existing convention-matched tests, but MUST NOT create files. Reverse lookups MUST list only files that actually exist. Therefore inverse symmetry is required only when both endpoints exist. Missing dependencies MUST NOT be fabricated with a static output list.

An empty result is valid for an unmapped artifact or a source with no matching unit test. Invalid configuration, unknown relations, command failures, and validation failures MUST remain distinguishable from a successful empty query through diagnostics and a nonzero exit where appropriate.

## Configuration and helper contract

`depmesh.toml` MUST declare relation descriptions and both directions of every supported mapping. Rules SHOULD use exact ownership predicates or narrow path families, with filesystem output sources that include only existing files. Broad repository-wide discovery and automatic relations from every text mention SHOULD be avoided.

Template captures SHOULD preserve the source path and extension. When a captured path contains glob metacharacters such as `[slug]`, output lookup MUST treat those characters literally, so dynamic-route directories are not mistaken for glob patterns. Configuration MUST implement this through a filtered file source with an exact artifact predicate, or an equivalently safe resolver.

Depmesh helper scripts, when needed, MUST live in `bin/depemesh/`, preserving the requested directory spelling. The CLI and root configuration retain the names `depmesh` and `depmesh.toml`. Helpers MUST work independently of the caller's current directory, avoid network/provider calls, avoid modifying project artifacts, and report failures with a nonzero status. Temporary verification fixtures MAY be created outside the repository and MUST be cleaned up.

`python3 bin/depemesh/files.py [--root-files] [paths ...]` enumerates eligible files under literal repository-relative roots, including otherwise eligible hidden paths. `--root-files` includes immediate files at the project root without recursively scanning unrelated directories. Missing roots return no files; out-of-project roots or unreadable discovery roots fail explicitly. Excluded generated directories MUST be pruned during traversal. Its stdout MUST contain one sorted, unique artifact id per line; diagnostics go to stderr.

`depmesh.toml` uses this discovery helper only with constant arguments. Exact predicates match captured test paths after enumeration so shell or glob interpretation cannot alter dynamic-route names. The configuration owns relation meanings; the helper only discovers existing files. No import analyzer is required. Future command-based resolvers MUST validate or safely quote all substituted arguments.

`python3 bin/depemesh/check.py` validates specification structure/index links and representative forward/reverse relations. It MUST verify current files and isolated fixture cases covering prospective paths, nested TypeScript/Python source files, `.tsx`, literal dynamic-route names, eligible hidden files, platform ownership, explicit browser pairs, excluded runtime/cache/database files, and missing/deleted targets. Its optional `--relations-only` mode MAY be used during setup before every specification has been created; final validation MUST run without that option.

## Change procedure and acceptance

1. Before editing, list relations and query the affected files. Read every returned governing specification and inspect tests as relevant. A specification change also requires its `governs` query.
2. When adding a file family, define its owning specification and any test convention. Add paired rules and a verification case in the same change.
3. When moving/deleting files, update the index, links, fixed rule paths, and affected workflow references. Rerun both directions and confirm the old path is no longer emitted.
4. Run `python3 bin/depemesh/check.py`, inspect representative `depmesh -p llm dependencies` results, and run Donna validation if workflows or their contracts changed.
5. Record actual results. Relation discovery is change-planning support; it MUST NOT be reported as application test coverage, scientific source validation, or a passed live-provider check.

Acceptance requires a loadable configuration, the four documented relations, accurate current ownership, inverse consistency for existing endpoints, literal dynamic-route matching, absent-target omission, exclusion of generated/private files, and successful execution of the helper from both the repository root and another working directory.
