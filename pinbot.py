import logging
import discord
import lux
from utils import utils_image, utils_text
import pprint
import CONSTANTS
import itertools
import CONFIG_DEFAULT
import ast
import typing as ty

pers_d = {}
pers_l = []
pers = None

logging.basicConfig(level=logging.INFO)
CONFIG = lux.config.Config(botname="PINBOT", config_defaults=CONFIG_DEFAULT.PINBOT).load()


def check_auth(ctx: lux.contexter.Contexter) -> bool:
    return ctx.m.author.id in ctx.config["ALLOWED_IDS"] or \
           any(role.id in ctx.config["ALLOWED_IDS"] for role in ctx.m.author.roles) or \
           ctx.m.author.id == 129706966460137472 or \
           ctx.m.author.guild_permissions.manage_guild


client = lux.client.Lux(CONFIG, auth_function=check_auth,
                        activity=discord.Game(name=",,help | pinbot.page.link/invite for support"),
                        heartbeat_timeout=60, fetch_offline_members=False)


@client.command(authtype="whitelist", name="help")
async def get_help(ctx: lux.contexter.Contexter):
    message_list = [f"```{block}```" for block in
                    utils_text.format_rows([row[:-1] for row in CONSTANTS.PINBOT["COMMAND_HELP"]])]
    return message_list


@client.command(authtype="whitelist", name="help_note")
async def get_help(ctx: lux.contexter.Contexter):
    message_list = [f"```{block}```" for block in
                    utils_text.format_rows([row[:-2] + [row[-1]] for row in CONSTANTS.PINBOT["COMMAND_HELP"]])]
    return message_list


@client.command(authtype="whitelist", name="setup")
async def get_help(ctx: lux.contexter.Contexter):
    debug_message = ("```Note that:\n"
                     "  1) You need to first ,,map a channel to another one\n"
                     "  2) ,,setmax will determine how many pins the bot will allow before converting the pins\n"
                     "  2b) You can use ,,pinall after ,,setmax to retroactively convert pins. This is slow.\n"
                     "  3) The bot will only recognize pins on messages that were sent after the bot was added. This is due to API limitations.```")
    return debug_message


@client.command(authtype="whitelist", name="pinall")
async def pin_all(ctx: lux.contexter.Contexter):
    for source_channel in [client.get_channel(source) for source in ctx.config["PINMAP"].keys()]:
        while await process_pin(ctx=ctx, channel=source_channel):
            pass


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")])
async def whitelist(ctx: lux.contexter.Contexter):
    target_list = lux.dutils.mention_to_id(ctx.called_with["args"].split(" "))
    target = target_list[0]
    if not lux.zutils.check_int(target):
        target = ctx.find_role(target)
        if target:
            target = target.id
        else:
            return "Syntax error in [target]. Must be a mention, id, or role name"
    target = int(target)
    if target in ctx.config["ALLOWED_IDS"]:
        ctx.config["ALLOWED_IDS"].remove(target)
        target_role = ctx.find_role(target)
        if target_role:
            return f"Removed role `[{target_role.name}]` from command whitelist"
        target_member = ctx.m.guild.get_member(target)
        if target_member:
            return f"Removed member `[{str(target_member)}]` from command whitelist"
        else:
            return f"Removed ?unknown? `{target}` from command whitelist"
    else:
        ctx.config["ALLOWED_IDS"].append(int(target))
        target_role = ctx.find_role(target)
        if target_role:
            return f"Added role `[{target_role.name}]` to command whitelist"
        target_member = ctx.m.guild.get_member(target)
        if target_member:
            return f"Added member `[{str(target_member)}]` to command whitelist"
        else:
            return f"Added ?unknown? `{target}` to command whitelist"


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")])
async def setmax(ctx: lux.contexter.Contexter):
    args = ctx.called_with["args"].split(" ")
    try:
        ctx.config["PIN_THRESHOLD"] = int(args[0])

        for source_channel in [client.get_channel(source) for source in ctx.config["PINMAP"].keys()]:
            while await process_pin(ctx=ctx, channel=source_channel):
                pass

        return f"PIN_THRESHOLD set to be {args[0]}"
    except ValueError:
        return f"{args[0]} was not recognized as a valid number. Please try again."


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")], name="map")
async def map_channel(ctx: lux.contexter.Contexter):
    args = lux.dutils.mention_to_id(ctx.called_with["args"].split(" "))
    source_channel_id = int(args[0])
    destination_channel_id = int(args[1])

    res = await permission_check(ctx.m.guild, client.get_channel(source_channel_id), client.get_channel(destination_channel_id))
    if res:
        return res

    ctx.config["PINMAP"][source_channel_id] = destination_channel_id

    while await process_pin(ctx, channel=client.get_channel(source_channel_id)):
        pass

    return f"Mapped pins from <#{args[0]}> to be overflowed into <#{args[1]}>"


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")], name="unmap")
async def unmap_channel(ctx: lux.contexter.Contexter):
    args = lux.dutils.mention_to_id(ctx.called_with["args"].split(" "))
    if args[0] in ctx.config["PINMAP"]:
        del ctx.config["PINMAP"][args[0]]
        return f"No longer overflowing pins from <#{args[0]}>"
    else:
        return f"<#{args[0]}> is not currently mapped"


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")], name="stick")
async def stick(ctx: lux.contexter.Contexter):
    fixeds = ctx.config.get("FIXED", set())
    fixeds.add(int(ctx.called_with["args"].split(" ")[0]))
    ctx.config["FIXED"] = fixeds
    return f":white_check_mark:"


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")], name="unstick")
async def unstick(ctx: lux.contexter.Contexter):
    fixeds = ctx.config.get("FIXED", set())
    fixeds.remove(int(ctx.called_with["args"].split(" ")[0]))
    ctx.config["FIXED"] = fixeds
    # print(ctx.config["FIXED"])

    return f":white_check_mark:"


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")], name="setprefix")
async def set_prefix(ctx: lux.contexter.Contexter):
    new_prefix = ctx.called_with["args"].split(" ")[0]
    resp = f"Prefix changed from `{ctx.config['PREFIX']}` to `{new_prefix}`"
    ctx.config["PREFIX"] = new_prefix
    return resp


@client.command(authtype="whitelist", posts=[(CONFIG.save, "sync", "noctx")])
async def config(ctx: lux.contexter.Contexter):
    args = lux.dutils.mention_to_id(ctx.called_with["args"].split(" "))
    subcommand = args[0]
    if len(args) > 1:
        args = args[1:]

    if subcommand == "set":
        ctx.config[args[0]] = ast.literal_eval(args[1])
        return f"Set key `{args[0]}` to be `{ctx.config[args[0]]}`"
    elif subcommand == "print":
        return [f"```{block}```" for block in utils_text.format_rows(list(ctx.config.items()))]
    elif subcommand == "unset":
        resp = f"Unset {args[0]}, old value = {config[args[0]]}" if args[
                                                                        0] in config.keys() else "Invalid key, no changes made"
        CONFIG.reset_key(ctx.m.guild.id, args[0])
        return resp
    elif subcommand == "reset":
        CONFIG.reset(ctx.m.guild.id)
        return "Config reset to default"


@client.event
async def on_message_edit(message_bef: discord.Message, message_aft: discord.Message):
    ctx = lux.contexter.Contexter(message_aft, guild=message_bef.guild, configs=CONFIG, auth_func=check_auth)
    if ctx.m.channel.id in CONFIG.of(message_bef.guild)[
        "PINMAP"].keys() and not message_bef.pinned and message_aft.pinned:
        while await process_pin(ctx):
            pass


# @client.event
# async def on_message_edit(message_bef: discord.Message, message_aft: discord.Message):
#     ctx = lux.contexter.Contexter(message_aft, CONFIG, auth_func=check_auth)
#     if ctx.m.channel.id in CONFIG.of(message_bef.guild)[
#         "PINMAP"].keys() and not message_bef.pinned and message_aft.pinned:
#         await process_pin(ctx)


@client.append_event
async def on_message(message: discord.Message):
    if message.guild is None and message.author != client.user:
        channel: ty.Optional[discord.abc.Messageable] = client.get_channel(541021292116312066)
        if channel is not None:
            emb_resp = discord.Embed(
                title=f"{message.author}",
                description=f"{message.content}",
                timestamp=message.created_at
            )
            emb_resp.set_footer(text=message.created_at)

            await channel.send(embed=emb_resp)
            print("", flush=True)
        await message.author.send(content="For support, join the server at <http://pinbot.page.link/invite>")
        h = await get_help.func(None)
        await message.author.send(content=f"Common problems: \n{h}")
        await message.author.send(
            content=f"To invite me to your server, use <https://discordapp.com/oauth2/authorize?client_id=535572077118488576&scope=bot&permissions=26688>")


# @client.event
# async def on_ready():
#     await client.change_presence(activity=discord.Game(name="pinbot.page.link/invite for support"))

@client.event
async def on_resumed():
    await client.change_presence(activity=discord.Game(name="pinbot.page.link/invite for support"))


async def permission_check(guild: discord.Guild, source: discord.TextChannel, destination: discord.TextChannel):
    output = ""
    if not source.permissions_for(guild.me).manage_messages:
        output += f"\n<Manage Messages> in {source.mention}"
    if not destination.permissions_for(guild.me).send_messages:
        output += f"\n<Send Messages> in {destination.mention}"
    if not destination.permissions_for(guild.me).embed_links:
        output += f"\n<Embed Links> in {destination.mention}"
    if output:
        return "I require permissions:" + output


async def process_pin(ctx: lux.contexter.Contexter, channel=None):
    print(f"Firing process pin with ctx {ctx}")
    if ctx.m.channel.id not in ctx.config["PINMAP"].keys():
        return

    res = await permission_check(ctx.m.guild, ctx.m.channel, ctx.find_channel(query=ctx.config["PINMAP"][ctx.m.channel.id], dynamic=True))

    if res:
        await ctx.m.channel.send(res)
        return

    if channel:
        channel_pins = await channel.pins()
    else:
        channel_pins = await ctx.m.channel.pins()

    if len(channel_pins) > ctx.config["PIN_THRESHOLD"]:
        sorted_pins = sorted(channel_pins, key=lambda x: x.created_at)

        fixeds = ctx.config.get("FIXED", set())

        earliest_pin = next(pin for pin in sorted_pins if pin.id not in fixeds)

        if earliest_pin:
            target_channel = ctx.find_channel(query=ctx.config["PINMAP"][earliest_pin.channel.id], dynamic=True)
            colour = None
            if "EMBED_COLOR_CALC" in ctx.config.keys() and ctx.config["EMBED_COLOR_CALC"]:
                avg_color = utils_image.average_color_url(earliest_pin.author.avatar_url)
                colour = discord.Colour.from_rgb(*avg_color)

            embed = lux.dutils.message2embed(earliest_pin, embed_color=colour)
            # embed.set_footer(text = f"{Pinned by {embed.footer.text})
            await target_channel.send(embed=embed)
            await earliest_pin.unpin()
            return True
    return False


def delta_messages(before: discord.Message, after: discord.Message):
    delta = set(lux.dutils.message2dict(before).items()) ^ set(lux.dutils.message2dict(after).items())
    delta_attrs = [i[0] for i in delta]
    # print(delta_attrs)
    return delta_attrs


client.run(CONFIG.TOKEN, bot=True, )
