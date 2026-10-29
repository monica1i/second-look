# Second Look

Second Look extends [AgentEval by Jingyu Tang and collaborators](https://github.com/jytang0621/AgentEval) with a DeepSeek browser actor and selective human review before consequential actions. The original React website supplies 16 dark-pattern scenarios. Our Python runner uses Browser Use to operate Chrome; an independent checker reviews proposed actions using live page evidence, the original instruction, and earlier user decisions.

This repository publishes the website, runtime code, and seven current-version sample runs. Development tests, personal documentation, historical runs, and original upstream recordings are not included in the current file tree.

## Requirements

- macOS with Google Chrome installed at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` (the runner currently uses this fixed path).
- Python 3.11 or newer; Node.js 20.19+ or 22.12+ and npm for Vite 7.
- A DeepSeek API key with access to `deepseek-v4-flash`. Model calls incur API charges.
- An interactive desktop for human oversight.

## Install and start the website

```bash
git clone https://github.com/monica1i/second-look.git
cd second-look/website
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Leave this terminal running. The original Vite configuration uses the `/AgentEval` base path; the runner opens `http://127.0.0.1:5173/AgentEval/#/task/<id>?agent=true`.

In a second terminal, from the cloned repository root:

```bash
cd agent_runner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `agent_runner/.env` and replace the API-key placeholder:

```dotenv
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
AGENTEVAL_BASE_URL=http://127.0.0.1:5173/AgentEval
# Optional: defaults to the actor model
SECOND_LOOK_MODEL=deepseek-v4-flash
```

Keep `.env` private; it is ignored by Git. The benchmark uses fictional study identities from `agent_runner/tasks.py`, supplied through site-scoped Browser Use secret placeholders. Use the supplied fictional data for these scenarios.

## Run

From `agent_runner/`, check the website and Chrome configuration without a model call:

```bash
.venv/bin/python run_task.py --check --task 5
```

Run live oversight:

```bash
.venv/bin/python run_task.py --task 5 --mode oversight --keep-open
```

Run the actor without Second Look:

```bash
.venv/bin/python run_task.py --task 5 --mode baseline
```

`baseline` is the default. `--task` accepts 1–16; `--max-steps` defaults to 40. `--thinking` enables DeepSeek API thinking mode. `--headless` is suitable for baseline; interactive oversight requires visible Chrome. `--keep-open` retains Chrome and shows a collapsed trace after completion; press Enter in the terminal to close it.

The original website's `?agent=true` mode hides participant instructions; the runner supplies the actor's instruction separately. The original `/task/<id>/taskvideo` mode plays prerecorded videos and is separate from live Second Look.

### Human review

The actor proposes one action at a time. The gate resolves the live target, collects rendered page/form evidence, and calls the checker for actions outside its read-action allowlist. Allowed actions execute through Browser Use. Flagged actions display an injected review card:

- **Allow this step / Allow only this step:** execute the pending action if the observed page has not changed; permission covers that action only.
- **Change plan / Adjust:** save your correction with the concern it answered, discard the pending action, and ask the actor to observe and replan.
- **Activity approval:** when a clearly described form activity is available, its concrete approval button saves an instruction covering that activity and requests replanning. It does not execute the old proposal.
- **Stop task:** discard the pending action and end automation.

Both models receive persistent user decisions and the last eight observed action outcomes. Repeated actions or page cycles can open recovery controls: take over manually, then resume automation for a fresh checked proposal, or stop. Waiting for human review never automatically grants approval.

For another site, provide both arguments:

```bash
.venv/bin/python run_task.py --mode oversight \
  --url 'https://example.com/' \
  --instruction 'Describe the action you want performed'
```

Custom sites receive no benchmark credentials. The browser restricts navigation to the configured host and localhost; workflows requiring other hosts may be blocked.

For explicitly scripted evaluation, `--review-script /path/to/decisions.json` accepts a JSON list of responses, for example `[{"choice":"stop"}]`. Supported choices are `proceed`, `adjust`, `stop`, and `continue_activity`; adjustments include a `correction` string. These runs are marked `scripted_reviewer` and must not be treated as human interaction data.

## Sample logs and reproduction

Published samples are under [`agent_runner/runs/second_look/`](agent_runner/runs/second_look/), for tasks **1, 3, 5, 7, 11, 13, and 14**. All have recorded checker prompt hash `a00b543b686faf679578004461490c3fe8102764c6ca1c462c870a59b3417674`, policy `general_replan_v5`, observation version `field_presence_v2`, and actor context `scoped_credential_context_v1`. All seven summaries mark `scripted_reviewer: false`.

[`index.json`](agent_runner/runs/second_look/index.json) contains artifact checksums and configuration provenance. Runtime source matches checkpoint `0cf711b60e02acca001952f059debdde964e130a`; execution-time Git revisions were not recorded, so this association is based on matching source/configuration rather than an embedded run revision. These are development examples, not a controlled comparison or user study.

To repeat the scenarios, run each task with `--mode oversight` and respond to the review cards. Consult each sample's `interventions.jsonl` for its recorded human choices. Model output, latency, and human choices can vary; these commands reproduce the setup and procedure, not identical transcripts. The model/framework differ from the original paper, so this is an extension rather than an exact study replication.

Every run writes to `agent_runner/runs/baseline/` or `agent_runner/runs/second_look/`:

| Artifact | Meaning |
|---|---|
| `summary.json` | Task, model, configuration, aggregate metrics, termination, actor-reported result |
| `history.json` | Browser Use observations, model proposals, and action results |
| `conversations/` | Actor model request/response transcripts |
| `agent_history.gif` | Condensed replay; oversight combines actor/checker phases and actual human review UI |
| `interventions.jsonl` | Oversight proposal, checker, human response, and execution events |
| `trace.html` | Standalone oversight trace |

A proposed action is not proof of execution: use `execution` events in `interventions.jsonl`. A successful click or actor-reported completion is not proof of dark-pattern avoidance or server-side task success. Sample artifacts can contain the benchmark's fictional personal data.

## Runtime structure

```text
website/                       Original React/Vite experiment environment
agent_runner/
  run_task.py                  CLI, model/browser setup, agent construction, output saving
  tasks.py                     Task instructions and fictional domain-specific details
  requirements.txt             Pinned direct Python dependencies
  .env.example                 Local configuration template
  second_look/
    gate.py                    Agent subclass, execution gate, decisions, recovery, audit trail
    checker.py                 Independent review prompt, structured response, evidence validation
    browser.py                 Browser target resolution, snapshot/UI injection, response polling
    snapshot.js                Read-only rendered DOM and form-state extraction
    overlay.js                 In-page human review and recovery interface
    tools.py                   Read-only inspect_form tool; arbitrary actor evaluate excluded
    recording.py               Combined replay capture and GIF export
    __init__.py                Package marker
  runs/second_look/             Published current-version sample evidence and checksum index
```

The runner operates through browser events rather than importing React or dispatching Redux actions directly. Its Python task definitions correspond to `website/src/data/tasks.js`; fictional identities correspond to `website/src/data/PII.js`. They are separate definitions, not automatically synchronized. The checker sees runtime evidence rather than website source, task labels, or actor rationale. `overlay.js` is injected by Python, not built into the website's React source.

## Limitations

The checker is model-based and can miss consequences or pause unnecessarily. Evidence substring validation checks quotations, not semantic correctness. Snapshots are bounded, exclude field values, and do not comprehensively inspect iframe contents. Page-change checks compare observed snapshots, not all hidden state. Recovery heuristics can miss loops or flag intentional revisits. Browser Use is pinned to 0.13.14 because the gate uses framework internals; upgrading requires compatibility verification. Transitive Python dependencies and remote model behavior are not fully locked.

The original website has its own interaction logger and Firebase submission code. Those are separate from the runner's local audit files. Original recordings are available from the upstream repository.

## Attribution and license

Based on *Dark Patterns Meet GUI Agents: LLM Agent Susceptibility to Manipulative Interfaces and the Role of Human Oversight*, by Jingyu Tang and collaborators ([paper](https://arxiv.org/abs/2509.10723), [upstream](https://github.com/jytang0621/AgentEval)). The original website, task designs, data, and recordings belong to the upstream authors. Extensions were developed by Monica Li.

This repository retains the original [MIT License](LICENSE), including Copyright (c) 2025 Jingyu Tang.
