import discord
from discord.ext import commands
import asyncio
import traceback
import sys
import aiohttp
import openai
import schedule
from pdfchat import download_pdf, extract_text_from_pdf, get_vector_store, setup_conversational_chain
from web_summ import summarize_website
import logging
import ajou_portal
import os


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

client = openai.OpenAI()

bot = commands.Bot(command_prefix='!', intents=intents)

async def download_file(ctx, url, filename):
    # 파일 다운로드
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                pdf_data = await resp.read()
                with open(filename, 'wb') as f:
                    f.write(pdf_data)
                
                await ctx.send(f'{filename} 다운로드 완료!')
            else:
                await ctx.send('파일 다운로드 실패')
                
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    if os.environ.get("RESTAURANT_CHANNEL_ID"):
        print("Scheduling menu sending...")
        time = "09:00" # 9시에 메뉴 전송
        schedule.every().monday.at(time).do(lambda: asyncio.create_task(ajou_portal.send_menu(bot)))
        schedule.every().tuesday.at(time).do(lambda: asyncio.create_task(ajou_portal.send_menu(bot)))
        schedule.every().wednesday.at(time).do(lambda: asyncio.create_task(ajou_portal.send_menu(bot)))
        schedule.every().thursday.at(time).do(lambda: asyncio.create_task(ajou_portal.send_menu(bot)))
        schedule.every().friday.at(time).do(lambda: asyncio.create_task(ajou_portal.send_menu(bot)))

        while True:
            schedule.run_pending()
            await asyncio.sleep(60)
    else:
        print("No RESTAURANT_CHANNEL_ID found in environment variables. Skipping menu sending.")

@bot.event
async def on_error(event, *args, **kwargs):
    """전역 이벤트 핸들러에서 발생한 예외를 처리합니다."""
    error = sys.exc_info()[1]
    error_msg = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    print(f"Ignoring exception in {event}:\n{error_msg}")
    # 개발자에게 DM으로 오류 메시지 보내기 (선택사항)
    # dev_user = await bot.fetch_user(YOUR_USER_ID)  # 개발자의 Discord ID
    # await dev_user.send(f"An error occurred in {event}:\n```{error_msg}```")

@bot.event
async def on_command_error(ctx, error):
    """명령어 실행 중 발생한 예외를 처리합니다."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("존재하지 않는 명령어입니다.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("명령어에 필요한 인자가 누락되었습니다.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("잘못된 인자가 제공되었습니다.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("이 명령어를 실행할 권한이 없습니다.")
    else:
        # 기타 예외 처리
        error_msg = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        print(f"Ignoring exception in command {ctx.command}:\n{error_msg}")
        await ctx.send(f"명령어 실행 중 오류가 발생했습니다: {type(error).__name__}")
        # 개발자에게 DM으로 오류 메시지 보내기 (선택사항)
        # dev_user = await bot.fetch_user(YOUR_USER_ID)  # 개발자의 Discord ID
        # await dev_user.send(f"An error occurred in command {ctx.command}:\n```{error_msg}```")


async def get_openai_response(prompt, model="gpt-4o-mini", system_prompt="You are a helpful AI assistant specializing in answering questions."):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4096,
    )
    return response.choices[0].message.content

ALLOWED_MODELS = ["gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"]

@bot.command()
async def paper(ctx, input: str = None, model: str = "gpt-4o-mini"):
    url = None
    attachment = None

    if model not in ALLOWED_MODELS:
        await ctx.send(f"모델은 {', '.join(ALLOWED_MODELS)} 중 하나여야 합니다.")
        return

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
    elif input:
        url = input

    if url is None and attachment is None:
        await ctx.send("PDF 파일 또는 URL을 첨부해주세요.")
        return
    
    try:
        await ctx.send("논문을 분석 중입니다. 잠시만 기다려주세요...")

        # PDF 다운로드 및 텍스트 추출 (기존 함수 사용)
        pdf_path = download_pdf(url)
        print(pdf_path)
        pdf_text = await extract_text_from_pdf(pdf_path)

        # GPT를 사용하여 논문 분석
        analysis_prompt = f"""
다음 논문을 분석하고 아래 항목에 대해 반드시 한글로 답변해주세요. 논문이 길어서 내용이 일부 생략될 수 있습니다.
각 요소는 bullet point로 정리하고, 하이픈 대신 • 사용

