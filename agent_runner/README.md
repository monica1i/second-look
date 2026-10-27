# AgentEval DeepSeek runner

This directory contains the operational instructions for the DeepSeek/Browser
Use runner. See the [repository README](../README.md) for the research context,
extension overview, evaluation framework, attribution, and limitations.

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
