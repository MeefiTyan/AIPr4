import requests
from datetime import datetime
from collections import defaultdict, Counter
from transliterate import translit
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from db import init_db, add_user, add_order, get_orders_by_user

init_db()

# === Меню ===
main_menu = ReplyKeyboardMarkup(
    [["🌸 Замовити букет", "📦 Переглянути замовлення"],
     ["☁️ Погода", "💱 Обмін валют"],
     ["🔮 Гороскоп", "ℹ️ Про компанію"]],
    resize_keyboard=True
)

bouquet_menu = ReplyKeyboardMarkup(
    [["🌹 Романтичний", "🌻 Весняний", "🌼 Святковий"], ["⬅️ Назад"]],
    resize_keyboard=True
)

zodiac_menu = ReplyKeyboardMarkup(
    [["Aries", "Taurus", "Gemini", "Cancer"],
     ["Leo", "Virgo", "Libra", "Scorpio"],
     ["Sagittarius", "Capricorn", "Aquarius", "Pisces"],
     ["⬅️ Назад"]],
    resize_keyboard=True
)

OWM_API_KEY = "1bc0cb331198cebe74c5f3c8ebaa1a06"
OWM_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
CURRENCY_API_KEY = "e70864b830e5f11963c11264ea6b5909"
CURRENCY_API_URL = "https://api.currencylayer.com/live"
HOROSCOPE_API_KEY = "cPKtC/x3er16fYINXK3C+w==DXlXUvQ6288cs6nK"
HOROSCOPE_API_URL = "https://api.api-ninjas.com/v1/horoscope"

# === Функції для погоди ===
def get_forecast_for_city(city_name: str, days: int = 3):
    try:
        city_translit = translit(city_name, 'uk', reversed=True)
        params = {
            "q": city_translit,
            "appid": OWM_API_KEY,
            "units": "metric",
            "lang": "uk"
        }
        resp = requests.get(OWM_URL_FORECAST, params=params)
        data = resp.json()
        if resp.status_code != 200 or data.get("cod") not in ("200", 200):
            return None
        grouped = defaultdict(list)
        for entry in data["list"]:
            dt = datetime.utcfromtimestamp(entry["dt"])
            date_str = dt.strftime("%d.%m.%Y")
            temp = entry["main"]["temp"]
            wind = entry["wind"]["speed"]
            desc = entry["weather"][0]["description"]
            grouped[date_str].append((temp, wind, desc))
        forecast = []
        for date, records in list(grouped.items())[:days]:
            temps = [t for t, _, _ in records]
            winds = [w for _, w, _ in records]
            descs = [d for _, _, d in records]
            avg_temp = sum(temps) / len(temps)
            avg_wind = sum(winds) / len(winds)
            common_desc = Counter(descs).most_common(1)[0][0].capitalize()
            forecast.append((date, avg_temp, common_desc, avg_wind))
        return forecast
    except Exception as e:
        print("Weather forecast error:", e)
        return None

def format_forecast(forecast, city_name: str):
    msg = f"📅 Прогноз погоди у місті {city_name.capitalize()}:\n\n"
    for date, temp, desc, wind in forecast:
        msg += f"🔹 {date}\n🌡 Температура: {temp:.1f}°C\n☁️ {desc}\n💨 Вітер: {wind:.1f} м/с\n\n"
    return msg

# === Функція для обміну валют ===
def convert_currency(amount, from_currency, to_currency):
    try:
        params = {"access_key": CURRENCY_API_KEY}
        resp = requests.get(CURRENCY_API_URL, params=params)
        data = resp.json()
        if not data.get("success"):
            return None
        quotes = data.get("quotes", {})
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        if from_currency == "USD":
            rate_from = 1.0
        else:
            rate_from = quotes.get(f"USD{from_currency}")
        if to_currency == "USD":
            rate_to = 1.0
        else:
            rate_to = quotes.get(f"USD{to_currency}")
        if (rate_from is None) or (rate_to is None):
            return None
        usd_amount = amount / rate_from
        converted_amount = usd_amount * rate_to
        return converted_amount
    except Exception as e:
        print("Currency conversion error:", e)
        return None

# === Функція для гороскопу ===
def get_horoscope_for_sign(sign: str):
    try:
        params = {"zodiac": sign.lower()}
        headers = {"x-api-key": HOROSCOPE_API_KEY}

        response = requests.get(HOROSCOPE_API_URL, params=params, headers=headers)
        data = response.json()

        if response.status_code != 200 or "horoscope" not in data:
            print(f"Error fetching horoscope for {sign}: {response.text}")
            return None, None

        horoscope = data["horoscope"]
        date = data.get("date", "сьогодні")

        return horoscope, date

    except Exception as e:
        print("Horoscope API exception:", e)
        return None, None


# === Обробка команди /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"Вітаю, {user.first_name}! 🌷\nЯ — бот-магазин букетів FlowerBot.\nОберіть дію нижче:",
        reply_markup=main_menu
    )

