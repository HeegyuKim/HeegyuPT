import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import schedule
import time
import asyncio
import os

CHANNEL_ID = os.environ.get("RESTAURANT_CHANNEL_ID") # 1255031256555458600 # Heegyupt-lab

async def get_menu():
    # 웹드라이버 설정
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # 웹페이지 접속
    url = "https://portal.ajou.ac.kr/main.do"
    driver.get(url)

    # 식당 버튼 목록
    restaurant_buttons = ['기숙사식당', '교직원식당']
    
    menu_text = "오늘의 식당 메뉴:\n\n"

    # 각 식당 메뉴 가져오기
    for restaurant in restaurant_buttons:
        # 식당 버튼 찾기 및 클릭
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//em[text()='{restaurant}']"))
        )
        button.click()
        
        # 메뉴 로딩 대기
        time.sleep(2)
        
        # 메뉴 내용 가져오기
        menu_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "course-contents"))
        )
        
        menu_text += f"## {restaurant} 메뉴:\n{menu_content.text}\n\n"

    # 브라우저 종료
    driver.quit()

    return menu_text

async def send_menu(bot):
    print("Sending menu...")
    channel = bot.get_channel(int(CHANNEL_ID))
    menu = await get_menu()
    await channel.send(menu)

if __name__ == "__main__":
    import asyncio
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')
        await send_menu(bot)
    
    bot.run(os.environ.get("DISCORD_BOT_TOKEN"))