import os
from bot import bot
from webserver import keep_alive

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