1. 제목 및 저자
2. 주요 컨트리뷰션
3. 연구 방법론 요약
4. 주요 결과
5. 한계점
6. Future works 추천

===논문 내용===
{pdf_text[:40000]}
        """.strip()

        analysis = await get_openai_response(
            analysis_prompt, 
            model,
            system_prompt="You are a helpful AI assistant specializing in summarizing research papers."
            )

        print(analysis)
        # 분석 결과를 여러 메시지로 나누어 보내기
        chunks = [analysis[i:i+1900] for i in range(0, len(analysis), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)

    except Exception as e:
        await ctx.send(f"논문 분석 중 오류가 발생했습니다: {str(e)}")
        print(f"Error in analyze_paper command: {e}")
        traceback.print_exc()


user_history = {}

@bot.command(pass_context=True)
async def on_message(message):
    if not message.guild:
        await message.channel.send('this is a dm')
        
@bot.command()
async def chat(ctx, *, message: str):
    global user_history

    if ctx.author.id not in user_history:
        user_history[ctx.author.id] = []

    user_history[ctx.author.id].append({"role": "user", "content": message},)

    if len(user_history[ctx.author.id]) > 9:
        user_history[ctx.author.id].pop(0)

    history = user_history[ctx.author.id]

    try:
        async with ctx.typing():
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant specializing in answering questions."},
                    *history
                ],
                max_tokens=1024
            )

        await ctx.send(response.choices[0].message.content)
        history.append({"role": "assistant", "content": response.choices[0].message.content})

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        print(f"Error in chat command: {e}")
        traceback.print_exc()

GEN_MEET_PROMPT = """
제목에 어울리는 회의 내용을 생성해주세요. GPT 사용 내역은 마지막에 추가해주세요. 전문적인 용어를 사용하고 최신 기술 트렌드를 반영해주세요.
GPT API는 ChatGPT, GPT-4, GPT-4o, Claude Opus, Gemini Pro 등을 사용할 수 있습니다. 다음 예시를 참고하고 간단하게 5-6줄로 작성하세요.

예시 1
제목: 스타일 변환 모델 관련 논의
내용:
스타일 변환 모델 관련 논의
- GPT 활용 스타일 변환 모델 방법 논의
- 프롬프트 관련 최적화 기법 조사
- 스타일 변환 학습을 위한 공개 데이터 조사
- 스타일 변환을 위한 독자적 seq2seq 모델 조사
GPT 사용 내역:
스타일 변환 모델을 학습 데이터를 생성하기 위해서 OpenAI API를 사용하였습니다.

예시 2
제목: 멀티모달 LLM 연구 논의
내용:
멀티모달 LLM 연구 논의
- 최근 멀티모달 모델인 LLaVA 성능 확인
- 최근 멀티모달 LLM 벤치마크 테스트 결과 분석
- 최근 멀티모달 LLM 추론 능력 논의
- 멀티모달 LLM에서의 연합학습 방법론 조사
GPT 사용 내역:
OpenAI ChatGPT API를 사용해서 멀티모달 LLM 연구 데이터 수집 및 분석을 수행하였습니다.
===

이제 다음 제목에 어울리는 회의 내용을 생성해주세요.
제목: {title}
""".strip()

@bot.command()
async def gen_meet(ctx, title: str):
    async with ctx.typing():
        print(title)
        response = await get_openai_response(GEN_MEET_PROMPT.format(title=title), model="gpt-4o")
        await ctx.send(response)

@bot.command()
async def clear(ctx):
    global user_history
    user_history = {}
    await ctx.send("Chat history has been cleared.")

@bot.command()
async def websumm(ctx, url: str, model: str = "gpt-4o-mini"):
    try:
        async with ctx.typing():
            summary = await summarize_website(client, url, model=model)

            await ctx.send(summary)

    except Exception as e:
        await ctx.send(f"An error occurred while summarizing the website: {str(e)}")
        print(f"Error in summarize command: {e}")
        traceback.print_exc()

# Replace 'YOUR_DISCORD_BOT_TOKEN' with your actual bot token
bot.run(os.getenv('DISCORD_BOT_TOKEN'))