from pydantic import BaseModel
from datetime import datetime
import json
from .convert import download_pdf, parse_pdf
from .firebase_utils import FirebaseManager, PaperStore
from bs4 import BeautifulSoup
import requests
import base64, markdown
import markdownify
from pprint import pprint



class PaperInfoExtraction(BaseModel):
    title: str
    abstract: str
    authors: str
    tldr: str

class ArxivHTMLPaperReviewSection(BaseModel):
    content: str
    figure_ids: list[str]

class ArxivHTMLPaperReview(BaseModel):
    in_depth_insights: ArxivHTMLPaperReviewSection
    methodology: ArxivHTMLPaperReviewSection
    results: ArxivHTMLPaperReviewSection
    limitations: str
    future_works: str

class MarkdownReview(BaseModel):
    in_depth_insights: str
    methodology: str
    results: str
    limitations: str
    future_works: str

def extract_paper_info(client, model, pdf_text: str):
    extract_prompt = f"""주어진 논문을 읽고 아래 항목을 추출해주세요: 제목, abstract, 저자, TLDR(한글로 작성해주세요).
    
===논문 내용===
{pdf_text[:40000]}""".strip()

    response = client.beta.chat.completions.parse(
        # model=model,
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": extract_prompt}
        ],
        max_tokens=4096,
        response_format=PaperInfoExtraction,
    )
    return response.choices[0].message.parsed


REVIEW_FORMAT = """
## In-depth Insights
{in_depth_insights_figures}{in_depth_insights}

## Methodology
{methodology_figures}{methodology}

## Results
{results_figures}{results}

## Limitations
{limitations}

## Future Works
{future_works}

""".strip()

def get_ai_review_from_arxiv_html(client, model, pdf_text: str, figures: list[dict]):
    if len(pdf_text) > 40000:
        pdf_text = pdf_text[:40000]

    analysis_prompt = f"다음 논문을 치밀하게 분석하고 아래 항목에 대해 반드시 한글로 답변해주세요. 논문이 길어서 내용이 일부 생략될 수 있습니다."
    analysis_prompt += "\n각 섹션은 500단어 이상으로 상세하고 명확하게 작성해주시고, 논문의 내용을 정확히 반영해야 합니다. 설명에 도움이 되는 figure를 논문에서 찾아 첨부해주세요."
    analysis_prompt += f"\n===논문 내용==={pdf_text}"
    
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "user", "content": analysis_prompt}
        ],
        max_tokens=4096,
        response_format=ArxivHTMLPaperReview,
    )
    review = response.choices[0].message.parsed

    in_depth_insights = review.in_depth_insights.content
    methodology = review.methodology.content
    results = review.results.content
    limitations = review.limitations
    future_works = review.future_works

    in_depth_insights_figures = []
    methodology_figures = []
    results_figures = []

    if figures:
        for fig in figures:
            if fig['figure_id'] in review.in_depth_insights.figure_ids:
                in_depth_insights_figures.append(fig['content'])
            if fig['figure_id'] in review.methodology.figure_ids:
                methodology_figures.append(fig['content'])
            if fig['figure_id'] in review.results.figure_ids:
                results_figures.append(fig['content'])

    review = REVIEW_FORMAT.format(
        in_depth_insights_figures="\n".join(in_depth_insights_figures),
        in_depth_insights=in_depth_insights,
        methodology_figures="\n".join(methodology_figures),
        methodology=methodology,
        results_figures="\n".join(results_figures),
        results=results,
        limitations=limitations,
        future_works=future_works
    )

    return review


