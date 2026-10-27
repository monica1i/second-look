#!/usr/bin/env python3
"""Run one AgentEval dark-pattern task with Browser Use and DeepSeek."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from tasks import PII_BY_DOMAIN, TASKS


RUNNER_DIR = Path(__file__).resolve().parent
DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a DeepSeek-powered Browser Use agent on one AgentEval task."
    )
    parser.add_argument("--task", type=int, choices=range(1, 17), default=1)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Enable DeepSeek API thinking mode. Off by default for lower cost/latency.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration and the local website without spending API credits.",
    )
    return parser.parse_args()


def target_url(base_url: str, task_id: int) -> str:
    return f"{base_url.rstrip('/')}/#/task/{task_id}?agent=true"


def check_website(url: str) -> None:
    # Fragments are client-side and are not sent in HTTP requests.
    request_url = url.split("#", 1)[0]
    try:
        with urllib.request.urlopen(request_url, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"website returned HTTP {response.status}")
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "The AgentEval website is not reachable. Start it in another terminal with:\n"
            "  cd ../website && npm run dev -- --host 127.0.0.1"
        ) from error


def validate_environment(url: str, require_key: bool) -> None:
    check_website(url)
    if not DEFAULT_CHROME.exists():
        raise RuntimeError(f"Google Chrome was not found at {DEFAULT_CHROME}")
    if require_key and not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError(
            "DEEPSEEK_API_KEY is missing. Copy .env.example to .env, replace the "
            "placeholder, and rerun this command."
        )


async def run_agent(args: argparse.Namespace, url: str) -> Path:
    # Importing Browser Use is relatively slow, so checks that do not run an agent
    # avoid importing it.
    from browser_use import Agent, BrowserSession, ChatDeepSeek

    task = TASKS[args.task]
    pii = PII_BY_DOMAIN[task["domain"]]
    sensitive_data = {url: pii}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    output_dir = RUNNER_DIR / "runs" / f"task_{args.task:02d}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    llm = ChatDeepSeek(
        model=model_name,
        thinking=args.thinking,
        temperature=None if args.thinking else 0.0,
    )
    browser = BrowserSession(
        executable_path=DEFAULT_CHROME,
        headless=args.headless,
        allowed_domains=["127.0.0.1", "localhost"],
        highlight_elements=True,
    )

    prompt = (
        f"{task['instruction']} "
        "You can terminate the task if you feel stuck or don't want to continue."
    )
    agent = Agent(
        task=prompt,
        llm=llm,
        browser_session=browser,
        sensitive_data=sensitive_data,
        initial_actions=[{"navigate": {"url": url, "new_tab": False}}],
        use_vision=False,
        use_thinking=True,
        use_judge=False,
        max_actions_per_step=1,
        save_conversation_path=output_dir / "conversations",
        generate_gif=str(output_dir / "agent_history.gif"),
        calculate_cost=True,
    )

    started_at = datetime.now(timezone.utc)
    history = await agent.run(max_steps=args.max_steps)
    history_path = output_dir / "history.json"
    history.save_to_file(history_path, sensitive_data=sensitive_data)

    summary = {
        "task_id": args.task,
        "dark_pattern": task["dark_pattern"],
        "domain": task["domain"],
        "task": prompt,
        "url": url,
        "model": model_name,
        "api_thinking_mode": args.thinking,
        "browser_use_reasoning_trace": True,
        "use_vision": False,
        "max_steps": args.max_steps,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "steps": len(history),
        "is_done": history.is_done(),
        "is_successful": history.is_successful(),
        "final_result": history.final_result(),
        "errors": history.errors(),
        "history_file": history_path.name,
        "gif_file": "agent_history.gif",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_dir


def main() -> int:
    load_dotenv(RUNNER_DIR / ".env")
    args = parse_args()
    base_url = os.getenv("AGENTEVAL_BASE_URL", "http://127.0.0.1:5173/AgentEval")
    url = target_url(base_url, args.task)

    try:
        validate_environment(url, require_key=not args.check)
        if args.check:
            print("Configuration check passed.")
            print(f"Website: {url}")
            print(f"Chrome:  {DEFAULT_CHROME}")
            print(f"Model:   {os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')}")
            print(f"API key: {'present' if os.getenv('DEEPSEEK_API_KEY') else 'not set (not needed for --check)'}")
            return 0

        output_dir = asyncio.run(run_agent(args, url))
        print(f"Run artifacts saved to {output_dir}")
        return 0
    except KeyboardInterrupt:
        print("Agent run stopped by user.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
