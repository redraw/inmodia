import os
import time
import html
import json
import asyncio
import aiohttp
from hashlib import md5

import redis
from aiotg import Bot
from bs4 import BeautifulSoup


# redis
db = redis.StrictRedis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASS'),
    decode_responses=True
)
assert db.ping()
REDIS_KEY = os.getenv('REDIS_KEY')

# telegram
bot = Bot(api_token=os.environ['TELEGRAM_TOKEN'])
canal = bot.channel(os.environ['BOT_CHANNEL'])

# config
with open('config.json') as f:
    config = json.load(f)


async def enviar(avisos=[]):
    if not avisos:
        return

    print(f"enviando {len(avisos)} avisos...")
    lineas = []

    for aviso in avisos:
        texto = aviso.text.strip()

        if aviso.a:
            link = aviso.a['href']
            texto = "{texto} (<a href='{link}'>link</a>)".format(
                link=html.escape(link),
                texto=html.escape(texto)
            )

        lineas.append(f"🏠 {texto}")

    texto = "\n".join(lineas)
    print(texto)

    await canal.send_text(texto, parse_mode="HTML")


async def f5(session, url):
    print(f"f5 - {url}")
    avisos = []

    nuevos = set()
    visitados = db.zrange(REDIS_KEY, 0, -1)

    async with session.get(url) as r:
        content = await r.text()

    dom = BeautifulSoup(content, 'html.parser')

    selector = config.get('selector')
    keywords = config.get('keywords')

    for aviso in dom.select(selector):
        txt = aviso.text.lower()
        key = md5(txt.encode('utf8')).hexdigest()

        if key in visitados:
            continue

        if not keywords or any(kw in txt for kw in keywords):
            avisos.append(aviso)
            nuevos.add(key)

    if nuevos:
        ts = time.time()
        db.zadd(REDIS_KEY, **{key: ts for key in nuevos})

    return avisos


async def run():
    async def task(session, url):
        avisos = await f5(session, url)
        await enviar(avisos)

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[
            task(session, url)
            for url in config.get('urls', [])
        ])


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
