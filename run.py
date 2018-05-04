import os
import time
import html
import asyncio
import aiohttp
from hashlib import md5

import redis
from aiotg import Bot
from bs4 import BeautifulSoup


BOT_CHANNEL = os.getenv('BOT_CHANNEL')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
URL = os.getenv('URL')
REDIS_KEY = os.getenv('REDIS_KEY')

db = redis.StrictRedis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASS'),
    decode_responses=True
)

assert db.ping()

bot = Bot(api_token=TELEGRAM_TOKEN)
canal = bot.channel(BOT_CHANNEL)


async def enviar(avisos=[]):
    if not avisos:
        return

    print(f"enviando {len(avisos)} avisos...")
    lineas = []

    for aviso in avisos:
        texto = aviso.text.strip()

        if aviso.a:
            link = aviso.a['href']
            texto = "<a href='{link}'>{texto}</a>".format(
                link=html.escape(link), 
                texto=html.escape(texto)
            )

        lineas.append(f"🏠 {texto}")

    texto = "\n".join(lineas)
    print(texto)

    await canal.send_text(texto, parse_mode="HTML")


async def f5():
    print("f5!")
    avisos = []

    nuevos = set()
    visitados = db.zrange(REDIS_KEY, 0, -1)

    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as r:
            content = await r.text()

    dom = BeautifulSoup(content, 'html.parser')

    for aviso in dom.select('.avisos p, .avisosconfoto'):
        txt = aviso.text.strip().encode('utf8')
        key = md5(txt).hexdigest()

        if key in visitados:
            continue

        if "particular" in aviso.text.lower():
            avisos.append(aviso)
            nuevos.add(key)

    if nuevos:
        ts = time.time()
        db.zadd(REDIS_KEY, **{key: ts for key in nuevos})

    return avisos


async def run():
    avisos = await f5()
    await enviar(avisos)


def handler(event, ctx):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


def sync(event, ctx):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(f5())


def clean(event, ctx):
    return db.zremrangebyrank(REDIS_KEY, 0, -1000)


def delete(event, ctx):
    return db.delete(REDIS_KEY)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    async def cron():
        errors = 0
        while errors < 5:
            try:
                await run()
                errors = 0
            except Exception as e:
                print(e)
                errors += 1
            finally:
                await asyncio.sleep(60 * 60)

    loop.run_until_complete(cron())
    loop.close()