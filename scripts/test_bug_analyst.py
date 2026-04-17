#!/usr/bin/env python3
"""
Simple test to show agent conversation output
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from dotenv import load_dotenv

from src.agentic_ai.utils import (
    load_system_message,
    get_required_env,
    create_anthropic_client,
    AnthropicModels,
)

load_dotenv()

async def main() -> None:
    anthropic_client = create_anthropic_client(AnthropicModels.SONNET)

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

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    async with jira_workbench as jira:
        # Only create the Bug Analyst for testing
        bug_analyst = AssistantAgent(
            name="bugAnalyst",
            model_client=anthropic_client,
            workbench=jira,
            system_message=load_system_message(
                os.path.join(script_dir, "assets", "prompts", "bug_analyst_prompt.txt")
            ),
        )

        # Simple task to test the Bug Analyst
        task = """Please search for bugs in the KAN project and create a comprehensive smoke test for the GreenKart application. Focus on the discount code functionality and provide clear test steps. End with 'HANDOFF TO AUTOMATION'."""

        print("🔍 Starting Bug Analyst test...")

        # Create a simple team with just the bug analyst
        team = RoundRobinGroupChat(
            participants=[bug_analyst],
            termination_condition=TextMentionTermination("HANDOFF TO AUTOMATION"),
            max_turns=3,
        )

        # Run the team
        async for message in team.run_stream(task=task):
            print(f"\n{'='*60}")
            print(f"Agent: {getattr(message, 'source', 'Unknown')}")
            print(f"Content: {getattr(message, 'content', message)}")
            print(f"{'='*60}")

    await anthropic_client.close()

if __name__ == "__main__":
    asyncio.run(main())

