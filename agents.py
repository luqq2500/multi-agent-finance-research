from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolCall, ToolMessage
from langchain_core.tools import BaseTool

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
        loop_count = 0

        while loop_count < self.max_loop:

            loop_budget_warning = (self.max_loop - loop_count) == 1
            if loop_budget_warning:
                messages.append(HumanMessage(content='Warning. This is your last session. Do not call any tools. Finalize the next final response.'))

            response: AIMessage = self.llm.invoke(messages)
            messages.append(response)

            if response.tool_calls:
                tool_calls: list[ToolCall] = response.tool_calls
                for tool_call in tool_calls:
                    tool = self.tool_map[tool_call["name"]]
                    tool_message: ToolMessage = tool.invoke(tool_call)
                    messages.append(tool_message)
            else:
                return response, messages

            loop_count+=1

        raise TimeoutError(f"Agent failed to return finalize response after loop budget warning triggered. Max loop: {self.max_loop}, loop count: {loop_count}")

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