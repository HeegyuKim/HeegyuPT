import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
from markdownify import markdownify as md




def get_openreview(url):
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저를 표시하지 않음
    
    # WebDriver 설정
    service = Service('/usr/bin/chromedriver')  # ChromeDriver 경로 지정
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 페이지 로드
    driver.get(url)
    # driver.implicitly_wait(10)  # 최대 5초 대기
    time.sleep(5)
    page_source = driver.page_source
    
    # WebDriver 종료
    driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    div = soup.find("div", {"class": "forum-container"})
    # reviews = markdown.markdown(div.prettify())
    reviews = md(div.prettify())
    # reviews = div.text.replace("−＝≡", "\n---\n")
    return reviews

SUMMARY_PROMPT="""다음은 OpenReview에서 가져온 논문 리뷰와 저자 응답입니다. 이를 분석하여 핵심 인사이트를 추출해주세요:

{text}

## 요약 내용
위 내용을 바탕으로 다음 사항들을 간결하게 요약해주세요:

1. Overall score / confidence
2. 리뷰어들이 제기한 주요 장점
3. 리뷰어들이 제기한 주요 문제점 또는 개선사항
4. 저자들의 핵심 반박 또는 설명 (3개 이내)

""".strip()

# 1. Overall scores: 리뷰어들의 Rating과 Confidence 점수와 평균을 표로 작성
# 4. 저자들의 핵심 반박 또는 설명
# 5. 저자들의 반박이 효과적이었는지, 또는 추가 개선이 필요한지 여부

def summarize_openreview(client, text, model="gpt-4o"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 웹 사이트를 분석하고 유용한 정보를 사용자에게 전달하는 한국어 요약 AI입니다."},
            {"role": "user", "content": SUMMARY_PROMPT.format(text=text)}
        ],
        max_tokens=2048
    )
    return response.choices[0].message.content.strip()

async def get_openreview_summarization(client, url: str, model: str):
    review = get_openreview(url)
    summ = summarize_openreview(client, review, model)
    return summ



if __name__ == "__main__":
    import openai
    client = openai.OpenAI()
    paper_url = "https://openreview.net/forum?id=JffVqPWQgg"
    review = get_openreview(paper_url)
    # print(review)

    summ = summarize_openreview(client, review)
    print(summ)

    # forum_id = get_forum_id_from_url(paper_url)
    # reviews = get_paper_reviews(forum_id)

    # # 리뷰 내용 출력
    # for review in reviews:
    #     print(f"Rating: {review.content['rating']}")
    #     print(f"Review: {review.content['review']}")
    #     print("-" * 50)