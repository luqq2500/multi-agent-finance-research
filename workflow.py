from datetime import datetime
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel

from agents import SubAgent
from instructions import RESEARCH_PLANNER, RESEARCH_PLAN_AUDITOR, RESEARCH_SYNTHESIZER, SUBAGENT_RESEARCHER, RESEARCH_REPORT_WRITER, RESEARCH_REPORT_AUDITOR
from model import FinancialMarketResearchAssistantResponse, ResearchTasks, ResearchTasksCritique, ResearchReport, ResearchReportAudit, ResearchAssistantConfig, ResearchSynthesis


class FinancialMarketResearchAssistant:
    def __init__(self, config: ResearchAssistantConfig):
        self.config = config
        self.base_llm = self.config.base_llm
        self.higher_llm = self.config.upgrade_llm if self.config.upgrade_llm else self.base_llm
        self.tool_map = {tool.name: tool for tool in self.config.tools} if self.config.tools else None
        self.max_planner_loop = self.config.max_planner_loop
        self.max_writer_loop = self.config.max_writer_loop
        self.max_agents = self.config.max_agents
        self.max_agent_loop = self.config.max_agent_loop
        self.session_messages: list[BaseMessage] = []
        self.research_query = None

    def run(self, research_query: str) -> FinancialMarketResearchAssistantResponse:
        self.research_query = research_query

        research_tasks, planner_msg, plan_auditor_msg = self.plan_research_task()

        task_list = research_tasks.get_list_of_research_task()
        if len(task_list) > self.max_agents:
            raise ValueError(f"Plan produced {len(task_list)} tasks, exceeding subagent budget of {self.max_agents}")

        subagent_messages: list[list[BaseMessage]] = []
        subagent_contexts: list[str] = []
        for task in task_list:
            agent_tools = [self.tool_map[tool_name] for tool_name in task.get_list_of_tools() if tool_name in self.tool_map]

            subagent = SubAgent(llm=self.base_llm, tools=agent_tools, max_loop=self.max_agent_loop)

            response, messages = subagent.run(initial_messages=[
                SystemMessage(content=SUBAGENT_RESEARCHER),
                HumanMessage(content=task.get_manifest())
            ])

            subagent_contexts.append(f"{response.content}")
            subagent_messages.append(messages)

        research_synthesis: ResearchSynthesis|BaseModel = self.higher_llm.with_structured_output(ResearchSynthesis).invoke([
            SystemMessage(content=RESEARCH_SYNTHESIZER),
            HumanMessage(content=self.get_research_query_manifest() + research_tasks.get_manifest() + self.get_subagent_contexts_manifest(subagent_contexts))
        ])

        research_report, writer_msg, report_auditor_msg = self.write_research_report(research_synthesis)

        return FinancialMarketResearchAssistantResponse(
            configurations=self.config,
            research_query=self.research_query,
            research_tasks=research_tasks.get_list_of_research_task(),
            planner_messages=planner_msg,
            plan_auditor_messages=plan_auditor_msg,
            subagent_messages=subagent_messages,
            research_synthesis=research_synthesis.research_synthesis,
            writer_messages=writer_msg,
            writer_auditor_messages=report_auditor_msg,
            research_report=research_report.report
        )

    def plan_research_task(self):
        planner = self.base_llm.with_structured_output(ResearchTasks)
        auditor = self.higher_llm.with_structured_output(ResearchTasksCritique)

        planner_msg: list[BaseMessage] = [
            SystemMessage(
                content=RESEARCH_PLANNER + self.config.get_available_tools_manifest() + self.config.get_subagent_budget_manifest() + self.config.get_planner_budget_manifest()
            ),
            HumanMessage(
                content=self.get_research_query_manifest()
            )
        ]
        auditor_msg: list[BaseMessage] = [
            SystemMessage(
                content=RESEARCH_PLAN_AUDITOR + self.config.get_available_tools_manifest() + self.config.get_subagent_budget_manifest() + self.config.get_planner_budget_manifest()
            )
        ]

        for loop in range(self.max_planner_loop):
            tasks: ResearchTasks = planner.invoke(planner_msg)
            planner_msg.append(AIMessage(content=tasks.get_manifest()))
            auditor_msg.append(HumanMessage(content=tasks.get_manifest()))

            critique: ResearchTasksCritique = auditor.invoke(auditor_msg)
            if not critique.require_improvement:
                return tasks, planner_msg, auditor_msg

            auditor_msg.append(AIMessage(content=critique.get_manifest()))
            planner_msg.append(HumanMessage(content=critique.get_manifest()))

        tasks = planner.invoke(planner_msg)
        return tasks, planner_msg, auditor_msg

    def write_research_report(self, research_synthesis: ResearchSynthesis):
        writer = self.base_llm.with_structured_output(ResearchReport)
        auditor = self.higher_llm.with_structured_output(ResearchReportAudit)

        writer_msg: list[BaseMessage] = [
            SystemMessage(
                content=RESEARCH_REPORT_WRITER + self.config.get_writer_budget_manifest()
            ),
            HumanMessage(
                content= self.get_research_query_manifest() + research_synthesis.get_manifest()
            ),
        ]

        auditor_msg: list[BaseMessage] = [
            SystemMessage(
                content=RESEARCH_REPORT_AUDITOR + self.config.get_writer_budget_manifest()
            )
        ]

        for loop in range(self.max_writer_loop):
            report = writer.invoke(writer_msg)
            writer_msg.append(AIMessage(content=report.get_manifest()))
            auditor_msg.append(HumanMessage(content=self.get_research_query_manifest() + research_synthesis.get_manifest() + f"### Draft Report Under Review\n{report.get_manifest()}"))

            audit: ResearchReportAudit = auditor.invoke(auditor_msg)
            if not audit.require_improvement:
                return report, writer_msg, auditor_msg

            auditor_msg.append(AIMessage(content=audit.get_manifest()))
            writer_msg.append(HumanMessage(content=audit.get_manifest()))

        report: ResearchReport = writer.invoke(writer_msg)
        return report, writer_msg, auditor_msg

    def get_research_query_manifest(self):
        return f"""
        ### RESEARCH QUERY
        
        {self.research_query}
        """

    @staticmethod
    def get_subagent_contexts_manifest(subagent_contexts: list[str]) -> str:
        subagent_contexts_manifest = f"### Research Findings\n" + "\n".join(subagent_contexts)
        return subagent_contexts_manifest

    @staticmethod
    def _prepare_text_content(message: AIMessage) -> str:
        content = message.content
        if isinstance(content, list) and len(content) > 0 and all(isinstance(item, dict) for item in content):
            text_item = next((item for item in content if item.get('type') == 'text'), None)
            return text_item.get('text', '') if text_item else ''
        return str(content)

    @staticmethod
    def _get_current_date_manifest():
        return f"""
        **Current Date**: {datetime.now().date().isoformat()}
        """

