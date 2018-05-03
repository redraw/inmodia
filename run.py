import os
import time
import itertools
import asyncio
import aiohttp
import redis

from aiotg import Bot, Chat

from bs4 import BeautifulSoup
from hashlib import md5


BOT_CHANNEL = os.getenv('BOT_CHANNEL', '@inmueblesparticularlp')
URL = "http://clasificados.eldia.com/clasificados-alquiler-departamentos-1-dormitorio-la-plata"
NAMESPACE = os.getenv('NAMESPACE', 'inmodia.avisos')

db = redis.StrictRedis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=os.getenv('REDIS_PORT', 6379),
    password=os.getenv('REDIS_PASS'),
    decode_responses=True
)

assert db.ping()

bot = Bot(api_token=os.environ['TELEGRAM_TOKEN'])
canal = bot.channel(BOT_CHANNEL)


async def spamear(avisos=[]):
    print(f"spameando {len(avisos)} avisos...")
    lineas = []

    for aviso in avisos:
        texto = aviso.text.strip()
        link = aviso.a['href'] if aviso.a else None
        linea = "🏠 "

        if link:
            linea += f"[{texto}]({link})"
        else:
            linea += texto

        lineas.append(linea)

    await canal.send_text("\n".join(lineas), parse_mode="markdown")


async def f5():
    print("f5!")
    avisos = []

    avisos_nuevos = set()
    avisos_visitados = db.zrange(NAMESPACE, 0, -1)

    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as r:
            content = await r.text()

    dom = BeautifulSoup(content, 'html.parser')

    for aviso in dom.select('.avisos p, .avisosconfoto'):
        txt = aviso.text.strip().encode('utf8')
        key = md5(txt).hexdigest()

        if key in avisos_visitados:
            continue

        if "particular" in aviso.text.lower():
            avisos.append(aviso)
            avisos_nuevos.add(key)

    if avisos_nuevos:
        ts = time.time()
        db.zadd(NAMESPACE, **{key: ts for key in avisos_nuevos})

    return avisos


async def run():
    avisos = await f5()
    await spamear(avisos)


def handler(event, ctx):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


def sync(event, ctx):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(f5())


def clean(event, ctx):
    """me quedo con los ultimos 1000"""
    db.zremrangebyrank(NAMESPACE, 0, -1000)


if __name__ == '__main__':

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