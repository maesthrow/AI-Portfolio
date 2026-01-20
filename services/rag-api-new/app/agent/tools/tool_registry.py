"""
Tool Registry - central dispatch for all specialized tools.

Provides execute_tool function that routes tool calls to the
appropriate specialized tool based on tool name.
"""
from __future__ import annotations

import logging
from typing import Any

from .schemas import (
    ToolResult,
    TOOL_GET_COMPANY_PROJECTS,
    TOOL_GET_PROJECT_DETAILS,
    TOOL_GET_TECHNOLOGIES,
    TOOL_GET_CONTACTS,
    TOOL_SEARCH_PORTFOLIO,
    # New tools (ТЗ v3)
    TOOL_GET_WORK_HISTORY,
    TOOL_GET_COMPANY_ACHIEVEMENTS,
    TOOL_GET_PROJECT_ACHIEVEMENTS,
    TOOL_GET_PROJECT_SUMMARY,
    TOOL_GET_COMPANY_SUMMARY,
)
from .company_tools import get_company_projects
from .project_tools import get_project_details
from .technology_tools import get_technologies
from .contact_tools import get_contacts
from .search_tools import search_portfolio
# New tools (ТЗ v3)
from .history_tools import get_work_history
from .achievements_tools import get_company_achievements, get_project_achievements
from .summary_tools import get_project_summary, get_company_summary

logger = logging.getLogger(__name__)


# Tool registry with metadata for Planner prompt
TOOL_REGISTRY = {
    TOOL_GET_COMPANY_PROJECTS: {
        "function": get_company_projects,
        "description": "Get projects for a specific company",
        "parameters": {
            "company_name": {
                "type": "string",
                "required": True,
                "description": "Company name or slug (aston, spargo, alor, etc.)",
            },
            "include_achievements": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include project achievements",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of projects",
            },
        },
        "examples": [
            "проекты в Aston",
            "над чем работал в Спарго",
            "чем занимался в ALOR",
        ],
    },
    TOOL_GET_PROJECT_DETAILS: {
        "function": get_project_details,
        "description": "Get detailed information about a specific project",
        "parameters": {
            "project_name": {
                "type": "string",
                "required": True,
                "description": "Project name or slug (t2, ai-portfolio, alor-broker, etc.)",
            },
            "include_technologies": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include technology list",
            },
            "include_achievements": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include achievements",
            },
        },
        "examples": [
            "расскажи о проекте t2",
            "какой стек в AI-Portfolio",
            "детали проекта ALOR Broker",
        ],
    },
    TOOL_GET_TECHNOLOGIES: {
        "function": get_technologies,
        "description": "Get technologies by project or by category",
        "parameters": {
            "project_name": {
                "type": "string",
                "required": False,
                "description": "Project name to get technologies for",
            },
            "category": {
                "type": "string",
                "required": False,
                "description": "Category: language, database, ml_framework, framework, tool, cloud",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of technologies",
            },
        },
        "examples": [
            "какие языки знает",
            "какие базы данных использует",
            "технологии в проекте t2",
            "ML-фреймворки",
        ],
    },
    TOOL_GET_CONTACTS: {
        "function": get_contacts,
        "description": "Get contact information (email, telegram, github, etc.)",
        "parameters": {
            "kind": {
                "type": "string",
                "required": False,
                "description": "Contact kind filter: email, telegram, github, linkedin, hh, leetcode",
            },
        },
        "examples": [
            "как связаться",
            "контакты",
            "есть гитхаб?",
            "telegram",
        ],
    },
    TOOL_SEARCH_PORTFOLIO: {
        "function": search_portfolio,
        "description": "Semantic search across portfolio data",
        "parameters": {
            "query": {
                "type": "string",
                "required": True,
                "description": "Search query text",
            },
            "company_filter": {
                "type": "string",
                "required": False,
                "description": "Filter by company slug",
            },
            "project_filter": {
                "type": "string",
                "required": False,
                "description": "Filter by project slug",
            },
            "type_filter": {
                "type": "array",
                "required": False,
                "description": "Filter by document types: project, technology, achievement",
            },
            "k": {
                "type": "integer",
                "default": 8,
                "description": "Number of results",
            },
        },
        "examples": [
            "где применял RAG",
            "расскажи об ML-проектах",
            "опыт работы с нейросетями",
        ],
    },
    # ========== NEW TOOLS (ТЗ v3) ==========
    TOOL_GET_WORK_HISTORY: {
        "function": get_work_history,
        "description": "Get work history (list of companies with roles and periods)",
        "parameters": {
            "include_current": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include current workplace",
            },
            "order": {
                "type": "string",
                "default": "chronological_desc",
                "description": "Sort order: chronological_desc (latest first) or chronological_asc",
            },
        },
        "examples": [
            "где работал ранее",
            "предыдущие места работы",
            "до этого где работал",
        ],
    },
    TOOL_GET_COMPANY_ACHIEVEMENTS: {
        "function": get_company_achievements,
        "description": "Get achievements for a specific company",
        "parameters": {
            "company_name": {
                "type": "string",
                "required": True,
                "description": "Company name or slug",
            },
        },
        "examples": [
            "достижения в Спарго",
            "результаты в АЛОР",
            "чего добился в Aston",
        ],
    },
    TOOL_GET_PROJECT_ACHIEVEMENTS: {
        "function": get_project_achievements,
        "description": "Get achievements for a specific project",
        "parameters": {
            "project_name": {
                "type": "string",
                "required": True,
                "description": "Project name or slug",
            },
        },
        "examples": [
            "достижения в t2",
            "результаты AI-Portfolio",
            "чего добился в проекте",
        ],
    },
    TOOL_GET_PROJECT_SUMMARY: {
        "function": get_project_summary,
        "description": "Get project summary for 'what is X' questions",
        "parameters": {
            "project_name": {
                "type": "string",
                "required": True,
                "description": "Project name or slug",
            },
        },
        "examples": [
            "что такое t2",
            "что за проект AI-Portfolio",
            "расскажи о проекте",
        ],
    },
    TOOL_GET_COMPANY_SUMMARY: {
        "function": get_company_summary,
        "description": "Get company summary for 'what is company X' questions",
        "parameters": {
            "company_name": {
                "type": "string",
                "required": True,
                "description": "Company name or slug",
            },
        },
        "examples": [
            "что за компания АЛОР",
            "расскажи о компании Aston",
            "что за Спарго",
        ],
    },
}


