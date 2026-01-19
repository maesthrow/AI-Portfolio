"""
Tool wrappers for plan execution.

Provides clean interfaces for both legacy tools (graph_query, portfolio_search)
and new specialized tools (get_company_projects, get_project_details, etc.)
"""
# Legacy tools (kept for backward compatibility)
from .graph_query_tool import execute_graph_query
from .portfolio_search_tool import execute_portfolio_search

# New specialized tools
from .schemas import ToolResult, TOOL_GET_COMPANY_PROJECTS, TOOL_GET_PROJECT_DETAILS, TOOL_GET_TECHNOLOGIES, TOOL_SEARCH_PORTFOLIO
from .company_tools import get_company_projects
from .project_tools import get_project_details
from .technology_tools import get_technologies
from .search_tools import search_portfolio
from .tool_registry import execute_tool, get_tools_description, get_tool_names, is_valid_tool, TOOL_REGISTRY

__all__ = [
    # Legacy tools
    "execute_graph_query",
    "execute_portfolio_search",
    # New specialized tools
    "ToolResult",
    "get_company_projects",
    "get_project_details",
    "get_technologies",
    "search_portfolio",
    # Tool registry
    "execute_tool",
    "get_tools_description",
    "get_tool_names",
    "is_valid_tool",
    "TOOL_REGISTRY",
    # Tool name constants
    "TOOL_GET_COMPANY_PROJECTS",
    "TOOL_GET_PROJECT_DETAILS",
    "TOOL_GET_TECHNOLOGIES",
    "TOOL_SEARCH_PORTFOLIO",
]
