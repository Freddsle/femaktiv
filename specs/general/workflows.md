# FemAktiv development workflows

## Goal of the document

This document lists the Donna workflows needed to maintain FemAktiv's specifications, implement the prototype, verify its behavior, and prepare an honest demonstration.

## Scope

The catalogue covers development-time workflow responsibilities, prerequisites, execution rules, and completion criteria. It does not redefine product schemas, clinical content, or application runtime orchestration. Planned workflows are requirements for later implementation, not runnable artifacts today.

## Shared execution contract

Donna MUST be used as the workflow controller; the agent performs requested work and reports the allowed next transition. Agents MUST inspect `donna -p llm status` before starting a workflow and MUST address pending work for the active task. An unrelated request MUST NOT silently replace an active session. `new-session` MUST be used only when a fresh session is intended and authorized by the task context.

Permanent workflows MUST live under `workflows/` with the `.donna.md` suffix. Temporary implementation plans and execution notes MUST use ignored `.session/donna/`. `donna.toml` MUST discover both locations. File-level ownership follows [the relation specification](../behavior/files_relations.md).

Every executable workflow MUST have an intentional start operation, stable operation ids, explicit action transitions, success/failure routing for scripts, and a terminal report. Deterministic checks SHOULD use `donna.lib.run_script`; research, editing, review, and decisions SHOULD use `donna.lib.request_action`. Script stdout/stderr needed for repair MUST be captured and shown at the repair action.

A failing check MUST lead to a repair step and a relevant rerun. A retry loop MUST follow an actual change or new evidence; it MUST NOT repeatedly issue paid provider calls. Missing credentials, application commands, human review, or hosting access MUST be reported as missing prerequisites. A workflow MAY finish with a clearly stated blocked or partial outcome, but MUST NOT label that outcome successful acceptance.

Each workflow MUST be validated with `donna -p llm validate` before use. The agent MUST follow actual action-request ids and allowed transitions, and MUST verify the final Donna status before claiming completion. Starting a workflow grants no authority beyond the user's task and applicable instructions.

## Workflow inventory and status

| Workflow | Artifact path | Status and introduction gate |
| --- | --- | --- |
| Establish specifications | [establish-specifications.donna.md](../../workflows/establish-specifications.donna.md) | Available; implements the six requested repository-setup steps and validation/review. |
| Maintain specifications | `workflows/maintain-specifications.donna.md` | Planned; introduce for the next substantial specification or file-layout change. |
| Plan prototype implementation | `workflows/plan-implementation.donna.md` | Planned; introduce before application implementation begins. |
| Implement a scoped change | `workflows/implement-change.donna.md` | Planned; introduce with the first implementation work package. |
| Verify implementation quality | `workflows/verify-quality.donna.md` | Planned; introduce when application scripts and test suites exist. |
| Review evidence and catalogue | `workflows/review-evidence.donna.md` | Planned; introduce when content schemas and draft records exist, before presented recommendations. |
| Verify live anymize integration | `workflows/verify-live-provider.donna.md` | Planned; introduce with the provider adapter and an explicitly authorized live check. |
| Prepare the demonstration | `workflows/prepare-demo.donna.md` | Planned; introduce before demonstration acceptance and presentation. |

This table is the complete required workflow set for the current prototype scope. A planned workflow MUST be implemented and validated by its introduction gate, or reported as an unmet prerequisite. It MUST NOT appear as an available command or successful run before its artifact exists. A new permanent workflow MUST be added here in the same change that creates it; `donna list` and the available entries MUST agree.

The [build specification](../../00_initial/FEMAKTIV_BUILD_SPEC.md) owns the implementation milestones, acceptance cases T01–T20, content requirements, and P0/P1 boundaries. The workflow descriptions below sequence those requirements rather than replacing them.

## Establish specifications

