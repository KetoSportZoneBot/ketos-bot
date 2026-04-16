import telebot
from telebot import types
import requests
import os

TOKEN = os.environ.get("TOKEN", "8758161336:AAF3cFGkiBWThibk9rfCWdMj8-2RDh4EvB4")
LOGMEAL_TOKEN = os.environ.get("LOGMEAL_TOKEN", "e13a5e2122a3d3ec6c44cedbee0b99b344a3395e")
bot = telebot.TeleBot(TOKEN)

users = {}
states = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "name": "", "weight": "", "goal": "", "activity": "",
            "ketones": 0.0, "fat": 0, "protein": 0, "carbs": 0,
            "calories": 0, "meals": [], "region": "🇷🇺 Россия/СНГ",
            "fat_target": 140, "protein_target": 120, "carbs_target": 25,
            "sport_type": "", "last_gel_carbs": 0,
            "search_results": [], "pending_food": None
        }
    return users[uid]

def set_state(uid, state):
    states[uid] = state

def get_state(uid):
    return states.get(uid, "menu")

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Мой статус", "🍽 Добавить еду")
    kb.row("📸 Фото блюда", "⚡ Спортивный режим")
    kb.row("👨‍👩‍👧 Семья", "🧪 Ввести кетоны")
    kb.row("⚙️ Настройки", "🔄 Перезапуск")
    return kb

def food_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 Фото блюда", "🔍 Поиск продукта")
    kb.row("🥑 Авокадо 200г", "🥩 Стейк 200г")
    kb.row("🥚 Яйца 2шт", "🐟 Лосось 150г")
    kb.row("🥗 Салат+масло", "🧀 Сыр 50г")
    kb.row("🥜 Миндаль 30г", "🫐 Черника 80г")
    kb.row("🍳 Бекон 3шт", "✏️ Ввести вручную")
    kb.row("◀️ Главное меню")
    return kb

def sport_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏃 Трейл/Бег", "🚴 Велогонка")
    kb.row("🏊 Триатлон", "⛷️ Лыжи")
    kb.row("🏋️ Силовая", "🔄 Возврат в кетоз")
    kb.row("◀️ Главное меню")
    return kb

def after_gel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 План возврата в кетоз")
    kb.row("📊 Мой статус", "🍽 Добавить еду")
    kb.row("◀️ Главное меню")
    return kb

def choice_kb(n):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(*[str(i) for i in range(1, n+1)])
    kb.row("🔍 Искать снова", "◀️ Главное меню")
    return kb

def confirm_photo_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✅ Добавить в дневник", "✏️ Скорректировать")
    kb.row("❌ Отмена")
    return kb

FOOD_DB = {
    "🥑 Авокадо 200г": {"name": "Авокадо (200г)", "fat": 21, "protein": 2, "carbs": 2, "cal": 200},
    "🥩 Стейк 200г": {"name": "Стейк говяжий (200г)", "fat": 18, "protein": 30, "carbs": 0, "cal": 280},
    "🥚 Яйца 2шт": {"name": "Яйца (2 шт)", "fat": 10, "protein": 12, "carbs": 1, "cal": 140},
    "🐟 Лосось 150г": {"name": "Лосось (150г)", "fat": 14, "protein": 28, "carbs": 0, "cal": 240},
    "🥗 Салат+масло": {"name": "Салат + оливк. масло", "fat": 14, "protein": 2, "carbs": 3, "cal": 145},
    "🧀 Сыр 50г": {"name": "Сыр твёрдый (50г)", "fat": 14, "protein": 12, "carbs": 0, "cal": 180},
    "🥜 Миндаль 30г": {"name": "Миндаль (30г)", "fat": 15, "protein": 6, "carbs": 3, "cal": 170},
    "🫐 Черника 80г": {"name": "Черника (80г)", "fat": 0, "protein": 1, "carbs": 9, "cal": 45},
    "🍳 Бекон 3шт": {"name": "Бекон (3 полоски)", "fat": 12, "protein": 9, "carbs": 0, "cal": 140},
}

