from google.adk.agents import Agent

from mcp_playwright_agent.prompt import ROOT_AGENT_INSTRUCTION
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters

root_agent = Agent(
    name="mcp_playwright_agent",
    model="gemini-2.5-flash",
    description="...",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=[
                        "-y",
                        "@playwright/mcp@latest",
                    ],
                ),
                timeout=30
            ),
            tool_filter=[
                'browser_navigate',
                'browser_screenshot',
                'browser_click',
                'browser_fill_form',
                'browser_snapshot',
                'browser_hover',
                'browser_press_key'
            ]
        )
    ],
)
