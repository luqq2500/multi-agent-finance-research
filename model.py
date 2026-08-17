from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class ResearchTask(BaseModel):
    rationale: str = Field(description="Rationale")
    research_task: str = Field(description="Unit task")

class ResearchTaskPlan(BaseModel):
    rationale: str = Field(description="Rationale")
    tasks: list[ResearchTask] = Field(description="list of research tasks")

class ResearchTaskPlanReflection(BaseModel):
    critique: str = Field(description="Critique")
    required_improvement: str = Field(description="Required improvement")

class SubAgentConfig(BaseModel):
    name: str = Field(description="Agent unique name")
    role: str = Field(description="Agent's role and expertise.")
    objective: str = Field(description="Agent's one primary objective.")
    task: str = Field(description="Agent's one primary task.")
    tools: list[str] = Field(description="Agent's tools list.")

    def get_system_instruction(self):
        return (f"You are subagent named {self.name}."
                f"Role and expertise: {self.role}."
                f"Objective: {self.objective}."
                f"Task: {self.task}."
                f"Tools: {self.tools}")

    def get_task_instruction(self):
        return f"Task: {self.task}"

class SubAgentsSpawn(BaseModel):
    rationale: str = Field(description="Rationale")
    subagent_configs: list[SubAgentConfig] = Field(description="Subagent configurations. Subagent spawn limit is up to 50 subagents.")

@dataclass
class FinancialMarketResearchAssistantResponse:
    content_text: str
    research_plan: ResearchTaskPlan
    subagent_spawn: SubAgentsSpawn
    subagent_configs: list[SubAgentConfig]
    subagent_messages: list[list[BaseMessage]]
    session_messages: list[BaseMessage]