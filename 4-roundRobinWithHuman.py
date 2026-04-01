import asyncio
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
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

    # first assistant agent - math teacher
    teacher = AssistantAgent(name="mathTeacher",
                             model_client=anthropic_client,
                             system_message="You are a helpful and precise math tutor who explains concepts in a simple way. "
                                            "When user says 'Thanks', acknowledge and say 'Happy Learning' to end the session")

    # second agent - HUMAN
    human = UserProxyAgent(name = "human")

    classroom = RoundRobinGroupChat(participants = [teacher, human],
                                    termination_condition = TextMentionTermination("Happy Learning"),)
    await Console(classroom.run_stream(task = "Explain Pythagoras Theorem"))
    await anthropic_client.close()


asyncio.run(main())