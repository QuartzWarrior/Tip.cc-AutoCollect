import logging
from asyncio import sleep
from logging import Formatter, StreamHandler, getLogger
from re import compile
from pushbullet import Pushbullet
from discord import Client, Message
from discord.ext import tasks


class AirdropBot(Client):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.logger = self.setup_logger()
        self.config = self.load_config(config_path)
        self.pushbullet = Pushbullet(self.config.get("PUSHBULLET_API_KEY", ""))
        self.airdrop_regex = compile(r"[$]airdrop|[$]phrasedrop|[$]mathdrop|[$]triviadrop|[$]redpacket")
        self.stake_regex = compile(r"https?:\/\/stake\.(us|com)\/settings(?:\/[^\s?]*)?(?:\?[^\s]*)?")
        self.detected_stake_codes = set()  # Keeps track of detected Stake.us bonus codes

    def setup_logger(self):
        """Setup logger with custom formatting."""
        logger = getLogger("AirdropBot")
        logger.setLevel(self.config.get("LOG_LEVEL", logging.INFO))
        handler = StreamHandler()
        formatter = Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def load_config(self, config_path):
        """Load the configuration from the JSON file."""
        import json
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    async def on_ready(self):
        """Triggered when the bot is ready."""
        self.logger.info(f"Logged in as {self.user.name}#{self.user.discriminator}")
        self.logger.info(f"Monitoring airdrops and events...")

    async def on_message(self, message: Message):
        """Monitor events and handle drops."""
        if message.author.bot or not message.embeds:
            return

        if self.airdrop_regex.search(message.content):
            await self.handle_airdrop(message)
        elif self.stake_regex.match(message.content):
            await self.handle_stake_drop(message)

    async def handle_airdrop(self, message):
        """Handle airdrop and send Pushbullet notification."""
        try:
            embed = message.embeds[0]
            drop_info = embed.description

            # Extract drop details
            drop_user = message.author.name + "#" + message.author.discriminator
            drop_channel = message.channel.name
            drop_amount = "Unknown"
            drop_currency = "Unknown"

            # Parse amount and currency
            if "≈" in drop_info:
                try:
                    drop_amount = drop_info.split("≈")[1].split(")")[0].strip()
                except IndexError:
                    self.logger.warning("Unable to parse drop amount.")
            if "**" in drop_info:
                try:
                    drop_currency = drop_info.split("**")[1].split("**")[0].strip()
                except IndexError:
                    self.logger.warning("Unable to parse drop currency.")

            # Click the button if possible
            button = message.components[0].children[0]
            if "Enter airdrop" in button.label:
                await button.click()
                self.logger.info(
                    f"Airdrop entered: Channel: {drop_channel}, User: {drop_user}, "
                    f"Amount: {drop_amount}, Currency: {drop_currency}"
                )
                self.push_to_pushbullet(
                    title="Airdrop Entered!",
                    body=(
                        f"Airdrop was found and entered:\n"
                        f"**Channel**: {drop_channel}\n"
                        f"**User**: {drop_user}\n"
                        f"**Amount**: {drop_amount}\n"
                        f"**Currency**: {drop_currency}"
                    )
                )
        except Exception as e:
            self.logger.error(f"Failed to handle airdrop: {e}")

    async def handle_stake_drop(self, message):
        """Handle Stake.us drops and send Pushbullet notification."""
        try:
            url = self.stake_regex.search(message.content).group(0)
            bonus_code = self.extract_bonus_code(url)
            if bonus_code in self.detected_stake_codes:
                self.logger.info(f"Duplicate Stake drop detected. Skipping: {bonus_code}")
                return

            self.detected_stake_codes.add(bonus_code)  # Add code to detected list
            drop_channel = message.channel.name
            drop_user = message.author.name + "#" + message.author.discriminator

            self.logger.info(f"Stake drop found: {url} in {drop_channel}")
            self.push_to_pushbullet(
                title="Stake Drop Found!",
                body=(
                    f"A Stake drop was found:\n"
                    f"**Channel**: {drop_channel}\n"
                    f"**User**: {drop_user}\n"
                    f"**Bonus Code**: {bonus_code}\n"
                    f"**Link**: {url}"
                )
            )
        except Exception as e:
            self.logger.error(f"Failed to handle Stake drop: {e}")

    def extract_bonus_code(self, url):
        """Extract the bonus code from the Stake.us URL."""
        try:
            from urllib.parse import parse_qs, urlparse
            query = urlparse(url).query
            params = parse_qs(query)
            return params.get("code", ["Unknown"])[0]
        except Exception as e:
            self.logger.error(f"Failed to extract bonus code: {e}")
            return "Unknown"

    def push_to_pushbullet(self, title, body):
        """Send a notification to Pushbullet."""
        try:
            self.pushbullet.push_note(title, body)
            self.logger.info(f"Pushbullet notification sent: {title}")
        except Exception as e:
            self.logger.error(f"Failed to send Pushbullet notification: {e}")

    def run_bot(self):
        """Run the bot with the token from the config."""
        token = self.config.get("TOKEN")
        if not token:
            self.logger.error("Bot token not found in the configuration.")
            return
        super().run(token)


if __name__ == "__main__":
    bot = AirdropBot(config_path="config.json")
    bot.run_bot()
