
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import asyncio
from database import Database
from config import BOT_TOKEN, ADMIN_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
db = Database()

logging.basicConfig(level=logging.INFO)

# Buttons
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("💰 Deposit", "💼 My Wallet")
main_menu.row("💳 Buy Prepaid Cards", "📖 View All CCs")
main_menu.row("🧾 Buy CCs - $15", "📦 My Orders")
main_menu.row("📦 Preorder Balance")

# Start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    db.add_user(message.from_user.id)
    await message.answer("👋 Welcome to PrepaidHavenBot!", reply_markup=main_menu)

# Wallet
@dp.message_handler(lambda msg: msg.text == "💼 My Wallet")
async def my_wallet(message: types.Message):
    balance = db.get_balance(message.from_user.id)
    await message.answer(f"💰 Your Wallet Balance: ${balance:.2f}")

# Deposit
@dp.message_handler(lambda msg: msg.text == "💰 Deposit")
async def deposit(message: types.Message):
    deposit_msg = (
        "To deposit, send LTC or BTC to the following addresses:

"
        "BTC: `your_btc_address_here`
"
        "LTC: `your_ltc_address_here`

"
        "Once payment is made, send proof to the admin. Your balance will be updated manually."
    )
    await message.answer(deposit_msg, parse_mode="Markdown")

# Admin: Load balance
@dp.message_handler(commands=["load"], user_id=ADMIN_ID)
async def load_balance(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Usage: /load <user_id> <amount>")
        return
    user_id, amount = int(args[1]), float(args[2])
    db.update_balance(user_id, amount)
    await message.answer(f"✅ Loaded ${amount:.2f} to user {user_id}")
    await bot.send_message(user_id, f"💰 You have received ${amount:.2f} from the admin!")

# Admin: Add card
@dp.message_handler(commands=["addcard"], user_id=ADMIN_ID)
async def add_card(message: types.Message):
    try:
        _, name, bin_code, balance, price = message.text.split("|")
        card_id = db.add_card(name.strip(), bin_code.strip(), float(balance), float(price))
        await message.answer(f"✅ Card #{card_id} added successfully.")
    except:
        await message.answer("❌ Usage:
/addcard | name | bin | balance | price")

# View Cards
@dp.message_handler(lambda msg: msg.text == "💳 Buy Prepaid Cards")
async def view_cards(message: types.Message):
    cards = db.get_available_cards()
    if not cards:
        await message.answer("❌ No cards available.")
        return
    msg = ""
    for c in cards:
        locked = db.get_card_lock_time(c["id"])
        lock_str = f"🔒 Locked: ⏳ {locked} remaining" if locked else ""
        msg += f"#{c['id']} | {c['name']} | BIN {c['bin']} | Balance: ${c['balance']:.2f}
{lock_str}

"
    await message.answer(msg)

# Gamble
@dp.message_handler(lambda msg: msg.text.startswith("🎲 Gamble"))
async def gamble(message: types.Message):
    cost = 5.0
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    if balance < cost:
        await message.answer("❌ Not enough balance.")
        return
    card = db.get_random_card()
    if not card:
        await message.answer("❌ No cards available.")
        return
    db.lock_card(card["id"])
    db.update_balance(user_id, -cost)
    db.record_purchase(user_id, card["id"], card["price"])
    await message.answer(
        f"🎉 You got:
#{card['id']} | {card['name']} | BIN {card['bin']} | Balance: ${card['balance']:.2f}"
    )
    await bot.send_message(ADMIN_ID, f"🎲 User {user_id} gambled and got card #{card['id']}")
