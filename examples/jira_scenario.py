import asyncio
import sys
import os

from autogen_agentchat.base import TaskResult

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat

# from autogen_agentchat.messages import TaskResult
from autogen_agentchat.ui import Console
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from dotenv import load_dotenv

from src.agentic_ai.utils import (
    load_system_message,
    get_required_env,
    create_anthropic_client,
    AnthropicModels,
)

load_dotenv()  # loads .env from current directory


async def main() -> None:
    print("🚀 Starting Jira Scenario with Bug Analyst and Playwright Agent")

    # Use utility function to create Anthropic client - API key automatically from env
    anthropic_client = create_anthropic_client(AnthropicModels.SONNET)
    print("✅ Anthropic client created")

    jira_server_params = StdioServerParams(
        command="uvx",
        args=["mcp-atlassian"],
        env={
            "JIRA_URL": get_required_env("JIRA_URL"),
            "JIRA_USERNAME": get_required_env("JIRA_USERNAME"),
            "JIRA_API_TOKEN": get_required_env("JIRA_API_TOKEN"),
            "TOOLSETS": "all",  # Explicit toolsets to avoid deprecation warning
        },
        read_timeout_seconds=60,
    )
    jira_workbench = McpWorkbench(jira_server_params)

    playwright_server_params = StdioServerParams(
        command="npx", args=["@playwright/mcp@latest"], env={}, read_timeout_seconds=60
    )
    playwright_workbench = McpWorkbench(playwright_server_params)

    # Get script directory for relative paths - fix the path calculation
    script_dir = os.path.dirname(os.path.abspath(__file__))  # This gets examples/
    parent_dir = os.path.dirname(script_dir)  # This gets the root project dir

    print("📁 Loading prompt files...")

    async with jira_workbench as jira, playwright_workbench as playwright:
        print("🔗 Connected to Jira and Playwright workbenches")

        # first assistant agent - JIRA
        manual_engineer = AssistantAgent(
            name="bugAnalyst",
            model_client=anthropic_client,
            workbench=jira,
            system_message=load_system_message(
                os.path.join(parent_dir, "assets", "prompts", "bug_analyst_prompt.txt")
            ),
        )

        # second assistant agent - Playwright
        automation_engineer = AssistantAgent(
            name="playwrightAgent",
            model_client=anthropic_client,
            workbench=playwright,
            system_message=load_system_message(
                os.path.join(
                    parent_dir, "assets", "prompts", "playwright_analyst_prompt.txt"
                )
            ),
        )

        # Use a direct task instead of loading from file to avoid termination issues
        task = """
        Bug Analyst: Please search for recent bugs in the KAN project and create a comprehensive smoke test for the GreenKart application. 
        Focus on discount code functionality and provide detailed test steps. When done, say 'HANDOFF TO AUTOMATION'.
        Playwright Agent: Wait for the Bug Analyst handoff, then implement the smoke test using Playwright. 
        Execute all test steps and verify results. When finished, say 'TESTING COMPLETE'.
        """

        print(f"📋 Task created: {len(task)} characters")

        team = RoundRobinGroupChat(
            participants=[manual_engineer, automation_engineer],
            termination_condition=TextMentionTermination("TESTING COMPLETE"),
            max_turns=10,  # Increased for proper conversation flow
        )

        print("🎬 Starting agent conversation...")
        print("-" * 80)

        # Verify tools are available on each agent's workbench
        jira_tools = await jira.list_tools()
        playwright_tools = await playwright.list_tools()
        print(f"🔧 Jira workbench tools available: {len(jira_tools)}")
        for t in jira_tools:
            print(f"   - {t.name}")
        print(f"🎭 Playwright workbench tools available: {len(playwright_tools)}")
        print("-" * 80)

        # Console streams every message type (TextMessage, ToolCallMessage,
        # ToolCallResultMessage, TaskResult) with full content as they arrive.
        result: TaskResult = await Console(team.run_stream(task=task))

        # Full structured dump of the completed conversation so nothing is hidden.
        print("\n" + "=" * 80)
        print("📊 FULL CONVERSATION DUMP")
        print("=" * 80)
        for i, msg in enumerate(result.messages, 1):
            source = getattr(msg, "source", "system")
            msg_type = type(msg).__name__
            content = getattr(msg, "content", None)
            print(f"\n[{i}] {msg_type} | source={source}")
            if content is None:
                print("  <no content>")
            elif isinstance(content, str):
                print(content)
            elif isinstance(content, list):
                for item in content:
                    print(f"  {item}")
            else:
                print(f"  {content}")
        print("=" * 80)
        print(
            f"\n✅ Conversation completed — {len(result.messages)} total messages"
            f"  |  stop_reason={result.stop_reason}"
        )

    await anthropic_client.close()
    print("🏁 Jira scenario completed")


if __name__ == "__main__":
    asyncio.run(main())
