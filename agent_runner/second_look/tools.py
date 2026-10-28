"""Bounded observation capability; page mutations stay in ordinary gated tools."""
import json

from browser_use import BrowserSession, Tools
from browser_use.agent.views import ActionResult

from .browser import snapshot


def create_tools():
    tools = Tools(exclude_actions=['evaluate'])

    async def inspect_form(browser_session: BrowserSession, selector: str | None = None):
        page = await browser_session.must_get_current_page()
        observation = await snapshot(page, {'selector': selector} if selector else {})
        return ActionResult(extracted_content=json.dumps(observation, ensure_ascii=False))

    tools.registry.action(
        'Read rendered page text, form state, and visible controls. '
        'Optional CSS selector focuses an element. No field secrets, storage, application '
        'source, or page changes.')(inspect_form)
    return tools