def execute_tool(tool_name: str, params: dict[str, Any]) -> ToolResult:
    """
    Execute a tool by name with given parameters.

    Args:
        tool_name: Name of the tool to execute
        params: Parameters to pass to the tool

    Returns:
        ToolResult from the tool execution

    Raises:
        ValueError: If tool_name is not registered
    """
    if tool_name not in TOOL_REGISTRY:
        logger.error("Unknown tool: %s", tool_name)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=tool_name,
            params=params,
            error=f"Unknown tool: {tool_name}",
        )

    tool_config = TOOL_REGISTRY[tool_name]
    tool_func = tool_config["function"]

    # Filter params to only include valid parameters
    valid_params = {}
    for param_name, param_config in tool_config["parameters"].items():
        if param_name in params:
            valid_params[param_name] = params[param_name]
        elif "default" in param_config:
            valid_params[param_name] = param_config["default"]
        elif param_config.get("required", False):
            logger.warning(
                "Missing required parameter '%s' for tool '%s'",
                param_name,
                tool_name,
            )

    logger.info(
        "Executing tool '%s' with params: %s",
        tool_name,
        {k: v for k, v in valid_params.items() if k != "query" or len(str(v)) < 50},
    )

    try:
        result = tool_func(**valid_params)
        return result
    except Exception as e:
        logger.error("Tool '%s' execution error: %s", tool_name, e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=tool_name,
            params=params,
            error=str(e),
        )


def get_tools_description() -> str:
    """
    Generate tools description for Planner prompt.

    Returns formatted description of all available tools
    with their parameters and examples.
    """
    lines = ["Available tools:\n"]

    for i, (tool_name, config) in enumerate(TOOL_REGISTRY.items(), 1):
        lines.append(f"{i}. {tool_name}")
        lines.append(f"   Description: {config['description']}")

        # Parameters
        params_list = []
        for param_name, param_config in config["parameters"].items():
            param_type = param_config.get("type", "string")
            required = param_config.get("required", False)
            desc = param_config.get("description", "")

            if required:
                params_list.append(f"{param_name}: {param_type} (required) - {desc}")
            else:
                default = param_config.get("default", "None")
                params_list.append(f"{param_name}?: {param_type} = {default} - {desc}")

        if params_list:
            lines.append("   Parameters:")
            for param in params_list:
                lines.append(f"     - {param}")

        # Examples
        examples = config.get("examples", [])
        if examples:
            lines.append(f"   Examples: {', '.join(f'\"{e}\"' for e in examples[:3])}")

        lines.append("")

    return "\n".join(lines)


def get_tool_names() -> list[str]:
    """Return list of all available tool names."""
    return list(TOOL_REGISTRY.keys())


def is_valid_tool(tool_name: str) -> bool:
    """Check if tool name is valid."""
    return tool_name in TOOL_REGISTRY
