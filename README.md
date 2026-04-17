# Agentic AI — Multi-Agent Automation with Claude + AutoGen

A collection of autonomous agent examples built with [AutoGen](https://github.com/microsoft/autogen) and [Anthropic Claude](https://www.anthropic.com). The flagship example (`jira_scenario_II.py`) demonstrates a two-agent pipeline that reads live Jira bugs, executes them against a real website using a headless browser, and generates a production-ready Playwright test file — all without human intervention.

---

## What the Flagship Scenario Does

```
Jira (KAN project)
       │
       ▼
 Bug Analyst Agent          ← Claude Sonnet; reads bugs, produces numbered repro steps
       │  handoff
       ▼
 Playwright Agent           ← Claude Sonnet + Playwright MCP; executes steps in a live browser
       │
       ▼
 output/tests/greenkart.spec.ts   ← production-quality TypeScript test file, saved to disk
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | `python --version` to check |
| Node.js | 18+ | Required for Playwright MCP (`npx`) and `uvx` |
| npm / npx | bundled with Node | `npx --version` to check |
| uv / uvx | latest | `pip install uv` then `uvx --version` |

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/SriSatyaKalyan/python-agenticAI.git
cd python-agenticAI
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install Python dependencies

```bash
pip install autogen-agentchat autogen-core "autogen-ext[anthropic,mcp]" anthropic python-dotenv
```

> **Note:** The `autogen-ext[anthropic,mcp]` extra pulls in the Anthropic chat client and the MCP workbench that the Jira and Playwright tools run through.

### 4. Install Playwright browsers (first run only)

```bash
npx playwright install chromium
```

The Playwright MCP server (`@playwright/mcp`) is fetched automatically via `npx` at runtime — no separate install needed.

### 5. Install the Jira MCP server (first run only)

```bash
pip install uv          # if not already installed
uvx mcp-atlassian --help   # this caches the package for subsequent runs
```

---

## Getting Your API Tokens

### Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in (or create a free account).
2. Navigate to **API Keys** in the left sidebar.
3. Click **Create Key**, give it a name, and copy the key — it starts with `sk-ant-`.
4. You will not be shown this key again, so save it immediately.

> The free tier includes a usage limit. If you hit `429 RateLimitError`, the `ThrottledClient` in the code will back off and retry automatically.

### Jira API Token

1. Log in to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Click **Create API token**, name it, and copy the value.
3. Your `JIRA_URL` is `https://<your-subdomain>.atlassian.net` — find it in the browser address bar when logged in to Jira.
4. Your `JIRA_USERNAME` is the email address you use to log in to Atlassian.

> The scenario queries project `KAN` by default. If your project uses a different key, change the `jql` string in `examples/jira_scenario_II.py` at line ~292.

---

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` in any text editor and set:

```dotenv
ANTHROPIC_API_KEY=sk-ant-api03-...          # from console.anthropic.com
JIRA_URL=https://your-subdomain.atlassian.net
JIRA_USERNAME=your.email@example.com
JIRA_API_TOKEN=ATATT3x...                   # from id.atlassian.com
```

> **Never commit `.env` to git.** It is already listed in `.gitignore`.

---

## Running the Flagship Scenario

```bash
python examples/jira_scenario_II.py
```

The script will:

1. Connect to Jira and fetch the 5 most recent bugs in the `KAN` project.
2. The Bug Analyst agent translates them into a numbered repro script.
3. The Playwright agent opens a real Chromium browser and executes the steps live.
4. A TypeScript `.spec.ts` test file is written to `output/tests/greenkart.spec.ts`.

Expected runtime: **5–15 minutes** (the `ThrottledClient` paces API calls to stay within the free-tier 30k token/min limit).

---

## Running Other Examples

```bash
# Basic Claude conversation
python examples/text_messaging.py

# Agent with image input
python examples/multimodal_messaging.py

# Two agents taking turns
python examples/round_robin_agents.py

# Human in the loop
python examples/round_robin_with_human.py

# Web automation with screenshots
python examples/multimodal_web_surfer.py

# Agents with tools
python examples/tooling_example.py
```

Only `ANTHROPIC_API_KEY` is required for the examples above. The Jira credentials are only needed for `jira_scenario.py` and `jira_scenario_II.py`.

---

## Project Structure

```
agenticAI/
├── examples/
│   ├── jira_scenario_II.py       ← flagship: Jira → Playwright → .spec.ts
│   ├── jira_scenario.py
│   ├── demo.py                   ← project setup validator
│   ├── text_messaging.py
│   ├── multimodal_messaging.py
│   ├── round_robin_agents.py
│   ├── round_robin_with_human.py
│   ├── state_saving.py
│   ├── selector_group_chat.py
│   ├── multimodal_web_surfer.py
│   └── tooling_example.py
├── scripts/                      ← development & diagnostic utilities
│   ├── diagnose_agents.py        ← verify agent + workbench wiring
│   ├── diagnose_jira.py          ← verify Jira MCP connectivity
│   ├── minimal_agent_test.py     ← minimal two-agent smoke run
│   ├── test_bug_analyst.py       ← isolated Bug Analyst agent run
│   ├── test_jira_connection.py   ← basic Jira connection check
│   ├── test_kan_access.py        ← KAN project access check
│   ├── test_focused_jira_access.py
│   ├── test_improved_jira_access.py
│   └── test_improved_search.py
├── assets/
│   ├── images/
│   └── prompts/
│       ├── bug_analyst_prompt.txt        ← system prompt for the Bug Analyst agent
│       └── playwright_analyst_prompt.txt ← system prompt for the Playwright agent
├── src/agentic_ai/
│   ├── config.py                 ← model names, path helpers
│   └── utils.py                  ← shared utilities (retry, env helpers)
├── tests/                        ← pytest unit tests
│   ├── test_jira_scenario.py
│   └── test_utils.py
├── output/
│   └── tests/
│       └── greenkart.spec.ts     ← generated test file (created at runtime)
├── .env.example                  ← copy this to .env and fill in your keys
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**`ANTHROPIC_API_KEY not found`**
Ensure `.env` is in the project root and you are running the script from the project root directory.

**`429 RateLimitError` not recovering**
The `ThrottledClient` retries up to 6 times with exponential backoff. If it still fails, your API quota for the minute is exhausted — wait 60 seconds and rerun.

**Jira returns no bugs**
Verify your `JIRA_URL` ends with `.atlassian.net` (no trailing slash) and that the project key `KAN` exists. Check `JIRA_USERNAME` matches your Atlassian login email exactly.

**`npx: command not found`**
Install Node.js from [nodejs.org](https://nodejs.org) (LTS version). `npx` is bundled with `npm` which ships with Node.

**`uvx: command not found`**
Run `pip install uv` and then retry.

---

## License

MIT — see [LICENSE](LICENSE) for details.
