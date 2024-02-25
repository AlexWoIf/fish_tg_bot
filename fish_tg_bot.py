import logging
import os
import traceback
from enum import Enum

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Updater)

import strapi
from logger_handlers import TelegramLogsHandler


logger = logging.getLogger(__file__)


class Status(Enum):
    HANDLE_MENU = 0
    HANDLE_DESCRIPTION = 1


def start(update, context):
    logger.debug(f'Enter cmd_start: {update=}')

    backend = context.bot_data['backend']
    products = backend.get_all_products()

    text = 'Please choose:'
    keyboard = [
        [InlineKeyboardButton(product_title,
                              callback_data=f'product:{product_id}'),]
        for (product_id, product_title) in products
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text, reply_markup=reply_markup)
    return Status.HANDLE_MENU


def product_details(update, context):
    logger.debug(f'Enter cmd_start: {update.callback_query=}')

    button_details = update.callback_query.data.split(':')
    product_id = button_details[1]
    backend = context.bot_data['backend']
    title, description, price, picture = backend.get_product(product_id)
    text = f'{title} ({price} руб. за кг)\n\n{description}'
    keyboard = [[InlineKeyboardButton('Назад', callback_data='back')],]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(chat_id=update.effective_chat.id, caption=text,
                           photo=picture, reply_markup=reply_markup, )
    update.callback_query.delete_message()
    return Status.HANDLE_DESCRIPTION


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
                Status.HANDLE_MENU: [
                    CallbackQueryHandler(
                        product_details,
                        pattern=r'^product:\d+$'
                    ),
                ],
                Status.HANDLE_DESCRIPTION: [
                    CallbackQueryHandler(start, pattern=r'^back$')
                ]
            },
            fallbacks=[],
        )
        dispatcher.add_handler(conversation)
        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error({'Error': error, 'Traceback': traceback.format_exc()})
