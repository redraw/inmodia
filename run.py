import os
import asyncio
import time
import aiohttp

from aiotg import Bot, Chat

from bs4 import BeautifulSoup
from hashlib import md5

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = Bot(api_token=TELEGRAM_TOKEN)
canal = bot.channel('@inmueblesparticularlp')

avisos = {}

URL = "http://clasificados.eldia.com/clasificados-alquiler-departamentos-1-dormitorio-la-plata"


async def f5():
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as r:
            content = await r.text()
            dom = BeautifulSoup(content, 'html.parser')

            for aviso in dom.select('.avisosconfoto'):
                texto = aviso.text.strip()
                key = md5(texto.encode('utf8')).hexdigest()

                if key in avisos.keys():
                    continue

                if "particular" in texto.lower():
                    link = aviso.a['href']
                    avisos[key] = {'texto': texto, 'link': link}
                    payload = f"{texto}\n[{link}]({link})"
                    await canal.send_text(payload, parse_mode="markdown")


async def cron():
    while True:
        await f5()
        time.sleep(60 * 60)


if __name__ == '__main__':
    bot.run()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cron())
    loop.close()