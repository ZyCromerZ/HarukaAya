#    Haruka Aya (A telegram bot project)
#    Copyright (C) 2017-2019 Paul Larsen
#    Copyright (C) 2019-2021 Akito Mizukito (Haruka Aita)

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

from typing import List
import json
import requests

from telegram import Update, Bot, ParseMode
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters

import haruka.modules.sql.antispam_sql as sql
from haruka import dispatcher, STRICT_ANTISPAM, spamwatch_api, OWNER_ID, SUDO_USERS, GBAN_DUMP, MESSAGE_DUMP
from haruka.modules.helper_funcs.chat_status import user_admin, is_user_admin
from haruka.modules.helper_funcs.filters import CustomFilters
from haruka.modules.helper_funcs.extraction import extract_user, extract_user_and_text

from haruka.modules.tr_engine.strings import tld
from telegram.utils.helpers import mention_html

GBAN_ENFORCE_GROUP = 6


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    banner = update.effective_user
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(tld(chat.id, "common_err_no_user"))
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text(tld(chat.id, "antispam_err_usr_sudo"))
        return

    if user_id == bot.id:
        message.reply_text(tld(chat.id, "antispam_err_usr_bot"))
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text(tld(chat.id, "antispam_err_not_usr"))
        return

    if user_chat.first_name == '':
        message.reply_text(tld(chat.id, "antispam_err_usr_deleted"))
        return

    if not reason:
        message.reply_text("Global Ban must have a reason!")
        return

    full_reason = html.escape(
        f"{reason} // GBanned by {banner.first_name} id {banner.id}")

    if sql.is_user_gbanned(user_id):
        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name,
            full_reason) or "None"

        try:
            bot.send_message(
                GBAN_DUMP,
                tld(chat.id, "antispam_logger_update_gban").format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(user_chat.id, user_chat.first_name
                                 or "Deleted Account"), user_chat.id,
                    old_reason, full_reason),
                parse_mode=ParseMode.HTML)
        except Exception:
            pass

        message.reply_text(tld(chat.id, "antispam_reason_updated").format(
            html.escape(old_reason), html.escape(full_reason)),
                           parse_mode=ParseMode.HTML)

        return

    starting = tld(chat.id, "antispam_new_gban").format(
        mention_html(user_chat.id, user_chat.first_name or "Deleted Account"),
        user_chat.id, reason)
    message.reply_text(starting, parse_mode=ParseMode.HTML)

    try:
        bot.send_message(GBAN_DUMP,
                         tld(chat.id, "antispam_logger_new_gban").format(
                             mention_html(banner.id, banner.first_name),
                             mention_html(user_chat.id, user_chat.first_name),
                             user_chat.id, full_reason
                             or tld(chat.id, "antispam_no_reason")),
                         parse_mode=ParseMode.HTML)
    except Exception:
        print("nut")

    try:
        bot.kick_chat_member(chat.id, user_chat.id)
    except BadRequest as excp:
        if excp.message in GBAN_ERRORS:
            pass

    sql.gban_user(user_id, user_chat.username or user_chat.first_name,
                  full_reason)


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat

    user_id, reason = extract_user_and_text(message, args)

    reason = html.escape(reason)

    if not user_id:
        message.reply_text(tld(chat.id, "common_err_no_user"))
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text(tld(chat.id, "antispam_err_not_usr"))
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text(tld(chat.id, "antispam_user_not_gbanned"))
        return

    if not reason:
        message.reply_text(
            "Removal of Global Ban requires a reason to do so, why not send me one?"
        )
        return

    banner = update.effective_user

    message.reply_text(
        "<b>Initializing Global Ban Removal</b>\n<b>Sudo Admin:</b> {}\n<b>User:</b> {}\n<b>ID:</b> <code>{}</code>\n<b>Reason:</b> {}"
        .format(mention_html(banner.id, banner.first_name),
                mention_html(user_chat.id, user_chat.first_name), user_chat.id,
                reason),
        parse_mode=ParseMode.HTML)

    try:
        bot.send_message(GBAN_DUMP,
                         tld(chat.id, "antispam_logger_ungban").format(
                             mention_html(banner.id, banner.first_name),
                             mention_html(user_chat.id, user_chat.first_name),
                             user_chat.id, reason),
                         parse_mode=ParseMode.HTML)
    except Exception:
        pass

    # chats = get_all_chats()
    # for chat in chats:
    #     chat_id = chat.chat_id

    #     # Check if this group has disabled gbans
    #     if not sql.does_chat_gban(chat_id):
    #         continue

    #     try:
    #         member = bot.get_chat_member(chat_id, user_id)
    #         if member.status == 'kicked':
    #             bot.unban_chat_member(chat_id, user_id)

    #     except BadRequest as excp:
    #         if excp.message in UNGBAN_ERRORS:
    #             pass
    #         else:
    #             message.reply_text(
    #                 tld(chat.id, "antispam_err_ungban").format(excp.message))
    #             bot.send_message(
    #                 OWNER_ID,
    #                 tld(chat.id, "antispam_err_ungban").format(excp.message))
    #             return
    #     except TelegramError:
    #         pass

    sql.ungban_user(user_id)

    message.reply_text("This user have been ungbanned succesfully, they might have to ask 'admins' of chats they were banned to unban manually due to global ban." \
                       "\n\nPlease forward this message to them or let them know about this.")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "There aren't any gbanned users! You're kinder than I expected...")
        return

    banfile = 'Gbanned users:\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Here is the list of currently gbanned users.")


