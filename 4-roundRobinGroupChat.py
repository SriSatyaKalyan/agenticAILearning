import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
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
                             system_message="You are a helpful and precise math teacher who explains concepts in a simple way. You also ask follow-up questions")

    # second assistant agent - student
    student = AssistantAgent(name="mathStudent",
                             model_client=anthropic_client,
                             system_message="You are a curious student. Ask questions and show your thinking prowess")

    classroom = RoundRobinGroupChat(participants=[teacher, student],
                                    termination_condition=MaxMessageTermination(max_messages=4))
    await Console(classroom.run_stream(task="Let's get into Pythagoras theorem."))
    await anthropic_client.close()


asyncio.run(main())