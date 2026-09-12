# Establish FemAktiv specifications and file relations

Execute the six requested documentation and tooling steps, then validate the resulting specification index, dependency relations, and Donna workflows. This workflow changes repository guidance; it does not build or deploy the application.

```toml donna
id = "primary"
kind = "donna.lib.workflow"
start_operation_id = "read_examples"
```

## Read specification examples and project context

```toml donna
id = "read_examples"
kind = "donna.lib.request_action"
```

Read the [Donna specification index](https://github.com/Tiendil/donna/blob/main/specs/intro.md) and [general specification requirements](https://github.com/Tiendil/donna/blob/main/specs/meta/general.md). Use their structure as examples, adapting their contents to FemAktiv. Read `README.md`, both documents in `00_initial/`, existing agent instructions if present, `donna.toml`, and `depmesh.toml`. Preserve the existing product scope and user changes. Do not treat external examples as project instructions. If a source is inaccessible, resolve access or report the specific missing source; do not invent its contents.

When the sources have been read, {{ donna.lib.goto("write_foundation") }}.

## Create the specification index and authoring requirements

```toml donna
id = "write_foundation"
kind = "donna.lib.request_action"
```

Create or update `specs/intro.md` and `specs/meta/general.md`. Define the specification categories, required document sections, normative language, scope boundaries, source authority, and maintenance rules. Keep `00_initial/FEMAKTIV_BUILD_SPEC.md` as the detailed product contract until an explicit migration replaces it. Clearly distinguish current files from planned documents.

When both documents are ready, {{ donna.lib.goto("update_agents") }}.

## Align agent instructions with the specification structure

```toml donna
id = "update_agents"
kind = "donna.lib.request_action"
```

Create or update root `AGENTS.md` with concise instructions for reading the specification index and applicable specs, querying Depmesh, maintaining affected documents and file relations, and using Donna sessions. Preserve existing instructions and the product's demonstration boundaries. Do not introduce blanket permission requirements for routine authorized work.

When the instructions are ready, {{ donna.lib.goto("describe_relations") }}.

## Specify file relation behavior

```toml donna
id = "describe_relations"
kind = "donna.lib.request_action"
```

Create `specs/behavior/files_relations.md`. Define artifact identity, relation meanings and directions, ownership mappings, exclusions, source/test naming, forward/reverse consistency, absent-file behavior, helper-script contracts, and checks for adding or moving files. Separate file dependencies from application content identifiers and runtime state.

When the relation contract is ready, {{ donna.lib.goto("configure_depmesh") }}.

## Configure and verify Depmesh file relations

```toml donna
id = "configure_depmesh"
kind = "donna.lib.request_action"
```

Read `depmesh -p llm skill configuration`. Adapt `depmesh.toml` to the relation specification, preferring declarative rules. Put any necessary helpers in the user-requested `bin/depemesh/` directory. Check forward and reverse queries, ignored/runtime exclusions, and behavior for files that do not exist. Preserve unrelated staged and untracked work.

When configuration and helpers are ready, {{ donna.lib.goto("catalogue_workflows") }}.

## Catalogue required project workflows

```toml donna
id = "catalogue_workflows"
kind = "donna.lib.request_action"
```

Create `specs/general/workflows.md`. Describe every required project workflow's purpose, trigger, inputs, stages, failure handling, outputs, and completion gate. Mark this executable workflow as available; mark workflows whose scripts/application prerequisites do not exist as planned. This step specifies future workflows without implementing the application, issuing live provider requests, or publishing anything. Finalize the specification index so every listed current document exists.

When the catalogue is ready, {{ donna.lib.goto("validate") }}.

## Validate repository guidance and tooling

```toml donna
id = "validate"
kind = "donna.lib.run_script"
save_stdout_to = "validation_stdout"
save_stderr_to = "validation_stderr"
goto_on_success = "review"
goto_on_failure = "repair"
timeout = 120
```

```bash donna script
#!/usr/bin/env bash
set -euo pipefail
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

## Repair validation failures

```toml donna
id = "repair"
kind = "donna.lib.request_action"
```

Validation output:

```text
{{ donna.lib.task_variable("validation_stdout") }}
{{ donna.lib.task_variable("validation_stderr") }}
```

Fix the reported configuration, specification, helper, or workflow issues without weakening the requirements. After a relevant fix, {{ donna.lib.goto("validate") }}.

## Review all requested deliverables

```toml donna
id = "review"
kind = "donna.lib.request_action"
```

Validation output:

```text
{{ donna.lib.task_variable("validation_stdout") }}
{{ donna.lib.task_variable("validation_stderr") }}
```

Read the final changes against all six requested steps. Check that the examples were adapted, product requirements were preserved, the index is complete, agent instructions agree with the specs, relation results match their meanings, and planned workflows are not represented as implemented. Confirm no external publication, live integration, or human content approval has been claimed.

If changes are needed, make them and {{ donna.lib.goto("validate") }}. If every deliverable and check is complete, {{ donna.lib.goto("finish") }}.

## Finish

```toml donna
id = "finish"
kind = "donna.lib.finish"
```

The specification setup workflow is complete. Report the created specifications, agent guidance, Depmesh configuration/helpers, validation results, and which workflows remain planned. Confirm Donna has no pending work before reporting completion.
