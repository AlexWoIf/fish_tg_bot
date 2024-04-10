import logging
import os
import re
import traceback
from enum import Enum
from textwrap import dedent

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)

import strapi
from logger_handlers import TelegramLogsHandler
from persistence import RedisPersistence

logger = logging.getLogger(__file__)


class Status(Enum):
    HANDLE_MENU = 0
    HANDLE_DESCRIPTION = 1
    HANDLE_CART = 2
    WAITING_EMAIL = 3


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
    keyboard.append(
        [InlineKeyboardButton('🛒 Моя корзина', callback_data='showcart')],
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text, reply_markup=reply_markup)
    return Status.HANDLE_MENU


def product_details(update, context):
    logger.debug(f'Enter product_details: {update.callback_query=}')

    button_details = update.callback_query.data.split(':')
    product_id = button_details[1]
    backend = context.bot_data['backend']
    title, description, price, picture = backend.get_product(product_id)
    text = f'{title} ({price} руб. за кг)\n\n{description}'
    keyboard = [
        [InlineKeyboardButton('➕ Добавить в корзину',
                              callback_data=f'cart:{product_id}')],
        [InlineKeyboardButton('🛒 Моя корзина', callback_data='showcart')],
        [InlineKeyboardButton('В меню', callback_data='productlist')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(chat_id=update.effective_chat.id, caption=text,
                           photo=picture, reply_markup=reply_markup, )
    update.callback_query.delete_message()
    return Status.HANDLE_DESCRIPTION


def add_to_cart(update, context):
    logger.debug(f'Enter add_to_cart: {update.callback_query=}')

    backend = context.bot_data['backend']
    button_details = update.callback_query.data.split(':')
    product_id = button_details[1]

    backend.add_to_cart(update.effective_chat.id, product_id, None)
    update.callback_query.answer('Добавлено в корзину')
    return Status.HANDLE_CART


def remove_from_cart(update, context):
    logger.debug(f'Enter remove_from_cart: {update.callback_query=}')

    backend = context.bot_data['backend']
    button_details = update.callback_query.data.split(':')
    cart_product_id = button_details[1]

    backend.remove_from_cart(cart_product_id)
    update.callback_query.delete_message()
    return show_cart(update, context)


def show_cart(update, context):
    logger.debug(f'Enter show_cart: {update.callback_query=}')

    backend = context.bot_data['backend']
    cart_products = backend.get_cart_content(update.effective_chat.id)
    text = ''
    keyboard = []
    for (product_id, product_quantity, product_title, product_description,
         product_price) in cart_products:
        keyboard.append([
            InlineKeyboardButton(f'Убрать из корзины {product_title}',
                                 callback_data=f'remove:{product_id}')
        ])
        text += f'''
            #{product_id}.<b>{product_title}</b>
            <i>{product_description}</i>
            Количество: {product_quantity}
            <u>{product_price}руб. за кг</u>
        '''
    text = dedent(text)
    keyboard.append([InlineKeyboardButton('Оплатить',
                                          callback_data='payment')])
    keyboard.append([InlineKeyboardButton('В меню',
                                          callback_data='productlist')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                             parse_mode="HTML", reply_markup=reply_markup)
    return Status.HANDLE_CART


def ask_email(update, context):
    logger.debug(f'Enter ask_email: {update.callback_query=}')

    text = 'Пришлите, пожалуйста, Ваш е-майл'
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, )
    return Status.WAITING_EMAIL


def check_email(update, context):
    logger.debug(f'Enter check_email: {update=}')

    backend = context.bot_data['backend']
    emails = re.findall(r'([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})',
                        update.message.text)
    if emails:
        backend.save_email(update.effective_chat.id, emails[0])
        text = 'Email сохранен. Менеджер свяжется с Вами в ближайшее время.'
        update.message.reply_text(text)
        return Status.HANDLE_CART
    text = 'Такой email недопустим. Попробуйте ввести еще раз.'
    update.message.reply_text(text)
    return Status.WAITING_EMAIL


if __name__ == '__main__':
    load_dotenv(override=True)
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
    redis_storage = redis.Redis(host=redis_host, port=redis_port,
                                password=redis_password)
    persistence = RedisPersistence(redis_storage)

    strapi_token = os.getenv('STRAPI_TOKEN')
    backend = strapi.Strapi(strapi_token)

    try:
        updater = Updater(tg_token, persistence=persistence)
        dispatcher = updater.dispatcher
        dispatcher.bot_data['backend'] = backend
        conversation = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                Status.HANDLE_MENU: [
                    CallbackQueryHandler(product_details,
                                         pattern=r'^product:\d+$'),
                    CallbackQueryHandler(show_cart, pattern=r'^showcart$'),
                ],
                Status.HANDLE_DESCRIPTION: [
                    CallbackQueryHandler(add_to_cart, pattern=r'^cart:\d+$'),
                    CallbackQueryHandler(show_cart, pattern=r'^showcart$'),
                    CallbackQueryHandler(start, pattern=r'^productlist$'),
                ],
                Status.HANDLE_CART: [
                    CallbackQueryHandler(remove_from_cart,
                                         pattern=r'^remove:\d+$'),
                    CallbackQueryHandler(ask_email, pattern=r'^payment$'),
                    CallbackQueryHandler(start, pattern=r'^productlist$'),
                ],
                Status.WAITING_EMAIL: [
                    MessageHandler(Filters.text & (~Filters.command),
                                   check_email),
                ],
            },
            fallbacks=[],
            name='fish_shop_conversation',
            persistent=True,
        )
        dispatcher.add_handler(conversation)
        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error({'Error': error, 'Traceback': traceback.format_exc()})
