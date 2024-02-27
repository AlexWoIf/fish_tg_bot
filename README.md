# Продаём рыбу в Telegram

Учебный проект курса "Чат-боты на Python" компании Devman. 
![image](https://dvmn.org/media/filer_public/0a/5b/0a5b562c-7cb4-43e3-b51b-1b61721200fb/fish-shop.gif)

## Задание

Данный бота для Telegram, позволяет оформлять закакзы в интернет-магазине с использованием API [STRAPI](https://strapi.io/). 

## Подготовка к запуску, настройка окружения

Запустите сервис STRAPI используя инструкцию на их [сайте](https://docs.strapi.io/dev-docs/quick-start#_1-install-strapi-and-create-a-new-project)

Для запуска бота вам потребуется Python 3.10

Скачайте код бота, затем установите зависимости командой
```sh
pip install -r requirements.txt
```

## Настройка параметров

Получите все токены/ключи для заполнения `.env` файла.

```.env
TG_BOT_TOKEN=<получите у [**BotFather**](https://telegram.me/BotFather)>

STRAPI_TOKEN=<создайте API-токен в админ-панели [по инструкции](https://docs.strapi.io/user-docs/settings/API-tokens)>

LOG_LEVEL=[NOTSET|DEBUG|(INFO)|WARN|ERROR|CRITICAL] необязательный параметр. По умолчанию - INFO.
LOG_TG_CHAT_ID=<ID для отправки логов, можете узнать у [**userinfobot**](https://telegram.me/userinfobot)>
LOG_TG_BOT_TOKEN=<токен бота для отправки логов. можете не указывать, если хотите использовать одного и того же ТГ-бота>

REDIS_HOST=адрес сервера redis
REDIS_PORT=порт сервера
REDIS_PASSWORD=пароль для подключения к серверу redis
```

## Запуск бота

Для запуска телеграм бота используйте следующую команду:

```sh
python fish_tg_bot.py
```  

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).