def gen_ai_review_from_markdown(client, model, pdf_text: str):
    if len(pdf_text) > 40000:
        pdf_text = pdf_text[:40000]

    analysis_prompt = f"다음 논문을 치밀하게 분석하고 아래 항목에 대해 반드시 한글로 답변해주세요. 논문이 길어서 내용이 일부 생략될 수 있습니다."
    analysis_prompt += "\n각 섹션은 500단어 이상으로 상세하고 명확하게 작성해주시고, 논문의 내용을 정확히 반영해야 합니다. 설명에 도움이 되는 이미지나 테이블이 존재한다면, 각 섹션에 추가해주세요 단, 존재하지 않는 placeholder를 넣어서는 안됩니다."
    analysis_prompt += f"\n===논문 내용==={pdf_text}"
    
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "user", "content": analysis_prompt}
        ],
        max_tokens=4096,
        response_format=MarkdownReview,
    )
    review = response.choices[0].message.parsed

    in_depth_insights = review.in_depth_insights
    methodology = review.methodology
    results = review.results
    limitations = review.limitations
    future_works = review.future_works

    review = REVIEW_FORMAT.format(
        in_depth_insights=in_depth_insights,
        methodology=methodology,
        results=results,
        limitations=limitations,
        future_works=future_works,
        in_depth_insights_figures="",
        methodology_figures="",
        results_figures=""
    )

    return review

def review_pdf(client, model: str, manager: FirebaseManager, pdf_url: str, upload=True):

    if pdf_url.startswith("https://arxiv.org/abs/"):
        pdf_url = pdf_url.replace("abs", "pdf")

    pdf_json = check_html(pdf_url)
    is_arxiv_html = pdf_json is not None
    if pdf_json is None:
        pdf_path = download_pdf(pdf_url)
        pdf_json = parse_pdf(pdf_path)
    else:
        print("HTML content Found")

    pdf_text = pdf_json['text']
    images = pdf_json['images']
    
    paper_info = extract_paper_info(client, model, pdf_text)
    if is_arxiv_html:
        review = get_ai_review_from_arxiv_html(client, model, pdf_text, pdf_json.get('figures'))
    else:
        review = gen_ai_review_from_markdown(client, model, pdf_text)
    
    if upload:
        paper = PaperStore(
            title=paper_info.title,
            abstract=paper_info.abstract,
            authors=paper_info.authors,
            tldr=paper_info.tldr,
            markdown=pdf_text,
            review=review,
            url=pdf_url,
            review_time=datetime.now(),
            image_files=[img['image_name'] for img in images]
        )
        paper_id = manager.add_paper(paper)
        manager.upload_image(paper_id, images)

        return paper_id, paper
    else:
        return paper_info, review


def check_html(url):

    if url.startswith("https://arxiv.org/html/"):
        html_url = url  
    elif url.startswith("https://arxiv.org/abs/") or url.startswith("https://arxiv.org/pdf/"):
        html_url = url.replace("abs", "html").replace("pdf", "html")
    else:
        return None
    
    print(f"Checking HTML: {html_url}")

    content = requests.get(html_url).text
    soup = BeautifulSoup(content, 'html.parser')
    # article.ltx_document
    article = soup.find("article", class_="ltx_document")
    if article:
        images = article.find_all("img")
        image_files = []

        for img in images:
            src = img.get("src")
            name = src
            if src.startswith("data:image"):
                continue
            if not src.startswith("https://") or not src.startswith("http://"):
                if src.startswith("/"):
                    src = f"https://arxiv.org{src}"
                else:
                    src = f"{html_url}/{src}"
                
            img_content = requests.get(src).content
            img_content = base64.b64encode(img_content)
            image_files.append({
                "image_name": name,
                "image": img_content
            })


        figures = article.find_all("figure")
        figure_outputs = []
        for fig in figures:
            figid = fig.get("id")
            figure_outputs.append({
                "figure_id": figid,
                "content": markdownify.markdownify(str(fig))
            })


        text = article.prettify()
        return {
            "text": text,
            "images": image_files,
            "figures": figure_outputs
        }
    return None


if __name__ == "__main__":
    import openai
    from pprint import pprint

    # url = "https://arxiv.org/pdf/2411.01855"
    # url = "https://arxiv.org/pdf/2406.11161"
    url = "https://openreview.net/pdf?id=IRXyPm9IPW"
    # pprint(content['text'])
    # print(content['images'][0]['image_name'])

    client = openai.OpenAI()
    model = "gpt-4o-mini"

    # pdf_json = check_html(url)
    # pdf_text = pdf_json['text']
    # images = pdf_json['images']
    # print(pdf_json['figures'])



    manager = FirebaseManager()
    info, review = review_pdf(client, model, manager, url, upload=False)
    pprint(info.dict())
    print(review)