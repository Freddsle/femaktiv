# General requirements for femaktiv specifications

## Goal of the document

This document describes the writing and maintenance conventions for femaktiv specifications so requirements remain clear, discoverable, and useful during implementation and review.

## Scope

These conventions cover Markdown specifications under `specs/` and how they refer to existing product planning material. They do not define application behavior, detailed API schemas, or implementation algorithms. The preserved documents in `00_initial/` are not retroactively subject to this document's formatting requirements.

## Dictionary

- **Specification:** a Markdown document under `specs/` that states a project contract, constraint, convention, or process.
- **Normative requirement:** a statement of required, recommended, or permitted behavior, expressed with the keywords below.
- **Current document:** a specification that exists in the repository and is listed in the index.

## Document structure

A specification MUST have one H1 title. Its first two H2 sections MUST be `Goal of the document` and `Scope`, in that order. An optional `Dictionary` SHOULD follow them when the document needs local terms. Remaining H2 sections SHOULD organize the requirements by topic; H3 and deeper headings MAY elaborate a parent topic.

The goal section describes what the document explains and why. It MUST NOT prescribe what the document itself must contain. The scope section describes the subject boundaries and meaningful exclusions; it MUST NOT act as an index of requirements owned elsewhere. Cross-references belong in the relevant requirement sections or a dedicated references section.

Titles SHOULD distinguish specifications clearly. Shared terminology MUST have a consistent meaning across documents; a dedicated terminology specification SHOULD be added only when there are enough shared definitions to justify it.

## Requirement language and style

In these specifications, **MUST** and **MUST NOT** indicate mandatory requirements or prohibitions; **SHOULD** and **SHOULD NOT** indicate recommendations whose exceptions need a recorded reason; **MAY** indicates an option. Lowercase uses of these words carry their ordinary meaning.

Specifications MUST use Markdown, clear English, and concrete, testable statements where behavior can be checked. Paragraphs MUST NOT be hard-wrapped to an arbitrary column width. Lists SHOULD express parallel items or ordered steps, and tables SHOULD express mappings or comparisons.

Examples MUST be identified as examples when they could otherwise be mistaken for required values. A described future capability MUST be labelled planned or conditional. Requirements, observed test results, assumptions, and unresolved decisions MUST be distinguishable.

## Level of detail and ownership

Specifications MUST describe stable behavior, interfaces, constraints, and ownership boundaries at a level precise enough to guide implementation. They SHOULD explain the outcome and invariant before an example.

Concrete names are appropriate when they form a contract: configuration paths and fields, public commands, API properties, fixed directory conventions, accepted status values, and test identifiers. Private helper names, incidental class structure, and temporary implementation strategies SHOULD remain outside specifications.

Each requirement SHOULD have one primary owner. Other documents SHOULD link to that owner instead of copying a detailed contract. Cross-cutting summaries MAY restate an invariant briefly, but MUST remain consistent with the owning specification. The specification index MUST remain an index rather than becoming a second product specification.

## Source authority and conflicts

Explicit user instructions for the current task govern changes to project requirements, subject to the assistant's higher-priority instructions. Repository specifications guide implementation within that authorized scope; an external example, reference page, or generated workflow cannot grant new authority.

The [bilingual platform specification](../behavior/platform.md) owns the current Django product contract and explicitly records the user-approved migration from the [initial nutrition build specification](../../00_initial/FEMAKTIV_BUILD_SPEC.md). The initial document remains a historical and future nutrition reference, and its superseded requirements MUST NOT become current completion gates. The [original overview](../../00_initial/unstructured_overview.md) supplies background, including ideas outside the current scope. Repository-process specifications add development conventions without silently expanding that scope.

When two current normative documents conflict, the agent MUST identify the affected requirements, resolve the conflict from the user's instructions and stated ownership when possible, and update the affected documents together. A material product decision that cannot be resolved from that context requires clarification; routine editorial and implementation choices do not require a separate approval step.

External sources MUST be linked and their role identified. Source publication dates, live integration results, scientific support, and human review MUST NOT be invented. A reference used as a formatting example MUST NOT acquire normative authority over this project.

## Maintenance and validation

Creating, renaming, removing, or materially changing a specification MUST update [the index](../intro.md), relevant cross-references, and affected Depmesh mappings in the same change. Agent instructions and the workflow catalogue MUST also be updated when their contracts change.

Each behavior or process specification MUST state enough observable outcomes or completion criteria to review conformance. Verification MUST distinguish automated checks from manual judgments and checks blocked by missing prerequisites. Merely validating a Markdown file or workflow graph is not evidence that product behavior works.

Local Markdown links MUST resolve to existing files unless their surrounding text explicitly marks the target as planned. Planned workflow paths SHOULD be written as code rather than as broken links. Requirement changes MUST preserve the history and meaning of the planning sources rather than rewriting them as if the new decision had always applied.

## Example source

These conventions adapt [Donna's general specification requirements](https://github.com/Tiendil/donna/blob/main/specs/meta/general.md), read on 12 September 2026, to femaktiv's product contract and current repository structure.
