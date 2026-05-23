#!/usr/bin/env python3
"""Simple Jira connection test to debug issues."""

import json

import pytest
from autogen_ext.tools.mcp import McpWorkbench


QUERY_MATRIX = [
    {"jql": "project = KAN", "description": "All issues in KAN project"},
    {"jql": "project = KAN AND issuetype = Bug", "description": "Bugs in KAN project"},
    {"jql": "key >= KAN-1", "description": "Issues from KAN-1 onwards"},
    {"jql": "key = KAN-5", "description": "Specific issue KAN-5"},
    {"jql": "project = KAN ORDER BY created DESC", "description": "Recent KAN issues"},
]


def _tool_name(tool: object) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", "Unknown"))
    return str(getattr(tool, "name", "Unknown"))


def _result_content(result: object) -> str:
    if hasattr(result, "result") and getattr(result, "result"):
        return getattr(result, "result")[0].content
    if hasattr(result, "content"):
        return str(getattr(result, "content"))
    return str(result)


@pytest.mark.asyncio
async def test_jira_connection(jira_server_params):
    """Test basic Jira connectivity and a few representative search queries."""

    async with McpWorkbench(jira_server_params) as jira:
        print("🔗 Connected to Jira MCP server")

        tools = await jira.list_tools()
        assert tools, "Expected Jira MCP server to expose tools"

        tool_names = [_tool_name(tool) for tool in tools]
        print(f"📋 Available tools: {len(tool_names)} found")
        for name in tool_names:
            print(f"  - {name}")

        assert "jira_search" in tool_names, "jira_search tool is required for this test"

        for query_info in QUERY_MATRIX:
            jql = query_info["jql"]
            desc = query_info["description"]
            print(f"\n🔍 Testing: {desc}")
            print(f"   JQL: {jql}")

            result = await jira.call_tool(
                "jira_search",
                {
                    "jql": jql,
                    "fields": "summary,status,priority,description,created,reporter,assignee",
                    "limit": 10,
                },
            )

            data = json.loads(_result_content(result))
            total = data.get("total", 0)
            issues = data.get("issues", [])

            assert isinstance(total, int)
            assert isinstance(issues, list)

            print(f"✅ Success! Found {total} issues, returned {len(issues)} issues")

            if issues:
                for issue in issues[:3]:
                    key = issue.get("key", "Unknown")
                    summary = issue.get("fields", {}).get("summary", "No summary")
                    print(f"   📝 {key}: {summary}")
            else:
                print("   ℹ️  No issues returned")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
