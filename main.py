import os
import time
from dataclasses import asdict
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI

from model import FinancialMarketResearchAssistantResponse
from tools import finance_web_search
from workflow import FinancialMarketResearchAssistant

def diagnose(duration: int, response: FinancialMarketResearchAssistantResponse):
    print(f'\nSession metadata: ')

    print(f'\nResponse time: {duration} seconds')

    print(f'\n{len(response.subagent_configs)} subagents spawned: ')
    for i, (config, messages) in enumerate(zip(response.subagent_configs, response.subagent_messages)):
        print(f"{i+1}. Subagent {config.name}\n"
              f"    Objective: {config.objective}\n"
              f"    Task: {config.task}\n"
              f"    Messages: {messages}\n")

    print(f'Session messages: ')
    for i, message in enumerate(response.session_messages):
        print(f"    {i + 1}. {message.__class__.__name__}: {message.content}")

def save_response(response: FinancialMarketResearchAssistantResponse):
    time = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = "diagnostics"
    os.makedirs(directory, exist_ok=True)
    with open(f"{directory}/diagnostic-{time}.txt", "w", encoding="utf-8") as file:
        file.write(str(response))

def main():
    tools: list[BaseTool] = []
    load_dotenv()
    tools.append(finance_web_search)

    base_llm = ChatGoogleGenerativeAI(model='gemini-3.5-flash-lite')
    assistant = FinancialMarketResearchAssistant(base_llm=base_llm, eval_llm=None, tools=tools)

    while True:
        start_time = time.time()
        user_prompt = input(f"Research financial markets ('quit' to exit): ")
        if user_prompt.lower().strip() == 'quit':
            break
        response: FinancialMarketResearchAssistantResponse = assistant.run(user_prompt)
        end_time = time.time()

        print(f'Response: \n{response.content_text}')

        diagnose(int(end_time-start_time), response)

        save_response(response)


if __name__ == '__main__':
    main()