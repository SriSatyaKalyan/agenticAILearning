#!/usr/bin/env python3
"""
Test specific KAN project access
"""

import asyncio
import os
import json
from dotenv import load_dotenv
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench

load_dotenv()


async def test_kan_access():
    """Test KAN project specific access."""

    def get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"{key} environment variable not found")
        return value

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

    async with McpWorkbench(jira_server_params) as jira:
        print("🔗 Connected to Jira MCP server")

        # Try to get specific issue KAN-5 directly
        print("\n1️⃣ Testing direct access to KAN-5...")
        try:
            issue_result = await jira.call_tool("jira_get_issue", {"key": "KAN-5"})
            if hasattr(issue_result, "result") and issue_result.result:
                content = json.loads(issue_result.result[0].content)
                print(f"✅ Found issue KAN-5:")
                print(
                    f"   🎫 Summary: {content.get('fields', {}).get('summary', 'N/A')}"
                )
                print(
                    f"   📝 Status: {content.get('fields', {}).get('status', {}).get('name', 'N/A')}"
                )
                print(
                    f"   🔍 Project: {content.get('fields', {}).get('project', {}).get('key', 'N/A')}"
                )
            else:
                print(f"❌ Could not access KAN-5: {issue_result}")
        except Exception as e:
            print(f"❌ Error accessing KAN-5: {e}")

        # Try bounded search with project filter
        print("\n2️⃣ Testing project-bounded search...")
        try:
            search_result = await jira.call_tool(
                "jira_search",
                {
                    "jql": "project = KAN AND created >= -30d",
                    "fields": "summary,status,priority,created,issuetype",
                    "limit": 10,
                },
            )
            if hasattr(search_result, "result") and search_result.result:
                data = json.loads(search_result.result[0].content)
                total = data.get("total", 0)
                issues = data.get("issues", [])
                print(f"✅ Search successful! Found {total} issues in last 30 days")
                for issue in issues:
                    key = issue.get("key", "Unknown")
                    summary = issue.get("fields", {}).get("summary", "No summary")
                    issue_type = (
                        issue.get("fields", {})
                        .get("issuetype", {})
                        .get("name", "Unknown")
                    )
                    print(f"   🎫 {key} ({issue_type}): {summary}")
            else:
                print(f"❌ Search failed: {search_result}")
        except Exception as e:
            print(f"❌ Error in bounded search: {e}")

        # Try getting project issues directly
        print("\n3️⃣ Testing get_project_issues...")
        try:
            project_result = await jira.call_tool(
                "jira_get_project_issues", {"project_key": "KAN", "limit": 10}
            )
            if hasattr(project_result, "result") and project_result.result:
                content = project_result.result[0].content
                print(f"✅ Raw project response: {content[:200]}...")

                # Try to parse as JSON
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "issues" in data:
                        issues = data["issues"]
                    elif isinstance(data, list):
                        issues = data
                    else:
                        issues = [data] if data else []

                    print(f"✅ Project issues found: {len(issues)} issues")
                    for issue in issues:
                        if isinstance(issue, dict):
                            key = issue.get("key", "Unknown")
                            summary = issue.get("fields", {}).get(
                                "summary", "No summary"
                            )
                            print(f"   🎫 {key}: {summary}")
                        else:
                            print(f"   📄 {str(issue)[:100]}...")
                except json.JSONDecodeError:
                    print(f"❌ Could not parse JSON: {content}")

            else:
                print(f"❌ No project issues found: {project_result}")
        except Exception as e:
            print(f"❌ Error getting project issues: {e}")


if __name__ == "__main__":
    asyncio.run(test_kan_access())
