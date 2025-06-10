from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel, VisitWebpageTool, LogLevel, Tool, ToolCallingAgent
from smolagents.utils import truncate_content
from crawl4ai import AsyncWebCrawler
import re
import asyncio
import nest_asyncio 
nest_asyncio.apply()
import time



AUTHORIZED_IMPORTS = [
    "requests",
    "zipfile",
    "os",
    "pandas",
    "numpy",
    "sympy",
    "json",
    "bs4",
    "pubchempy",
    "xml",
    "yahoo_finance",
    "Bio",
    "sklearn",
    "scipy",
    "pydub",
    "io",
    "PIL",
    "chess",
    "PyPDF2",
    "pptx",
    "torch",
    "datetime",
    "fractions",
    "csv",
]

class Crawl4AIVistWebpageTool(Tool):
    name = "visit_webpage"
    description = (
        "Visits a webpage at the given url and reads its content as a markdown string. Use this to browse webpages."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "The url of the webpage to visit.",
        }
    }
    output_type = "string"

    async def async_forward(self, url: str) -> str:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
            )
        return result.markdown

    def forward(self, url: str) -> str:
        try:
            # run and get the result
            result = asyncio.run(self.async_forward(url))

            # Remove multiple line breaks
            markdown_content = re.sub(r"\n{3,}", "\n\n", result)

            markdown_content = truncate_content(markdown_content, 10000)
            return f"# Web Search Result for {url}:\n\n{markdown_content}"

        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"
        
async def get_deep_research(question: str, model_name: str = "o3-mini"):
    custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}
    search_model = LiteLLMModel(
        custom_role_conversions=custom_role_conversions,
        model_id="gpt-4o-mini",
        max_tokens=4096
    )
    final_model = LiteLLMModel(
        model_id=model_name,
        max_completion_tokens=8192,
        reasoning_effort="low",
        custom_role_conversions=custom_role_conversions,
    )

    text_limit = 100000

    WEB_TOOLS = [
        Crawl4AIVistWebpageTool(),
        DuckDuckGoSearchTool(),
    ]
    text_webbrowser_agent = ToolCallingAgent(
        model=search_model,
        tools=WEB_TOOLS,
        max_steps=20,
        verbosity_level=2,
        planning_interval=4,
        name="search_agent",
        description="""A team member that will search the internet to answer your question.
    Ask him for all your questions that require browsing the web.
    Provide him as much context as possible, in particular if you need to search on a specific timeframe!
    And don't hesitate to provide him with a complex search task, like finding a difference between two webpages.
    Your request must be a real sentence, not a google search! Like "Find me this information (...)" rather than a few keywords.
    """,
        provide_run_summary=True,
    )

    today = time.strftime("%Y-%m-%d %H:%M:%S")
    question_augmented = f"""Now: {today}
You must provide professional answers to my instruction, based on the facts and the most recent information available on the web.
Search by a variety of keywords, visit many websites, find the best insights using the search_agent(str) function. Finally, provide the most satisfying answers with inline citations.

## Instruction: 
{question}

You must call search_agent("your subquestion here") at least once.""" + """

## Note
Your final answer in a structured format with proper citations in the following format:
1. All factual information must be cited inline format [number].
2. List the citations at the end of the answer in a separate section titled "## References".
3. The citation format should be [number] Document Title (Author, Year), Website Name, URL.
4. For example: "According to Wikipedia[...][1]"."""


    manager_agent = CodeAgent(
        model=final_model,
        tools=[],
        max_steps=12,
        verbosity_level=2,
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        planning_interval=4,
        managed_agents=[text_webbrowser_agent],
    )

    return manager_agent.run(question_augmented)


def main():
    question = "대한민국 2025년 경제 전망 리포트를 작성해줘."
    result = asyncio.run(get_deep_research(question))
    print(result)

if __name__ == "__main__":
    main()