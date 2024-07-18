import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests
from config import TOKEN
import sqlite3
import logging
import random

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

# Создаем кнопки
button_registr = KeyboardButton(text='Регистрация в Телеграм-боте')
button_exchange_rates = KeyboardButton(text='Курс валют')
button_tips = KeyboardButton(text='Советы по экономии')
button_finances = KeyboardButton(text='Личные финансы')

keyboard = ReplyKeyboardMarkup(keyboard=[
    [button_registr, button_exchange_rates],
    [button_tips, button_finances]
], resize_keyboard=True)

# Функция для создания базы данных
def init_db():
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS users')  # Удаляем старую таблицу, если она существует
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        category1 TEXT,
        category2 TEXT,
        category3 TEXT,
        expenses1 REAL,
        expenses2 REAL,
        expenses3 REAL
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Класс состояний
class FinancesForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()

# Обработчики сообщений
@dp.message(CommandStart())
async def send_start(message: Message):
    await message.answer('Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:', reply_markup=keyboard)

@dp.message(F.text == 'Регистрация в Телеграм-боте')
async def registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name

    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        await message.answer("Вы уже зарегистрированы!")
    else:
        cursor.execute('''INSERT INTO users (telegram_id, name) VALUES (?, ?)''', (telegram_id, name))
        conn.commit()
        await message.answer("Вы успешно зарегистрированы!")

    conn.close()

@dp.message(F.text == 'Курс валют')
async def exchange_rates(message: Message):
    url = 'https://v6.exchangerate-api.com/v6/74b1cd5d92dcc922fd3a7382/latest/USD'
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await message.answer('Не удалось получить данные о курсе валют')
            return
        usd_to_rub = data['conversion_rates']['RUB']
        eur_to_usd = data['conversion_rates']['EUR']
        eur_to_rub = eur_to_usd * usd_to_rub

        await message.answer(f'1 USD = {usd_to_rub:.2f} RUB\n'
                             f'1 EUR = {eur_to_rub:.2f} RUB')
    except Exception as e:
        logging.error(f"Error fetching exchange rates: {e}")
        await message.answer('Произошла ошибка')

@dp.message(F.text == 'Советы по экономии')
async def send_tips(message: Message):
    tips = [
        "Совет 1: Ведите бюджет и следите за своими расходами.",
        "Совет 2: Откладывайте часть доходов на сбережения.",
        "Совет 3: Покупайте товары по скидкам и распродажам."
    ]
    tip = random.choice(tips)
    await message.answer(tip)

@dp.message(F.text == 'Личные финансы')
async def finances(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.category1)
    await message.reply('Введите первую категорию расходов')

@dp.message(FinancesForm.category1)
async def finances_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await state.set_state(FinancesForm.expenses1)
    await message.reply('Введите сумму расходов для категории 1:')

@dp.message(FinancesForm.expenses1)
async def finances_expenses1(message: Message, state: FSMContext):
    await state.update_data(expenses1=float(message.text))
    await state.set_state(FinancesForm.category2)
    await message.reply('Введите вторую категорию расходов')

@dp.message(FinancesForm.category2)
async def finances_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await state.set_state(FinancesForm.expenses2)
    await message.reply('Введите сумму расходов для категории 2:')

@dp.message(FinancesForm.expenses2)
async def finances_expenses2(message: Message, state: FSMContext):
    await state.update_data(expenses2=float(message.text))
    await state.set_state(FinancesForm.category3)
    await message.reply('Введите третью категорию расходов')

@dp.message(FinancesForm.category3)
async def finances_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await state.set_state(FinancesForm.expenses3)
    await message.reply('Введите сумму расходов для категории 3:')

@dp.message(FinancesForm.expenses3)
async def finances_expenses3(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = message.from_user.id
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users SET category1 = ?, expenses1 = ?, category2 = ?, expenses2 = ?, category3 = ?, expenses3 = ? WHERE telegram_id = ?''',
                   (data['category1'], data['expenses1'], data['category2'], data['expenses2'], data['category3'], float(message.text), telegram_id))

    conn.commit()
    conn.close()
    await state.clear()

    await message.answer('Категории и расходы сохранены')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
