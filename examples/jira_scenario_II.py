import asyncio
import os
import anthropic as anthropic_sdk
import random

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import MultiModalMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import Image
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from dotenv import load_dotenv

load_dotenv()  # loads .env from current directory

from autogen_ext.models.anthropic import AnthropicChatCompletionClient  # noqa: E402


async def run_with_retry(team, task, max_retries=5):
    for attempt in range(max_retries):
        try:
            await Console(team.run_stream(task=task))
            return
        except anthropic_sdk.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = (2**attempt) + random.uniform(0, 1)  # noqa: F821
            print(f"[Rate Limited] Retry {attempt + 1}/{max_retries} in {wait:.1f}s...")
            await asyncio.sleep(wait)


async def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    # haiku_client = AnthropicChatCompletionClient(
    #     model="claude-haiku-4-5",
    #     api_key=api_key,
    # )

    anthropic_client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-6",  # this model allows tooling
        api_key=api_key,
    )

    def get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"{key} environment variable not found")
        return value

    # Function to read system message from file
    def load_system_message(filename: str) -> str:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise RuntimeError(f"System message file '{filename}' not found")
        except Exception as e:
            raise RuntimeError(f"Error reading system message file '{filename}': {e}")

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
        command="npx",
        args=["@playwright/mcp@latest", "--no-sandbox", "--headless", "--isolated"],
        env={},
        read_timeout_seconds=120,
    )
    playwright_workbench = McpWorkbench(playwright_server_params)

    prompts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "prompts"
    )

    async with jira_workbench as jira, playwright_workbench as playwright:
        # first assistant agent - JIRA
        manualEngineer = AssistantAgent(
            name="bugAnalyst",
            model_client=anthropic_client,
            workbench=jira,
            system_message=load_system_message(
                os.path.join(prompts_dir, "bug_analyst_prompt.txt")
            ),
        )

        # second assistant agent - Playwright
        automationEngineer = AssistantAgent(
            name="playwrightAgent",
            model_client=anthropic_client,
            workbench=playwright,
            system_message=load_system_message(
                os.path.join(prompts_dir, "playwright_analyst_prompt.txt")
            ),
        )

        task = """
            Bug Analyst:
            1. Search for recent bugs in the project
            2. Then design a stable user flow that can be used as a smoke test
            3. Use REAL URLs like: "https://rahulshettyacademy.com/seleniumPractise/#/"

            Playwright Agent:
            1. Implement the smoke test in Playwright based on the user flow designed by the Bug Analyst
            2. Ensure the test is stable and can be run multiple times (atleast 2) without failure
            3. Build a Playwright test with appropriate selectors, assertions and best practices
          """

        team = RoundRobinGroupChat(
            participants=[manualEngineer, automationEngineer],
            termination_condition=TextMentionTermination("TESTING COMPLETE"),
            max_turns=6,
        )

        await run_with_retry(team, task=task)

    await anthropic_client.close()


asyncio.run(main())
