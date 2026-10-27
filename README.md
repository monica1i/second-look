# Second Look: Extending AgentEval with DeepSeek

This repository extends [AgentEval](https://github.com/jytang0621/AgentEval),
the research artifact for *Dark Patterns Meet GUI Agents: LLM Agent
Susceptibility to Manipulative Interfaces and the Role of Human Oversight*.

The original project provides a React-based evaluation environment containing
16 dark-pattern tasks and recorded results from six GUI-agent configurations.
This extension adds a runnable DeepSeek V4 Flash agent based on Browser Use,
structured execution logging, repeatable trials, and a foundation for studying
agent behavior across the original tasks.

## What the original project provides

- A React/Vite website implementing 16 dark patterns across e-commerce,
  social-media, and video-streaming domains.
- Agent-only, human-only, and human-oversight presentation modes.
- Recorded results from six GUI-agent configurations.
- JSON execution traces and visual recordings from the original evaluation.

The website is an experiment environment rather than an agent launcher. Its
agent-only mode hides participant-facing instructions because an external agent
receives the task prompt separately.

The authors' original documentation is preserved in
[docs/UPSTREAM_README.md](docs/UPSTREAM_README.md).

## What this extension adds

The `agent_runner/` pipeline:

1. Selects one of the 16 original tasks.
2. Opens the corresponding local website route in agent-only mode.
3. Supplies the paper's fictional, domain-specific personal information through
   protected Browser Use secret placeholders.
4. Uses DeepSeek V4 Flash to inspect the page and select browser actions.
5. Executes those actions in Chrome through Browser Use.
6. Stores observations, visible rationale, actions, results, timing, model
   conversations, and an animated replay in a timestamped run directory.

See [agent_runner/README.md](agent_runner/README.md) for installation, API-key
configuration, commands, output files, and CLI options.

## Repository structure

```text
AgentEval/
├── README.md                 # Extension overview
├── LICENSE                   # Original MIT license
├── docs/
│   └── UPSTREAM_README.md    # Preserved upstream documentation
├── website/                  # Original experiment website
├── AgentResult/              # Original recorded agent results
└── agent_runner/             # DeepSeek runner and new experiment runs
```

## Quick start

Start the website:

```bash
cd website
npm install
npm run dev -- --host 127.0.0.1
```

In a second terminal, configure and run the agent:

```bash
cd agent_runner
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Add your DEEPSEEK_API_KEY to .env, then:
.venv/bin/python run_task.py --check --task 1
.venv/bin/python run_task.py --task 1
```

Never commit `agent_runner/.env`; it is ignored by Git.

## Experiment outputs and evaluation

Every run produces a timestamped directory under `agent_runner/runs/` with:

- `history.json`: structured observations, model outputs, actions, results, and
  timing for every step.
- `summary.json`: task, configuration, completion status, and final result.
- `conversations/`: the model requests and responses for detailed inspection.
- `agent_history.gif`: a visual replay of the browser interaction.

Within each `history.json` entry:

| Field | Source | Evaluation use |
| --- | --- | --- |
| `state_message` | Browser Use | Instructions and browser observation supplied to the model. |
| `model_output.thinking` | Model | Visible action rationale, not hidden chain-of-thought. |
| `model_output.evaluation_previous_goal` | Model | The agent's assessment of whether its previous action worked. |
| `model_output.memory` | Model | Information the agent chose to carry into later steps. |
| `model_output.next_goal` | Model | The next immediate objective selected by the agent. |
| `model_output.action` | Model | The browser operation requested by the agent. |
| `result` | Browser Use | The observed outcome, errors, and completion status. |
| `state` | Browser Use | Browser state such as URL, title, tabs, and interacted element. |
| `metadata` | Browser Use | Step number and timing information. |

These artifacts support evaluation of task completion, dark-pattern avoidance,
explicit awareness of manipulation, rationale-action mismatches, repetition,
recovery, termination, tool-use failures, and variation across repeated trials.
The prompted `thinking` field is an externally visible rationale and should not
be interpreted as privileged access to a model's internal state.

## Relationship to the original study

This project is an extension, not an exact replication. The original paper used
Browser Use 0.2.6 with DeepSeek V3. The current runner uses Browser Use 0.13.14
with DeepSeek V4 Flash, so changes in the model, system prompt, browser
observation layer, and action framework may affect results.

## Attribution

The original AgentEval website, task designs, data, and recorded results were
created by Jingyu Tang and collaborators. The upstream repository is available
at <https://github.com/jytang0621/AgentEval>.

Original work Copyright (c) 2025 Jingyu Tang. Extensions in `agent_runner/` and
other clearly identified additions were developed by Monica Li.

## License

This repository retains the original [MIT License](LICENSE). The original
copyright and permission notice must remain included in copies or substantial
portions of the software.
