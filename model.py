from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from instructions import SUBAGENT_RESEARCHER

class ResearchTask(BaseModel):
    rationale: str = Field(description="Brief explanation of decomposition strategy")
    research_task: str = Field(description="Specific, actionable research task with entities and objectives")

class ResearchTaskPlan(BaseModel):
    rationale: str = Field(description="Brief explanation of decomposition strategy")
    tasks: list[ResearchTask] = Field(description="A list of specific, actionable research tasks with entities and objectives")

class ResearchTaskPlanReflection(BaseModel):
    critique: str = Field(description="Assessment of plan quality")
    required_improvement: str = Field(description="Structured list of specific weaknesses and improvement areas")

class SubAgentConfig(BaseModel):
    name: str = Field(description="Agent unique name")
    role: str = Field(description="Agent's role, persona, and expertise.")
    objective: str = Field(description="Specific, measurable objective for this agent")
    task: str = Field(description="Detailed, actionable task description")
    tools: list[str] = Field(description="Tool name list.")

    def get_system_instruction(self):
        return f"""
        ### **Role**
        ***You are a specialized {self.name} agent.***
        
        Your domain expertise and research focus:
        {self.role}
        
        ### **Objective**
        ***{self.objective}***
        
        This is your singular research goal. All investigation, tool use, and reasoning must target this objective.
        
        ### **Research Task**
        ***{self.task}***
        
        This task defines the scope, specific entities, metrics, and success criteria for your research.
        
        {SUBAGENT_RESEARCHER}
        """

    def get_task_instruction(self):
        return f"""
        ### **Objective**: {self.objective}
        
        ### **Research Task**: {self.task}
        """

class SubAgentsSpawn(BaseModel):
    rationale: str = Field(description="High-level strategy for agent spawning and tool allocation")
    subagent_configs: list[SubAgentConfig] = Field(description="Subagent configurations. Subagent spawn limit is up to 50 subagents.")

@dataclass
class FinancialMarketResearchAssistantResponse:
    content_text: str
    research_plan: ResearchTaskPlan
    subagent_spawn: SubAgentsSpawn
    subagent_configs: list[SubAgentConfig]
    subagent_messages: list[list[BaseMessage]]
    session_messages: list[BaseMessage]