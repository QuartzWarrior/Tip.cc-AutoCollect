from asyncio import TimeoutError, sleep, CancelledError
from datetime import datetime, UTC
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Formatter,
    StreamHandler,
    getLogger,
)
from math import acosh, asinh, atanh, ceil, cos, cosh, e, erf, exp
from math import fabs as abs
from math import factorial, floor
from math import fmod as mod
from math import (
    gamma,
    gcd,
    hypot,
    log,
    log1p,
    log2,
    log10,
    pi,
    pow,
    sin,
    sinh,
    sqrt,
    tan,
    tau,
)
from os import listdir
from random import randint, uniform
from re import compile
from time import time
from urllib.parse import quote, unquote

from aiohttp import ClientSession
from art import tprint
from discord import Client, HTTPException, LoginFailure, Message, NotFound, Status, Embed
from discord.ext import tasks
from questionary import checkbox, select, text


class ColourFormatter(
    Formatter
):  # Taken from discord.py-self and modified to my liking.

    LEVEL_COLOURS = [
        (DEBUG, "\x1b[40;1m"),
        (INFO, "\x1b[34;1m"),
        (WARNING, "\x1b[33;1m"),
        (ERROR, "\x1b[31m"),
        (CRITICAL, "\x1b[41m"),
    ]

    FORMATS = {
        level: Formatter(
            f"\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s \x1b[30;1m(%(filename)s:%(lineno)d)\x1b[0m",
            "%d-%b-%Y %I:%M:%S %p",
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[DEBUG]

        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[31m{text}\x1b[0m"

        output = formatter.format(record)

        record.exc_text = None
        return output


handler = StreamHandler()
formatter = ColourFormatter()

handler.setFormatter(formatter)
logger = getLogger("tipcc_autocollect")
logger.addHandler(handler)
logger.setLevel("INFO")


def cbrt(x):
    return pow(x, 1 / 3)


try:
    from ujson import dump, load, JSONDecodeError
except (ModuleNotFoundError, ImportError):
    logger.warning("ujson not found, using json instead.")
    from json import dump, load, JSONDecodeError
else:
    logger.info("ujson found, using ujson.")

channel = None

print("\033[0;35m")
tprint("QuartzWarrior", font="smslant")
print("\033[0m")

try:
    with open("config.json", "r") as f:
        config = load(f)
except (FileNotFoundError, JSONDecodeError):
    config = {
        "TOKEN": "",
        "PRESENCE": "",
        "FIRST": True,
        "ID": 0,
        "CHANNEL_ID": 0,
        "TARGET_AMOUNT": 0.0,
        "WHITELIST": [],
        "BLACKLIST": [],
        "WHITELIST_ON": False,
        "BLACKLIST_ON": False
    }
    with open("config.json", "w") as f:
        dump(config, f, indent=4)

try:
    with open("servers/default.json", "r") as f:
        default = load(f)
except (FileNotFoundError, JSONDecodeError):
    default = {
        "CPM": [200, 310],
        "SMART_DELAY": True,
        "RANGE_DELAY": False,
        "DELAY": [0, 1],
        "BANNED_WORDS": ["bot", "ban"],
        "MESSAGES": [],
        "CHANNEL_WHITELIST": [],
        "CHANNEL_BLACKLIST": [],
        "IGNORE_USERS": [],
        "SEND_MESSAGE": False,
        "CHANNEL_WHITELIST_ON": False,
        "CHANNEL_BLACKLIST_ON": False,
        "IGNORE_DROPS_UNDER": 0.0,
        "IGNORE_TIME_UNDER": 0.0,
        "IGNORE_THRESHOLDS": [],
        "DISABLE_AIRDROP": False,
        "DISABLE_TRIVIADROP": False,
        "DISABLE_MATHDROP": False,
        "DISABLE_PHRASEDROP": False,
        "DISABLE_REDPACKET": False,
        "DELAY_AIRDROP": True,
        "DELAY_TRIVIADROP": True,
        "DELAY_MATHDROP": True,
        "DELAY_PHRASEDROP": True,
        "DELAY_REDPACKET": False,
    }
    with open("servers/default.json", "w") as f:
        dump(default, f, indent=4)

token_regex = compile(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27,}")
decimal_regex = compile(r"^-?\d+\.\d+$")


def validate_token(token):
    if token_regex.search(token):
        return True
    else:
        return False


def validate_decimal(decimal):
    if decimal_regex.match(decimal):
        return True
    else:
        return False


def validate_threshold_chance(s):
    try:
        threshold, chance = s.split(":")
        return (
                validate_decimal(threshold)
                and chance.isnumeric()
                and 0 <= int(chance) <= 100
        )
    except ValueError:
        if s == "":
            return True
        return False


if config["TOKEN"] == "":
    token_input = text(
        "What is your discord token?",
        qmark="->",
        validate=lambda x: validate_token(x),
    ).ask()
    if token_input is not None:
        config["TOKEN"] = token_input
        with open("config.json", "w") as f:
            dump(config, f, indent=4)
        logger.debug("Token saved.")

if config["FIRST"]:
    config["PRESENCE"] = select(
        "What do you want your presence to be?",
        choices=[
            "online",
            "idle",
            "dnd",
            "invisible",
        ],
        default="invisible",
        qmark="->",
    ).ask()
    default["CPM"][0] = int(
        text(
            "What is your minimum CPM (Characters Per Minute)?\nThis is to make the phrase drop collector more legit.\nRemember, the higher the faster!",
            default="200",
            qmark="->",
            validate=lambda x: (validate_decimal(x) or x.isnumeric()) and float(x) >= 0,
        ).ask()
    )
    default["CPM"][1] = int(
        text(
            "What is your maximum CPM (Characters Per Minute)?\nThis is to make the phrase drop collector more legit.\nRemember, the higher the faster!",
            default="310",
            qmark="->",
            validate=lambda x: (validate_decimal(x) or x.isnumeric()) and float(x) >= 0,
        ).ask()
    )
    config["FIRST"] = False
    default["DISABLE_AIRDROP"] = False
    default["DISABLE_TRIVIADROP"] = False
    default["DISABLE_MATHDROP"] = False
    default["DISABLE_PHRASEDROP"] = False
    default["DISABLE_REDPACKET"] = False
    default["DELAY_AIRDROP"] = True
    default["DELAY_TRIVIADROP"] = True
    default["DELAY_MATHDROP"] = True
    default["DELAY_PHRASEDROP"] = True
    default["DELAY_REDPACKET"] = False
    disable_drops = checkbox(
        "What drop types do you want to disable? (Leave blank for none)",
        choices=[
            "airdrop",
            "triviadrop",
            "mathdrop",
            "phrasedrop",
            "redpacket",
        ],
        qmark="->",
    ).ask()
    if not disable_drops:
        disable_drops = []
    if "airdrop" in disable_drops:
        default["DISABLE_AIRDROP"] = True
    if "triviadrop" in disable_drops:
        default["DISABLE_TRIVIADROP"] = True
    if "mathdrop" in disable_drops:
        default["DISABLE_MATHDROP"] = True
    if "phrasedrop" in disable_drops:
        default["DISABLE_PHRASEDROP"] = True
    if "redpacket" in disable_drops:
        default["DISABLE_REDPACKET"] = True
    delay_drops = checkbox(
        "What drop types do you want to enable delay for? (Leave blank for none)",
        choices=[
            "airdrop",
            "triviadrop",
            "mathdrop",
            "phrasedrop",
            "redpacket",
        ],
        qmark="->",
    ).ask()
    if not delay_drops:
        delay_drops = []
    if "airdrop" in delay_drops:
        default["DELAY_AIRDROP"] = True
    if "triviadrop" in delay_drops:
        default["DELAY_TRIVIADROP"] = True
    if "mathdrop" in delay_drops:
        default["DELAY_MATHDROP"] = True
    if "phrasedrop" in delay_drops:
        default["DELAY_PHRASEDROP"] = True
    if "redpacket" in delay_drops:
        default["DELAY_REDPACKET"] = True
    ignore_drops_under = text(
        "What is the minimum amount of money you want to ignore?",
        default="0",
        qmark="->",
        validate=lambda x: ((validate_decimal(x) or x.isnumeric()) and float(x) >= 0)
                           or x == "",
    ).ask()
    if ignore_drops_under != "":
        default["IGNORE_DROPS_UNDER"] = float(ignore_drops_under)
    else:
        default["IGNORE_DROPS_UNDER"] = 0.0
    ignore_time_under = text(
        "What is the minimum time you want to ignore?",
        default="0",
        qmark="->",
        validate=lambda x: ((validate_decimal(x) or x.isnumeric()) and float(x) >= 0)
                           or x == "",
    ).ask()
    if ignore_time_under != "":
        default["IGNORE_TIME_UNDER"] = float(ignore_time_under)
    else:
        default["IGNORE_TIME_UNDER"] = 0.0
    ignore_thresholds = text(
        "Enter your ignore thresholds and chances in the format 'threshold:chance', separated by commas (e.g. '0.10:10,0.20:20')",
        validate=lambda x: all(validate_threshold_chance(pair) for pair in x.split(","))
                           or x == "",
        default="",
        qmark="->",
    ).ask()
    if ignore_thresholds != "":
        default["IGNORE_THRESHOLDS"] = [
            {"threshold": float(pair.split(":")[0]), "chance": int(pair.split(":")[1])}
            for pair in ignore_thresholds.split(",")
        ]
    else:
        default["IGNORE_THRESHOLDS"] = []
    smart_delay = select(
        "Do you want to enable smart delay? (This will make the bot wait for the drop to end before claiming it)",
        choices=["yes", "no"],
        qmark="->",
    ).ask()
    if smart_delay == "yes":
        default["SMART_DELAY"] = True
    else:
        default["SMART_DELAY"] = False
        range_delay = select(
            "Do you want to enable range delay? (This will make the bot wait for a random delay between two values)",
            choices=["yes", "no"],
            qmark="->",
        ).ask()
        if range_delay == "yes":
            default["RANGE_DELAY"] = True
            min_delay = text(
                "What is the minimum delay you want to use in seconds?",
                validate=lambda x: (validate_decimal(x) or x.isnumeric()) and float(x) >= 0,
                qmark="->",
            ).ask()
            max_delay = text(
                "What is the maximum delay you want to use in seconds?",
                validate=lambda x: (validate_decimal(x) or x.isnumeric()) and float(x) >= 0,
                qmark="->",
            ).ask()
            default["DELAY"] = [float(min_delay), float(max_delay)]
        else:
            manual_delay = text(
                "What is the delay you want to use in seconds? (Leave blank for none)",
                validate=lambda x: (validate_decimal(x) or x.isnumeric()) or x == "",
                default="0",
                qmark="->",
            ).ask()
            if manual_delay != "":
                default["DELAY"] = [float(manual_delay), float(manual_delay)]
            else:
                default["DELAY"] = [0, 0]
    banned_words = text(
        "What words do you want to ban? Separate each word with a comma.",
        validate=lambda x: len(x) > 0 or x == "",
        qmark="->",
    ).ask()
    if not banned_words:
        banned_words = []
    else:
        banned_words = banned_words.split(",")
    default["BANNED_WORDS"] = banned_words
    send_messages = select(
        "Do you want to send messages after claiming a drop?",
        choices=["yes", "no"],
        qmark="->",
    ).ask()
    default["SEND_MESSAGE"] = send_messages == "yes"
    if default["SEND_MESSAGE"]:
        messages = text(
            "What messages do you want to send after claiming a drop? Separate each message with a comma.",
            validate=lambda x: len(x) > 0 or x == "",
            qmark="->",
        ).ask()
        if not messages:
            messages = []
        else:
            messages = messages.split(",")
        default["MESSAGES"] = messages
    enable_whitelist = select(
        "Do you want to enable whitelist? (This will only enter drops in the servers you specify)",
        choices=["yes", "no"],
        qmark="->",
    ).ask()
    config["WHITELIST_ON"] = enable_whitelist == "yes"
    if not config["WHITELIST_ON"]:
        enable_blacklist = select(
            "Do you want to enable blacklist? (This will ignore drops in the servers you specify)",
            choices=["yes", "no"],
            qmark="->",
        ).ask()
        config["BLACKLIST_ON"] = enable_blacklist == "yes"
        if config["BLACKLIST_ON"]:
            blacklist = text(
                "What servers do you want to blacklist? Separate each server ID with a comma.",
                validate=lambda x: (
                                           len(x) > 0
                                           and all(y.isnumeric() and 17 <= len(y) <= 19 for y in x.split(","))
                                   )
                                   or x == "",
                qmark="->",
            ).ask()
            if not blacklist:
                blacklist = []
            else:
                blacklist = [int(x) for x in blacklist.split(",")]
            config["BLACKLIST"] = blacklist
    else:
        whitelist = text(
            "What servers do you want to whitelist? Separate each server ID with a comma.",
            validate=lambda x: (
                                       len(x) > 0
                                       and all(y.isnumeric() and 17 <= len(y) <= 19 for y in x.split(","))
                               )
                               or x == "",
            qmark="->",
        ).ask()
        if not whitelist:
            whitelist = []
        else:
            whitelist = [int(x) for x in whitelist.split(",")]
        config["WHITELIST"] = whitelist
    enable_channel_whitelist = select(
        "Do you want to enable channel whitelist? (This will only enter drops in the channels you specify)",
        choices=["yes", "no"],
        qmark="->",
    ).ask()
    default["CHANNEL_WHITELIST_ON"] = enable_channel_whitelist == "yes"
    if not default["CHANNEL_WHITELIST_ON"]:
        enable_blacklist = select(
            "Do you want to enable channel blacklist? (This will ignore drops in the channels you specify)",
            choices=["yes", "no"],
            qmark="->",
        ).ask()
        default["CHANNEL_BLACKLIST_ON"] = enable_blacklist == "yes"
        if default["CHANNEL_BLACKLIST_ON"]:
            blacklist = text(
                "What channels do you want to blacklist? Separate each channel ID with a comma.",
                validate=lambda x: (
                                           len(x) > 0
                                           and all(y.isnumeric() and 17 <= len(y) <= 19 for y in x.split(","))
                                   )
                                   or x == "",
                qmark="->",
            ).ask()
            if not blacklist:
                blacklist = []
            else:
                blacklist = [int(x) for x in blacklist.split(",")]
            default["CHANNEL_BLACKLIST"] = blacklist
    else:
        whitelist = text(
            "What channels do you want to whitelist? Separate each channel ID with a comma.",
            validate=lambda x: (
                                       len(x) > 0
                                       and all(y.isnumeric() and 17 <= len(y) <= 19 for y in x.split(","))
                               )
                               or x == "",
            qmark="->",
        ).ask()
        if not whitelist:
            whitelist = []
        else:
            whitelist = [int(x) for x in whitelist.split(",")]
        default["CHANNEL_WHITELIST"] = whitelist
    ignore_users = text(
        "What users do you want to ignore? Separate each user ID with a comma.",
        validate=lambda x: (
                                   len(x) > 0
                                   and all(y.isnumeric() and 17 <= len(y) <= 19 for y in x.split(","))
                           )
                           or x == "",
        qmark="->",
    ).ask()
    if not ignore_users:
        ignore_users = []
    else:
        ignore_users = [int(x) for x in ignore_users.split(",")]
    default["IGNORE_USERS"] = ignore_users
    user_id = int(
        text(
            "What is your main accounts id?\n\nIf you are sniping from your main, put your main accounts' id.",
            validate=lambda x: x.isnumeric() and 17 <= len(x) <= 19,
            qmark="->",
        ).ask()
    )
    config["ID"] = user_id
    channel_id = int(
        text(
            "What is the channel id where you want your alt to tip your main?\n(Remember, the tip.cc bot has to be in the server with this channel.)\n\nIf None, send 1.",
            validate=lambda x: x.isnumeric() and (17 <= len(x) <= 19 or int(x) == 1),
            default="1",
            qmark="->",
        ).ask()
    )
    config["CHANNEL_ID"] = channel_id
    target_amount = float(
        text(
            "What is the target amount you want to tip your main at? Set it to 0 to disable.",
            validate=lambda x: validate_decimal(x) or x.isnumeric(),
            default="0",
            qmark="->",
        ).ask()
    )
    config["TARGET_AMOUNT"] = target_amount
    with open("config.json", "w") as f:
        dump(config, f, indent=4)
    logger.debug("Config saved.")

banned_words = set(default["BANNED_WORDS"])

client = Client(
    status=(
        Status.invisible
        if config["PRESENCE"] == "invisible"
        else (
            Status.online
            if config["PRESENCE"] == "online"
            else (
                Status.idle
                if config["PRESENCE"] == "idle"
                else Status.dnd if config["PRESENCE"] == "dnd" else Status.unknown
            )
        )
    )
)


@client.event
async def on_ready():
    global channel
    channel = client.get_channel(config["CHANNEL_ID"])
    logger.info(f"Logged in as {client.user.name}#{client.user.discriminator}")
    if config["CHANNEL_ID"] != 1 and client.user.id != config["ID"]:
        tipping.start()
        logger.info("Tipping started.")
    else:
        logger.warning("Disabling tipping as requested.")


@tasks.loop(minutes=10.0)
async def tipping():
    await channel.send("$bals top")
    logger.debug("Sent command: $bals top")
    answer = await client.wait_for(
        "message",
        check=lambda message: message.author.id == 617037497574359050
                              and message.embeds,
    )
    try:
        total_money = float(
            answer.embeds[0]
            .fields[-1]
            .value.split("$")[1]
            .replace(",", "")
            .replace("**", "")
            .replace(")", "")
            .replace("\u200b", "")
            .strip()
        )
    except Exception as e:
        logger.exception("Error occurred while getting total money, skipping tipping.")
        total_money = 0.0
    logger.debug(f"Total money: {total_money}")
    if total_money < config["TARGET_AMOUNT"]:
        logger.info("Target amount not reached, skipping tipping.")
        return
    try:
        pages = int(answer.embeds[0].author.name.split("/")[1].replace(")", ""))
    except:
        pages = 1
    if not answer.components:
        button_disabled = True
    for _ in range(pages):
        try:
            button = answer.components[0].children[1]
            button_disabled = button.disabled
        except:
            button_disabled = True
        for crypto in answer.embeds[0].fields:
            if "Estimated total" in crypto.name:
                continue
            if "DexKit" in crypto.name:
                content = f"$tip <@{config['ID']}> all {crypto.name.replace('*', '').replace('DexKit (BSC)', 'bKIT')}"
            else:
                content = f"$tip <@{config['ID']}> all {crypto.name.replace('*', '')}"
            async with channel.typing():
                await sleep(len(content) / randint(default["CPM"][0], default["CPM"][1]) * 60)
            await channel.send(content)
            logger.debug(f"Sent tip: {content}")
        if button_disabled:
            try:
                await answer.components[0].children[2].click()
                logger.debug("Clicked next page button")
                return
            except IndexError:
                try:
                    await answer.components[0].children[0].click()
                    logger.debug("Clicked first page button")
                    return
                except IndexError:
                    return
        else:
            await button.click()
            await sleep(1)
            answer = await channel.fetch_message(answer.id)


@tipping.before_loop
async def before_tipping():
    logger.info("Waiting for bot to be ready before tipping starts...")
    await client.wait_until_ready()


@client.event
async def on_message(original_message: Message):
    if f"{original_message.channel.id}.json" in listdir("servers"):
        try:
            with open(f"servers/{original_message.channel.id}.json", "r") as f:
                configuration = load(f)
        except (FileNotFoundError, JSONDecodeError):
            configuration = default
    else:
        configuration = default
    if (any([True if word in original_message.content.split(" ")[0] else False for word in
             ["airdrop", "phrasedrop", "triviadrop", "mathdrop", "redenvelope", "redpacket"]]) and
            not any(word in original_message.content.lower() for word in banned_words)
            and (
                    not config["WHITELIST_ON"]
                    or (
                            config["WHITELIST_ON"]
                            and original_message.guild.id in config["WHITELIST"]
                    )
            )
            and (
                    not config["BLACKLIST_ON"]
                    or (
                            config["BLACKLIST_ON"]
                            and original_message.guild.id not in config["BLACKLIST"]
                    )
            )
            and (
                    not configuration["CHANNEL_WHITELIST_ON"]
                    or (
                            configuration["CHANNEL_WHITELIST_ON"]
                            and original_message.channel.id in configuration["CHANNEL_WHITELIST"]
                    )
            )
            and (
                    not configuration["CHANNEL_BLACKLIST_ON"]
                    or (
                            configuration["CHANNEL_BLACKLIST_ON"]
                            and original_message.channel.id not in configuration["CHANNEL_BLACKLIST"]
                    )
            )
            and original_message.author.id not in configuration["IGNORE_USERS"]
    ):
        logger.debug(
            f"Detected drop in {original_message.channel.name}: {original_message.content}"
        )
        try:
            tip_cc_message = await client.wait_for(
                "message",
                check=lambda message: message.author.id == 617037497574359050
                                      and message.channel.id == original_message.channel.id
                                      and ((message.embeds
                                            and message.embeds[0].footer
                                            and "ends" in message.embeds[0].footer.text.lower()
                                            and str(original_message.author.id) in message.embeds[0].description) or (
                                                   "ends" in message.content.lower() and str(
                                               original_message.author.id) in message.content)),
                timeout=15,
            )
            logger.debug("Detected tip.cc message from drop.")
        except (TimeoutError, CancelledError):
            logger.exception(
                "Timeout occurred while waiting for tip.cc message, skipping."
            )
            return
        if tip_cc_message.embeds:
            embed = tip_cc_message.embeds[0]
        else:
            content_lines = tip_cc_message.content.split("\n")
            logger.debug(content_lines)
            timestamp = datetime.fromtimestamp(int(content_lines[-1].split("<t:")[1].split(":")[0].split(">")[0]), UTC)
            logger.debug(timestamp)
            embed = Embed(title=content_lines[0], description="\n".join(content_lines[1:len(content_lines) - 1]),
                          timestamp=timestamp)
            embed.set_footer(text=content_lines[-1])
        if "$" not in embed.description or "≈" not in embed.description:
            money = 0.0
            logger.debug("No money found, defaulting to 0")
        else:
            try:
                money = float(
                    embed.description.split("≈")[1]
                    .split(")")[0]
                    .strip()
                    .replace("$", "")
                    .replace(",", "")
                )
            except IndexError:
                logger.exception(
                    "Index error occurred during money splitting, skipping..."
                )
                return
        if money < configuration["IGNORE_DROPS_UNDER"]:
            logger.info(
                f"Ignored drop for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
            )
            return
        for threshold in configuration["IGNORE_THRESHOLDS"]:
            logger.debug(
                f"Checking threshold: {threshold['threshold']} with chance: {threshold['chance']}"
            )
            if money <= threshold["threshold"]:
                logger.debug(
                    f"Drop value {money} is less than or equal to threshold {threshold['threshold']}"
                )
                random_number = randint(0, 100)
                if random_number < threshold["chance"]:
                    logger.info(
                        f"Ignored drop from failed threshold for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                    )
                    return
        logger.debug(f"Money: {money}")
        logger.debug(f"Drop ends in: {embed.timestamp.timestamp() - time()}")
        drop_ends_in = embed.timestamp.timestamp() - time()
        if drop_ends_in < configuration["IGNORE_TIME_UNDER"]:
            logger.info(
                f"Ignored drop for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
            )
            return
        if (
                "An airdrop appears" in embed.title
                and configuration["DELAY_AIRDROP"]
                or "Trivia time - " in embed.title
                and configuration["DELAY_TRIVIADROP"]
                or "Math" in embed.title
                and configuration["DELAY_MATHDROP"]
                or "Phrase drop!" in embed.title
                and configuration["DELAY_PHRASEDROP"]
                or "appeared" in embed.title
                and configuration["DELAY_REDPACKET"]
        ):
            if configuration["SMART_DELAY"]:
                logger.debug("Smart delay enabled, waiting...")
                if drop_ends_in < 0:
                    logger.debug("Drop ended, skipping...")
                    return
                delay = drop_ends_in / 4
                logger.debug(f"Delay: {round(delay, 2)}")
                await sleep(delay)
                logger.info(f"Waited {round(delay, 2)} seconds before proceeding.")
            elif configuration["RANGE_DELAY"]:
                logger.debug("Range delay enabled, waiting...")
                delay = uniform(configuration["DELAY"][0], configuration["DELAY"][1])
                logger.debug(f"Delay: {delay}")
                await sleep(delay)
                logger.info(f"Waited {delay} seconds before proceeding.")
            elif configuration["DELAY"] != [0, 0]:
                logger.debug(f"Manual delay enabled, waiting {configuration['DELAY'][0]}...")
                await sleep(configuration["DELAY"][0])
                logger.info(f"Waited {configuration['DELAY'][0]} seconds before proceeding.")
        try:
            if "ended" in embed.footer.text.lower():
                logger.debug("Drop ended, skipping...")
                return
            elif "An airdrop appears" in embed.title and not configuration["DISABLE_AIRDROP"]:
                logger.debug("Airdrop detected, entering...")
                try:
                    button = tip_cc_message.components[0].children[0]
                except IndexError:
                    logger.exception(
                        "Index error occurred, meaning the drop most likely ended, skipping..."
                    )
                    return
                if "Enter airdrop" in button.label:
                    await button.click()
                    logger.info(
                        f"Entered airdrop in {original_message.channel.name} for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                    )
            elif "Phrase drop!" in embed.title and not configuration["DISABLE_PHRASEDROP"]:
                logger.debug("Phrasedrop detected, entering...")
                content = embed.description.replace("\n", "").replace("**", "")
                content = content.split("*")
                try:
                    content = content[1].replace("​", "").replace("\u200b", "").strip()
                except IndexError:
                    logger.exception("Index error occurred, skipping...")
                    return
                else:
                    logger.debug("Typing and sending message...")
                    length = len(content) / randint(configuration["CPM"][0], configuration["CPM"][1]) * 60
                    async with original_message.channel.typing():
                        await sleep(length)
                    await original_message.channel.send(content)
                    logger.info(
                        f"Entered phrasedrop in {original_message.channel.name} for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                    )
            elif "appeared" in embed.title and not configuration["DISABLE_REDPACKET"]:
                logger.debug("Redpacket detected, claiming...")
                try:
                    button = tip_cc_message.components[0].children[0]
                except IndexError:
                    logger.exception(
                        "Index error occurred, meaning the drop most likely ended, skipping..."
                    )
                    return
                if "envelope" in button.label:
                    await button.click()
                    logger.info(
                        f"Claimed envelope in {original_message.channel.name} for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                    )
            elif "Math" in embed.title and not configuration["DISABLE_MATHDROP"]:
                logger.debug("Mathdrop detected, entering...")
                content = embed.description.replace("\n", "").replace("**", "")
                content = content.split("`")
                try:
                    content = content[1].replace("​", "").replace("\u200b", "")
                except IndexError:
                    logger.exception("Index error occurred, skipping...")
                    return
                else:
                    logger.debug("Evaluating math and sending message...")
                    answer = eval(content)
                    if isinstance(answer, float) and answer.is_integer():
                        answer = int(answer)
                    logger.debug(f"Answer: {answer}")
                    if not configuration["SMART_DELAY"] and configuration["DELAY"] == 0:
                        length = len(str(answer)) / randint(configuration["CPM"][0], configuration["CPM"][1]) * 60
                        async with original_message.channel.typing():
                            await sleep(length)
                    await original_message.channel.send(answer)
                    logger.info(
                        f"Entered mathdrop in {original_message.channel.name} for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                    )
            elif "Trivia time - " in embed.title and not configuration["DISABLE_TRIVIADROP"]:
                logger.debug("Triviadrop detected, entering...")
                category = embed.title.split("Trivia time - ")[1].strip()
                bot_question = embed.description.replace("**", "").split("*")[1]
                async with ClientSession() as session:
                    async with session.get(
                            f"https://raw.githubusercontent.com/QuartzWarrior/OTDB-Source/main/{quote(category)}.csv"
                    ) as resp:
                        lines = (await resp.text()).splitlines()
                        for line in lines:
                            question, answer = line.split(",")
                            if bot_question.strip() == unquote(question).strip():
                                answer = unquote(answer).strip()
                                try:
                                    buttons = tip_cc_message.components[0].children
                                except IndexError:
                                    logger.exception(
                                        "Index error occurred, meaning the drop most likely ended, skipping..."
                                    )
                                    return
                                for button in buttons:
                                    if button.label.strip() == answer:
                                        await button.click()
                                logger.info(
                                    f"Entered triviadrop in {original_message.channel.name} for {embed.description.split('**')[1]} {embed.description.split('**')[2].split(')')[0].replace(' (', '')}"
                                )
            else:
                logger.debug(f"Drop type non existent?!, skipping...\n{embed.title}")
                return
            if configuration["SEND_MESSAGE"]:
                message = configuration["MESSAGES"][
                    randint(0, len(configuration["MESSAGES"]) - 1)
                ]
                length = len(message) / randint(configuration["CPM"][0], configuration["CPM"][1]) * 60
                async with original_message.channel.typing():
                    await sleep(length)
                await original_message.channel.send(message)
                logger.info(f"Sent message: {message}")
            return

        except AttributeError:
            logger.exception("Attribute error occurred")
            return
        except HTTPException:
            logger.exception("HTTP exception occurred")
            return
        except NotFound:
            logger.exception("Not found exception occurred")
            return
    elif original_message.content.startswith(
            ("$airdrop", "$triviadrop", "$mathdrop", "$phrasedrop", "$redpacket")
    ) and any(word in original_message.content.lower() for word in banned_words):
        logger.info(
            f"Banned word detected in {original_message.channel.name}, skipping..."
        )
    elif original_message.content.startswith(
            ("$airdrop", "$triviadrop", "$mathdrop", "$phrasedrop", "$redpacket")
    ) and (
            config["WHITELIST_ON"] and original_message.guild.id not in config["WHITELIST"]
    ):
        logger.info(
            f"Whitelist enabled and drop not in whitelist, skipping {original_message.channel.name}..."
        )
    elif original_message.content.startswith(
            ("$airdrop", "$triviadrop", "$mathdrop", "$phrasedrop", "$redpacket")
    ) and (config["BLACKLIST_ON"] and original_message.guild.id in config["BLACKLIST"]):
        logger.info(
            f"Blacklist enabled and drop in blacklist, skipping {original_message.channel.name}..."
        )
    elif original_message.content.startswith(
            ("$airdrop", "$triviadrop", "$mathdrop", "$phrasedrop", "$redpacket")
    ) and (
            configuration["CHANNEL_BLACKLIST_ON"]
            and original_message.channel.id in configuration["CHANNEL_BLACKLIST"]
    ):
        logger.info(
            f"Channel blacklist enabled and drop in channel blacklist, skipping {original_message.channel.name}..."
        )
    elif (
            original_message.content.startswith(
                ("$airdrop", "$triviadrop", "$mathdrop", "$phrasedrop", "$redpacket")
            )
            and original_message.author.id in configuration["IGNORE_USERS"]
    ):
        logger.info(
            f"User in ignore list detected in {original_message.channel.name}, skipping..."
        )


if __name__ == "__main__":
    try:
        client.run(config["TOKEN"], log_handler=handler, log_formatter=formatter)
    except LoginFailure:
        logger.critical("Invalid token, restart the program.")
        config["TOKEN"] = ""
        with open("config.json", "w") as f:
            dump(config, f, indent=4)
