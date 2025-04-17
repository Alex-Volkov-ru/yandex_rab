# Telegram Homework Bot

Этот проект представляет собой Telegram-бота для проверки статуса домашней работы на платформе Яндекс.Практикум. Бот позволяет получать информацию о статусе домашних заданий, используя API Яндекс.Практикума, и отправлять уведомления в Telegram.

## Структура проекта

### Dockerfile

Для запуска проекта используется Docker. В `Dockerfile` описаны все шаги для сборки контейнера с необходимыми зависимостями и запуском бота.

##  Функции бота
Проверка токенов: Бот использует несколько переменных окружения (токенов), которые загружаются из файла .env.

Запрос статуса домашней работы: Бот отправляет запросы к API Яндекс.Практикума, чтобы получить статусы домашних заданий.

## Команды бота: Поддерживается команда /status, а также кнопка "Проверить статус домашнего задания", которая отправляет статус в чат.

Обработчик ошибок: В проекте реализована обработка ошибок при запросах и отправке сообщений в Telegram.

##  Установка и запуск
##  Требования
Python 3.11

Docker (если хотите запускать в контейнере)

Установить зависимости:

pip install -r requirements.txt
Запуск в Docker
Собрать образ Docker:

docker build -t telebot-backend .
Запустить контейнер:


docker run --env-file .env -d telebot-backend
Запуск без Docker
Просто запустите homework.py:



python homework.py
Переменные окружения

## ENV

PRACTICUM_TOKEN=<ваш токен для API Яндекс.Практикум>
TELEGRAM_TOKEN=<ваш токен для Telegram-бота>
TELEGRAM_CHAT_ID=<ID чата Telegram для отправки сообщений>

Это проект распространяется под лицензией MIT.
Тебе нужно будет заменить `<repo_url>` и `<repo_directory>` на реальные значения. Также убедись, что `.env` файл правильно настроен перед запуском.