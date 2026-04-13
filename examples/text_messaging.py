import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from dotenv import load_dotenv

from agentic_ai.utils import AnthropicModels, create_anthropic_client

load_dotenv()  # loads .env from current directory

from autogen_ext.models.anthropic import AnthropicChatCompletionClient


async def main() -> None:

    anthropic_client = create_anthropic_client(AnthropicModels.HAIKU)

    assistant = AssistantAgent(name="assistant", model_client=anthropic_client)
    await Console(assistant.run_stream(task="What is the capital of India?"))
    await anthropic_client.close()


asyncio.run(main())
