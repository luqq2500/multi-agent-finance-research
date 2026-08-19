import os
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from agents import SubAgent
from instructions import RESEARCH_PLANNER, RESEARCH_PLAN_AUDITOR, RESEARCH_SYNTHESIZER, SUBAGENT_RESEARCHER, RESEARCH_REPORT_WRITER, RESEARCH_REPORT_AUDITOR
from model import FinancialMarketResearchAssistantResponse, ResearchTasks, ResearchTasksCritique, ResearchReport, ResearchReportAudit


class FinancialMarketResearchAssistant:
    def __init__(self, base_llm: BaseChatModel, audit_llm: BaseChatModel | None, tools: list[BaseTool], plan_research_max_loop: int=2, max_agents: int=50, write_report_max_loop: int=2):
        self.research_query = None
        self.base_llm = base_llm
        self.audit_llm = audit_llm if audit_llm else base_llm
        self.tool_map = {tool.name: tool for tool in tools} if tools else None
        self.available_tool_descriptions = self._get_available_tool_system_instruction()
        self.plan_research_max_loop = plan_research_max_loop
        self.write_report_max_loop = write_report_max_loop
        self.max_agents = max_agents
        self.session_messages: list[BaseMessage] = []

    def run(self, research_query: str) -> FinancialMarketResearchAssistantResponse:
        self.research_query = research_query

        tasks, planner_msg, plan_auditor_msg = self.plan_research_task()

        subagent_messages: list[list[BaseMessage]] = []
        subagent_contexts: list[str] = []
        for task in tasks.get_list_of_research_task():
            agent_tools = [self.tool_map[tool_name] for tool_name in task.get_list_of_tools()]

            subagent = SubAgent(llm=self.base_llm, tools=agent_tools)

            response, messages = subagent.run(initial_messages=[
                SystemMessage(content=SUBAGENT_RESEARCHER),
                HumanMessage(content=task.get_message())
            ])

            subagent_contexts.append(f"{response.content}")
            subagent_messages.append(messages)

        subagent_contexts_text = "\n".join(subagent_contexts)

        synthesized_response: AIMessage = self.base_llm.invoke([
            SystemMessage(content=RESEARCH_SYNTHESIZER),
            HumanMessage(content=f"""
                    **Research Query**
                    {self.research_query}
                    
                    **Research Findings**
                    {subagent_contexts_text}
                    """)
        ])
        synthesized_text = self._prepare_text_content(synthesized_response)

        research_report, writer_msg, report_auditor_msg = self.write_research_report(synthesized_text)

        return FinancialMarketResearchAssistantResponse(
            research_query=self.research_query,
            research_tasks=tasks,
            research_planner_messages=planner_msg,
            research_plan_auditor_messages=plan_auditor_msg,
            subagent_messages=subagent_messages,
            synthesized_research=synthesized_text,
            report_writer_messages=writer_msg,
            report_auditor_messages=report_auditor_msg,
            research_report=research_report
        )

    def plan_research_task(self):
        planner = self.base_llm.with_structured_output(ResearchTasks)
        auditor = self.audit_llm.with_structured_output(ResearchTasksCritique)

        planner_msg: list[BaseMessage] = [
            SystemMessage(content=RESEARCH_PLANNER + self._get_available_tool_system_instruction()),
            HumanMessage(content=f"**Research Query**\n{self.research_query}")
        ]
        auditor_msg: list[BaseMessage] = [
            SystemMessage(content=RESEARCH_PLAN_AUDITOR + self._get_available_tool_system_instruction())
        ]

        for loop in range(self.plan_research_max_loop):
            tasks: ResearchTasks = planner.invoke(planner_msg)
            planner_msg.append(AIMessage(content=tasks.get_message()))
            auditor_msg.append(HumanMessage(content=tasks.get_message()))

            critique: ResearchTasksCritique = auditor.invoke(auditor_msg)
            if not critique.require_improvement:
                return tasks, planner_msg, auditor_msg

            auditor_msg.append(AIMessage(content=critique.get_message()))
            planner_msg.append(HumanMessage(content=critique.get_message()))

        tasks = planner.invoke(planner_msg)
        return tasks, planner_msg, auditor_msg

    def write_research_report(self, synthesized_research: str):
        writer = self.base_llm.with_structured_output(ResearchReport)
        auditor = self.audit_llm.with_structured_output(ResearchReportAudit)

        writer_msg: list[BaseMessage] = [
            SystemMessage(content=RESEARCH_REPORT_WRITER),
            HumanMessage(content=f"\n**Research Query**\n{self.research_query}\n**Synthesized Research** \n{synthesized_research}"),
        ]
        auditor_msg: list[BaseMessage] = [
            SystemMessage(content=RESEARCH_REPORT_AUDITOR)
        ]

        for loop in range(self.write_report_max_loop):
            report = writer.invoke(writer_msg)
            writer_msg.append(AIMessage(content=report.get_message()))
            auditor_msg.append(HumanMessage(content=f"\n### Research Query\n{self.research_query}\n### Synthesized Research\n{synthesized_research}" + report.get_message()))

            audit: ResearchReportAudit = auditor.invoke(auditor_msg)
            if not audit.require_improvement:
                return report, writer_msg, auditor_msg

            auditor_msg.append(AIMessage(content=audit.get_message()))
            writer_msg.append(HumanMessage(content=audit.get_message()))

        report: ResearchReport = writer.invoke(writer_msg)
        return report, writer_msg, auditor_msg

    @staticmethod
    def _prepare_text_content(message: AIMessage) -> str:
        content = message.content
        if isinstance(content, list) and len(content) > 0 and all(isinstance(item, dict) for item in content):
            text_item = next((item for item in content if item.get('type') == 'text'), None)
            return text_item.get('text', '') if text_item else ''
        return str(content)

    def _get_available_tool_system_instruction(self)->str:
        tool_descriptions: list[str] = []
        for i, tool in enumerate(self.tool_map.values()):
            tool_descriptions.append(f"""
            # Tool: {tool.name}
            # Description: {tool.description}
            # Args: {tool.args}
            """)

        tool_descriptions_join = "\n".join(tool_descriptions)
        return f"""
        ### AVAILABLE TOOLS
        
        {tool_descriptions_join}
        """
    @staticmethod
    def _get_current_date():
        return datetime.now().date().isoformat()

