from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from instructions import SUBAGENT_RESEARCHER

def get_list_str_messages(items: list[str]) -> str:
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

class ResearchModel(BaseModel, ABC):
    @abstractmethod
    def get_manifest(self)->str:
        pass

@dataclass
class ResearchAssistantConfig:
    base_llm: BaseChatModel
    upgrade_llm: BaseChatModel
    tools: list[BaseTool]
    max_planner_loop: int
    max_agents: int
    max_agent_loop: int
    max_writer_loop: int

    def get_base_model_id(self):
        return self.get_chat_model_id(self.base_llm)

    def get_upgrade_model_id(self):
        return self.get_chat_model_id(self.upgrade_llm)

    def get_available_tools_manifest(self) -> str:
        tool_descriptions: list[str] = []
        for i, tool in enumerate(self.tool_map.values()):
            tool_descriptions.append(f"""
            # Tool: {tool.name}
            # Description: {tool.description}
            # Args: {tool.args}
            """)

        tool_descriptions_join = "\n".join(tool_descriptions)
        return f"""
        ### AVAILABLE RESEARCH TOOLS

        {tool_descriptions_join}
        """

    def get_planner_budget_manifest(self):
        return f"""
        ***LOOP BUDGET***: {self.max_planner_loop}
        """

    def get_subagent_budget_manifest(self):
        return f"""       
        ***NUMBER OF SUBAGENTS BUDGET: *** {self.max_agents}

        ***EACH SUBAGENT LOOP BUDGET*** {self.max_agent_loop}
        
        ***TOTAL TOOL-CALL CAPACITY ACROSS THE WHOLE PLAN (subagents x loop budget — an outer ceiling, NOT a target to fill):*** {self.max_agents*self.max_agent_loop}
        """

    def get_writer_budget_manifest(self):
        return f"""
        ***LOOP BUDGET: ***{self.max_writer_loop} 
        """


    @staticmethod
    def get_chat_model_id(model: BaseChatModel) -> str:
        # 1. Check for standard variants across most providers
        for attr in ["model_name", "model", "model_id", "deployment_name"]:
            if hasattr(model, attr):
                val = getattr(model, attr)
                if isinstance(val, str) and val:
                    return val

        # 2. Check if it's tucked inside provider configuration objects
        if hasattr(model, "client") and hasattr(model.client, "model"):
            return model.client.model

        # 3. Last resort fallback to class name
        return model.__class__.__name__

class ResearchTask(ResearchModel):
    task: str = Field(description="**One** specific research task — a single scope of investigation for a single isolated agent. "
                                  "Name the targeted entity and topics and the subject to investigate."
                                  "This must be one task, not several joined by 'and' or by a numbered sequence.")
    success_criteria: list[str] = Field(description="A list of explicit checklist items or targets that must be met to consider this task complete.")
    required_expertise: list[str] = Field(description="A list of specific expertises needed to execute tasks.")
    tools: list[str] = Field(description="List of necessary tools to help execute research task.")
    tool_use_strategy: list[str] = Field(description="A step-by-step blueprint of tool use, detailing how the selected tools will be utilized, including exact arguments and parameters.")
    task_boundary: list[str] = Field(description="Strict out-of-scope boundaries. Explicitly lists what should NOT be researched or done during this task.")

    def get_manifest(self) ->str:
        return (
        f"""
        ### RESEARCH TASK
                
        **Task**: {self.task}
        
        **Success Criteria**: 
        {get_list_str_messages(self.success_criteria)}
        
        **Required Expertise**: {self.required_expertise}
        
        **Tools**:
        {get_list_str_messages(self.tools)}
        
        **Tool Use Strategy**:
        {get_list_str_messages(self.tool_use_strategy)}
        
        **Task Boundary**:
        {get_list_str_messages(self.task_boundary)}        
        """)

    def get_list_of_tools(self)->list[str]:
        return self.tools

class ResearchTasks(ResearchModel):
    research_tasks: list[ResearchTask] = Field(description="Research tasks")

    def get_manifest(self) ->str:
        research_tasks = "\n".join(f"## Research Task {i+1}\n {task.get_manifest()}" for i, task in enumerate(self.research_tasks))
        return f"""
        ### RESEARCH TASKS
        
        {research_tasks}
        """

    def get_list_of_research_task(self)->list[ResearchTask]:
        return self.research_tasks

class ResearchTasksCritique(ResearchModel):
    reflection: list[str] = Field(description="Objective research tasks critique reflection.")
    critique: list[str] = Field(description="Research task's constructive critiques.")
    improvement: list[str] = Field(description="Actionable, specific steps or modifications needed to resolve the issues identified in the critique.")
    require_improvement: bool = Field(description="Set to True if any critical issues or necessary improvements are found. Set to False only if the tasks are completely ready to execute.")

    def get_manifest(self) ->str:
        return f"""
        ### RESEARCH_TASK_CRITIQUE
        
        ***Reflection***:
        {get_list_str_messages(self.reflection)}
        
        ***Critiques***:
        {get_list_str_messages(self.critique)}
        
        ***Improvement Required***:
        {get_list_str_messages(self.improvement)}
        """

class ResearchSynthesis(ResearchModel):
    research_synthesis: str = Field(description="Complete research synthesis")

    def get_manifest(self) ->str:
        return f"""
        ### RESEARCH_SYNTHESIS
        
        {self.research_synthesis}
        """

class ResearchReport(ResearchModel):
    title: str = Field(description="Title of the research report.")
    outlines: str = Field(description="Outlines of the research report.")
    report: str = Field(description="Complete content of the research report.")

    def get_manifest(self)->str:
        return f"""
        ### RESEARCH REPORT
        
        ## Title
        {self.title}
        
        ## Outlines
        {self.outlines}
        
        ## Content
        {self.report}
        """

class ResearchReportAudit(ResearchModel):
    reflection: list[str] = Field(description="List of research report audit reflection.")
    critique: list[str] = Field(description="List of research report critique.")
    require_improvement: bool = Field(description="Set to True if any critical issues or necessary improvements are found. Set to False only if the tasks are completely ready to execute.")
    improvements_required: list[str] = Field(description="Actionable, specific steps or modifications needed to resolve the issues identified in the critique.")

    def get_manifest(self) -> str:
        return f"""
        ### RESEARCH REPORT AUDIT
        
        ***Reflection***:
        {get_list_str_messages(self.reflection)}
        
        ***Critique***:
        {get_list_str_messages(self.critique)}
        
        ***Improvement Required***:
        {get_list_str_messages(self.improvements_required)}
        """


@dataclass
class FinancialMarketResearchAssistantResponse:
    configurations: ResearchAssistantConfig
    research_query: str
    research_tasks: list[ResearchTask]
    planner_messages: list[BaseMessage]
    plan_auditor_messages: list[BaseMessage]
    subagent_messages: list[list[BaseMessage]]
    research_synthesis: str
    writer_messages: list[BaseMessage]
    writer_auditor_messages: list[BaseMessage]
    research_report: str