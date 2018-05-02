import os
import asyncio
import aiohttp
import redis

from aiotg import Bot, Chat

from bs4 import BeautifulSoup
from hashlib import md5


BOT_CHANNEL = os.getenv('BOT_CHANNEL', '@inmueblesparticularlp')
URL = "http://clasificados.eldia.com/clasificados-alquiler-departamentos-1-dormitorio-la-plata"

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
    for aviso in avisos:
        texto = aviso.text.strip()
        link = aviso.a['href']
        payload = f"{texto}\n[{link}]({link})"
        await canal.send_text(payload, parse_mode="markdown")


async def f5(debug=False):
    print("f5!")
    avisos = []

    avisos_nuevos = {}
    avisos_visitados = db.hgetall('inmodia.avisos')

    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as r:
            content = await r.text()

    dom = BeautifulSoup(content, 'html.parser')

    for aviso in dom.select('.avisosconfoto'):
        txt = aviso.text.strip().encode('utf8')
        key = md5(txt).hexdigest()

        if key in avisos_visitados.keys():
            continue

        if "particular" in aviso.text.lower():
            avisos.append(aviso)
            avisos_nuevos[key] = True

    if avisos_nuevos:
        db.hmset('inmodia.avisos', avisos_nuevos)

    return avisos


async def cron():
    errors = 0
    while errors < 100:
        try:
            avisos = await f5()
            await spamear(avisos)
            errors = 0
        except Exception as e:
            print(e)
            errors += 1
        finally:
            await asyncio.sleep(60)


@bot.command("whoami")
async def whoami(chat, match):
    return await chat.reply(chat.sender["id"])


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(cron(), bot.loop())
    loop.run_until_complete(tasks)
    loop.close()