def bar(done, target):
    pct = min(int(done / max(target, 1) * 10), 10)
    return "▓" * pct + "░" * (10 - pct)

def analyze_photo(image_bytes):
    """Анализ фото через LogMeal API — исправленные endpoints"""
    try:
        headers = {"Authorization": f"Bearer {LOGMEAL_TOKEN}"}

        # Шаг 1: Распознавание блюда (новый endpoint)
        files = {"image": ("food.jpg", image_bytes, "image/jpeg")}
        r1 = requests.post(
            "https://api.logmeal.com/v2/image/segmentation/complete",
            headers=headers,
            files=files,
            timeout=30
        )
        print(f"LogMeal step1 status: {r1.status_code}")
        print(f"LogMeal step1 response: {r1.text[:300]}")

        if r1.status_code != 200:
            return None

        data1 = r1.json()
        image_id = data1.get("imageId")

        # Собираем названия блюд
        segmentation = data1.get("segmentation_results", [])
        dish_names = []
        for seg in segmentation:
            recognition = seg.get("recognition_results", [])
            for rec in recognition:
                name = rec.get("name", "")
                if name:
                    dish_names.append(name)

        if not image_id:
            return None

        # Шаг 2: Нутриенты (новый endpoint)
        r2 = requests.post(
            "https://api.logmeal.com/v2/nutrition/recipe/nutritionalInfo",
            headers=headers,
            json={"imageId": image_id},
            timeout=15
        )
        print(f"LogMeal step2 status: {r2.status_code}")
        print(f"LogMeal step2 response: {r2.text[:300]}")

        nutrients = {}
        if r2.status_code == 200:
            data2 = r2.json()
            nutrients = data2.get("nutritional_info", {})

        result = {
            "dishes": dish_names if dish_names else ["Блюдо"],
            "calories": round(float(nutrients.get("calories", 0) or 0)),
            "fat": round(float(nutrients.get("totalFat", 0) or 0), 1),
            "protein": round(float(nutrients.get("proteins", 0) or 0), 1),
            "carbs": round(float(nutrients.get("totalCarbs", 0) or 0), 1),
        }
        return result

    except Exception as e:
        print(f"LogMeal error: {e}")
        return None

def search_food(query):
    try:
        headers = {"User-Agent": "KetOSBot/1.0 (Telegram bot for keto diet tracking)"}
        params = {
            "search_terms": query, "search_simple": 1,
            "action": "process", "json": 1, "page_size": 20,
            "fields": "product_name,nutriments,brands"
        }
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl",
            params=params, headers=headers, timeout=15)
        data = r.json()
        results = []
        for p in data.get("products", []):
            name = p.get("product_name", "").strip()
            if not name or len(name) < 2: continue
            n = p.get("nutriments", {})
            fat = round(float(n.get("fat_100g") or 0), 1)
            protein = round(float(n.get("proteins_100g") or 0), 1)
            carbs = round(float(n.get("carbohydrates_100g") or 0), 1)
            cal = round(float(n.get("energy-kcal_100g") or 0))
            if fat == 0 and protein == 0 and carbs == 0: continue
            brand = p.get("brands", "").strip()
            display = name + (f" — {brand}" if brand and brand.lower() not in name.lower() else "")
            results.append({"name": display[:50], "fat": fat, "protein": protein, "carbs": carbs, "cal": cal})
            if len(results) >= 5: break
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def recovery_text(total_carbs):
    hours = max(4, int(total_carbs / 15))
    return (
        f"🔄 *План возврата в кетоз*\nПосле {total_carbs}г углеводов\n\n"
        f"⏱ *0–2 часа:* Вода, соль, электролиты\n"
        f"⏱ *2–3 часа:* 1 ст.л. MCT масла\n"
        f"⏱ *3–5 часов:* Голодай + прогулка\n"
        f"⏱ *~{hours} часов:* Жирное мясо + овощи\n\n"
        f"✅ *Через {hours}–{hours+2} часов снова в кетозе!*\n"
        f"💡 Измерь кетоны через {hours} часов 🧪"
    )

