from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agents import SubAgent
from model import ResearchTaskPlan, ResearchTaskPlanReflection, SubAgentsSpawn, SubAgentConfig, \
    FinancialMarketResearchAssistantResponse


class FinancialMarketResearchAssistant:
    def __init__(self, base_llm: BaseChatModel, eval_llm: BaseChatModel|None, tools: list[BaseTool], max_agents: int=50):
        self.base_llm = base_llm
        self.eval_llm = eval_llm if eval_llm else base_llm
        self.tool_map = {tool.name: tool for tool in tools} if tools else None
        self.max_agents = max_agents
        self.session_messages: list[BaseMessage] = []

    def run(self, research_query: str) -> FinancialMarketResearchAssistantResponse:
        research_plan: ResearchTaskPlan = self._plan_reflect_revise_task(research_query)

        subagent_spawn: SubAgentsSpawn = self._subagent_spawner(research_plan=research_plan)

        configs: list[SubAgentConfig] = subagent_spawn.subagent_configs

        subagent_messages: list[list[BaseMessage]] = []
        subagent_contexts: list[str] = []
        for config in configs:
            agent_tools = [self.tool_map[tool_name] for tool_name in config.tools]
            subagent = SubAgent(config=config, llm=self.base_llm, tools=agent_tools)
            response, messages = subagent.run()
            subagent_messages.append(messages)
            subagent_contexts.append(f"Context from subagent {config.name}"
                                     f"-Objective: {config.objective}"
                                     f"-Task: {config.task}"
                                     f"-Response: {response.content}")
            self.session_messages.append(response)

        synthesized_response: AIMessage = self.base_llm.invoke([
            SystemMessage(content="You are a financial market researcher expert. Perform research based on given research query and gathered context."),
            HumanMessage(content=f"The research query: '{research_query}'."
                         f"Gathered context: '{', '.join(subagent_contexts)}'")
        ])

        return FinancialMarketResearchAssistantResponse(
            content_text=self._prepare_text_content(synthesized_response),
            research_plan=research_plan,
            subagent_spawn=subagent_spawn,
            subagent_configs=subagent_spawn.subagent_configs,
            subagent_messages=subagent_messages,
            session_messages=self.session_messages
        )

    def _plan_reflect_revise_task(self, user_prompt: str)->ResearchTaskPlan:
        planner = self.base_llm.with_structured_output(ResearchTaskPlan)
        planner_message = [
            SystemMessage(content="You are a financial market research planner expert."
                                  "Breakdown research query into decomposed research tasks using Mutually Exclusive, Collectively Exhaustive framework alongside Financial Chain-of-Thought."),
            HumanMessage(content=f"Given user prompt '{user_prompt}', prepare a task decomposition plan.")
        ]
        draft_plan: ResearchTaskPlan | BaseModel = planner.invoke(planner_message)
        self.session_messages.extend(planner_message)
        self.session_messages.append(AIMessage(content=f"draft_plan: {draft_plan.model_dump_json()}"))

        plan_reflector = self.eval_llm.with_structured_output(ResearchTaskPlanReflection)
        plan_reflector_message = [
            SystemMessage(content="You are a financial market research plan reflect and audit expert."
                                  "Use Mutually Exclusive, Collectively Exhaustive framework alongside Financial Chain-of-Thought to reflect, critique, and suggest for improvement for given research plan."),
            HumanMessage(content=f"Given user prompt: {user_prompt}, draft plan: {draft_plan.model_dump_json()}"
                                 f"Prepare research task decomposition plan reflection.")

        ]
        plan_reflection: ResearchTaskPlanReflection | BaseModel = plan_reflector.invoke(plan_reflector_message)
        self.session_messages.extend(plan_reflector_message)
        self.session_messages.append(AIMessage(content=f"plan_reflection: {plan_reflection.model_dump_json()}"))

        plan_reviser = self.base_llm.with_structured_output(ResearchTaskPlan)
        plan_reviser_message = [
            SystemMessage(content="You are a financial market research plan reviser expert."
                                  "Understand thoroughly based on given reflection."
                                  "Use Mutually Exclusive, Collectively Exhaustive framework alongside Financial Chain-of-Thought as guidance to improvise the research plan."),
            HumanMessage(content="Given user prompt, draft plan, and plan reflection."
                                 f"User prompt: '{user_prompt}', draft plan: '{draft_plan.model_dump_json()}', plan reflection: {plan_reflection.model_dump_json()}"
                                 f"Prepare the revised and optimized plan.")
        ]
        revised_plan: ResearchTaskPlan | BaseModel = plan_reviser.invoke(plan_reviser_message)
        self.session_messages.extend(plan_reviser_message)
        self.session_messages.append(AIMessage(content=f'revised_plan: {revised_plan.model_dump_json()}'))

        return revised_plan

    def _subagent_spawner(self, research_plan: ResearchTaskPlan, state: list[BaseMessage] | None=None) -> SubAgentsSpawn:
        spawner = self.base_llm.with_structured_output(SubAgentsSpawn)
        messages: list[BaseMessage] = state if state else [
            SystemMessage(
                content=f"You are an expert in spawning research subagents."
                        f"Use given research plan as guidance to spawn subagents."
                        f"Each subagents must assigned with single task based on the research plan."
                        f"For example, if research plan has 10 plans, subagents are expected to be 10, each assigned task based on each research task."
                        f"Use given available tools to appropriately provide subagent necessary tools."
                        f"You are able to spawn up to {self.max_agents} subagents."
                        f"Using subagent spawn quota efficiently to maximize better research task execution is necessary."),
            HumanMessage(
                content=f"Given the task decomposition plan and available tools."
                        f"The task decomposition plan: {research_plan.model_dump_json()}."
                        f"The available tools: '{', '.join(self.tool_map.keys())}'."
                        f"Prepare the subagent spawn plan. ")
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
