import asyncio
import json
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.anthropic import AnthropicChatCompletionClient


async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    anthropic_client = AnthropicChatCompletionClient(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
    )

    # first assistant agent
    agentI = AssistantAgent(name="main", model_client=anthropic_client)

    # second assistant agent
    agentII = AssistantAgent(name="helper", model_client=anthropic_client)

    await Console(agentI.run_stream(task="My favorite food is lentil soup"))
    state = await agentI.save_state()

    # state-saving
    with open("memory.json", "w") as f:
        json.dump(state, f, default=str)

    with open("memory.json", "r") as f:
        saved_state = json.load(f)

    await agentII.load_state(saved_state)
    await Console(agentII.run_stream(task="What is my favorite food?"))

    await anthropic_client.close()


asyncio.run(main())
