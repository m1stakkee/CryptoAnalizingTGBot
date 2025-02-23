import telebot
import requests
import logging
import numpy as np
from sklearn.linear_model import LinearRegression



BOT_TOKEN = "7604544284:AAEQphOyIi-KI2V5XQj9c1n89zxIKDJGIi8"
bot = telebot.TeleBot(BOT_TOKEN)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"


SUPPORTED_CRYPTO = {
    "bitcoin": "Bitcoin",
    "ethereum": "Ethereum",
    "the-open-network": "TONcoin",
    "binancecoin": "BNBcoin",
    "tether": "Tether(USDT)",
    "tron": "TRX",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

user_crypto = {}


historical_data = {}



@bot.message_handler(commands=['help'])
def send_welcome(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for crypto_id, name in SUPPORTED_CRYPTO.items():
        keyboard.add(telebot.types.KeyboardButton(name))
    bot.send_message(message.chat.id, "Выберите криптовалюту:", reply_markup=keyboard)




@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for crypto_id, name in SUPPORTED_CRYPTO.items():
        keyboard.add(telebot.types.KeyboardButton(name))
    bot.send_message(message.chat.id, "Приветствую! В этом боте вы можете узнать актуальную цену на криптовалюты и посмотреть прогнозы.")
    bot.send_message(message.chat.id, "Выберите криптовалюту:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: True)
def handle_crypto_choice(message):
    crypto_name = message.text
    for cid, name in SUPPORTED_CRYPTO.items():
        if name == crypto_name:
            crypto_id = cid
            break
    else:
        bot.reply_to(message, "Неизвестная криптовалюта. Выберите из списка.")
        return

    user_crypto[message.chat.id] = crypto_id

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(telebot.types.InlineKeyboardButton("Цена", callback_data=f"price_{crypto_id}"),
                 telebot.types.InlineKeyboardButton("Прогноз", callback_data=f"predict_{crypto_id}"))

    bot.send_message(message.chat.id, f"Выбрана {crypto_name}. Что хотите узнать?", reply_markup=keyboard)


def get_historical_data(crypto_id, days=7):
    if crypto_id in historical_data and len(historical_data[crypto_id]) >= days:
        return historical_data[crypto_id]

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': days}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()['prices']
        historical_data[crypto_id] = data
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка получения исторических данных: {e}")
        return None



def predict_price(crypto_id):
    data = get_historical_data(crypto_id)
    if data is None:
        return None

    prices = [p[1] for p in data]
    days = np.arange(len(prices)).reshape(-1, 1)

    model = LinearRegression()
    model.fit(days, prices)

    next_day = len(prices)
    predicted_price = model.predict([[next_day]])[0]
    return predicted_price

def get_price_and_predict(crypto_id):

    try:
        params = {'ids': crypto_id, 'vs_currencies': 'usd'}
        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if crypto_id not in data:
            return None, None

        current_price = data[crypto_id]['usd']
        predicted_price = predict_price(crypto_id)
        return current_price, predicted_price

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка API или сети: {e}")
        return None, None




@bot.callback_query_handler(func=lambda call: call.data.startswith("price_"))
def handle_price_callback(call):
    crypto_id = call.data.split("_")[1]
    current_price, _ = get_price_and_predict(crypto_id)
    if current_price is not None:
        bot.send_message(call.message.chat.id, f"Текущая цена {crypto_id}: ${current_price:.2f}")
    else:
        bot.send_message(call.message.chat.id, "Ошибка получения цены. Попробуйте позже.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("predict_"))
def handle_predict_callback(call):
    crypto_id = call.data.split("_")[1]
    _, predicted_price = get_price_and_predict(crypto_id)
    if predicted_price is not None:
        bot.send_message(call.message.chat.id, f"Прогноз цены {crypto_id} на завтра: ${predicted_price:.2f}")
    else:
        bot.send_message(call.message.chat.id, "Ошибка получения прогноза. Попробуйте позже.")


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling

