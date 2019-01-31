import asyncio
import logging

import discord
import praw
from praw import models as praw_models
import lux
import TOKENS
logging.basicConfig(level=logging.INFO)

CONFIG = lux.config.Config(botname="KVSRSTREAM").load()
client = lux.client.Lux(CONFIG)

redd = praw.Reddit(client_id=TOKENS.REDDIT_ID, client_secret=TOKENS.REDDIT_SECRET, user_agent="KVStream")

@client.event
async def on_message(mess_in):
    print("message received?", flush=True)


@asyncio.coroutine
async def astream():
    for submission in redd.subreddit("all").stream.submissions():
        print("Yielding...?", flush=True)
        embed = discord.Embed()
        embed.set_author(name="/u/"+submission.author.name, icon_url=submission.author.icon_img,
                         url=f"https://www.reddit.com/u/{submission.author.name}")
        embed.description = lux.zutils.threshold_string(submission.selftext, 1000)
        embed.set_footer(text=f"Submitted at {submission.created_utc}")
        await client.get_channel(540332172670926851).send(content=submission.shortlink, embed=embed)

client.loop.create_task(astream())
client.run(CONFIG.TOKEN)
