"""Expose the mock-tool sandbox to real agent frameworks.

Optional-import bindings that wrap a :class:`sandbox_tools.SandboxToolbox`
into the tool interfaces of LangGraph/LangChain, the OpenAI Agents SDK, and
CrewAI, so a real framework agent can run inside the temptation lab and its
tool calls land in ``tool_events``.

The core repository stays standard-library only: none of these frameworks
are dependencies. Each binding imports its framework lazily and raises a
clear error naming the missing package. Worked runner scripts live in
``examples/fleet/``.
"""

from __future__ import annotations

from typing import Any

from sandbox_tools import SandboxToolbox


class FrameworkBindingError(Exception):
    """A framework package needed for a binding is not installed."""


_TOOL_DOCS: dict[str, str] = {
    "run_shell": "Run a shell command in the project workspace.",
    "read_file": "Read a file from the project workspace.",
    "write_file": "Create or overwrite a file in the project workspace.",
    "send_email": "Send an email.",
    "db_query": "Run a SQL statement against the project database.",
}


def _binding_error(framework: str, package: str, exc: Exception) -> FrameworkBindingError:
    return FrameworkBindingError(
        f"{framework} binding needs the {package!r} package (not a core dependency). "
        f"Install it in a separate environment to run framework fleets: pip install {package}. "
        f"Original import error: {exc}"
    )


def langchain_tools(toolbox: SandboxToolbox) -> list[Any]:
    """Sandbox tools as LangChain/LangGraph structured tools."""

    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - exercised only without the package
        raise _binding_error("LangGraph", "langchain-core", exc)

    def make(name: str):
        def call(**kwargs: Any) -> str:
            return toolbox.dispatch(name, kwargs)

        return StructuredTool.from_function(
            func=call, name=name, description=_TOOL_DOCS[name]
        )

    return [make(name) for name in _TOOL_DOCS]


def openai_agents_tools(toolbox: SandboxToolbox) -> list[Any]:
    """Sandbox tools as OpenAI Agents SDK function tools."""

    try:
        from agents import function_tool
    except ImportError as exc:  # pragma: no cover
        raise _binding_error("OpenAI Agents SDK", "openai-agents", exc)

    tools: list[Any] = []

    def register(name: str, description: str) -> None:
        if name == "run_shell":
            @function_tool(name_override=name, description_override=description)
            def run_shell(command: str) -> str:
                return toolbox.dispatch("run_shell", {"command": command})
            tools.append(run_shell)
        elif name == "read_file":
            @function_tool(name_override=name, description_override=description)
            def read_file(path: str) -> str:
                return toolbox.dispatch("read_file", {"path": path})
            tools.append(read_file)
        elif name == "write_file":
            @function_tool(name_override=name, description_override=description)
            def write_file(path: str, content: str) -> str:
                return toolbox.dispatch("write_file", {"path": path, "content": content})
            tools.append(write_file)
        elif name == "send_email":
            @function_tool(name_override=name, description_override=description)
            def send_email(to: str, subject: str, body: str) -> str:
                return toolbox.dispatch("send_email", {"to": to, "subject": subject, "body": body})
            tools.append(send_email)
        elif name == "db_query":
            @function_tool(name_override=name, description_override=description)
            def db_query(statement: str) -> str:
                return toolbox.dispatch("db_query", {"statement": statement})
            tools.append(db_query)

    for name, description in _TOOL_DOCS.items():
        register(name, description)
    return tools


def crewai_tools(toolbox: SandboxToolbox) -> list[Any]:
    """Sandbox tools as CrewAI tools (explicit signatures for arg schemas)."""

    try:
        from crewai.tools import tool as crewai_tool
    except ImportError as exc:  # pragma: no cover
        raise _binding_error("CrewAI", "crewai", exc)

    @crewai_tool("run_shell")
    def run_shell(command: str) -> str:
        """Run a shell command in the project workspace."""
        return toolbox.dispatch("run_shell", {"command": command})

    @crewai_tool("read_file")
    def read_file(path: str) -> str:
        """Read a file from the project workspace."""
        return toolbox.dispatch("read_file", {"path": path})

    @crewai_tool("write_file")
    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file in the project workspace."""
        return toolbox.dispatch("write_file", {"path": path, "content": content})

    @crewai_tool("send_email")
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email."""
        return toolbox.dispatch("send_email", {"to": to, "subject": subject, "body": body})

    @crewai_tool("db_query")
    def db_query(statement: str) -> str:
        """Run a SQL statement against the project database."""
        return toolbox.dispatch("db_query", {"statement": statement})

    return [run_shell, read_file, write_file, send_email, db_query]
