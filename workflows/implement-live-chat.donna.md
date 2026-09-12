# Implement evidence-linked live chat

Implement the user-approved live chat plan for nutrition and family care in the existing Django platform. Preserve approved public examples, use fictional data, and keep all ordinary verification offline. Live provider evaluation requires a separately invoked opt-in command.

```toml donna
id = "primary"
kind = "donna.lib.workflow"
start_operation_id = "contracts"
```

## Establish the scoped contracts

```toml donna
id = "contracts"
kind = "donna.lib.request_action"
```

Read the approved plan and governing specifications. Add the live-chat specification, align platform ownership, workflow guidance and Depmesh mappings, and record work packages under `.session/donna/live-chat/`. Preserve unrelated work. Once the contracts match the approved plan, {{ donna.lib.goto("implement") }}.

## Implement and integrate

```toml donna
id = "implement"
kind = "donna.lib.request_action"
```

Implement durable requests, active note context, anonymous structured intake/composition, evidence and safe public lookup, bilingual live-state UI, migrations, mocked tests, and an opt-in fictional evaluation command. Use the live-chat specification. Preserve existing public example wording. When implementation and focused checks are ready, {{ donna.lib.goto("verify") }}.

## Verify without provider credits

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

Repair these actual failures without weakening the contract, then {{ donna.lib.goto("verify") }}.

```text
{{ donna.lib.task_variable("checks_stdout") }}
{{ donna.lib.task_variable("checks_stderr") }}
```

## Review and document

```toml donna
id = "review"
kind = "donna.lib.request_action"
```

Review both locales at 390px and 1440px and production-mode serving in an isolated local instance. Record actual tests, source checks, setup instructions, and remaining live-evaluation prerequisites. Do not exercise paid providers implicitly or claim clinical review. If repairs remain, {{ donna.lib.goto("implement") }}. Once implementation and offline verification are complete and live readiness is reported separately, {{ donna.lib.goto("finish") }}.

## Finish

```toml donna
id = "finish"
kind = "donna.lib.finish"
```

Report implemented behavior, actual verification and configuration requirements. Check final Donna status. Distinguish implementation completion from unperformed live provider evaluation.
