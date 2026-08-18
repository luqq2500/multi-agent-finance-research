from dataclasses import dataclass
from typing import Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from instructions import SUBAGENT_RESEARCHER


class ResearchTask(BaseModel):
<<<<<<< HEAD
    rationale: str = Field(description="Brief explanation of decomposition strategy")
    research_task: str = Field(description="Specific, actionable research task with entities and objectives")

class ResearchTaskPlan(BaseModel):
    rationale: str = Field(description="Brief explanation of decomposition strategy")
    tasks: list[ResearchTask] = Field(description="A list of specific, actionable research tasks with entities and objectives")

class ResearchTaskPlanReflection(BaseModel):
    critique: str = Field(description="Assessment of plan quality")
=======
    rationale: str = Field(description="Rationale for why this task is necessary")
    research_task: str = Field(description="Specific, actionable research task")

class ResearchTaskPlan(BaseModel):
    rationale: str = Field(description="Rationale for the decomposition strategy and MECE application")
    tasks: list[ResearchTask] = Field(description="List of research tasks")

class ResearchTaskPlanReflection(BaseModel):
    critique: str = Field(description="Overall assessment of plan quality and completeness")
>>>>>>> bc98d92f8c5bfe1d1742c99f7b5c023b965245d4
    required_improvement: str = Field(description="Structured list of specific weaknesses and improvement areas")

class SubAgentConfig(BaseModel):
    name: str = Field(description="Agent unique name")
<<<<<<< HEAD
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
=======
    role: str = Field(description="Agent's role and expertise")
    objective: str = Field(description="Agent's one primary objective")
    task: str = Field(description="Agent's primary tasks")
    tools: list[str] = Field(description="Agent's tools list")

    def get_system_instruction(self, tools_info: Optional[str] = None):
>>>>>>> bc98d92f8c5bfe1d1742c99f7b5c023b965245d4
        """
        Generate comprehensive system instruction for the subagent.
        
        Args:
            tools_info: Optional formatted tool descriptions (if not provided, uses tool names)
        
        Returns:
            Formatted system instruction string
        """
        tools_section = self._format_tools_section(tools_info)
        
        return f"""### **Role**
***You are a specialized {self.name} agent.***

<<<<<<< HEAD
    def get_task_instruction(self):
        return f"""
        ### **Objective**: {self.objective}
        
        ### **Research Task**: {self.task}
        """

class SubAgentsSpawn(BaseModel):
    rationale: str = Field(description="High-level strategy for agent spawning and tool allocation")
    subagent_configs: list[SubAgentConfig] = Field(description="Subagent configurations. Subagent spawn limit is up to 50 subagents.")
=======
Your domain expertise and research focus:
{self.role}

### **Objective**
***{self.objective}***

This is your singular research goal. All investigation, tool use, and reasoning must target this objective.

### **Research Task**
"""{self.task}"""

This task defines the scope, specific entities, metrics, and success criteria for your research.

{tools_section}

### **Guidelines**
- **Stay Focused**: Every tool call and reasoning step must target your assigned objective
- **Be Specific**: Use tool parameters to target exact entities, markets, or metrics defined in your task
- **Avoid Scope Creep**: Do not research related but out-of-scope topics
- **Synthesize Information**: After gathering data, integrate findings into coherent insights
- **Check Quality**: Verify information from multiple sources when possible
- **Ground in Facts**: Distinguish between facts (data, confirmed reports) and analysis/opinions
- **Cite Sources**: Reference where information came from (press releases, earnings reports, analyst reports)

### **Constraints**
***You MUST:***
- Focus exclusively on your assigned objective — nothing else
- Include specific entities from your task in every tool call parameter
- Execute your research task fully before concluding
- Provide actionable findings that directly address the objective
- Clearly state what you found and what you couldn't find
- Use all available tools if necessary to achieve quality results

***You MUST NOT:***
- Investigate topics outside your task scope
- Use vague or broad tool queries (be specific with entities and timeframes)
- Conduct research for other agents or broader topics
- Make claims without grounding in available information
- Stop early without fully pursuing your objective
- Ignore contradictions or conflicting information

### **Research Process**
1. **Understand Your Task**: Carefully read your assigned research task
2. **Identify Key Questions**: Break task into 3-5 specific research questions
3. **Plan Tool Usage**: Determine which tools to use and in what sequence
4. **Gather Information**: Execute tool calls with specific, targeted queries
5. **Assess Quality**: Evaluate information completeness and reliability
6. **Synthesize Findings**: Integrate information into coherent analysis
7. **Validate Completeness**: Confirm you've addressed all aspects of the task
8. **Deliver Findings**: Present clear, structured findings that answer the objective

### **Tool Usage Standards**
Every tool call MUST include:
- **Specific entities**: Use company names, market segments, indices (not generic terms)
- **Time scope**: Specify relevant timeframe (Q4 2024, last 6 months, 2025 guidance)
- **Metric focus**: Indicate what data/metrics you're looking for
- **Context**: Explain why you're using this tool at this step

### **Output Format**
When you conclude your research, provide a structured summary with:
- Key Findings (with supporting evidence)
- Data & Metrics (with sources)
- Gaps & Limitations
- Recommendations for downstream analysis

### **Quality Standards**
Your research output must:
- Be specific and reference concrete entities, numbers, time periods
- Indicate source for each fact (press releases, earnings reports, analyst reports)
- Address all aspects of your assigned task
- State gaps, contradictions, and limitations clearly
- Provide findings useful for final synthesis
- Stay within assigned scope

### **Execution Constraints**
- Loop Budget: Up to 10 reasoning/tool-use steps — use wisely
- Tool Calls: Each should target specific information needed for objective
- Fallback: If unable to complete task with available tools, state clearly
- Scope Boundary: Stop when objective fully addressed
"""

    def _format_tools_section(self, tools_info: Optional[str] = None) -> str:
        """
        Format the tools section of the system instruction.
        
        Args:
            tools_info: Optional pre-formatted tool descriptions
        
        Returns:
            Formatted tools section
        """
        if tools_info:
            return f"### **Available Tools**\n{tools_info}"
        elif self.tools:
            tools_list = "\n".join([f"- {tool}" for tool in self.tools])
            return f"### **Available Tools**\n{tools_list}"
        else:
            return "### **Available Tools**\nNo specific tools assigned for this task. Use reasoning and analysis only."

    def get_task_instruction(self) -> str:
        """
        Generate the task instruction message for the agent.
        
        Returns:
            Formatted task instruction string
        """
        return f"""### **Your Assigned Task**

{self.task}

**Execute this task using your assigned tools and reasoning. Provide structured findings that directly address the objective.**
"""

class SubAgentsSpawn(BaseModel):
    rationale: str = Field(description="Rationale for spawning strategy and agent allocation")
    subagent_configs: list[SubAgentConfig] = Field(
        description="Subagent configurations. Subagent spawn limit is up to 50 subagents."
    )
>>>>>>> bc98d92f8c5bfe1d1742c99f7b5c023b965245d4

@dataclass
class FinancialMarketResearchAssistantResponse:
    content_text: str
    research_plan: ResearchTaskPlan
    subagent_spawn: SubAgentsSpawn
    subagent_configs: list[SubAgentConfig]
    subagent_messages: list[list[BaseMessage]]
    session_messages: list[BaseMessage]
