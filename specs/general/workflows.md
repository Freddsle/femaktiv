# femaktiv development workflows

## Goal of the document

This document lists the Donna workflows needed to maintain femaktiv's specifications, implement the prototype, verify its behavior, and prepare an honest demonstration.

## Scope

The catalogue covers development-time workflow responsibilities, prerequisites, execution rules, and completion criteria. It does not redefine product schemas, clinical content, or application runtime orchestration. Planned workflows are requirements for later implementation, not runnable artifacts today.

## Shared execution contract

Donna MUST be used as the workflow controller; the agent performs requested work and reports the allowed next transition. Agents MUST inspect `donna -p llm status` before starting a workflow and MUST address pending work for the active task. An unrelated request MUST NOT silently replace an active session. `new-session` MUST be used only when a fresh session is intended and authorized by the task context.

Permanent workflows MUST live under `workflows/` with the `.donna.md` suffix. Temporary implementation plans and execution notes MUST use ignored `.session/donna/`. `donna.toml` MUST discover both locations. File-level ownership follows [the relation specification](../behavior/files_relations.md).

Every executable workflow MUST have an intentional start operation, stable operation ids, explicit action transitions, success/failure routing for scripts, and a terminal report. Deterministic checks SHOULD use `donna.lib.run_script`; research, editing, review, and decisions SHOULD use `donna.lib.request_action`. Script stdout/stderr needed for repair MUST be captured and shown at the repair action.

A failing check MUST lead to a repair step and a relevant rerun. A retry loop MUST follow an actual change or new evidence; it MUST NOT repeatedly issue paid provider calls. Missing credentials, application commands, human review, or hosting access MUST be reported as missing prerequisites. A workflow MAY finish with a clearly stated blocked or partial outcome, but MUST NOT label that outcome successful acceptance.

Each workflow MUST be validated with `donna -p llm validate` before use. The agent MUST follow actual action-request ids and allowed transitions, and MUST verify the final Donna status before claiming completion. Starting a workflow grants no authority beyond the user's task and applicable instructions.

Workflows MUST preserve the platform's [approved website wording](../behavior/platform.md#website-wording-approval). Unchanged approved copy MUST NOT create a new approval gate or block authorized development. Future example changes follow that contract's requirement for approval of the exact proposed text.

## Workflow inventory and status

| Workflow | Artifact path | Status and introduction gate |
| --- | --- | --- |
| Establish specifications | [establish-specifications.donna.md](../../workflows/establish-specifications.donna.md) | Available; implements repository setup and validation/review. |
| Implement the bilingual platform | [implement-platform.donna.md](../../workflows/implement-platform.donna.md) | Available; combines specification alignment, implementation planning, scoped implementation, quality checks and local handoff. |
| Implement live chat | [implement-live-chat.donna.md](../../workflows/implement-live-chat.donna.md) | Available; scoped contracts, live adapters and UI, offline checks and honest live-evaluation handoff. |
| Maintain specifications separately | `workflows/maintain-specifications.donna.md` | Planned; introduce if recurring independent specification work needs a dedicated controller. |
| Review evidence and catalogue | `workflows/review-evidence.donna.md` | Deferred; needed only when separately authorized nutrition recommendations require reviewed content. |
| Verify live provider integration | `workflows/verify-live-provider.donna.md` | Deferred; needed with a real provider adapter and an explicitly authorized live check. |
| Prepare a nutrition demonstration | `workflows/prepare-demo.donna.md` | Deferred; applies to a separately authorized nutrition demonstration. |

The available entries are the executable workflows required for the current scope. The platform workflow performs the planning, implementation and quality responsibilities described below in one controller; separate planning, implementation and quality workflow artifacts are not prerequisites. Planned or deferred entries MUST NOT be presented as runnable or successfully executed. A new permanent workflow MUST be added here in the same change; `donna list` and available entries MUST agree.

The [platform specification](../behavior/platform.md) owns current product behavior and acceptance. The [initial nutrition build specification](../../00_initial/FEMAKTIV_BUILD_SPEC.md) remains a historical/future reference; its T01–T20 gates and live-provider/evidence-review milestones do not apply to this placeholder platform.

## Implement the bilingual platform

- **Trigger and inputs:** the authorized platform implementation or a related scoped change; the current platform contract, repository reality, governing specifications, and relevant tests.
- **Stages:** establish the migrated requirements and work packages; implement and integrate accounts, notes, persistent chats, bilingual examples and the placeholder API; run automated checks; repair failures; review browser behavior and local production serving; document actual results and local access commands.
- **Failure handling:** failed checks route to repair and rerun. Missing dependencies are reported precisely. Existing task authorization covers routine fixes; no live AI, external publishing or forum functionality is implied.
- **Outputs:** integrated application, dependency lockfile, migrations, translations, meaningful tests, startup instructions and `docs/VALIDATION.md` with observed results.
- **Completion gate:** platform acceptance passes, automated repository checks pass, browser review covers both locales and 390px/1440px, production smoke checks pass, and the local URL is verified. Check Donna status before declaring the workflow complete.

