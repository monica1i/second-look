# AgentEval DeepSeek runner

This directory extends the original AgentEval research artifact with a runnable
DeepSeek browser agent and structured local experiment logging.

## Original repository

The upstream AgentEval repository accompanies the paper *Dark Patterns Meet GUI
Agents: LLM Agent Susceptibility to Manipulative Interfaces and the Role of
Human Oversight*. It provides:

- A React/Vite website implementing 16 dark-pattern tasks across e-commerce,
  social-media, and video-streaming domains.
- Agent-only, human-only, and human-oversight presentation modes.
- Recorded results from six GUI-agent configurations, including Browser Use
  agents backed by GPT-4o, Claude 3.7 Sonnet, DeepSeek V3, and Gemini 2.0 Flash.
- JSON execution traces and visual recordings from the original evaluation.

The website is an experiment environment, not an agent launcher. In particular,
`?agent=true` hides the participant-facing task banner because an external agent
receives the task instruction separately.

## This extension

`agent_runner` adds a reproducible local pipeline that:

1. Selects one of the 16 original task instructions.
2. Opens the corresponding local website route in agent-only mode.
3. Supplies the paper's fictional, domain-specific personal information through
   Browser Use's protected secret placeholders.
4. Uses DeepSeek V4 Flash to inspect the browser state and select actions.
5. Lets Browser Use execute those actions in Chrome.
6. Stores the observations, visible rationale, actions, outcomes, timing, and a
   visual replay in a new timestamped run directory.

The default model is `deepseek-v4-flash`. DeepSeek API thinking mode is off by
default, while Browser Use's visible `thinking`/planning fields remain enabled
for behavioral analysis.

This is an extension rather than an exact replication. The paper used Browser
Use 0.2.6 with DeepSeek V3; this runner currently uses Browser Use 0.13.14 with
DeepSeek V4 Flash.

## One-time setup

From this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and replace the placeholder with your DeepSeek API key. Do not use
a `VITE_` variable or put the key under `website/`, because Vite client variables
can be exposed to the browser.

## Start the website

In terminal 1:

```bash
cd ../website
npm run dev -- --host 127.0.0.1
```

## Check without spending API credits

In terminal 2, from `agent_runner/`:

```bash
.venv/bin/python run_task.py --check --task 1
```

## Run an agent

```bash
.venv/bin/python run_task.py --task 1
```

Options:

- `--task 1` through `--task 16` selects an experiment task.
- `--max-steps 40` limits model/browser iterations.
- `--headless` hides the Chrome window.
- `--thinking` enables DeepSeek API thinking mode. It is off by default.

Each execution creates `runs/task_NN_TIMESTAMP/` with:

- `history.json`: detailed Browser Use states, actions, results, and reasoning.
- `summary.json`: compact run metadata and outcome.
- `agent_history.gif`: visual replay of the run.
- `conversations/`: model request/response transcripts.
