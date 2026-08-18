import os
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agents import SubAgent
from instructions import RESEARCH_PLANNER, RESEARCH_PLAN_AUDITOR, RESEARCH_PLAN_REVISER, SUBAGENT_SPAWNER, \
    LEAD_RESEARCHER, RESEARCH_WRITER
from model import ResearchTaskPlan, ResearchTaskPlanReflection, SubAgentsSpawn, SubAgentConfig, \
    FinancialMarketResearchAssistantResponse


class FinancialMarketResearchAssistant:
    def __init__(self, base_llm: BaseChatModel, audit_llm: BaseChatModel | None, tools: list[BaseTool], max_agents: int=50):
        self.research_query = None
        self.base_llm = base_llm
        self.audit_llm = audit_llm if audit_llm else base_llm
        self.tool_map = {tool.name: tool for tool in tools} if tools else None
        self.available_tool_descriptions = self._get_available_tool_descriptions()
        self.max_agents = max_agents
        self.session_messages: list[BaseMessage] = []

    def run(self, research_query: str) -> FinancialMarketResearchAssistantResponse:
        self.research_query = research_query

        research_plan: ResearchTaskPlan = self._plan_reflect_revise_task()

        subagent_spawn: SubAgentsSpawn = self._subagent_spawner(research_plan=research_plan)

        configs: list[SubAgentConfig] = subagent_spawn.subagent_configs

        subagent_messages: list[list[BaseMessage]] = []
        research_contexts: list[str] = []
        for config in configs:
            agent_tools = [self.tool_map[tool_name] for tool_name in config.tools]
            subagent = SubAgent(config=config, llm=self.base_llm, tools=agent_tools)
            response, messages = subagent.run()
            subagent_messages.append(messages)
            research_contexts.append(f"""
                ### Research Context from {config.name}
                
                ## Research Objective
                {config.objective}
                
                ## Research Task
                {config.task}
                
                ## Research Finding
                {response.content}
            """)

            self.session_messages.append(response)

        joined_research_context = "\n\n".join(research_contexts)
        synthesized_response: AIMessage = self.base_llm.invoke([
            SystemMessage(content=LEAD_RESEARCHER),
            HumanMessage(content=f"""
            **Research Query**
            {research_query}

            **Research Contexts**
            {joined_research_context}
            """)
        ])

        synthesized_response_content = self._prepare_text_content(synthesized_response)

        final_report = self.base_llm.invoke([
            SystemMessage(content=RESEARCH_WRITER),
            HumanMessage(content=f"""
                ***Contexts***
                
                **Synthesized Research**
                {synthesized_response_content}
                
                **Research Query**
                {self.research_query}
                
                ***Task***: Write the final research report answering the user's research query. 
            """)
        ])

        final_report_content = self._prepare_text_content(final_report)

        return FinancialMarketResearchAssistantResponse(
            content_text=final_report_content,
            research_plan=research_plan,
            subagent_spawn=subagent_spawn,
            subagent_configs=subagent_spawn.subagent_configs,
            subagent_messages=subagent_messages,
            session_messages=self.session_messages
        )

    def _plan_reflect_revise_task(self)->ResearchTaskPlan:
        planner = self.base_llm.with_structured_output(ResearchTaskPlan)
        planner_message = [
            SystemMessage(content=RESEARCH_PLANNER),
            HumanMessage(content=f"""
            **Contexts**
            - User Research Query: {self.research_query}
            - Current Date: {self._get_current_date()}            
            - Available Tools: {self.available_tool_descriptions}
            
            ***Task**: Prepare research task plan.
            """)
        ]
        draft_plan: ResearchTaskPlan | BaseModel = planner.invoke(planner_message)
        self.session_messages.extend(planner_message)
        self.session_messages.append(AIMessage(content=f"draft_plan: {draft_plan.model_dump_json()}"))

        plan_reflector = self.audit_llm.with_structured_output(ResearchTaskPlanReflection)
        plan_reflector_message = [
            SystemMessage(content=RESEARCH_PLAN_AUDITOR),
            HumanMessage(content=f"""
            **Context**:
                - User Research Query: {self.research_query}
                - Current Date: {self._get_current_date()}
                - Available Tools: {self.available_tool_descriptions}
                - Research Plan: {draft_plan.model_dump_json()}
            
            **Task**: Prepare research plan reflection.
            """)
        ]
        plan_reflection: ResearchTaskPlanReflection | BaseModel = plan_reflector.invoke(plan_reflector_message)
        self.session_messages.extend(plan_reflector_message)
        self.session_messages.append(AIMessage(content=f"plan_reflection: {plan_reflection.model_dump_json()}"))

        plan_reviser = self.base_llm.with_structured_output(ResearchTaskPlan)
        plan_reviser_message = [
            SystemMessage(content=RESEARCH_PLAN_REVISER),
            HumanMessage(content=f"""
            **Context**:
                - User Research Query: {self.research_query}
                - Current Date: {self._get_current_date()}
                - Available Tools: {self.available_tool_descriptions}
                - Research Plan: {draft_plan.model_dump_json()}
                - Research Plan Reflection: {plan_reflection.model_dump_json()}
            
            **Task**: Prepare revised research plan.
            """)
        ]
        revised_plan: ResearchTaskPlan | BaseModel = plan_reviser.invoke(plan_reviser_message)
        self.session_messages.extend(plan_reviser_message)
        self.session_messages.append(AIMessage(content=f'revised_plan: {revised_plan.model_dump_json()}'))

        return revised_plan

    def _subagent_spawner(self, research_plan: ResearchTaskPlan, state: list[BaseMessage] | None=None) -> SubAgentsSpawn:
        spawner = self.base_llm.with_structured_output(SubAgentsSpawn)
        messages: list[BaseMessage] = state if state else [
            SystemMessage(
                content=SUBAGENT_SPAWNER),
            HumanMessage(
                content=f"""
                **Context**:
                # User Research Query
                    {self.research_query}
                    
                # Available Tools
                    {self.available_tool_descriptions}
                
                # Research Plan
                    {research_plan.model_dump_json()}

                **Task**: Prepare subagent spawn plan.
                """)
        ]
        self.session_messages.extend(messages)
        subagent_spawn: SubAgentsSpawn | BaseModel = spawner.invoke(messages)
        self.session_messages.append(AIMessage(content=f'subagent_spawn: {subagent_spawn.model_dump_json()}'))

        return subagent_spawn

    @staticmethod
    def _prepare_text_content(message: AIMessage) -> str:
        content = message.content
        if isinstance(content, list) and len(content) > 0 and all(isinstance(item, dict) for item in content):
            text_item = next((item for item in content if item.get('type') == 'text'), None)
            return text_item.get('text', '') if text_item else ''
        return str(content)

    def _get_available_tool_descriptions(self)->str:
        tool_descriptions: list[str] = []
        for i, tool in enumerate(self.tool_map.values()):
            tool_descriptions.append(f"""
            # Tool: {tool.name}
            # Description: {tool.description}
            # Args: {tool.args}
            """)
        return "\n".join(tool_descriptions)

    @staticmethod
    def _get_current_date():
        return datetime.now().date().isoformat()

