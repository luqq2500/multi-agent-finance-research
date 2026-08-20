from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from instructions import SUBAGENT_RESEARCHER

def get_list_str_messages(items: list[str]) -> str:
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

class ResearchModel(BaseModel, ABC):
    @abstractmethod
    def get_message(self)->str:
        pass

class ResearchTask(ResearchModel):
    task: str = Field(description="**One** specific research task — a single scope of investigation for a single isolated agent. "
                                  "Name the targeted entity and topics and the subject to investigate."
                                  "This must be one task, not several joined by 'and' or by a numbered sequence.")
    success_criteria: list[str] = Field(description="A list of explicit checklist items or targets that must be met to consider this task complete.")
    required_expertise: list[str] = Field(description="A list of specific expertises needed to execute tasks.")
    tools: list[str] = Field(description="List of necessary tools to help execute research task.")
    tool_use_strategy: list[str] = Field(description="A step-by-step blueprint of tool use, detailing how the selected tools will be utilized, including exact arguments and parameters.")
    task_boundary: list[str] = Field(description="Strict out-of-scope boundaries. Explicitly lists what should NOT be researched or done during this task.")

    def get_message(self) ->str:
        return (
        f"""
        # Research Task Specification
                
        **Task**
        {self.task}
        
        **Success Criteria**
        {get_list_str_messages(self.success_criteria)}
        
        **Required Expertise**
        {self.required_expertise}
        
        **Tools**
        {get_list_str_messages(self.tools)}
        
        **Tool Use Strategy**
        {get_list_str_messages(self.tool_use_strategy)}
        
        **Task Boundary**
        {get_list_str_messages(self.task_boundary)}        
        """)

    def get_tasks(self)->str:
        return get_list_str_messages(self.task)

    def get_list_of_tools(self)->list[str]:
        return self.tools

class ResearchTasks(ResearchModel):
    research_tasks: list[ResearchTask] = Field(description="Research tasks")

    def get_message(self) ->str:
        research_tasks = "\n".join(f"## Research Task {i+1}\n {task.get_message()}" for i, task in enumerate(self.research_tasks))
        return f"""
        ### List of Research Tasks
        
        {research_tasks}
        """

    def get_list_of_research_task(self)->list[ResearchTask]:
        return self.research_tasks

class ResearchTasksCritique(ResearchModel):
    reflection: list[str] = Field(description="Objective research tasks critique reflection.")
    critique: list[str] = Field(description="Research task's constructive critiques.")
    improvement: list[str] = Field(description="Actionable, specific steps or modifications needed to resolve the issues identified in the critique.")
    require_improvement: bool = Field(description="Set to True if any critical issues or necessary improvements are found. Set to False only if the tasks are completely ready to execute.")

    def get_message(self) ->str:
        return f"""
        ### Research Tasks Critique
        
        ## Reflection
        {get_list_str_messages(self.reflection)}
        
        ## Critiques
        {get_list_str_messages(self.critique)}
        
        ## Improvement
        {get_list_str_messages(self.improvement)}
        """

class ResearchReport(ResearchModel):
    title: str = Field(description="Title of the research report.")
    outlines: str = Field(description="Outlines of the research report.")
    report: str = Field(description="Complete content of the research report.")

    def get_message(self)->str:
        return f"""
        ### Research Report Details
        
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
    improvement_suggestions: list[str] = Field(description="Actionable, specific steps or modifications needed to resolve the issues identified in the critique.")

    def get_message(self) -> str:
        return f"""
        ### Research Report Audit
        
        ## Reflection
        {get_list_str_messages(self.reflection)}
        
        ## Critique
        {get_list_str_messages(self.critique)}
        
        ## Improvement Suggestions
        {get_list_str_messages(self.improvement_suggestions)}
        """


@dataclass
class FinancialMarketResearchAssistantResponse:
    base_llm: str
    audit_llm: str
    max_loops: str
    research_query: str
    research_tasks: str
    planner_messages: list[BaseMessage]
    planauditor_messages: list[BaseMessage]
    subagent_messages: list[list[BaseMessage]]
    synthesized_research: str
    writer_messages: list[BaseMessage]
    writerauditor_messages: list[BaseMessage]
    research_report: str