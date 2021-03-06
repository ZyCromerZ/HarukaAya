#    Haruka Aya (A telegram bot project)
#    Copyright (C) 2017-2019 Paul Larsen
#    Copyright (C) 2019-2021 A Haruka Aita and Intellivoid Technologies project

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import sys
import yaml
import spamwatch
import os

from telethon import TelegramClient
import telegram.ext as tg

#Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

LOGGER.info("Starting haruka...")

# If Python version is < 3.6, stops the bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 8:
    LOGGER.error(
        "You MUST have a python version of at least 3.8! Multiple features depend on this. Bot quitting."
    )
    quit(1)

# Load config
TOKEN = os.environ.get("TOKEN",None)
API_KEY = os.environ.get("API_KEY",None)
API_HASH = os.environ.get("API_HASH",None)

try:
    OWNER_ID = int(os.environ.get("OWNER_ID",None))
except ValueError:
    raise Exception("Your 'OWNER_ID' variable is not a valid integer.")

try:
    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP",None)
except ValueError:
    raise Exception("Your 'MESSAGE_DUMP' must be set.")

try:
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME",None)
except ValueError:
    raise Exception("Your 'OWNER_USERNAME' must be set.")

try:
    SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS",None) or [])
except ValueError:
    raise Exception("Your sudo users list does not contain valid integers.")

try:
    WHITELIST_USERS = set(int(x) for x in os.environ.get("WHITELIST_USERS",None) or [])
except ValueError:
    raise Exception(
        "Your whitelisted users list does not contain valid integers.")

DB_URI = os.environ.get("DATABASE_URL")
LOAD = os.environ.get("LOAD","").split()
NO_LOAD = os.environ.get("NO_LOAD","").split()
DEL_CMDS = os.environ.get("DEL_CMDS",False)
STRICT_ANTISPAM = os.environ.get("STRICT_ANTISPAM",False)
WORKERS = os.environ.get("WORKERS",8)

SUDO_USERS.add(OWNER_ID)

# SpamWatch
spamwatch_api = os.environ.get("SW_API",None)

if spamwatch_api == "None":
    sw = None
    LOGGER.warning("SpamWatch API key is missing! Check your config.env.")
else:
    try:
        sw = spamwatch.Client(spamwatch_api)
    except Exception:
        sw = None

updater = tg.Updater(TOKEN, workers=WORKERS)

dispatcher = updater.dispatcher

tbot = TelegramClient("haruka", API_KEY, API_HASH)

SUDO_USERS = list(SUDO_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)

# Load at end to ensure all prev variables have been set
from haruka.modules.helper_funcs.handlers import CustomCommandHandler, CustomRegexHandler

# make sure the regex handler can take extra kwargs
tg.RegexHandler = CustomRegexHandler

tg.CommandHandler = CustomCommandHandler