- **Trigger and inputs:** the user's request to establish or refresh repository specifications; the two supplied Donna examples; the current README, planning files, agent instructions, and Donna/Depmesh configuration.
- **Stages:** read the examples and project context; create the index and meta requirements; align `AGENTS.md`; specify file relations; configure Depmesh and necessary helpers in `bin/depemesh/`; catalogue required workflows; run automated checks; review all six requested deliverables.
- **Failure handling:** inaccessible examples require access recovery or a truthful source blocker. Configuration, link, graph, or workflow errors route to repair and revalidation. Re-execution MUST preserve unrelated changes and adapt existing files instead of overwriting them blindly.
- **Outputs:** the four current specifications, root agent instructions, working relation configuration/helper, and the executable setup workflow. Execution evidence remains in Donna's session and the final report.
- **Completion gate:** `python3 bin/depemesh/check.py`, `donna -p llm validate --all`, and `git diff --check` pass; manual review confirms the product contract and six deliverables; Donna has no pending work for the completed task. This gate says nothing about application readiness.

## Maintain specifications

- **Trigger and inputs:** an authorized requirement, ownership, naming, workflow, or document-layout change; the affected specs and their `governed_by`/`governs` results.
- **Stages:** identify the requirement owner and impact; resolve conflicts using [the meta requirements](../meta/general.md); edit the owning document and affected guidance; update the index, links, Depmesh rules, and workflow catalogue; validate and review.
- **Failure handling:** repair missing links, conflicting requirements, or asymmetric rules and rerun the failed checks. Seek clarification only for a material unresolved decision that existing user instructions cannot resolve.
- **Outputs:** a consistent specification change and updated impact mappings, with an explicit migration note when product-contract sections change ownership.
- **Completion gate:** specification/relation checks pass, affected executable workflows validate, and the review identifies no stale authoritative copy or unindexed current spec.

## Plan prototype implementation

- **Trigger and inputs:** a request to implement the prototype or a milestone; repository reality, installed tools, the build contract, and the relevant specification graph.
- **Stages:** inspect existing code and commands; compare scope to actual implementation; identify dependencies and blockers; break the milestone into bounded changes with acceptance checks; create a temporary Donna implementation plan under `.session/donna/`; validate that plan.
- **Failure handling:** record missing credentials or tooling precisely and continue planning independent demo/mock work. Do not invent a package version, endpoint behavior, passed check, or guaranteed schedule.
- **Outputs:** a dependency-ordered implementation plan, actual starting-state notes, and a validated session workflow whose steps connect to the build-specification milestones.
- **Completion gate:** every planned work package names its inputs, outcome, and verification; P0 precedes P1; unrelated scope and automatic live-provider calls are absent. This workflow prepares the plan; implementation starts only within the user's authorized scope.

## Implement a scoped change

- **Trigger and inputs:** an authorized feature/fix or active implementation-plan action; the target requirements, impacted files, applicable tests, and existing application structure.
- **Stages:** read governing specs; reproduce the issue or state the acceptance gap; implement a bounded change; update relevant tests/content/docs; run focused checks; inspect the result against the requested behavior; call quality verification when its prerequisites exist.
- **Failure handling:** route failed invariants back to focused repair. When the requested result requires an unresolved product decision or human content approval, preserve completed work and report that dependency rather than weakening the contract.
- **Outputs:** integrated code and relevant documentation, with actual focused-check results and remaining limitations.
- **Completion gate:** the selected acceptance gap is closed, relevant tests pass, and required relation/spec updates are complete. No hypothetical test file or mocked provider result may be described as live verification.

## Verify implementation quality

- **Trigger and inputs:** implementation changes ready for regression review, or an explicit request to check the app; installed dependencies, the actual package scripts, fixtures, and acceptance requirements.
- **Stages:** resolve the repository's package manager from its manifest/lockfile; run the configured formatter when present and appropriate; run `lint`, `typecheck`, `test`, `test:e2e`, and `build`; exercise the local production server for relevant browser checks; inspect results and rerun only checks affected by repairs.
- **Failure handling:** capture the command and its output; repair the specific failure; rerun the affected stage. Missing required scripts are an unmet implementation gate, not skipped success. Do not replace the lockfile merely to run preferred commands.
- **Outputs:** reproducible commands and observed results, including which build/browser checks ran and any remaining blockers; maintain `docs/VALIDATION.md` once that report exists.
- **Completion gate:** the build specification's applicable automated acceptance invariants and required commands pass. Routine runs MUST use deterministic demo/mock providers and MUST make no billable inference requests. Specification/tooling-only changes use the repository checks from the setup workflow instead of claiming application checks ran.

