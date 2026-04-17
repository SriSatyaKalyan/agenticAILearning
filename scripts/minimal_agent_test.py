#!/usr/bin/env python3
"""
Minimal working agent scenario to test conversation
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
    print("🚀 Starting Minimal Agent Test")

    anthropic_client = create_anthropic_client(AnthropicModels.SONNET)
    print("✅ Anthropic client created")

    # Set up Jira workbench
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

    # Set up Playwright workbench
    playwright_server_params = StdioServerParams(
        command="npx", args=["@playwright/mcp@latest"], env={}, read_timeout_seconds=60
    )
    playwright_workbench = McpWorkbench(playwright_server_params)

    async with jira_workbench as jira, playwright_workbench as playwright:
        print("🔗 Connected to workbenches")

        # Create Bug Analyst with simple prompt
        bug_analyst = AssistantAgent(
            name="BugAnalyst",
            model_client=anthropic_client,
            workbench=jira,
            system_message="""You are a Bug Analyst. When asked to analyze bugs:
1. Try to search for bugs in the KAN project using Jira tools
2. If no bugs found, create a test for GreenKart e-commerce app
3. Always end your response with 'HANDOFF TO AUTOMATION'
4. Be concise but specific in your test scenarios"""
        )

        # Create Playwright Agent with simple prompt
        playwright_agent = AssistantAgent(
            name="PlaywrightAgent",
            model_client=anthropic_client,
            workbench=playwright,
            system_message="""You are a Playwright automation expert. When you receive a handoff:
1. Wait for a message containing 'HANDOFF TO AUTOMATION'
2. Implement the test scenario using Playwright tools
3. Execute the test step by step
4. End with 'TESTING COMPLETE' when done"""
        )

        # Simple task
        task = "BugAnalyst: Please analyze bugs and create a test scenario for GreenKart application. Focus on basic functionality."

        # Create team
        team = RoundRobinGroupChat(
            participants=[bug_analyst, playwright_agent],
            termination_condition=TextMentionTermination("TESTING COMPLETE"),
            max_turns=6,
        )

        print("🎬 Starting conversation...")

        conversation_count = 0
        try:
            async for message in team.run_stream(task=task):
                conversation_count += 1
                print(f"\n📝 Message {conversation_count}:")
                print(f"   Source: {getattr(message, 'source', 'Unknown')}")
                print(f"   Type: {type(message).__name__}")

                if hasattr(message, 'content'):
                    content = message.content
                    if len(content) > 300:
                        print(f"   Content: {content[:300]}...")
                        print(f"   [Truncated - Total: {len(content)} chars]")
                    else:
                        print(f"   Content: {content}")

                # Show any tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    print(f"   🔧 Tool calls: {len(message.tool_calls)}")
                    for tool_call in message.tool_calls:
                        print(f"      - {getattr(tool_call, 'name', 'Unknown tool')}")

        except Exception as e:
            print(f"❌ Error in conversation: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n✅ Conversation completed with {conversation_count} messages")

    await anthropic_client.close()
    print("🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(main())
