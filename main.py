import os
import time
from datetime import datetime

from InquirerPy import inquirer
from InquirerPy.validator import NumberValidator
from dotenv import load_dotenv
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI

from model import FinancialMarketResearchAssistantResponse, ResearchReport, ResearchAssistantConfig
from tools import finance_web_search, research_tools
from workflow import FinancialMarketResearchAssistant

def save_response(response: FinancialMarketResearchAssistantResponse):
    # Create a unique folder name using the current timestamp
    folder_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = os.path.join("diagnostics", folder_time)
    os.makedirs(directory, exist_ok=True)

    # Handle both Pydantic models (.model_dump()) and standard Python classes (.__dict__)
    fields = (
        response.model_dump()
        if hasattr(response, "model_dump")
        else getattr(response, "__dict__", {})
    )

    # Loop through each field, using the field name as the filename
    for field_name, field_value in fields.items():
        filename = f"{field_name}.txt"
        filepath = os.path.join(directory, filename)

        with open(filepath, "w", encoding="utf-8") as file:
            # Safely convert lists, dicts, or objects to string format
            file.write(str(field_value))


def main():
    tools: list[BaseTool] = []
    load_dotenv()
    tools.append(finance_web_search)

    models = {
        'gemini-3.5-flash-lite': lambda: ChatGoogleGenerativeAI(model='gemini-3.5-flash-lite'),
        'gemini-3.5-flash': lambda: ChatGoogleGenerativeAI(model='gemini-3.5-flash'),
        'gemini-3.6-flash': lambda: ChatGoogleGenerativeAI(model='gemini-3.6-flash'),
        'gemini-3.7-flash': lambda: ChatGoogleGenerativeAI(model='gemini-3.7-flash'),
    }

    select_base_model = inquirer.select(
        message="Select base model: ",
        choices=list(models.keys()),
    ).execute()

    select_upgrade_model = inquirer.select(
        message="Select upgrade model: ",
        choices=list(models.keys()),
    ).execute()

    select_plan_reflect_max_loop = inquirer.number(
        message="Enter plan-reflect max loop:",
        default=None,
        min_allowed=1,
        max_allowed=100,
        validate=NumberValidator(float_allowed=False),
    ).execute()

    set_max_subagents = inquirer.number(
        message="Enter subagents budget:",
        default=None,
        min_allowed=1,
        max_allowed=100,
        validate=NumberValidator(float_allowed=False),
    ).execute()

    set_subagent_max_loop = inquirer.number(
        message="Enter subagent loop budget:",
        default=None,
        min_allowed=1,
        max_allowed=100,
        validate=NumberValidator(float_allowed=False),
    ).execute()

    try:
        base_model = models[select_base_model]()
        upgrade_model = models[select_upgrade_model]()
        max_plan_reflect_loop = int(select_plan_reflect_max_loop)
        max_subagents = int(set_max_subagents)
        max_subagent_loop = int(set_subagent_max_loop)
        base_model.invoke(input="ping")
        upgrade_model.invoke(input="ping")
    except Exception as e:
        raise RuntimeError(f"Model failed to invoke: {e}")

    config = ResearchAssistantConfig(
        base_llm=base_model,
        upgrade_llm=upgrade_model,
        tools=tools,
        max_planner_loop=max_plan_reflect_loop,
        max_agents=max_subagents,
        max_agent_loop=max_subagent_loop,
        max_writer_loop=max_plan_reflect_loop
    )

    assistant = FinancialMarketResearchAssistant(config)

    while True:
        start_time = time.time()
        user_prompt = input(f"\nResearch financial markets ('quit' to exit): ")
        if user_prompt.lower().strip() == 'quit':
            break
        response: FinancialMarketResearchAssistantResponse = assistant.run(user_prompt)
        end_time = time.time()

        print(f'\nResponse: \n{response.research_report}')

        duration = end_time - start_time
        print(f'Response time: {duration} seconds')

        save_response(response)


if __name__ == '__main__':
    main()