## Review evidence and catalogue

- **Trigger and inputs:** new or changed source, claim, or option records; content schemas, source links, and an identified evidence/quality owner.
- **Stages:** validate record structure and unique identifiers; verify option–claim–source references; inspect complete ingredient/allergen tags and eligibility behavior; prepare draft records and source-support notes; obtain the evidence owner's actual review; revalidate approved records and the approved-only output boundary.
- **Failure handling:** broken references and unsupported claims return to draft repair. Missing human review leaves records in draft and the presentation gate unmet. Identifier integrity alone MUST NOT be reported as scientific support or human approval.
- **Outputs:** validated catalogue data, honest draft/approval metadata, and a record of actual source and ingredient review. Automated logs MUST NOT contain user health data.
- **Completion gate:** structurally valid records, supported relationships, and actual human approval for the records presented in recommendations. This workflow MUST NOT invent reviewer identities or approve the agent's own drafts on behalf of a person.

## Verify live anymize integration

- **Trigger and inputs:** explicit authorization for a live check; the real adapter/smoke command, server-side credentials, account-accessible models, bounded fictional scenarios, and current provider documentation.
- **Stages:** confirm configuration without revealing secrets; retrieve supported model identifiers; perform the build specification's bounded fictional smoke/evaluation cases; validate structured output and required provider metadata; check controlled failures and mode honesty; record non-sensitive measurements.
- **Failure handling:** missing access, unsupported output mode, false/missing expected metadata, invalid model output, or provider failures are explicit failed/blocked results. No silent fixture substitution, direct-provider fallback, or repeated paid retry loop is allowed.
- **Outputs:** actual model/output mode, observed pass/fail results, timing when measured, and remaining integration constraints. Ordinary quality checks MUST NOT invoke this workflow implicitly.
- **Completion gate:** the authorized live cases actually ran and met the required adapter boundaries. If live access is unavailable, retain useful mock results but label live integration untested. Provider metadata MUST NOT be described as independent proof of anonymization quality.

## Prepare the demonstration

- **Trigger and inputs:** a presentation-readiness request; the integrated app, quality results, human content-review state, and any separately authorized live evaluation results.
- **Stages:** review T01–T20 coverage and known blockers; rehearse the canonical fictional scenario, a changed exclusion, an exact evidence explanation, and a refusal; review keyboard access and 390px/1440px layouts; verify reset, privacy, and mode labels; prepare a clearly identified backup recording and an accurate handoff.
- **Failure handling:** return product failures to implementation/quality repair and content gaps to evidence review. Unavailable live access requires an explicitly labelled demo-mode presentation. Unmet P0 gates MUST NOT be concealed by visual polish or a hosted URL.
- **Outputs:** observed readiness results, remaining limitations, start/run instructions, and demonstration material requested by the team. Slides, a one-pager, social imagery, or a hosted preview from the original overview are conditional deliverables, not automatic external publication instructions.
- **Completion gate:** the demonstrated mode is honest, shown records have actual approval, no known critical constraint/reset/privacy/source-integrity blocker remains, and presentation claims match observed results. A hosted preview is a separate optional P1 action within the user's authorization and the build specification's access/cost protections.

## Maintenance and verification

Workflow changes MUST keep this catalogue, the actual Donna artifacts, agent instructions, and dependency mappings consistent. Shared quality checks SHOULD be reused through an available child workflow rather than copied into multiple independent implementations. A parent action MUST wait for a child workflow's real outcome before reporting completion.

The setup verification command checks specification structure and file links, not the semantic completeness of planned workflows. Manual review MUST compare the available entries with `donna -p llm list`, inspect `donna -p llm validate --all`, and confirm that the planned gates still match the current product scope. Execution reports MUST distinguish an available/valid workflow from a successfully executed workflow.
