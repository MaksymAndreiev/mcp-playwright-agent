import os
import logging
import google.cloud.logging  # Розкоментуйте, якщо хочете красиві логи в хмарі
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from mcp import StdioServerParameters

from mcp_playwright_agent.prompt import ROOT_AGENT_INSTRUCTION
from mcp_playwright_agent.tools import get_client_edi, get_customer_credentials, get_current_date

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_auth_token(url):
    if "localhost" in url or "127.0.0.1" in url:
        return None

    from urllib.parse import urlparse
    parsed = urlparse(url)
    audience = f"{parsed.scheme}://{parsed.netloc}"

    try:
        auth_req = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(auth_req, audience)
    except Exception as e:
        return os.environ.get("ID_TOKEN")


mcp_url = os.environ.get("MCP_SERVER_URL")
if not mcp_url:
    raise ValueError("MCP_SERVER_URL environment variable is not set!")

audience = mcp_url.replace("/sse", "").replace("/mcp", "")
token = get_auth_token(audience)

headers = {}
if token:
    headers["Authorization"] = f"Bearer {token}"

MCP_toolset_cloud = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_url,
        headers=headers,
        timeout=120
    ),
    tool_filter=[
        'navigate',
        'click',
        'fill',
        'snapshot',
        'hover',
        'set_viewport',
        'set_checked',
        'fill_table_row',
        'get_current_date',
        'get_client_edi',
        'get_customer_credentials'
    ],
    errlog=logger
)

MCP_toolset_local = MCPToolset(
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
        'browser_press_key',
        'browser_handle_dialog',
        'browser_evaluate',
        'browser_resize'
    ],
    errlog=None
)

root_agent = Agent(
    name="mcp_playwright_agent",
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    description="Agent that automates browser actions to retrieve EDI and credentials.",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[MCP_toolset_local, get_client_edi, get_customer_credentials, get_current_date],
)
