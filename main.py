import logging
import shutil
import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from yt_dlp import YoutubeDL
from collections import defaultdict
from dotenv import load_dotenv
from tokens import bottoken, adminid

# Загрузка токенов из .env файла
load_dotenv()
API_TOKEN = bottoken

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# ID администратора для рассылки
ADMIN_ID = adminid

# Файл для хранения ID пользователей
USERS_FILE = "users.json"

# Хранение плейлистов и истории прослушиваний
user_playlists = defaultdict(lambda: defaultdict(list))
user_history = defaultdict(list)

# Функция для чтения ID пользователей из файла
def load_user_ids():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error("Ошибка при чтении файла users.json. Файл повреждён или пуст.")
            return []
    else:
        return []

# Функция для записи ID пользователей в файл
def save_user_ids(user_ids):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_ids, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при записи файла users.json: {e}")

# Функция для проверки, зарегистрирован ли пользователь
def user_exists(user_id):
    with open("user_info.txt", "r", encoding="utf-8") as file:
        return any(f"User ID: {user_id}" in line for line in file)

# Функция для сохранения информации о пользователе
def save_user_info(user_id, name, phone):
    with open("user_info.txt", "a", encoding="utf-8") as file:
        file.write(f"User ID: {user_id}, Name: {name}, Phone: {phone}\n")

@dp.message_handler(commands=['yeroadmin'])
async def broadcast_message(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        user_ids = load_user_ids()
        text_to_send = message.text.split(' ', 1)[1] if len(message.text.split(' ', 1)) > 1 else "Сообщение от администратора."

        for user_id in user_ids:
            try:
                await bot.send_message(user_id, text_to_send)
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

        await message.reply("Сообщение было отправлено всем пользователям.")
    else:
        await message.reply("У вас нет прав для отправки рассылки.")

# Хэндлер для приветствия и регистрации пользователя
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id

    # Сохранение ID пользователя в файл
    user_ids = load_user_ids()
    if user_id not in user_ids:
        user_ids.append(user_id)
        save_user_ids(user_ids)

    if user_exists(user_id):
        await message.reply("Добро пожаловать обратно! Вы уже зарегистрированы.")
    else:
        await message.reply("Привет! Пожалуйста, напиши свой номер телефона в формате +79991234567.")

# Хэндлер для отправки сообщения всем пользователям

# Хэндлер для обработки номера телефона
@dp.message_handler(lambda message: message.text.startswith('+'))  # Проверка на формат номера
async def handle_phone_number(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    phone = message.text

    if user_exists(user_id):
        await message.reply("Вы уже зарегистрированы, спасибо!")
    else:
        save_user_info(user_id, name, phone)
        await message.reply("Спасибо! Вы зарегистрированы.")

# Хэндлер для поиска музыки на YouTube
@dp.message_handler(commands=['search'])
async def search_genre_artist(message: types.Message):
    query = message.text.split(' ', 1)[1]  # Извлекаем запрос после команды
    await search_youtube(message, query)

# Хэндлер для поиска музыки
@dp.message_handler()
async def search_youtube(message: types.Message, search_query=None):
    if not search_query:
        search_query = message.text

    user_id = message.from_user.id
    user_history[user_id].append(search_query)

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': 'True',
        'quiet': True,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{search_query}", download=True)
            video = info['entries'][0]
            audio_file = f"downloads/{video['title']}.{video['ext']}"  # Путь к аудиофайлу
            video_title = video['title']

        with open(audio_file, 'rb') as audio:
            await message.reply_audio(audio, caption=f"Найдено: {video_title}")  # Отправляем аудио
        os.remove(audio_file)  # Удаляем аудиофайл после отправки

    except Exception as e:
        await message.reply("Произошла ошибка при поиске аудио. Пожалуйста, попробуйте еще раз.")
        logging.error(f"Error searching for audio: {e}")


# Основной цикл бота
async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