## Implement live chat

The [live-chat contract](../behavior/live_chat.md) owns the authorised fictional prototype and its scoped privacy fixes: approved tester access, durable request limits, private-data deletion and identifier-masking evaluation. Its workflow establishes scoped requirements, implements the feature, runs offline quality checks, repairs failures, and reviews bilingual browser/production behavior. Source checks are recorded honestly without invented human or clinical approval. Provider account settings and actual masked-output checks require honest separate reporting; the opt-in live evaluation is not an ordinary quality gate. The historical catalogue review and nutrition-demonstration processes below do not govern this extension.

## Establish specifications

- **Trigger and inputs:** the user's request to establish or refresh repository specifications; the two supplied Donna examples; the current README, planning files, agent instructions, and Donna/Depmesh configuration.
- **Stages:** read the examples and project context; create the index and meta requirements; align `AGENTS.md`; specify file relations; configure Depmesh and necessary helpers in `bin/depemesh/`; catalogue required workflows; run automated checks; review all six requested deliverables.
- **Failure handling:** inaccessible examples require access recovery or a truthful source blocker. Configuration, link, graph, or workflow errors route to repair and revalidation. Re-execution MUST preserve unrelated changes and adapt existing files instead of overwriting them blindly.
- **Outputs:** the setup specifications, root agent instructions, working relation configuration/helper, and the executable setup workflow. Execution evidence remains in Donna's session and the final report.
- **Completion gate:** `python3 bin/depemesh/check.py`, `donna -p llm validate --all`, and `git diff --check` pass; manual review confirms the product contract and six deliverables; Donna has no pending work for the completed task. This gate says nothing about application readiness.

## Maintain specifications

- **Trigger and inputs:** an authorized requirement, ownership, naming, workflow, or document-layout change; the affected specs and their `governed_by`/`governs` results.
- **Stages:** identify the requirement owner and impact; resolve conflicts using [the meta requirements](../meta/general.md); edit the owning document and affected guidance; update the index, links, Depmesh rules, and workflow catalogue; validate and review.
- **Failure handling:** repair missing links, conflicting requirements, or asymmetric rules and rerun the failed checks. Seek clarification only for a material unresolved decision that existing user instructions cannot resolve.
- **Outputs:** a consistent specification change and updated impact mappings, with an explicit migration note when product-contract sections change ownership.
- **Completion gate:** specification/relation checks pass, affected executable workflows validate, and the review identifies no stale authoritative copy or unindexed current spec.

## Plan platform implementation

- **Trigger and inputs:** a request to implement the platform or a related milestone; repository reality, installed tools, the platform contract, and the relevant specification graph.
- **Stages:** inspect existing code and commands; compare scope to actual implementation; identify dependencies and blockers; break the milestone into bounded changes with acceptance checks; record bounded work packages under `.session/donna/`; validate the execution workflow.
- **Failure handling:** record missing credentials or tooling precisely and continue planning independent demo/mock work. Do not invent a package version, endpoint behavior, passed check, or guaranteed schedule.
- **Outputs:** dependency-ordered work packages and actual starting-state notes; the available platform workflow supplies the validated execution controller.
- **Completion gate:** every planned work package names its inputs, outcome, and verification; platform dependencies determine the order; unrelated scope and live-provider calls are absent. This workflow prepares the plan; implementation starts only within the user's authorized scope.

## Implement a scoped change

- **Trigger and inputs:** an authorized feature/fix or active implementation-plan action; the target requirements, impacted files, applicable tests, and existing application structure.
- **Stages:** read governing specs; reproduce the issue or state the acceptance gap; implement a bounded change; update relevant tests/content/docs; run focused checks; inspect the result against the requested behavior; call quality verification when its prerequisites exist.
- **Failure handling:** route failed invariants back to focused repair. When the requested result requires an unresolved product decision or human content approval, preserve completed work and report that dependency rather than weakening the contract.
- **Outputs:** integrated code and relevant documentation, with actual focused-check results and remaining limitations.
- **Completion gate:** the selected acceptance gap is closed, relevant tests pass, and required relation/spec updates are complete. No hypothetical test file or mocked provider result may be described as live verification.

## Verify implementation quality

