import asyncio
import os
import time
import anthropic as anthropic_sdk
import random

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import FunctionExecutionResultMessage
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from dotenv import load_dotenv

load_dotenv()

from autogen_ext.models.anthropic import AnthropicChatCompletionClient  # noqa: E402


# ---------------------------------------------------------------------------
# Proactive throttle + built-in 429 retry.
#
# Math: org limit = 30,000 input tokens/min.
# Playwright tool schemas alone can reach ~20-25k tokens per call, so the
# minimum safe gap is ceil(25k / 30k * 60s) ≈ 65 s.
#
# If a 429 fires anyway (e.g. a prior run consumed the window), we read the
# `retry-after` header and sleep inside create() rather than propagating the
# error — that way the team session (and the open browser) stay alive.
# ---------------------------------------------------------------------------
class ThrottledClient:
    """Wraps AnthropicChatCompletionClient with proactive pacing and
    transparent 429-retry so rate limits never crash the team session.
    """

    def __init__(
        self,
        client: AnthropicChatCompletionClient,
        delay_seconds: float,
        max_retries: int = 6,
    ):
        self._client = client
        self._delay = delay_seconds
        self._max_retries = max_retries
        self._last_call: float = 0.0

    # Never wait longer than this even if the API asks for more.
    # Anthropic sends the full rolling-window reset time (can be ~20 min)
    # but for a per-minute TPM limit, 90 s is always enough.
    _MAX_BACKOFF = 90.0

    def _retry_after(self, exc: anthropic_sdk.RateLimitError) -> float:
        """Return seconds to wait, capped at _MAX_BACKOFF.

        `retry-after`               → plain integer duration in seconds.
        `x-ratelimit-reset-tokens`  → ISO-8601 timestamp; compute delta from now.
        """
        import datetime
        try:
            headers = exc.response.headers  # type: ignore[union-attr]

            # Plain duration (seconds) — most common header.
            raw = headers.get("retry-after")
            if raw:
                return min(float(raw) + 2, self._MAX_BACKOFF)

            # ISO timestamp headers — compute how many seconds until reset.
            for key in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
                raw = headers.get(key)
                if raw:
                    reset = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    delta = (reset - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                    if delta > 0:
                        return min(delta + 2, self._MAX_BACKOFF)
        except Exception:
            pass
        return 65.0  # safe default when headers are absent

    # browser_snapshot YAML can exceed 200k tokens per result.
    # We cap each tool-result string at this many chars (~20k tokens) so the
    # buffer never approaches the 1M context-window limit.
    _MAX_TOOL_RESULT_CHARS = 80_000

    def _trim_messages(self, messages):
        """Truncate oversized FunctionExecutionResult content in-place (copies)
        so a single browser snapshot can never blow the context window."""
        trimmed = []
        for msg in messages:
            if isinstance(msg, FunctionExecutionResultMessage):
                new_items = []
                for item in msg.content:
                    if isinstance(item.content, str) and len(item.content) > self._MAX_TOOL_RESULT_CHARS:
                        original_len = len(item.content)
                        kept = item.content[:self._MAX_TOOL_RESULT_CHARS]
                        suffix = (
                            f"\n...[truncated: {original_len:,} chars → "
                            f"{self._MAX_TOOL_RESULT_CHARS:,} to fit context window]"
                        )
                        item = item.model_copy(update={"content": kept + suffix})
                        print(
                            f"[Trim] Tool result '{item.name}' truncated "
                            f"({original_len:,} → {self._MAX_TOOL_RESULT_CHARS:,} chars)"
                        )
                    new_items.append(item)
                msg = msg.model_copy(update={"content": new_items})
            trimmed.append(msg)
        return trimmed

    async def create(self, messages, **kwargs):
        # ── trim oversized tool results before they hit the context window ─
        messages = self._trim_messages(messages)

        # ── proactive pacing ──────────────────────────────────────────────
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._delay:
            wait = self._delay - elapsed
            print(f"[Throttle] Pacing — waiting {wait:.1f}s before next LLM call...")
            await asyncio.sleep(wait)

        # ── call with internal 429 retry (keeps the team session alive) ───
        for attempt in range(self._max_retries):
            self._last_call = time.monotonic()
            try:
                return await self._client.create(messages, **kwargs)
            except anthropic_sdk.RateLimitError as exc:
                if attempt == self._max_retries - 1:
                    raise
                wait = self._retry_after(exc) + random.uniform(0, 10)
                print(
                    f"[Throttle] 429 received — backing off {wait:.0f}s "
                    f"(attempt {attempt + 1}/{self._max_retries})..."
                )
                await asyncio.sleep(wait)
                # Reset pacing clock so next iteration doesn't double-wait.
                self._last_call = time.monotonic()

    def __getattr__(self, name):
        return getattr(self._client, name)


def _is_rate_limit(exc: BaseException) -> bool:
    return isinstance(exc, anthropic_sdk.RateLimitError) or (
        isinstance(exc, RuntimeError) and "rate_limit" in str(exc).lower()
    )


async def run_with_retry(team, task, max_retries=5):
    for attempt in range(max_retries):
        try:
            await Console(team.run_stream(task=task))
            return
        except BaseException as exc:
            if not _is_rate_limit(exc):
                raise
            if attempt == max_retries - 1:
                raise
            wait = 60 + (2**attempt) + random.uniform(0, 5)
            print(f"[Rate Limited] Retry {attempt + 1}/{max_retries} in {wait:.0f}s...")
            await asyncio.sleep(wait)


async def fetch_jira_bugs(jira: McpWorkbench) -> str:
    """Call the Jira search tool directly in Python — no agent, zero tool
    schemas sent to Claude. Returns plain text injected into the task."""
    tools = await jira.list_tools()

    def tool_name(t) -> str:
        return t.name if hasattr(t, "name") else t["name"]

    names = [tool_name(t) for t in tools]
    print(f"[Jira] {len(tools)} tools available: {names}")

    search_tool = next(
        (t for t in tools if any(kw in tool_name(t).lower() for kw in ["search", "issues", "query", "jql"])),
        None,
    )
    if search_tool is None:
        return "(No Jira search tool found — proceeding with fallback smoke test design.)"

    print(f"[Jira] Using search tool: {tool_name(search_tool)}")
    try:
        result = await jira.call_tool(
            tool_name(search_tool),
            {"jql": "project = KAN AND issuetype = Bug ORDER BY created DESC", "limit": 5},
            CancellationToken(),
        )
        # ToolResult.result is a list of TextResultContent/ImageResultContent objects.
        parts = result.result
        if isinstance(parts, list):
            return "\n".join(getattr(item, "content", str(item)) for item in parts)
        return str(parts)
    except Exception as exc:
        return f"(Jira query failed: {exc} — proceeding with fallback smoke test design.)"


async def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    def get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"{key} environment variable not found")
        return value

    def load_system_message(filename: str) -> str:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise RuntimeError(f"System message file '{filename}' not found")
        except Exception as e:
            raise RuntimeError(f"Error reading system message file '{filename}': {e}")

    base_client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-6",
        api_key=api_key,
    )

    # Both agents share the same org rate limit (30k TPM).
    # Route all calls through one ThrottledClient so analyst + playwright
    # calls are serialised and paced. The playwright workbench alone sends
    # ~20-25k tokens of tool schemas per call → 65s gap keeps us under 30k TPM.
    shared_throttled = ThrottledClient(base_client, delay_seconds=65)
    analyst_client = shared_throttled
    playwright_client = shared_throttled

    jira_server_params = StdioServerParams(
        command="uvx",
        args=["mcp-atlassian"],
        env={
            "JIRA_URL": get_required_env("JIRA_URL"),
            "JIRA_USERNAME": get_required_env("JIRA_USERNAME"),
            "JIRA_API_TOKEN": get_required_env("JIRA_API_TOKEN"),
            "TOOLSETS": "all",
        },
        read_timeout_seconds=60,
    )
    jira_workbench = McpWorkbench(jira_server_params)

    playwright_server_params = StdioServerParams(
        command="npx", args=["@playwright/mcp@latest"], env={}, read_timeout_seconds=120
    )
    playwright_workbench = McpWorkbench(playwright_server_params)

    _prompts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "prompts"
    )

    async with jira_workbench as jira, playwright_workbench as playwright:
        print("[Jira] Pre-fetching KAN bugs...")
        bugs_text = await fetch_jira_bugs(jira)
        print(f"[Jira] Fetched bug data ({len(bugs_text)} chars)")

        # bugAnalyst has NO workbench — bugs injected as plain text.
        # Zero Jira tool schemas ever reach the LLM.
        manualEngineer = AssistantAgent(
            name="bugAnalyst",
            model_client=analyst_client,
            handoffs=["playwrightAgent"],
            model_context=BufferedChatCompletionContext(buffer_size=5),
            system_message=load_system_message(
                os.path.join(_prompts_dir, "bug_analyst_prompt.txt")
            ),
        )

        automationEngineer = AssistantAgent(
            name="playwrightAgent",
            model_client=playwright_client,
            workbench=playwright,
            # buffer_size=3: each snapshot can be 200k+ tokens; keeping only
            # the last 3 messages (+ trimming in ThrottledClient) stays well
            # under the 1M context-window limit.
            model_context=BufferedChatCompletionContext(buffer_size=3),
            system_message=load_system_message(
                os.path.join(_prompts_dir, "playwright_analyst_prompt.txt")
            ),
        )

        task = f"""
            Here are the most recent bugs from the KAN Jira project:

            {bugs_text}

            Based on these bugs, design a numbered smoke test for:
            https://rahulshettyacademy.com/seleniumPractise/#/
            Then hand off to the Playwright Agent.
        """

        team = Swarm(
            participants=[manualEngineer, automationEngineer],
            termination_condition=TextMentionTermination("TESTING COMPLETE"),
        )

        await run_with_retry(team, task=task)

    await base_client.close()


asyncio.run(main())
