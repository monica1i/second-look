# Second Look

Ask a browser agent to “subscribe to this creator,” and it may also accept a preselected box that shares your information with advertisers. **Second Look pauses before the agent clicks**, shows the page text behind the concern, and lets you tell the agent which consequences you accept.

I’m Monica Li. I designed the review interaction and built the Python browser runner, the model-based checker, and the event logging that connects each decision to what the agent did next. I used the 16 shopping, social media, and streaming scenarios from Jingyu Tang and collaborators’ [AgentEval](https://github.com/jytang0621/AgentEval) as the test environment.

![Second Look pauses at a registration form while the agent is trying to post a comment. The review card offers to register and post, approve a single step, or change the plan.](demo/task13.gif)

*I asked the agent to post “Unforgettable!” The site asked for my name, email, username, and a password. The card appeared before the agent entered my name, while I could still decide whether posting the comment was worth creating an account.* [Inspect this run](agent_runner/runs/second_look/task_13_oversight_20261120_200817_562265Z/summary.json)

## Three decisions in the prototype

I operated the review interface in these demonstrations. The agent performed the browser actions using fictional benchmark identities.

| What the site asked for | My decision | What happened next |
| --- | --- | --- |
| **Optional ad sharing.** A creator’s subscription dialog opened with personalized advertising selected. | Subscribe with ad sharing turned off. | The agent cleared the advertising option and confirmed the subscription. [Watch task 5](demo/task5.gif) |
| **Required partner sharing.** Another creator’s subscription terms tied subscribing to disclosure of personal information. | Skip the subscription if it requires sharing. | The agent clicked **Cancel**. Leaving the task unfinished honored the instruction. [Watch task 11](demo/task11.gif) |
| **Registration to comment.** Posting a comment required several fields of personal information. | Choose **Register & post comment** after reviewing the listed details. | The agent replanned with that permission and reported creating the account and posting the comment. [Read the event log](agent_runner/runs/second_look/task_13_oversight_20261120_200817_562265Z/interventions.jsonl) |

## How a decision reaches the browser

1. **Propose one action.** A DeepSeek actor drives Chrome through Browser Use. Before a proposed click or form entry executes, the Python gate resolves its target and reads the rendered page. The snapshot includes nearby labels, checkbox states, and whether fields are filled. [Execution gate](agent_runner/second_look/gate.py) · [Page snapshot](agent_runner/second_look/snapshot.js)
2. **Check the consequence.** Routine actions such as scrolling pass through fixed rules. For other actions, a separately prompted checker compares the proposal with the original request, visible page evidence, saved instructions, and the last eight observed outcomes. It can ask for review and quote the text behind its concern. The runner verifies those quotations against the snapshot. [Checker and response schema](agent_runner/second_look/checker.py)
3. **Give permission a scope.** The in-page card lets the person allow one step, change the plan, stop, or approve a described activity. One-step approval releases the pending action if the observed page still matches. A correction or activity approval discards that proposal, saves the instruction, and asks the actor to plan again. Later actions still pass through the gate. [Review interface](agent_runner/second_look/overlay.js)
4. **Record what executed.** Separate events capture the proposal, checker decision, human response, and execution outcome. Each oversight run also produces a standalone HTML trace and GIF replay. This makes it possible to follow a correction through to a later click. [Task 5 event log](agent_runner/runs/second_look/task_05_oversight_20261029_024806_173421Z/interventions.jsonl)

## Evidence and open questions

You can explore the [saved runs](agent_runner/runs/second_look/) to see the agent’s proposals, review decisions, and browser actions.

The demonstrations establish how the prototype behaves in these cases. Review accuracy, user workload, and the benefit over an unsupervised agent remain open questions. The actor and checker used the same underlying model and can share blind spots. The checker can also misinterpret a genuine quotation or miss a visual cue outside the rendered text it receives.

My proposed study would compare one-step approval with an interface that also offers activity approval. After the registration example, I would ask participants which later actions they believed they had authorized, then compare their answers with the displayed permission and the execution trace.

## Run it locally

The runner expects macOS with Google Chrome installed in the standard Applications folder, Python 3.11+, and Node.js 20.19+ or 22.12+ with npm. Live runs require a DeepSeek API key with access to `deepseek-v4-flash` and incur API charges.

**Start the benchmark site** in one terminal and leave it running.

```bash
git clone https://github.com/monica1i/second-look.git
cd second-look/website
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

**Set up the runner** in a second terminal, starting at the cloned repository root.

```bash
cd agent_runner
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python run_task.py --check --task 5
```

The check verifies Chrome and the local site without calling the model. Set `DEEPSEEK_API_KEY` in `agent_runner/.env`, then launch the optional ad-sharing scenario with the review interface visible.

```bash
.venv/bin/python run_task.py --task 5 --mode oversight --keep-open
```

With `--keep-open`, press Enter in the terminal when you finish inspecting the trace. To run the same scenario with the actor alone, use `--mode baseline`. Tasks are numbered 1–16. Run `run_task.py --help` with the virtual environment’s Python for custom URLs, scripted reviews, and other options. Browser Use is pinned to 0.13.14 because the gate uses its execution internals. [Runner](agent_runner/run_task.py) · [Task definitions](agent_runner/tasks.py)

## Credits and license

The React/Vite website, scenarios, and original study are the work of Jingyu Tang and collaborators. Second Look extends their research on human oversight of browser agents. This repository retains the original MIT license. [Research paper](https://arxiv.org/abs/2509.10723) · [Upstream repository](https://github.com/jytang0621/AgentEval) · [License](LICENSE)
