import asyncio
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat, RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench

async def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found")

    anthropic_client = AnthropicChatCompletionClient(
        model="claude-sonnet-4-6", # this model allows tooling
        api_key=api_key,
    )

    fs_mcp_params = StdioServerParams(
        command="npx",
        args=["-y",
              "@modelcontextprotocol/server-filesystem",
              os.getcwd()
              ],  # Add project directory
        read_timeout_seconds=10
    )
    fs_workbench = McpWorkbench(fs_mcp_params)

    async with fs_workbench as fs_wb:

        # first assistant agent
        teacher = AssistantAgent(  name="mathTeacher",
                                 model_client=anthropic_client,
                                 workbench = fs_wb,
                                 system_message = """You are a helpful and precise math teacher who explains concepts in a simple way. 
                                 You also ask follow-up questions. After the student has shown good understanding (around 2-3 exchanges), 
                                 acknowledge their progress, say 'Happy Learning' to end the session, and save a summary of the student 
                                 session to a file called 'student_summary.txt' using the file system tools available to you. 
                                 Include details about their eagerness to learn and topics covered."""
                               )

        # second agent - HUMAN
        human = UserProxyAgent(name="student",
                               description = "A human student who wants to learn concepts in a simple way.",
                               )

        # state-saving
        # with open("memory.json", "w") as f:
        #     json.dump(state, f, default=str)

        classroom = RoundRobinGroupChat(participants=[teacher, human],
                                        termination_condition = TextMentionTermination("Happy Learning")
                                        )

        await Console(classroom.run_stream(task = "Let's discuss about Pythagoras theorem. Answer any questions by the student and make sure he feels comfortable. "))

    await anthropic_client.close()

asyncio.run(main())