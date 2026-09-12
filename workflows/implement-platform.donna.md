# Implement the bilingual femaktiv platform

Implement the user-approved Django platform: real accounts, private notes and persistent chats with a placeholder reply service, bilingual examples and Q&A previews. Verify it and leave a working local website. No live LLM or external publication is part of this workflow.

```toml donna
id = "primary"
kind = "donna.lib.workflow"
start_operation_id = "foundation"
```

## Establish the approved platform contract

```toml donna
id = "foundation"
kind = "donna.lib.request_action"
```

Read project instructions and the approved conversation plan. Introduce the current platform specification, align ownership and workflow guidance, and freeze the implementation interfaces. Preserve staged and unrelated files. Prepare the Django dependency/configuration foundation. When the contract and work packages are established, {{ donna.lib.goto("implement") }}.

## Implement the complete platform

```toml donna
id = "implement"
kind = "donna.lib.request_action"
```

Implement accounts, notes, chat persistence and placeholder API, public bilingual examples, reusable responsive UI and translations according to specs/behavior/platform.md. Delegate bounded independent modules if useful, retaining a single owner for shared contracts and dependencies. Integrate all modules and add meaningful ownership, persistence, localization and browser tests. When the application and verification commands exist, {{ donna.lib.goto("verify") }}.

## Run the required verification

```toml donna
id = "verify"
kind = "donna.lib.run_script"
save_stdout_to = "checks_stdout"
save_stderr_to = "checks_stderr"
goto_on_success = "review"
goto_on_failure = "repair"
timeout = 300
```

```bash donna script
#!/usr/bin/env bash
set -euo pipefail
./bin/check
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

## Repair observed failures

```toml donna
id = "repair"
kind = "donna.lib.request_action"
```

Repair the actual failures below, without weakening the platform requirements. If necessary inspect the full recorded output in Donna. After relevant fixes, {{ donna.lib.goto("verify") }}.

```text
{{ donna.lib.task_variable("checks_stdout") }}
{{ donna.lib.task_variable("checks_stderr") }}
```

## Review the interface and local deployment

```toml donna
id = "review"
kind = "donna.lib.request_action"
```

Review all test results, the English/German interface and screenshots at 390px and 1440px. Exercise the production server locally. Confirm no external LLM requests occurred, private objects are owner-restricted, previews are labelled, and the final documentation reports actual outcomes. Start the local website and verify its URL. Write docs/VALIDATION.md and README startup instructions. If repairs are needed, {{ donna.lib.goto("implement") }}. If all required work and review are complete, {{ donna.lib.goto("finish") }}.

```text
{{ donna.lib.task_variable("checks_stdout") }}
{{ donna.lib.task_variable("checks_stderr") }}
```

## Finish and hand off the local website

```toml donna
id = "finish"
kind = "donna.lib.finish"
```

The implementation workflow is complete. Report the working features, observed verification results, remaining limitations and local URL. End the user-facing report with a code block containing exact commands to start/access the local website. Verify that Donna is idle before reporting completion.
