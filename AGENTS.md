# Working in femaktiv

## Read the applicable contracts

Start with [the specification index](specs/intro.md) and [specification authoring requirements](specs/meta/general.md). Read the relevant specifications before changing files. For product work, read [the bilingual platform specification](specs/behavior/platform.md), which owns the current Django implementation. [The initial nutrition build specification](00_initial/FEMAKTIV_BUILD_SPEC.md) is preserved as a historical and future nutrition reference; its superseded architecture and acceptance gates do not govern the platform. The unstructured overview remains background.

Explicit user instructions govern authorized requirement changes. Resolve conflicts using the ownership rules in the meta specification, and keep the affected documents consistent. Preserve unrelated work, including staged and untracked files.

## Check file relations

Use the installed Depmesh CLI in agent mode:

```bash
depmesh -p llm relations
depmesh -p llm dependencies @/path/to/file
```

Read returned `governed_by` specifications before editing. Inspect `governs` when changing a specification and `tested_by` when changing source. An empty query does not prove that nothing is affected: consult [file relation requirements](specs/behavior/files_relations.md), especially for new files or unmapped directories.

When adding, moving, or deleting files, update applicable Depmesh rules, tests, and documentation links in the same change. New specifications must appear in `specs/intro.md` and follow `specs/meta/general.md`. Keep detailed requirements in their owning spec rather than copying them into this file.

## Use Donna workflows

Read [the workflow catalogue](specs/general/workflows.md) and inspect `donna -p llm status` before starting or resuming workflow work. Follow pending action requests for the active task. If new, unrelated work conflicts with a pending session, clarify which task to continue; do not silently reset it.

Use `donna -p llm skill usage` for CLI guidance and `donna -p llm skill workflows` before authoring workflows. Run a workflow when requested by the user, an applicable project instruction, or an active Donna action. Complete action requests only after doing the work, using the exact request id and allowed transition Donna supplies.

Permanent workflows belong in `workflows/*.donna.md`; temporary plans and execution evidence belong in ignored `.session/donna/`. Every workflow edit requires Donna validation. Keep the catalogue's available/planned statuses accurate. Routine authorized edits and local checks do not need a separate approval step.

## Preserve prototype boundaries

Follow the platform specification's private-data ownership, bilingual interface and honest placeholder/example requirements. The initial nutrition specification remains a reference for any separately authorized future nutrition feature. Do not invent human content approval, clinical validation, live AI replies, or community participation. Keep provider secrets server-side and out of tracked files, browser output, and logs. Routine automated checks must use mocks and must not consume provider credits.

## Write commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope): description` (scope optional). Match the staged changes: `feat` for features, `fix` for bug fixes, `docs` for documentation, and `chore` for repository maintenance. Keep descriptions concise and imperative. Mark breaking changes with `!` before the colon.

## Verify and report

For specification, file-relation, or workflow changes, run:

```bash
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

Run the relevant product checks when implementation exists; the workflow catalogue defines their prerequisites. Report what changed, actual checks and outcomes, and any remaining blockers. Do not present planned workflows or unrun application checks as completed work.