- **Trigger and inputs:** implementation changes ready for regression review, or an explicit request to check the app; installed dependencies, the actual package scripts, fixtures, and acceptance requirements.
- **Stages:** use the committed `uv` dependency lockfile; run the application check entrypoint, Django system and missing-migration checks, automated tests, translation compilation and static-file collection; exercise the local production server and relevant browser checks; inspect results and rerun only checks affected by repairs.
- **Failure handling:** capture the command and its output; repair the specific failure; rerun the affected stage. Missing required check commands are an unmet implementation gate, not skipped success. Do not replace the lockfile merely to run preferred commands.
- **Outputs:** reproducible commands and observed results, including which build/browser checks ran and any remaining blockers; maintain `docs/VALIDATION.md` once that report exists.
- **Completion gate:** the platform specification's automated acceptance invariants and required checks pass. Routine runs MUST use the deterministic placeholder service or mocked live adapters and MUST make no provider requests. Specification/tooling-only changes use the repository checks from the setup workflow instead of claiming application checks ran.

## Future evidence and catalogue review

- **Trigger and inputs:** new or changed source, claim, or option records; content schemas, source links, and an identified evidence/quality owner.
- **Stages:** validate record structure and unique identifiers; verify option–claim–source references; inspect complete ingredient/allergen tags and eligibility behavior; prepare draft records and source-support notes; obtain the evidence owner's actual review; revalidate approved records and the approved-only output boundary.
- **Failure handling:** broken references and unsupported claims return to draft repair. Missing human review leaves records in draft and the presentation gate unmet. Identifier integrity alone MUST NOT be reported as scientific support or human approval.
- **Outputs:** validated catalogue data, honest draft/approval metadata, and a record of actual source and ingredient review. Automated logs MUST NOT contain user health data.
- **Completion gate:** structurally valid records, supported relationships, and actual human approval for the records presented in recommendations. This workflow MUST NOT invent reviewer identities or approve the agent's own drafts on behalf of a person.

## Future live provider verification

- **Trigger and inputs:** explicit authorization for a live check; the real adapter/smoke command, server-side credentials, account-accessible models, bounded fictional scenarios, and current provider documentation.
- **Stages:** confirm configuration without revealing secrets; retrieve supported model identifiers; perform the build specification's bounded fictional smoke/evaluation cases; validate structured output and required provider metadata; check controlled failures and mode honesty; record non-sensitive measurements.
- **Failure handling:** missing access, unsupported output mode, false/missing expected metadata, invalid model output, or provider failures are explicit failed/blocked results. No silent fixture substitution, direct-provider fallback, or repeated paid retry loop is allowed.
- **Outputs:** actual model/output mode, observed pass/fail results, timing when measured, and remaining integration constraints. Ordinary quality checks MUST NOT invoke this workflow implicitly.
- **Completion gate:** the authorized live cases actually ran and met the required adapter boundaries. If live access is unavailable, retain useful mock results but label live integration untested. Provider metadata MUST NOT be described as independent proof of anonymization quality.

## Future nutrition demonstration

- **Trigger and inputs:** a presentation-readiness request; the integrated app, quality results, human content-review state, and any separately authorized live evaluation results.
- **Stages:** review T01–T20 coverage and known blockers; rehearse the canonical fictional scenario, a changed exclusion, an exact evidence explanation, and a refusal; review keyboard access and 390px/1440px layouts; verify reset, privacy, and mode labels; prepare a clearly identified backup recording and an accurate handoff.
- **Failure handling:** return product failures to implementation/quality repair and content gaps to evidence review. Unavailable live access requires an explicitly labelled demo-mode presentation. Unmet P0 gates MUST NOT be concealed by visual polish or a hosted URL.
- **Outputs:** observed readiness results, remaining limitations, start/run instructions, and demonstration material requested by the team. Slides, a one-pager, social imagery, or a hosted preview from the original overview are conditional deliverables, not automatic external publication instructions.
- **Completion gate:** the demonstrated mode is honest, shown records have actual approval, no known critical constraint/reset/privacy/source-integrity blocker remains, and presentation claims match observed results. A hosted preview is a separate optional P1 action within the user's authorization and the build specification's access/cost protections.

## Maintenance and verification

Workflow changes MUST keep this catalogue, the actual Donna artifacts, agent instructions, and dependency mappings consistent. Shared quality checks SHOULD be reused through the application check entrypoint and available platform workflow. Separate child workflows MAY be introduced when needed. A parent action MUST wait for a child workflow's real outcome before reporting completion.

The setup verification command checks specification structure and file links, not the semantic completeness of planned workflows. Manual review MUST compare the available entries with `donna -p llm list`, inspect `donna -p llm validate --all`, and confirm that the planned gates still match the current product scope. Execution reports MUST distinguish an available/valid workflow from a successfully executed workflow.