# ===== ОБРАБОТЧИК ФОТО =====
@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    bot.send_message(msg.chat.id,
        "📸 *Фото получено!*\n🤖 Анализирую блюдо...\nЭто займёт 10-15 секунд ⏳",
        parse_mode="Markdown"
    )
    file_id = msg.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    image_bytes = requests.get(file_url).content
    result = analyze_photo(image_bytes)

    if not result or (result["calories"] == 0 and result["fat"] == 0):
        bot.send_message(msg.chat.id,
            "❌ Не удалось распознать блюдо.\n\n"
            "Попробуй:\n• Сфотографировать ближе\n• Лучше освещение\n• Или добавь вручную 👇",
            reply_markup=food_kb()
        )
        set_state(uid, "food")
        return

    u["pending_food"] = result
    set_state(uid, "confirm_photo")
    dishes_text = ", ".join(result["dishes"][:3])
    carbs_warn = "⚠️ Много углеводов для кето!" if result["carbs"] > 10 else "✅ Кето-дружественно"

    bot.send_message(msg.chat.id,
        f"🤖 *Результат анализа:*\n\n"
        f"🍽 *Блюдо:* {dishes_text}\n\n"
        f"🔥 Калории: *{result['calories']} ккал*\n"
        f"🟠 Жиры: *{result['fat']}г*\n"
        f"🔵 Белки: *{result['protein']}г*\n"
        f"🟡 Углеводы: *{result['carbs']}г*\n\n"
        f"{carbs_warn}\n\n"
        f"Всё правильно? Добавляем в дневник?",
        parse_mode="Markdown", reply_markup=confirm_photo_kb()
    )

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    set_state(uid, "ask_name")
    bot.send_message(msg.chat.id,
        "🔥 *Добро пожаловать в KetOS!*\n\nКак тебя зовут?",
        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    text = msg.text
    state = get_state(uid)

    if text in ["🔄 Перезапуск", "◀️ Главное меню"]:
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "✅ Главное меню:", reply_markup=main_kb())
        return

    if state == "ask_name":
        u["name"] = text
        set_state(uid, "ask_weight")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("50-60 кг", "60-70 кг"); kb.row("70-80 кг", "80-90 кг"); kb.row("90-100 кг", "100+ кг")
        bot.send_message(msg.chat.id, f"Привет, *{text}*! 💪\nКакой у тебя вес?", parse_mode="Markdown", reply_markup=kb)
        return

    if state == "ask_weight":
        u["weight"] = text; set_state(uid, "ask_activity")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🏃 Бег/Трейл", "🚴 Велоспорт"); kb.row("🏊 Плавание", "🏋️ Силовые"); kb.row("⛷️ Лыжи/Триатлон", "🚶 Лёгкая")
        bot.send_message(msg.chat.id, "Твой вид спорта?", reply_markup=kb)
        return

    if state == "ask_activity":
        u["activity"] = text; set_state(uid, "ask_goal")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🔥 Похудение", "💪 Набор мышц"); kb.row("⚡ Производительность", "🎯 Поддержание")
        bot.send_message(msg.chat.id, "Твоя главная цель?", reply_markup=kb)
        return

    if state == "ask_goal":
        u["goal"] = text
        cal = 1600 if "Похудение" in text else 2400 if "Набор" in text else 2200 if "Производительность" in text else 1900
        u["fat_target"] = round(cal * 0.70 / 9)
        u["protein_target"] = round(cal * 0.25 / 4)
        u["carbs_target"] = round(cal * 0.05 / 4)
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            f"✅ *Профиль готов!*\n\n👤 {u['name']} | ⚖️ {u['weight']}\n🏃 {u['activity']} | 🎯 {u['goal']}\n\n"
            f"📊 *Макросы:*\n🟠 Жиры: *{u['fat_target']}г*\n🔵 Белки: *{u['protein_target']}г*\n🟡 Углеводы: *{u['carbs_target']}г*\n\nПоехали! 🚀",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ПОДТВЕРЖДЕНИЕ ФОТО
    if state == "confirm_photo":
        if text == "✅ Добавить в дневник":
            food = u.get("pending_food")
            if food:
                u["fat"] += food["fat"]; u["protein"] += food["protein"]
                u["carbs"] += food["carbs"]; u["calories"] += food["calories"]
                dishes = ", ".join(food["dishes"][:2])
                u["meals"].append(f"{dishes[:30]} ({food['calories']}ккал)")
                carbs_left = u["carbs_target"] - u["carbs"]
                u["pending_food"] = None; set_state(uid, "menu")
                bot.send_message(msg.chat.id,
                    f"✅ *Добавлено!*\nОсталось углеводов: *{max(carbs_left,0)}г*",
                    parse_mode="Markdown", reply_markup=main_kb())
            return

        if text == "✏️ Скорректировать":
            food = u.get("pending_food")
            set_state(uid, "correct_photo")
            bot.send_message(msg.chat.id,
                f"Текущие значения:\nЖ:{food['fat']}г Б:{food['protein']}г У:{food['carbs']}г Кал:{food['calories']}\n\n"
                f"Введи исправленные:\n*Название, жиры, белки, углеводы*\n\nПример: `Рыба с овощами, 12, 25, 8`",
                parse_mode="Markdown")
            return

        if text == "❌ Отмена":
            u["pending_food"] = None; set_state(uid, "menu")
            bot.send_message(msg.chat.id, "Отменено.", reply_markup=main_kb())
            return

    if state == "correct_photo":
        try:
            parts = text.split(",")
            name = parts[0].strip()
            fat = int(parts[1].strip()); protein = int(parts[2].strip()); carbs = int(parts[3].strip())
            cal = fat*9 + protein*4 + carbs*4
            u["fat"] += fat; u["protein"] += protein; u["carbs"] += carbs; u["calories"] += cal
            u["meals"].append(f"{name} ({cal}ккал)")
            carbs_left = u["carbs_target"] - u["carbs"]
            u["pending_food"] = None; set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}* добавлено!\nЖ:{fat}г Б:{protein}г У:{carbs}г\nОсталось: *{max(carbs_left,0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Пример: `Рыба с овощами, 12, 25, 8`", parse_mode="Markdown")
        return

    if text == "📊 Мой статус":
        k = u["ketones"]
        ks = "❓ Не измерено" if k==0 else "❌ Не в кетозе" if k<0.5 else "🟡 Лёгкий кетоз" if k<1.5 else "✅ Оптимальный кетоз!" if k<3 else "🔥 Глубокий кетоз"
        meals_text = "\n".join(f"  • {m}" for m in u["meals"][-5:]) if u["meals"] else "  Пока ничего"
        bot.send_message(msg.chat.id,
            f"📊 *Статус на сегодня*\n\n🧪 {ks} ({k} ммоль/л)\n\n"
            f"🟠 Жиры:     {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}г\n"
            f"🔵 Белки:    {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}г\n"
            f"🟡 Углеводы: {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}г\n\n"
            f"🍽 *Съедено:*\n{meals_text}",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "📸 Фото блюда":
        set_state(uid, "waiting_photo")
        bot.send_message(msg.chat.id,
            "📸 *Отправь фото своего блюда!*\n\nAI посчитает калории, жиры, белки и углеводы.\nПросто прикрепи фото 👇",
            parse_mode="Markdown")
        return

    if text == "🍽 Добавить еду":
        set_state(uid, "food")
        bot.send_message(msg.chat.id, "Что добавляем?", reply_markup=food_kb())
        return

    if text in ["🔍 Поиск продукта", "🔍 Искать снова"]:
        set_state(uid, "search_food")
        bot.send_message(msg.chat.id,
            "🔍 Напиши название:\n🇷🇺 `творог`, `курица`\n🇬🇧 `salmon`, `chicken`",
            parse_mode="Markdown")
        return

    if state == "search_food":
        bot.send_message(msg.chat.id, f"🔍 Ищу *{text}*...", parse_mode="Markdown")
        results = search_food(text)
        translations = {"колбаса":"sausage","творог":"cottage cheese","гречка":"buckwheat","курица":"chicken","говядина":"beef","свинина":"pork","рыба":"fish"}
        if not results:
            eng = translations.get(text.lower())
            if eng: results = search_food(eng)
        if not results:
            bot.send_message(msg.chat.id, "❌ Не найдено. Попробуй по-английски.", reply_markup=food_kb())
            set_state(uid, "food"); return
        u["search_results"] = results
        resp = f"✅ *Найдено {len(results)}* (на 100г):\n\n"
        for i, p in enumerate(results, 1):
            warn = "⚠️" if p["carbs"] > 10 else "✅"
            resp += f"*{i}.* {p['name']}\n   🟠{p['fat']}г 🔵{p['protein']}г {warn}{p['carbs']}г 🔥{p['cal']}ккал\n\n"
        resp += "Напиши номер:"
        set_state(uid, "choose_food")
        bot.send_message(msg.chat.id, resp, parse_mode="Markdown", reply_markup=choice_kb(len(results)))
        return

    if state == "choose_food":
        if text.isdigit():
            idx = int(text) - 1
            results = u.get("search_results", [])
            if 0 <= idx < len(results):
                food = results[idx]
                u["fat"] += food["fat"]; u["protein"] += food["protein"]
                u["carbs"] += food["carbs"]; u["calories"] += food["cal"]
                u["meals"].append(f"{food['name'][:30]} ({food['cal']}ккал/100г)")
                carbs_left = u["carbs_target"] - u["carbs"]
                set_state(uid, "menu")
                bot.send_message(msg.chat.id,
                    f"✅ *{food['name'][:40]}* добавлено!\n🟠+{food['fat']}г 🔵+{food['protein']}г 🟡+{food['carbs']}г\nОсталось: *{max(carbs_left,0)}г*",
                    parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "✏️ Ввести вручную":
        set_state(uid, "manual_food")
        bot.send_message(msg.chat.id, "Напиши: *Название, жиры, белки, углеводы*\n\nПример: `Творог 5%, 5, 18, 3`", parse_mode="Markdown")
        return

    if text in FOOD_DB:
        food = FOOD_DB[text]
        u["fat"] += food["fat"]; u["protein"] += food["protein"]; u["carbs"] += food["carbs"]; u["calories"] += food["cal"]
        u["meals"].append(f"{food['name']} ({food['cal']} ккал)")
        carbs_left = u["carbs_target"] - u["carbs"]
        set_state(uid, "food")
        bot.send_message(msg.chat.id,
            f"✅ *{food['name']}* добавлено!\n🟠+{food['fat']}г 🔵+{food['protein']}г 🟡+{food['carbs']}г\nОсталось: *{max(carbs_left,0)}г*",
            parse_mode="Markdown", reply_markup=food_kb())
        return

    if state == "manual_food":
        try:
            parts = text.split(",")
            name = parts[0].strip(); fat = int(parts[1].strip()); protein = int(parts[2].strip()); carbs = int(parts[3].strip())
            cal = fat*9 + protein*4 + carbs*4
            u["fat"] += fat; u["protein"] += protein; u["carbs"] += carbs; u["calories"] += cal
            u["meals"].append(f"{name} ({cal}ккал)")
            carbs_left = u["carbs_target"] - u["carbs"]
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}* добавлено!\nЖ:{fat}г Б:{protein}г У:{carbs}г\nОсталось: *{max(carbs_left,0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Пример: `Творог 5%, 5, 18, 3`", parse_mode="Markdown")
        return

    if text == "🧪 Ввести кетоны":
        set_state(uid, "ketones")
        bot.send_message(msg.chat.id, "Введи уровень кетонов (ммоль/л)\nНапример: *1.8*", parse_mode="Markdown")
        return

    if state == "ketones":
        try:
            val = float(text.replace(",", "."))
            u["ketones"] = val
            s = "❌ Не в кетозе\n💡 Сократи углеводы" if val<0.5 else "🟡 Лёгкий кетоз\n💡 Уменьши углеводы на 5г" if val<1.5 else "✅ Оптимальный кетоз!\n💡 Продолжай!" if val<3 else "🔥 Глубокий кетоз\n💡 Пей воду + электролиты"
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, f"🧪 *{val} ммоль/л*\n\n{s}", parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Введи число: *1.8*", parse_mode="Markdown")
        return

    if text == "⚡ Спортивный режим":
        set_state(uid, "sport")
        bot.send_message(msg.chat.id, "⚡ Выбери активность:", reply_markup=sport_kb())
        return

    if text in ["🔄 План возврата в кетоз", "🔄 Возврат в кетоз"]:
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, recovery_text(u.get("last_gel_carbs", 60)), parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "🏋️ Силовая":
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "🏋️ *Силовая на кето*\n\nДо: MCT масло + кофе\nВо время: вода + соль\nПосле: 30-40г белка за 30 мин", parse_mode="Markdown", reply_markup=main_kb())
        return

    if text in ["🏃 Трейл/Бег", "🚴 Велогонка", "🏊 Триатлон", "⛷️ Лыжи"]:
        u["sport_type"] = text; set_state(uid, "ask_distance")
        bot.send_message(msg.chat.id, "Дистанция или время?\nПример: *42 км* или *3 часа*", parse_mode="Markdown")
        return

    if state == "ask_distance":
        try:
            t = text.lower()
            hours = float(''.join(c for c in t if c.isdigit() or c=='.')) if "час" in t else float(''.join(c for c in t if c.isdigit() or c=='.'))/10 if "км" in t else 2
            gels = max(1, int(hours/1.5)); total = gels*20; u["last_gel_carbs"] = total
            resp = f"⚡ *Протокол гелей*\n📍 {text} (~{int(hours)}ч)\n💊 Гелей: {gels} шт\n\n"
            times = [0, 0.4, 0.7, 0.9]
            for i in range(gels):
                t_min = int(hours*times[min(i,3)]*60)
                resp += f"🟡 *{'За 30 мин до старта' if i==0 else f'Через {t_min} мин'}:* Гель #{i+1} — 20г\n"
            resp += f"\n📊 Итого: *{total}г*\n⏱ Возврат: *~{max(4,int(total/15))} часов*\n\n🏁 После финиша нажми:\n👉 *🔄 План возврата в кетоз*"
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, resp, parse_mode="Markdown", reply_markup=after_gel_kb())
        except:
            bot.send_message(msg.chat.id, "Напиши: *42 км* или *3 часа*", parse_mode="Markdown")
        return

    if text == "👨‍👩‍👧 Семья":
        meals_text = "\n".join(f"  • {m}" for m in u["meals"]) if u["meals"] else "  Пока нет"
        bot.send_message(msg.chat.id,
            f"👨‍👩‍👧 *Семейный режим*\n\nПригласи партнёра:\n`https://t.me/ketOSzoneBot?start=family_{uid}`\n\n📋 *Рацион:*\n{meals_text}",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "⚙️ Настройки":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🔄 Сбросить день"); kb.row("◀️ Главное меню")
        bot.send_message(msg.chat.id,
            f"⚙️ *Настройки*\n\n👤 {u.get('name','—')} | ⚖️ {u.get('weight','—')}\n🏃 {u.get('activity','—')} | 🎯 {u.get('goal','—')}\n\n🟠 {u['fat_target']}г 🔵 {u['protein_target']}г 🟡 {u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=kb)
        return

    if text == "🔄 Сбросить день":
        u["fat"] = u["protein"] = u["carbs"] = u["calories"] = 0; u["meals"] = []
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "✅ День сброшен!", reply_markup=main_kb())
        return

    set_state(uid, "menu")
    bot.send_message(msg.chat.id, "Используй кнопки 👇", reply_markup=main_kb())

print("🔥 KetOS бот запущен с исправленным LogMeal API!")
bot.polling(none_stop=True, interval=0, timeout=20)
