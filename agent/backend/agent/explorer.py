"""ReAct explorer agent factory (LangGraph)."""

from __future__ import annotations

from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from agent.memory_agent import build_llm
from agent.prompts import build_explorer_prompt, explorer_reasoning_effort


def create_explorer_agent(
    tools: list[BaseTool],
    explorer_model: str,
    memory_context: str,
    max_steps: int = 50,
    max_human_assists: int = 0,
):
    """Build a LangGraph ReAct agent with OpenRouter LLM and the game tools."""
    llm = build_llm(explorer_model, reasoning_effort=explorer_reasoning_effort(explorer_model))
    prompt = build_explorer_prompt(
        explorer_model,
        memory_context,
        max_steps=max_steps,
        max_human_assists=max_human_assists,
    )
    return create_react_agent(llm, tools, prompt=prompt)
