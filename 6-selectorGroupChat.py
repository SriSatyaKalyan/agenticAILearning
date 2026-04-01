import asyncio
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
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
    researcher = AssistantAgent(name="researcher",
                            model_client=anthropic_client,
                            system_message="You are a researcher. Your role is to gather information and provide research findings to the writer."
                            "Do not write articles or create content - just provide research data and facts"
                            "Provide your research no more than two times. After second time, say 'That is all I have'."
                            )

    # second assistant agent
    writer = AssistantAgent(name="writer",
                             model_client=anthropic_client,
                             system_message="You are a writer. Your role is to take research information and write well-written articles in 150 words title 'My Research'"
                             "Wait for research to be provided, write the article, and ask the critic for feedback."
                             "If you have questions, ask the researcher but always be inclined to write the article."
                             "If researcher says 'That is all I have', write the article based on the research provided and end with 'I am done writing'."
                             "If critic gives you any feedback and if you have questions, ask the researcher about those topics and improve your article accordingly."
                             )

    # third assistant agent
    critic = AssistantAgent(name="critic",
                             model_client=anthropic_client,
                             system_message="You are a critic. Review written content and provide feedback to the writer to improve the article."
                             "When writer says 'I am done writing', provide constructive criticism and suggestions for improvement."
                             "After providing critique once, for the second time, always say 'I am done critiquing'"
                             )

    team = SelectorGroupChat(participants=[critic, writer, researcher],
                      model_client=anthropic_client,
                      allow_repeated_speaker=True,
                      termination_condition= MaxMessageTermination(max_messages=10) | TextMentionTermination("I am done critiquing")
                      )

    await Console(team.run_stream(task = "Hey Researcher! Research on renewable energy trends and the future of solar energy. Hand it over to writer."))

    await anthropic_client.close()

asyncio.run(main())