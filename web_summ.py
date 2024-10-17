from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import openai
import re
import asyncio
import nest_asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
import json
import time
from pydantic import BaseModel, Field

nest_asyncio.apply()



def load_page(url):
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저를 표시하지 않음
    
    # WebDriver 설정
    service = Service('/usr/bin/chromedriver')  # ChromeDriver 경로 지정
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 페이지 로드
    driver.get(url)
    driver.implicitly_wait(5)  # 최대 5초 대기
    page_source = driver.page_source
    
    # WebDriver 종료
    driver.quit()
    
    return page_source

def extract_main_content(page_source):
    # BeautifulSoup을 사용하여 HTML 파싱
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # 불필요한 태그 제거
    for script in soup(["script", "style", "link", "head", "meta"]):
        script.decompose()
    
    # 메인 콘텐츠 추출 (이 부분은 웹사이트 구조에 따라 조정이 필요할 수 있습니다)
    main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
    
    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
    else:
        text = soup.get_text(separator=' ', strip=True)
    
    # 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

async def load_webpage_crawl4ai(url):
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)
        print(len(result.markdown))
    return result.markdown

SUMMARY_PROMPT="""다음 웹사이트의 HTML 텍스트를 분석하고 아래 정보를 제공해주세요:
1. 간단한 요약 (3-4문장)
2. 연구 방법론 (사용된 경우)
3. 주요 연구 결과 (2-3개)
4. 관련 연구 분야 제안 (2-3개)
{text}
""".strip()
def summarize_with_openai(client, text, model="gpt-4o-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 웹 사이트를 분석하고 유용한 정보를 사용자에게 전달하는 한국어 요약 AI입니다."},
            {"role": "user", "content": SUMMARY_PROMPT.format(text=text)}
        ],
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()

async def summarize_website(client, url, model="gpt-4o-mini"):
    # page_source = load_page(url)
    # main_content = extract_main_content(page_source)
    main_content = await load_webpage_crawl4ai(url)
    print(main_content)
    summary = summarize_with_openai(client, main_content, model)
    return summary

# 사용 예제
if __name__ == "__main__":
    client = openai.OpenAI()
    # url = "https://huggingface.co/blog/zero-shot-vqa-docmatix"
    # summary = summarize_website(client, url)
    # url = "https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct"
    url = "https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/"
    summary = asyncio.run(summarize_website(client, url))
    print(f"웹사이트 요약:\n{summary}")