@run_async
def ungban_quicc(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    try:
        user_id = int(args[0])
    except Exception:
        return
    sql.ungban_user(user_id)
    message.reply_text(
        f"Yeety mighty your mom is gay, {user_id} have been ungbanned.")


def check_and_ban(update, user_id, should_message=True):
    chat = update.effective_chat
    message = update.effective_message
    try:
        if spamwatch_api != None:
            headers = {'Authorization': f'Bearer {spamwatch_api}'}
            resp = requests.get("https://api.spamwat.ch/banlist/{user_id}",
                                headers=headers,
                                timeout=5)
            if resp.status_code == 200:
                sw_ban = json.loads(resp.content)
                reason = sw_ban['reason']
                chat.kick_member(user_id)
                if should_message:
                    message.reply_text(tld(
                        chat.id, "antispam_spamwatch_banned").format(reason),
                                       parse_mode=ParseMode.HTML)
                    return
                else:
                    return
        else:
            return
    except:
        pass


#GMUTE


@run_async
def gmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("I spy, with my little eye... a sudo user war! Why are you guys turning on each other?")
        return

    if user_id == bot.id:
        message.reply_text("-_- So funny, lets gmute myself why don't I? Nice try.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.first_name == '':
        message.reply_text("That's a deleted account! Why even bother gmuting them?")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("That's not a user!")
        return

    if sql.is_user_gmuted(user_id):
        if not reason:
            message.reply_text("This user is already gmuted; I'd change the reason, but you haven't given me one...")
            return

        success = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("This user is already gmuted; I've gone and updated the gmute reason though!")
        else:
            message.reply_text("Do you mind trying again? I thought this person was gmuted, but then they weren't? "
                               "Am very confused")

        return

    message.reply_text("*Gets duct tape ready* 😉")

    muter = update.effective_user  # type: Optional[User]
    bot.send_message(MESSAGE_DUMP,
                 "{} is gmuting user {} "
                 "because:\n{}".format(mention_html(muter.id, muter.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "No reason given"),
                 parse_mode=ParseMode.HTML)

    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)

    #chats = get_all_chats()
    #for chat in chats:
    #    chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        #if not sql.does_chat_gban(chat_id):
        #    continue

        #try:
        #    bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
        #except BadRequest as excp:
        #    if excp.message == "User is an administrator of the chat":
        #        pass
        #    elif excp.message == "Chat not found":
        #        pass
        #    elif excp.message == "Not enough rights to restrict/unrestrict chat member":
        #        pass
        #    elif excp.message == "User_not_participant":
        #        pass
        #    elif excp.message == "Peer_id_invalid":  # Suspect this happens when a group is suspended by telegram.
        #        pass
        #    elif excp.message == "Group chat was deactivated":
        #        pass
        #    elif excp.message == "Need to be inviter of a user to kick it from a basic group":
        #        pass
        #    elif excp.message == "Chat_admin_required":
        #        pass
        #    elif excp.message == "Only the creator of a basic group can kick group administrators":
        #        pass
        #    elif excp.message == "Method is available only for supergroups":
        #        pass
        #    elif excp.message == "Can't demote chat creator":
        #        pass
        #    else:
        #        message.reply_text("Could not gmute due to: {}".format(excp.message))
        #        bot.send_message(MESSAGE_DUMP, "Could not gmute due to: {}".format(excp.message))
        #        sql.ungmute_user(user_id)
        #        os.environ['GPROCESS'] = '0'
        #        return
        #except TelegramError:
        #    pass

    bot.send_message(MESSAGE_DUMP, "gmute complete!")
    message.reply_text("Person has been gmuted.")


@run_async
def ungmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("That's not a user!")
        return

    if not sql.is_user_gmuted(user_id):
        message.reply_text("This user is not gmuted!")
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("I'll let {} speak again, globally.".format(user_chat.first_name))

    bot.send_message(MESSAGE_DUMP,
                 "{} has ungmuted user {}".format(mention_html(muter.id, muter.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 parse_mode=ParseMode.HTML)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted':
                bot.restrict_chat_member(chat_id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Method is available for supergroup and channel chats only":
                pass
            elif excp.message == "Not in the chat":
                pass
            elif excp.message == "Channel_private":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            else:
                message.reply_text("Could not un-gmute due to: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Could not un-gmute due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)

    bot.send_message(MESSAGE_DUMP, "un-gmute complete!")

    message.reply_text("Person has been un-gmuted.")


@run_async
def gmutelist(bot: Bot, update: Update):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("There aren't any gmuted users! You're kinder than I expected...")
        return

    mutefile = 'Screw these guys.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Here is the list of currently gmuted users.")


def check_and_mute(bot, update, user_id, should_message=True):
    if sql.is_user_gmuted(user_id):
        bot.restrict_chat_member(update.effective_chat.id, user_id, can_send_messages=False)
        if should_message:
            update.effective_message.reply_text("This is a bad person, I'll silence them for you!")


@run_async
def enforce_gmute(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_mute(bot, update, user.id, should_message=True)
        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_mute(bot, update, mem.id, should_message=True)
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_mute(bot, update, user.id, should_message=True)


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    try:
        if sql.does_chat_gban(
                update.effective_chat.id) and update.effective_chat.get_member(
                    bot.id).can_restrict_members:
            user = update.effective_user
            chat = update.effective_chat
            msg = update.effective_message

            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id)
                return

            if msg.new_chat_members:
                new_members = update.effective_message.new_chat_members
                for mem in new_members:
                    check_and_ban(update, mem.id)
                    return

            if msg.reply_to_message:
                user = msg.reply_to_message.from_user
                if user and not is_user_admin(chat, user.id):
                    check_and_ban(update, user.id, should_message=False)
                    return
    except Exception:
        # Often timeout, bot kicked from chat, or bot is not in chat.
        return


@run_async
@user_admin
def antispam(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_antispam(chat.id)
            update.effective_message.reply_text(tld(chat.id, "antispam_on"))
        elif args[0].lower() in ["off", "no"]:
            sql.disable_antispam(chat.id)
            update.effective_message.reply_text(tld(chat.id, "antispam_off"))
    else:
        update.effective_message.reply_text(
            tld(chat.id,
                "antispam_err_wrong_arg").format(sql.does_chat_gban(chat.id)))


@run_async
def clear_gbans(bot: Bot, update: Update):
    banned = sql.get_gban_list()
    deleted = 0
    update.message.reply_text(
        "*Beginning to cleanup deleted users from global ban database...*\nThis process might take a while...",
        parse_mode=ParseMode.MARKDOWN)
    for user in banned:
        id = user["user_id"]
        time.sleep(0.1)  # Reduce floodwait
        try:
            bot.get_chat(id)
        except BadRequest:
            deleted += 1
            sql.ungban_user(id)
    update.message.reply_text("Done! {} deleted accounts were removed " \
    "from the gbanlist.".format(deleted), parse_mode=ParseMode.MARKDOWN)

#Gkick

GKICK_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat",
    "Method is available for supergroup and channel chats only",
    "Reply message not found"
}

@run_async
def gkick(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)
    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in GKICK_ERRORS:
            pass
        else:
            message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
            return
    except TelegramError:
            pass


    if not user_id:
        message.reply_text("You do not seems to be referring to a user")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("OHHH! Someone's trying to gkick a sudo user! *Grabs popcorn*")
        return

    if int(user_id) == OWNER_ID:
        message.reply_text("Wow! Some's trying to gkick my owner! *Grabs Potato Chips*")
        return

    if user_id == bot.id:
        message.reply_text("Welp, I'm not gonna gkick myself!")
        return

    if user_chat.first_name == '':
        message.reply_text("That's a deleted account! Why u even bother gkicking dem")
        return

    chats = get_all_chats()
    message.reply_text("Globally kicking user @{}".format(user_chat.username))
    for chat in chats:
        try:
            bot.unban_chat_member(chat.chat_id, user_id)  # Unban_member = kick (and not ban)
        except BadRequest as excp:
            if excp.message in GKICK_ERRORS:
                pass
            else:
                message.reply_text("User cannot be Globally kicked because: {}".format(excp.message))
                return
        except TelegramError:
            pass


def __stats__():
    return "• `{}` gbanned users [We regularly clean off deleted account from the database].\n{} gmuted users.".format(
        sql.num_gbanned_users(), sql.num_gmuted_users())


def __user_info__(user_id, chat_id):
    is_gbanned = sql.is_user_gbanned(user_id)
    is_gmuted = sql.is_user_gmuted(user_id)

    if not user_id in SUDO_USERS:

        text = tld(chat_id, "antispam_userinfo_gbanned")
        if is_gbanned:
            text = text.format(tld(chat_id, "common_yes"))
            text += tld(chat_id, "anitspam_appeal")
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += tld(chat_id, "antispam_userinfo_gban_reason").format(
                    html.escape(user.reason))
        else:
            text = text.format(tld(chat_id, "common_no"))

        text += tld(chat_id, "antispam_userinfo_gmute")
        if is_gmuted:
            text = text.format(tld(chat_id, "common_yes"))
            text += tld(chat_id, "anitspam_appeal")
            user = sql.get_gmuted_user(user_id)
            if user.reason:
                text += tld(chat_id, "antispam_userinfo_gmute_reason").format(html.escape(user.reason))
        else:
            text = text.format(tld(chat_id, "common_no"))

        return text
    else:
        return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = True

ANTISPAM_STATUS = CommandHandler("antispam",
                                 antispam,
                                 pass_args=True,
                                 filters=Filters.group)

GBAN_HANDLER = CommandHandler("gban",
                              gban,
                              pass_args=True,
                              filters=CustomFilters.sudo_filter)
UNGBAN_HANDLER = CommandHandler("ungban",
                                ungban,
                                pass_args=True,
                                filters=CustomFilters.sudo_filter)

UNGBANQ_HANDLER = CommandHandler("ungban_quicc",
                                 ungban_quicc,
                                 pass_args=True,
                                 filters=CustomFilters.sudo_filter)

GBAN_LIST = CommandHandler("gbanlist",
                           gbanlist,
                           filters=Filters.user(OWNER_ID))

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)
CLEAN_DELACC_HANDLER = CommandHandler("cleandelacc",
                                      clear_gbans,
                                      filters=Filters.user(OWNER_ID))


GMUTE_HANDLER = CommandHandler("gmute", gmute, pass_args=True, filters=CustomFilters.sudo_filter)
UNGMUTE_HANDLER = CommandHandler("ungmute", ungmute, pass_args=True, filters=CustomFilters.sudo_filter)
GMUTE_LIST = CommandHandler("gmutelist", gmutelist, filters=CustomFilters.sudo_filter)

GKICK_HANDLER = CommandHandler("gkick", gkick, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(ANTISPAM_STATUS)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(CLEAN_DELACC_HANDLER)
dispatcher.add_handler(UNGBANQ_HANDLER)
dispatcher.add_handler(GBAN_LIST)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)

dispatcher.add_handler(GKICK_HANDLER)


if STRICT_ANTISPAM:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
