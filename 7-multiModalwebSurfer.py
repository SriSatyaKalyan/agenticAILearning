import asyncio
import json
import os

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models.anthropic import AnthropicChatCompletionClient

async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    anthropic_client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-6", # this model allows tooling
        api_key=api_key,
    )

    # first assistant agent
    web_surfer_agent = MultimodalWebSurfer(
        name = "webSurfer",
        model_client = anthropic_client,
        headless = True,
        animate_actions = True
    )

    agent_team = RoundRobinGroupChat(participants=[web_surfer_agent], max_turns=3)

    await Console(agent_team.run_stream(task = "Navigate to Google and search for 'FC Barcelona'. Summarize your findings here in 200 words."))
    await anthropic_client.close()

asyncio.run(main())