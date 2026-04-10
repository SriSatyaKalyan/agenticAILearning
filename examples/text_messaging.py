import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
from autogen_agentchat.ui import Console
from autogen_core import Image
from dotenv import load_dotenv

load_dotenv()  # loads .env from current directory

from autogen_core.models import UserMessage
from autogen_ext.models.anthropic import AnthropicChatCompletionClient


async def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    anthropic_client = AnthropicChatCompletionClient(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
    )

    assistant = AssistantAgent(name="assistant", model_client=anthropic_client)
    await Console(assistant.run_stream(task="What is the capital of India?"))
    await anthropic_client.close()

asyncio.run(main())