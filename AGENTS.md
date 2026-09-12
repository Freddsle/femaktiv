# Working in FemAktiv

## Read the applicable contracts

Start with [the specification index](specs/intro.md) and [specification authoring requirements](specs/meta/general.md). Read the relevant specifications before changing files. For product work, also read the applicable sections of [the prototype build specification](00_initial/FEMAKTIV_BUILD_SPEC.md); it remains the detailed product contract. The unstructured overview is background, including ideas outside the current scope.

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

Follow the build specification's fictional-adult demonstration scope, approved-content requirements, deterministic constraint checks, and separation of demo and live modes. Do not invent human content approval, clinical validation, or successful live integration results. Keep provider secrets server-side and out of tracked files, browser output, and logs. Routine automated checks must use mocks and must not consume provider credits.

## Verify and report

For specification, file-relation, or workflow changes, run:

```bash
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

Run the relevant product checks when implementation exists; the workflow catalogue defines their prerequisites. Report what changed, actual checks and outcomes, and any remaining blockers. Do not present planned workflows or unrun application checks as completed work.
