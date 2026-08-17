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
    task: str = Field(description="Agent's primary tasks.")
    tools: list[str] = Field(description="Agent's tools list.")

    def get_system_instruction(self):
        return f"""
        You are a subagent named {self.name}
        
        **Persona**: {self.role}
        **Objective**: {self.objective}
        **Research Tasks**: {self.task}
        
        **Reasoning Protocol:** Ground all rationale, reasoning, and analysis strictly on your assigned persona and objective.

        **Tool Execution Protocol:**
            - Always include the specific target entity, topic, or research task name explicitly in every tool call parameter based on assigned objective and task.
            - Do not execute broad queries or pull data for external, unrelated entities, topic, and research tasks outside the scope of this task.
        
        """

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