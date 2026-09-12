# FemAktiv specification index

## Goal of the document

This index describes the FemAktiv specification structure and the documents that guide product and repository work.

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
| [File relations](behavior/files_relations.md) | Artifact identity, specification ownership, source/test relationships, Depmesh behavior, and verification. |
| [Project workflows](general/workflows.md) | Required Donna workflows, their execution contracts, prerequisites, and implementation status. |

The index MUST include every Markdown specification under `specs/`. Entries MUST link to existing documents and describe their purpose. Adding, moving, or removing a specification MUST update this index in the same change.

## Product contract and planning sources

[The prototype build specification](../00_initial/FEMAKTIV_BUILD_SPEC.md) remains the detailed product contract. Its API schemas, demonstration boundaries, content-review requirements, privacy constraints, milestones, and acceptance cases remain applicable. Its location is `00_initial/FEMAKTIV_BUILD_SPEC.md`; references inside that document to a root-level build specification describe an earlier proposed layout.

[The unstructured overview](../00_initial/unstructured_overview.md) preserves the original product ideas and desired presentation outputs. It is background material, not an additional set of prototype acceptance requirements. Where it proposes broader functionality than the build specification, the build specification defines the current prototype scope.

New specifications MUST link to the product contract when they depend on its requirements. The original planning files MUST remain intact during this repository setup. A later migration into focused specifications MUST explicitly identify replacement sections and update the index, agent instructions, and Depmesh rules together.

## Reading and maintenance

Agents MUST start with this index and [the authoring requirements](meta/general.md), then read the specifications returned by Depmesh for the affected files. Product work also requires the relevant build-specification sections. `AGENTS.md` contains the concise working instructions; Donna workflows carry out the processes described by the workflow catalogue.

Specifications describe intended requirements. Their existence MUST NOT be used as evidence that an application, integration, content review, or workflow has been implemented or passed validation.

## Example source

The structure was adapted for FemAktiv from [Donna's specification index](https://github.com/Tiendil/donna/blob/main/specs/intro.md), read on 12 September 2026. The external document is an authoring example and does not govern FemAktiv behavior.
