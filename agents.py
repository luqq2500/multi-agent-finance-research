from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolCall, ToolMessage
from langchain_core.tools import BaseTool

from instructions import FINALIZE_SUBAGENT_RESEARCH
from model import SubAgentConfig, ResearchTaskPlan


class SubAgent:
    def __init__(self, config: SubAgentConfig, llm: BaseChatModel, tools: Optional[list[BaseTool]], max_loop: int=10):
        self.config = config
        self.base_llm = llm
        self.llm = llm.bind_tools(tools) if tools else llm
        self.tool_map = {tool.name: tool for tool in tools} if tools else None
        self.max_loop = max_loop

    def run(self, state: Optional[list[BaseMessage]]=None):
        messages = self._set_state_messages(state)

        for _ in range(self.max_loop):
            response: AIMessage = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response, messages

            for tool_call in response.tool_calls:
                tool = self.tool_map[tool_call["name"]]
                tool_message: ToolMessage = tool.invoke(tool_call)
                messages.append(tool_message)

        messages.append(HumanMessage(content=FINALIZE_SUBAGENT_RESEARCH))
        final: AIMessage = self.base_llm.invoke(messages)
        messages.append(final)

        return final, messages

    def _set_state_messages(self, state: list[BaseMessage] | None) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        if state:
            messages.extend(state)
        else:
            messages.extend([
                SystemMessage(content=self.config.get_system_instruction()),
                HumanMessage(content=self.config.get_task_instruction())
            ])
        return messages