# === Обробка повідомлень ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # === Погода ===
    if text == "☁️ Погода":
        await update.message.reply_text("Введіть назву міста для прогнозу погоди:")
        context.user_data["state"] = "awaiting_city"
        return

    if context.user_data.get("state") == "awaiting_city":
        city = text
        forecast = get_forecast_for_city(city, days=5)
        if forecast:
            msg = format_forecast(forecast, city)
            await update.message.reply_text(msg, reply_markup=main_menu)
        else:
            await update.message.reply_text("Не вдалося отримати прогноз для цього міста. Спробуйте інше 🌧️", reply_markup=main_menu)
        context.user_data.pop("state", None)
        return

    # === Обмін валют ===
    if text == "💱 Обмін валют":
        await update.message.reply_text("Введіть суму та валюти у форматі: `100 USD в EUR`")
        context.user_data["state"] = "awaiting_currency"
        return

    if context.user_data.get("state") == "awaiting_currency":
        parts = text.replace(",", ".").upper().split()
        if len(parts) == 4 and parts[2] in ("В", "IN"):
            try:
                amount = float(parts[0])
                from_curr = parts[1]
                to_curr = parts[3]
                result = convert_currency(amount, from_curr, to_curr)
                if result is None:
                    await update.message.reply_text("Не вдалося виконати конвертацію. Перевірте валюти.", reply_markup=main_menu)
                else:
                    await update.message.reply_text(f"{amount:.2f} {from_curr} = {result:.2f} {to_curr}", reply_markup=main_menu)
            except ValueError:
                await update.message.reply_text("Невірна сума. Спробуйте ще раз.", reply_markup=main_menu)
        else:
            await update.message.reply_text("Неправильний формат. Приклад: `100 USD в EUR`", reply_markup=main_menu)
        context.user_data.pop("state", None)
        return

    # === Гороскоп ===
    if text == "🔮 Гороскоп":
        await update.message.reply_text("Оберіть ваш знак зодіаку:", reply_markup=zodiac_menu)
        context.user_data["state"] = "awaiting_zodiac"
        return

    if context.user_data.get("state") == "awaiting_zodiac":
        sign = text.strip()
        valid = {
            "aries","taurus","gemini","cancer","leo","virgo",
            "libra","scorpio","sagittarius","capricorn","aquarius","pisces"
        }
        if sign.lower() in valid:
            result = get_horoscope_for_sign(sign)
            if result:
                horoscope_text, date = result
                await update.message.reply_text(f"Гороскоп для *{sign.capitalize()}* на {date}:\n{horoscope_text}", reply_markup=main_menu)
            else:
                await update.message.reply_text("Не вдалося отримати гороскоп — спробуйте пізніше.", reply_markup=main_menu)
        else:
            await update.message.reply_text("Невірний знак зодіаку. Спробуйте ще раз.", reply_markup=main_menu)
        context.user_data.pop("state", None)
        return

    # === Замовлення букетів ===
    if text == "🌸 Замовити букет":
        await update.message.reply_text("Оберіть тип букета:", reply_markup=bouquet_menu)

    elif text in ["🌹 Романтичний", "🌻 Весняний", "🌼 Святковий"]:
        context.user_data["bouquet"] = text
        await update.message.reply_text("Скільки букетів бажаєте замовити?")
        context.user_data["state"] = "quantity"

    elif context.user_data.get("state") == "quantity":
        try:
            qty = int(text)
            context.user_data["quantity"] = qty
            await update.message.reply_text("Вкажіть адресу доставки:")
            context.user_data["state"] = "address"
        except ValueError:
            await update.message.reply_text("Будь ласка, введіть кількість числом.")

    elif context.user_data.get("state") == "address":
        address = text
        bouquet = context.user_data["bouquet"]
        qty = context.user_data["quantity"]
        add_order(user_id, bouquet, qty, address)
        await update.message.reply_text(
            f"✅ Замовлення оформлено!\nБукет: {bouquet}\nКількість: {qty}\nАдреса: {address}",
            reply_markup=main_menu
        )
        context.user_data.clear()

    elif text == "📦 Переглянути замовлення":
        orders = get_orders_by_user(user_id)
        if not orders:
            await update.message.reply_text("У вас ще немає замовлень 🌼", reply_markup=main_menu)
        else:
            msg = "📋 Ваші замовлення:\n\n"
            for i, (b_type, qty, addr) in enumerate(orders, start=1):
                msg += f"{i}. {b_type} — {qty} шт.\n   📍 {addr}\n\n"
            await update.message.reply_text(msg, reply_markup=main_menu)

    elif text == "ℹ️ Про компанію":
        await update.message.reply_text(
            "🌷 FlowerBot — це сервіс замовлення букетів онлайн.\nПрацюємо щодня з 9:00 до 20:00 💐",
            reply_markup=main_menu
        )

    elif text == "⬅️ Назад":
        await update.message.reply_text("Повертаємось у головне меню:", reply_markup=main_menu)

    else:
        await update.message.reply_text("Будь ласка, скористайтесь меню ⬇️", reply_markup=main_menu)

# === Запуск бота ===
def main():
    TOKEN = "8383819822:AAFHCx3sAbJMgThexR47eEkcMXmwtWvJEQQ"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущений і працює")
    app.run_polling()

if __name__ == "__main__":
    main()

