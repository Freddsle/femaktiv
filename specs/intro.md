# femaktiv specification index

## Goal of the document

This index describes the femaktiv specification structure and the documents that guide product and repository work.

## Scope

This document covers specification locations, reading order, and the status of existing planning material. Detailed application contracts and individual tooling requirements are outside its scope.

## Specification directories

- `specs/` contains the current specification index and project specifications.
- `specs/meta/` contains requirements for writing and maintaining specifications.
- `specs/behavior/` contains observable behavior and tooling contracts.
- `specs/general/` contains development processes and requirements that apply across the project.

Architecture and documentation categories MAY be introduced when a concrete specification needs them. Empty categories and documents MUST NOT be presented as implemented specifications.

## Specification documents

| Document | Purpose |
| --- | --- |
| [Specification index](intro.md) | Entry point and inventory of current specifications. |
| [General specification requirements](meta/general.md) | Document structure, normative language, abstraction level, and maintenance rules. |
| [Bilingual platform](behavior/platform.md) | Current Django website, private accounts/notes/chats, placeholder API, localization, public examples, website wording approval and optional HTTPS tunnel previews. |
| [Live chat](behavior/live_chat.md) | Anonymous live assistance, approved tester access, durable usage limits, active context, evidence, local-care lookup and masking evaluation. |
| [File relations](behavior/files_relations.md) | Artifact identity, specification ownership, source/test relationships, Depmesh behavior, and verification. |
| [Project workflows](general/workflows.md) | Required Donna workflows, their execution contracts, prerequisites, and implementation status. |

The index MUST include every Markdown specification under `specs/`. Entries MUST link to existing documents and describe their purpose. Adding, moving, or removing a specification MUST update this index in the same change.

## Product contract and planning sources

[The bilingual platform specification](behavior/platform.md) owns the current product contract. It records the user's approved migration to Django, English/German interfaces, persistent accounts and personal notes, an offline default chat API, and static Q&A examples. The [live-chat specification](behavior/live_chat.md) owns the subsequently approved optional live extension.

The platform's [website wording approval](behavior/platform.md#website-wording-approval) records the user's approval of existing copy and the requirements for future example changes.

[The initial nutrition build specification](../00_initial/FEMAKTIV_BUILD_SPEC.md) remains intact as a historical and future nutrition reference. The platform contract supersedes its architecture, screens, English-only setting, no-account/no-database restrictions, milestones and completion gates for the current implementation. Historical TypeScript source conventions retain their initial-spec ownership; current Django files follow the platform contract. The live-chat contract defines its own fictional-prototype evidence and provider checks; it does not reinstate the historical recipe-catalogue or clinical-review gates. Further clinical features require their own scoped requirements.

[The unstructured overview](../00_initial/unstructured_overview.md) preserves original product ideas and desired presentation outputs as background. It does not add prototype acceptance requirements.

New specifications MUST link to the owning product contract where relevant. Future ownership migrations MUST identify superseded requirements and update the index, agent instructions and Depmesh rules together.

## Reading and maintenance

Agents MUST start with this index and [the authoring requirements](meta/general.md), then read the specifications returned by Depmesh for the affected files. Product work also requires the current platform specification; consult the preserved nutrition reference only for relevant historical context or separately authorized future work. `AGENTS.md` contains the concise working instructions; Donna workflows carry out the processes described by the workflow catalogue.

Specifications describe intended requirements. Their existence MUST NOT be used as evidence that an application, integration, content review, or workflow has been implemented or passed validation.

## Example source

The structure was adapted for femaktiv from [Donna's specification index](https://github.com/Tiendil/donna/blob/main/specs/intro.md), read on 12 September 2026. The external document is an authoring example and does not govern femaktiv behavior.
