import logging
import os
import traceback
from enum import Enum

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import strapi
from logger_handlers import TelegramLogsHandler


logger = logging.getLogger(__file__)


class Status(Enum):
    HANDLE_MENU = 0


def start(update, context):
    logger.debug(f'Enter cmd_start: {update.message.text=}')

    backend = context.bot_data['backend']
    products = backend.get_all_products()

    text = 'Please choose:'
    keyboard = [
        [InlineKeyboardButton(
            product.get('attributes', {}).get('title'),
            callback_data=f'product:{product.get("id")}'),]
        for product in products
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)
    storage = context.bot_data['storage']
    storage.set(update.message.from_user.id, 0)
    return Status.HANDLE_MENU


if __name__ == '__main__':
    load_dotenv()
    tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
    loglevel = os.getenv('LOG_LEVEL', default='INFO')
    log_chat = os.getenv('LOG_TG_CHAT_ID')
    log_tg_token = os.getenv('LOG_TG_BOT_TOKEN')
    logger.setLevel(loglevel)
    if log_chat:
        if not log_tg_token:
            log_tg_token = tg_token
        logger.addHandler(TelegramLogsHandler(log_tg_token, log_chat))
    logger.debug('Start logging')

    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')
    storage = redis.Redis(host=redis_host, port=redis_port,
                          password=redis_password)

    strapi_token = os.getenv('STRAPI_TOKEN')
    backend = strapi.Strapi(strapi_token)

    try:
        updater = Updater(tg_token)
        dispatcher = updater.dispatcher
        dispatcher.bot_data['storage'] = storage
        dispatcher.bot_data['backend'] = backend
        conversation = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                Status.HANDLE_MENU: [CommandHandler('start', start),],
            },
            fallbacks=[],
        )
        dispatcher.add_handler(conversation)
        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error({'Error': error, 'Traceback': traceback.format_exc()})
