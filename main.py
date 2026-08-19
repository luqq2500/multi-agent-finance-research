import os
import time
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI

from model import FinancialMarketResearchAssistantResponse, ResearchReport
from tools import finance_web_search, research_tools
from workflow import FinancialMarketResearchAssistant

def save_response1(response: FinancialMarketResearchAssistantResponse):
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = "diagnostics"
    os.makedirs(directory, exist_ok=True)
    with open(f"{directory}/diagnostic-{current_datetime}.txt", "w", encoding="utf-8") as file:
        file.write(str(response))

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

    base_llm = ChatGoogleGenerativeAI(model='gemini-3.5-flash-lite')
    audit_llm = ChatGoogleGenerativeAI(model='gemini-3.6-flash')
    assistant = FinancialMarketResearchAssistant(base_llm=base_llm, audit_llm=audit_llm, tools=research_tools, plan_research_max_loop=5, write_report_max_loop=5)

    while True:
        start_time = time.time()
        user_prompt = input(f"Research financial markets ('quit' to exit): ")
        if user_prompt.lower().strip() == 'quit':
            break
        response: FinancialMarketResearchAssistantResponse = assistant.run(user_prompt)
        end_time = time.time()

        research_report: ResearchReport = response.research_report
        print(f'Response: \n{research_report.report}')

        duration = end_time - start_time
        print(f'Response time: {duration} seconds')

        save_response(response)


if __name__ == '__main__':
    main()