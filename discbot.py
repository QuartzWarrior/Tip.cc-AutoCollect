import logging
from re import compile
from pushbullet import Pushbullet
from discord import Client, Message


class AirdropBot(Client):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config = self.load_config(config_path)  # Config is loaded first
        self.logger = self.setup_logger()  # Logger is set up after config
        self.pushbullet = Pushbullet(self.config.get("PUSHBULLET_API_KEY", ""))
        self.airdrop_regex = compile(r"[$]airdrop|[$]phrasedrop|[$]mathdrop|[$]triviadrop|[$]redpacket")
        self.stake_regex = compile(r"https?:\/\/stake\.(us|com)\/settings(?:\/[^\s?]*)?(?:\?[^\s]*)?")
        self.detected_stake_codes = set()  # Keeps track of detected Stake.us bonus codes

    def setup_logger(self):
        """Setup logger with custom formatting."""
        logger = logging.getLogger("AirdropBot")
        logger.setLevel(self.config.get("LOG_LEVEL", logging.INFO))
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
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
            raise

    async def on_message(self, message: Message):
        """Handle incoming messages."""
        
        self.logger.debug(message)
        if message.author.bot or not message.embeds:
            return

        # Stake drop detection
        if self.stake_regex.search(message.content):
            self.logger.info(f"Stake drop detected: {message.content}")
            stake_url = self.stake_regex.search(message.content).group()
            if stake_url not in self.detected_stake_codes:
                self.detected_stake_codes.add(stake_url)
                self.pushbullet.push_link("Stake Bonus Detected", stake_url)
                self.logger.info(f"Stake bonus pushed: {stake_url}")
            return

        # Airdrop detection
        if self.airdrop_regex.search(message.content):
            self.logger.info(f"Airdrop detected in channel: {message.channel.name}")
            embed = message.embeds[0]
            drop_amount = "Unknown"
            currency = "Unknown"

            # Extract drop details
            if "$" in embed.description and "≈" in embed.description:
                try:
                    drop_amount = embed.description.split("≈")[1].split(")")[0].strip()
                    currency = embed.description.split("**")[1]
                except IndexError:
                    self.logger.warning("Failed to parse drop details.")

            user = f"{message.author.name}#{message.author.discriminator}"
            channel = message.channel.name

            # Send Pushbullet notification
            self.pushbullet.push_note(
                "Airdrop Detected",
                f"User: {user}\nChannel: {channel}\nAmount: {drop_amount}\nCurrency: {currency}",
            )
            self.logger.info(f"Pushbullet notification sent for airdrop in {channel}")


if __name__ == "__main__":
    bot = AirdropBot(config_path="config.json")
    bot.run(bot.config["TOKEN"])
