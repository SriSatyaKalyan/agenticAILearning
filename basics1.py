import asyncio
import os
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

    result = await anthropic_client.create(
        [UserMessage(content="What is the capital of France?", source="user")]
    )

    print(result.content)
    await anthropic_client.close()


asyncio.run(main())