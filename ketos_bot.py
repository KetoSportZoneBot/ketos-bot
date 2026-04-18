import telebot
from telebot import types
import requests
import os

TOKEN = os.environ.get("TOKEN", "8758161336:AAF3cFGkiBWThibk9rfCWdMj8-2RDh4EvB4")
LOGMEAL_TOKEN = os.environ.get("LOGMEAL_TOKEN", "a50507ce2019da95e0341da750d887449d40df54")
bot = telebot.TeleBot(TOKEN)

users = {}
states = {}

# ============================================================
# HELPERS
# ============================================================

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "name": "", "weight": 70, "height": 170, "age": 30,
            "goal": "", "activity": "", "activity_coef": 1.55,
            "keto_level": "🟡 Нормальное кето", "sport_type": "",
            "ketones": 0.0,
            "fat": 0, "protein": 0, "carbs": 0, "calories": 0,
            "fat_target": 140, "protein_target": 120,
            "carbs_target": 25, "cal_target": 1900,
            "meals": [],
            "last_gel_carbs": 0,
            "search_results": [],
            "pending_food": None,
            "pending_alcohol": None,
            "pending_search_food": None,
        }
    return users[uid]

def set_state(uid, s):
    states[uid] = s

def get_state(uid):
    return states.get(uid, "menu")

def bar(done, target):
    pct = min(int(done / max(target, 1) * 10), 10)
    return "▓" * pct + "░" * (10 - pct)

def calc_macros(u):
    w = float(u.get("weight", 70))
    h = float(u.get("height", 170))
    a = float(u.get("age", 30))
    coef = float(u.get("activity_coef", 1.55))
    bmr = 10 * w + 6.25 * h - 5 * a - 161
    tdee = round(bmr * coef)
    goal = u.get("goal", "")
    if "Похудение" in goal:
        cal = tdee - 400
    elif "Набор" in goal:
        cal = tdee + 300
    else:
        cal = tdee
    return {
        "calories": cal,
        "fat": round(cal * 0.70 / 9),
        "protein": round(cal * 0.25 / 4),
        "carbs": round(cal * 0.05 / 4),
        "tdee": tdee,
    }

def apply_keto_level(u, level):
    cal = u["cal_target"]
    if level == "🔴 Строгое кето":
        u["fat_target"] = round(cal * 0.75 / 9)
        u["protein_target"] = round(cal * 0.20 / 4)
        u["carbs_target"] = round(cal * 0.05 / 4)
    elif level == "🟡 Нормальное кето":
        u["fat_target"] = round(cal * 0.70 / 9)
        u["protein_target"] = round(cal * 0.25 / 4)
        u["carbs_target"] = round(cal * 0.05 / 4)
    elif level == "🟢 Низкоуглеводная диета":
        u["fat_target"] = round(cal * 0.50 / 9)
        u["protein_target"] = round(cal * 0.30 / 4)
        u["carbs_target"] = round(cal * 0.20 / 4)
    u["keto_level"] = level

# ============================================================
# KEYBOARDS
# ============================================================

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Мой статус", "📋 Дневник питания")
    kb.row("📸 КБЖУ по фото", "✏️ Ввести еду вручную")
    kb.row("🔍 Поиск продукта", "⚡ Спортивный режим")
    kb.row("🍷 Выпил алкоголь", "🧪 Ввести кетоны")
    kb.row("👨‍👩‍👧 Семья", "⚙️ Настройки")
    kb.row("🔄 Перезапуск")
    return kb

def food_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 КБЖУ по фото", "🔍 Поиск продукта")
    kb.row("🥑 Авокадо 200г", "🥩 Стейк 200г")
    kb.row("🥚 Яйца 2шт", "🐟 Лосось 150г")
    kb.row("🥗 Салат+масло", "🧀 Сыр 50г")
    kb.row("🥜 Миндаль 30г", "🫐 Черника 80г")
    kb.row("🍳 Бекон 3шт", "✏️ Ввести еду вручную")
    kb.row("◀️ Главное меню")
    return kb

def sport_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏃 Трейл/Бег", "🚴 Велогонка")
    kb.row("🏊 Триатлон", "⛷️ Лыжи")
    kb.row("🏋️ Силовая", "🔄 Возврат в кетоз")
    kb.row("🍷 Выпил алкоголь", "◀️ Главное меню")
    return kb

def after_gel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 План возврата в кетоз")
    kb.row("📊 Мой статус", "◀️ Главное меню")
    return kb

def confirm_photo_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✅ Добавить в дневник", "✏️ Скорректировать")
    kb.row("❌ Отмена")
    return kb

def keto_level_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔴 Строгое кето")
    kb.row("🟡 Нормальное кето")
    kb.row("🟢 Низкоуглеводная диета")
    kb.row("✏️ Ручной ввод")
    return kb

def settings_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("⚖️ Изменить вес/рост/возраст")
    kb.row("🥗 Изменить режим питания")
    kb.row("🎯 Изменить цели вручную")
    kb.row("🔄 Пересчитать автоматически")
    kb.row("🗑 Сбросить день")
    kb.row("◀️ Главное меню")
    return kb

def alcohol_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🍷 Сухое вино (150мл)")
    kb.row("🍷 Полусухое вино (150мл)")
    kb.row("🍺 Пиво светлое (330мл)")
    kb.row("🍺 Пиво тёмное (330мл)")
    kb.row("🥃 Виски/Водка/Коньяк (50мл)")
    kb.row("🍹 Коктейль (200мл)")
    kb.row("🍾 Шампанское (150мл)")
    kb.row("🍻 Несколько пив (700мл)")
    kb.row("✏️ Ввести вручную")
    kb.row("◀️ Главное меню")
    return kb

def portions_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("1 порция", "2 порции", "3 порции")
    kb.row("◀️ Главное меню")
    return kb

def choice_kb(n):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(*[str(i) for i in range(1, n + 1)])
    kb.row("🔍 Искать снова", "◀️ Главное меню")
    return kb

# ============================================================
# FOOD DATABASE
# ============================================================

FOOD_DB = {
    "🥑 Авокадо 200г":  {"name": "Авокадо (200г)",           "fat": 21, "protein": 2,  "carbs": 2, "cal": 200},
    "🥩 Стейк 200г":    {"name": "Стейк говяжий (200г)",      "fat": 18, "protein": 30, "carbs": 0, "cal": 280},
    "🥚 Яйца 2шт":      {"name": "Яйца (2 шт)",               "fat": 10, "protein": 12, "carbs": 1, "cal": 140},
    "🐟 Лосось 150г":   {"name": "Лосось (150г)",              "fat": 14, "protein": 28, "carbs": 0, "cal": 240},
    "🥗 Салат+масло":   {"name": "Салат + оливк. масло",       "fat": 14, "protein": 2,  "carbs": 3, "cal": 145},
    "🧀 Сыр 50г":       {"name": "Сыр твёрдый (50г)",          "fat": 14, "protein": 12, "carbs": 0, "cal": 180},
    "🥜 Миндаль 30г":   {"name": "Миндаль (30г)",              "fat": 15, "protein": 6,  "carbs": 3, "cal": 170},
    "🫐 Черника 80г":   {"name": "Черника (80г)",               "fat": 0,  "protein": 1,  "carbs": 9, "cal": 45},
    "🍳 Бекон 3шт":     {"name": "Бекон (3 полоски)",           "fat": 12, "protein": 9,  "carbs": 0, "cal": 140},
}

ALCOHOL_DB = {
    "🍷 Сухое вино (150мл)":         {"name": "Сухое вино",        "ml": 150, "carbs": 4},
    "🍷 Полусухое вино (150мл)":      {"name": "Полусухое вино",    "ml": 150, "carbs": 8},
    "🍺 Пиво светлое (330мл)":        {"name": "Пиво светлое",      "ml": 330, "carbs": 13},
    "🍺 Пиво тёмное (330мл)":         {"name": "Пиво тёмное",       "ml": 330, "carbs": 18},
    "🥃 Виски/Водка/Коньяк (50мл)":   {"name": "Крепкий алкоголь",  "ml": 50,  "carbs": 0},
    "🍹 Коктейль (200мл)":            {"name": "Коктейль",          "ml": 200, "carbs": 25},
    "🍾 Шампанское (150мл)":          {"name": "Шампанское",        "ml": 150, "carbs": 6},
    "🍻 Несколько пив (700мл)":       {"name": "Несколько пив",     "ml": 700, "carbs": 28},
}

# ============================================================
# API FUNCTIONS
# ============================================================

def analyze_photo(image_bytes):
    try:
        headers = {"Authorization": f"Bearer {LOGMEAL_TOKEN}"}
        files = {"image": ("food.jpg", image_bytes, "image/jpeg")}
        r1 = requests.post(
            "https://api.logmeal.com/v2/image/segmentation/complete",
            headers=headers, files=files, timeout=30)
        print(f"LogMeal step1: {r1.status_code} {r1.text[:200]}")
        if r1.status_code != 200:
            return None
        data1 = r1.json()
        image_id = data1.get("imageId")
        dish_names = []
        for seg in data1.get("segmentation_results", []):
            for rec in seg.get("recognition_results", []):
                name = rec.get("name", "")
                if name:
                    dish_names.append(name)
        if not image_id:
            return None
        r2 = requests.post(
            "https://api.logmeal.com/v2/nutrition/recipe/nutritionalInfo",
            headers=headers, json={"imageId": image_id}, timeout=15)
        print(f"LogMeal step2: {r2.status_code} {r2.text[:200]}")
        nutrients = {}
        if r2.status_code == 200:
            nutrients = r2.json().get("nutritional_info", {})
        return {
            "dishes": dish_names if dish_names else ["Блюдо"],
            "calories": round(float(nutrients.get("calories", 0) or 0)),
            "fat":      round(float(nutrients.get("totalFat", 0) or 0), 1),
            "protein":  round(float(nutrients.get("proteins", 0) or 0), 1),
            "carbs":    round(float(nutrients.get("totalCarbs", 0) or 0), 1),
        }
    except Exception as e:
        print(f"LogMeal error: {e}")
        return None

def search_food(query):
    try:
        headers = {"User-Agent": "KetOSBot/1.0"}
        params = {
            "search_terms": query, "search_simple": 1,
            "action": "process", "json": 1, "page_size": 20,
            "fields": "product_name,nutriments,brands",
        }
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl",
                         params=params, headers=headers, timeout=15)
        results = []
        for p in r.json().get("products", []):
            name = p.get("product_name", "").strip()
            if not name or len(name) < 2:
                continue
            n = p.get("nutriments", {})
            fat     = round(float(n.get("fat_100g") or 0), 1)
            protein = round(float(n.get("proteins_100g") or 0), 1)
            carbs   = round(float(n.get("carbohydrates_100g") or 0), 1)
            cal     = round(float(n.get("energy-kcal_100g") or 0))
            if fat == 0 and protein == 0 and carbs == 0:
                continue
            brand = p.get("brands", "").strip()
            display = name + (f" — {brand}" if brand and brand.lower() not in name.lower() else "")
            results.append({"name": display[:50], "fat": fat, "protein": protein, "carbs": carbs, "cal": cal})
            if len(results) >= 5:
                break
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

# ============================================================
# TEXT BUILDERS
# ============================================================

def recovery_text(total_carbs):
    hours = max(4, int(total_carbs / 15))
    return (
        f"🔄 *План возврата в кетоз*\nПосле {total_carbs}г углеводов\n\n"
        f"⏱ *0–2 часа:* Вода, соль, электролиты\n"
        f"⏱ *2–3 часа:* 1 ст.л. MCT масла\n"
        f"⏱ *3–5 часов:* Голодай + лёгкая прогулка\n"
        f"⏱ *~{hours} часов:* Жирное мясо + овощи\n\n"
        f"✅ *Через {hours}–{hours+2} часов снова в кетозе!*\n"
        f"💡 Измерь кетоны через {hours} часов 🧪"
    )

def alcohol_recovery_text(name, ml, carbs):
    std_doses = ml / 50
    detox_hours = round(std_doses * 1.5)
    if carbs < 10:
        keto_hours = detox_hours + 8
        severity = "🟡 Умеренное влияние"
        tip = "Сухое вино и чистый алкоголь — меньший удар по кетозу."
    elif carbs < 30:
        keto_hours = detox_hours + 16
        severity = "🟠 Значительное влияние"
        tip = "Пиво и сладкие коктейли сильно выбивают из кетоза."
    else:
        keto_hours = detox_hours + 24
        severity = "🔴 Сильное влияние"
        tip = "Сладкие напитки и ликёры — самый долгий выход из кетоза."
    return (
        f"🍷 *План возврата в кетоз после алкоголя*\n\n"
        f"🥃 {name} — {ml}мл | ~{carbs}г углеводов\n"
        f"{severity}\n\n"
        f"⏱ *Алкоголь выведется:* ~{detox_hours} часов\n"
        f"✅ *Кетоз восстановится:* ~{keto_hours} часов\n\n"
        f"📋 *Твой план:*\n\n"
        f"🚰 *Сейчас:*\n"
        f"• Пей воду — 2-3 литра\n"
        f"• Электролиты: соль, магний, калий\n"
        f"• Никаких углеводов!\n\n"
        f"🌅 *Утром:*\n"
        f"• Вода + кофе без сахара\n"
        f"• 1 ст.л. MCT масла\n"
        f"• Пропусти завтрак если можешь\n\n"
        f"🥩 *Первый приём пищи:*\n"
        f"• Яйца + бекон + авокадо\n"
        f"• Жирное мясо или рыба\n"
        f"• Ноль углеводов!\n\n"
        f"🏃 *30 мин прогулка или кардио* — сожжёт глюкозу быстрее\n\n"
        f"❌ *Избегай:* соки, хлеб, крахмал, повторный алкоголь\n\n"
        f"💡 {tip}\n\n"
        f"🧪 Измерь кетоны через {keto_hours} часов!"
    )

def profile_done_text(u, macros):
    return (
        f"✅ *Профиль готов!*\n\n"
        f"👤 {u['name']} | ⚖️ {u['weight']}кг | 📏 {u['height']}см | 🎂 {int(u['age'])}лет\n"
        f"🏃 {u.get('sport_type','—')} | 🎯 {u.get('goal','—')}\n"
        f"🥗 Режим: {u.get('keto_level','—')}\n\n"
        f"📊 *Цели на день:*\n"
        f"🔥 Калории: *{u['cal_target']} ккал*\n"
        f"🟠 Жиры: *{u['fat_target']}г*\n"
        f"🔵 Белки: *{u['protein_target']}г*\n"
        f"🟡 Углеводы: *{u['carbs_target']}г*\n\n"
        f"_TDEE: {macros.get('tdee', u['cal_target'])} ккал_\n\nПоехали! 🚀"
    )

# ============================================================
# PHOTO HANDLER
# ============================================================

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    bot.send_message(msg.chat.id,
        "📸 *Фото получено!*\n🤖 Анализирую блюдо... ⏳",
        parse_mode="Markdown")
    file_info = bot.get_file(msg.photo[-1].file_id)
    image_bytes = requests.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}").content
    result = analyze_photo(image_bytes)
    if not result or result["calories"] == 0:
        bot.send_message(msg.chat.id,
            "❌ Не удалось распознать блюдо.\n\n"
            "Попробуй:\n• Сфотографировать ближе\n"
            "• Улучшить освещение\n• Или введи вручную 👇",
            reply_markup=food_kb())
        set_state(uid, "food")
        return
    u["pending_food"] = result
    set_state(uid, "confirm_photo")
    dishes_text = ", ".join(result["dishes"][:3])
    warn = "⚠️ Много углеводов!" if result["carbs"] > 10 else "✅ Кето-дружественно"
    bot.send_message(msg.chat.id,
        f"🤖 *Результат анализа:*\n\n"
        f"🍽 *Блюдо:* {dishes_text}\n\n"
        f"🔥 Калории: *{result['calories']} ккал*\n"
        f"🟠 Жиры: *{result['fat']}г*\n"
        f"🔵 Белки: *{result['protein']}г*\n"
        f"🟡 Углеводы: *{result['carbs']}г*\n\n"
        f"{warn}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=confirm_photo_kb())

# ============================================================
# MAIN HANDLER
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    set_state(uid, "ask_name")
    bot.send_message(msg.chat.id,
        "🔥 *Добро пожаловать в KetOS!*\n\n"
        "Кето-диета для спортсменов 💪\n\n"
        "Давай настроим твой профиль.\nКак тебя зовут?",
        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    text = msg.text
    state = get_state(uid)

    # --- глобальный сброс ---
    if text in ["🔄 Перезапуск", "◀️ Главное меню"]:
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "✅ Главное меню:", reply_markup=main_kb())
        return

    # ========================
    # ОНБОРДИНГ
    # ========================
    if state == "ask_name":
        u["name"] = text
        set_state(uid, "ask_weight")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("50", "55", "60", "65")
        kb.row("70", "75", "80", "85")
        kb.row("90", "95", "100", "110")
        bot.send_message(msg.chat.id,
            f"Привет, *{text}*! 💪\n\nВведи свой вес в кг:",
            parse_mode="Markdown", reply_markup=kb)
        return

    if state == "ask_weight":
        try:
            u["weight"] = float(text.replace("кг", "").strip())
            set_state(uid, "ask_height")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("155", "160", "165", "170")
            kb.row("175", "180", "185", "190")
            bot.send_message(msg.chat.id, "Твой рост в см:", reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, "Введи число, например: *65*", parse_mode="Markdown")
        return

    if state == "ask_height":
        try:
            u["height"] = float(text.replace("см", "").strip())
            set_state(uid, "ask_age")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("20", "25", "30", "35")
            kb.row("40", "45", "50", "55")
            bot.send_message(msg.chat.id, "Твой возраст:", reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, "Введи число, например: *170*", parse_mode="Markdown")
        return

    if state == "ask_age":
        try:
            u["age"] = float(text.replace("лет", "").strip())
            set_state(uid, "ask_activity")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🛋 Минимум (сидячий)")
            kb.row("🚶 Лёгкая (1-3 раза/нед)")
            kb.row("🏃 Умеренная (3-5 раз/нед)")
            kb.row("💪 Высокая (6-7 раз/нед)")
            kb.row("🏆 Очень высокая (проф. спорт)")
            bot.send_message(msg.chat.id, "Уровень физической активности:", reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, "Введи число, например: *30*", parse_mode="Markdown")
        return

    if state == "ask_activity":
        coef_map = {
            "🛋 Минимум (сидячий)": 1.2,
            "🚶 Лёгкая (1-3 раза/нед)": 1.375,
            "🏃 Умеренная (3-5 раз/нед)": 1.55,
            "💪 Высокая (6-7 раз/нед)": 1.725,
            "🏆 Очень высокая (проф. спорт)": 1.9,
        }
        u["activity"] = text
        u["activity_coef"] = coef_map.get(text, 1.55)
        set_state(uid, "ask_sport")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🏃 Бег/Трейл", "🚴 Велоспорт")
        kb.row("🏊 Плавание", "🏋️ Силовые")
        kb.row("⛷️ Лыжи/Триатлон", "🚶 Другое")
        bot.send_message(msg.chat.id, "Основной вид спорта:", reply_markup=kb)
        return

    if state == "ask_sport":
        u["sport_type"] = text
        set_state(uid, "ask_goal")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🔥 Похудение", "💪 Набор мышц")
        kb.row("⚡ Производительность", "🎯 Поддержание")
        bot.send_message(msg.chat.id, "Главная цель:", reply_markup=kb)
        return

    if state == "ask_goal":
        u["goal"] = text
        macros = calc_macros(u)
        u["cal_target"] = macros["calories"]
        set_state(uid, "ask_keto_level")
        bot.send_message(msg.chat.id,
            f"Рассчитанные калории: *{macros['calories']} ккал/день*\n\n"
            f"Выбери режим питания:\n\n"
            f"🔴 *Строгое кето* — до 20г углеводов\n"
            f"   Жиры 75% · Белки 20% · Углеводы 5%\n\n"
            f"🟡 *Нормальное кето* — до 30г углеводов\n"
            f"   Жиры 70% · Белки 25% · Углеводы 5%\n\n"
            f"🟢 *Низкоуглеводная* — до 80г углеводов\n"
            f"   Жиры 50% · Белки 30% · Углеводы 20%\n\n"
            f"✏️ *Ручной ввод* — задашь сам",
            parse_mode="Markdown", reply_markup=keto_level_kb())
        return

    if state == "ask_keto_level":
        if text == "✏️ Ручной ввод":
            set_state(uid, "manual_targets_onboard")
            macros = calc_macros(u)
            bot.send_message(msg.chat.id,
                f"Расчётные калории: *{macros['calories']} ккал*\n\n"
                f"Введи свои цели через запятую:\n"
                f"*калории, жиры, белки, углеводы*\n\n"
                f"Пример: `1800, 140, 110, 20`",
                parse_mode="Markdown")
            return
        if text in ["🔴 Строгое кето", "🟡 Нормальное кето", "🟢 Низкоуглеводная диета"]:
            apply_keto_level(u, text)
            macros = calc_macros(u)
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                profile_done_text(u, macros),
                parse_mode="Markdown", reply_markup=main_kb())
        return

    if state == "manual_targets_onboard":
        try:
            parts = text.split(",")
            u["cal_target"]     = int(parts[0].strip())
            u["fat_target"]     = int(parts[1].strip())
            u["protein_target"] = int(parts[2].strip())
            u["carbs_target"]   = int(parts[3].strip())
            u["keto_level"] = "✏️ Ручной ввод"
            set_state(uid, "menu")
            macros = {"tdee": u["cal_target"]}
            bot.send_message(msg.chat.id,
                profile_done_text(u, macros),
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Пример: `1800, 140, 110, 20`", parse_mode="Markdown")
        return

    # ========================
    # СТАТУС
    # ========================
    if text == "📊 Мой статус":
        k = u["ketones"]
        if k == 0:    ks = "❓ Не измерено"
        elif k < 0.5: ks = "❌ Не в кетозе"
        elif k < 1.5: ks = "🟡 Лёгкий кетоз"
        elif k < 3.0: ks = "✅ Оптимальный кетоз!"
        else:         ks = "🔥 Глубокий кетоз"
        bot.send_message(msg.chat.id,
            f"📊 *Статус на сегодня*\n\n"
            f"🧪 {ks} ({k} ммоль/л)\n\n"
            f"🔥 Калории:  {bar(u['calories'],u['cal_target'])} {u['calories']}/{u['cal_target']} ккал\n"
            f"🟠 Жиры:     {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}г\n"
            f"🔵 Белки:    {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}г\n"
            f"🟡 Углеводы: {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ========================
    # ДНЕВНИК
    # ========================
    if text == "📋 Дневник питания":
        meals = u["meals"]
        if meals:
            meals_text = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(meals))
        else:
            meals_text = "  Пока ничего не добавлено"
        bot.send_message(msg.chat.id,
            f"📋 *Дневник питания*\n\n{meals_text}\n\n"
            f"🔥 {u['calories']} ккал | 🟠 {u['fat']}г | 🔵 {u['protein']}г | 🟡 {u['carbs']}г",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ========================
    # ФОТО
    # ========================
    if text == "📸 КБЖУ по фото":
        set_state(uid, "waiting_photo")
        bot.send_message(msg.chat.id,
            "📸 *Отправь фото своего блюда!*\n\n"
            "AI определит блюдо и посчитает КБЖУ.\nПросто прикрепи фото 👇",
            parse_mode="Markdown")
        return

    # ========================
    # ВВОД ЕДЫ ВРУЧНУЮ
    # ========================
    if text == "✏️ Ввести еду вручную":
        set_state(uid, "manual_food")
        bot.send_message(msg.chat.id,
            "✏️ *Ввод еды вручную*\n\n"
            "Напиши название и цифры через пробел:\n"
            "*название жиры белки углеводы*\n\n"
            "Можно добавить граммы:\n"
            "*название количество_г жиры белки углеводы*\n\n"
            "Примеры:\n"
            "`творог 5 18 3`\n"
            "`курица 200г 2 30 0`\n"
            "`кофе с молоком 150мл 1 1 3`\n"
            "`Греческий салат 300г 12 8 5`\n\n"
            "Запятые не нужны, пиши как удобно 👌",
            parse_mode="Markdown")
        return

    if state == "manual_food":
        try:
            import re
            # Убираем лишние пробелы, приводим к нижнему регистру не нужно — берём как есть
            parts = text.strip().split()

            # Ищем числа (могут быть с г/мл/kcal)
            numbers = []
            name_parts = []
            amount_str = ""

            for part in parts:
                # Убираем единицы и проверяем число
                clean = re.sub(r'[гГмлМкКcалCкк]+$', '', part)
                if clean.replace('.', '').isdigit():
                    # Проверяем — это количество (г/мл) или макрос?
                    if (part.endswith('г') or part.endswith('Г') or
                            part.endswith('мл') or part.endswith('МЛ') or
                            part.endswith('мЛ') or part.lower().endswith('мл')):
                        amount_str = part  # запоминаем количество
                    else:
                        numbers.append(int(float(clean)))
                else:
                    name_parts.append(part)

            if len(numbers) < 3:
                raise ValueError("Мало цифр")

            name    = " ".join(name_parts) if name_parts else "Блюдо"
            name    = name.strip()
            # Первая буква заглавная автоматически
            name    = name[0].upper() + name[1:] if name else "Блюдо"

            fat     = numbers[0]
            protein = numbers[1]
            carbs   = numbers[2]
            cal     = fat * 9 + protein * 4 + carbs * 4

            amount_label = f" {amount_str}" if amount_str else ""

            u["fat"]      += fat
            u["protein"]  += protein
            u["carbs"]    += carbs
            u["calories"] += cal
            u["meals"].append(
                f"{name}{amount_label} (Ж{fat} Б{protein} У{carbs} | {cal}ккал)")

            carbs_left = u["carbs_target"] - u["carbs"]
            warn = "\n⚠️ Лимит углеводов близко!" if carbs_left < 5 else ""
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}{amount_label}* добавлено!\n"
                f"🟠 Жиры: +{fat}г | 🔵 Белки: +{protein}г | "
                f"🟡 Углеводы: +{carbs}г | 🔥 +{cal} ккал{warn}\n\n"
                f"Осталось углеводов: *{max(carbs_left, 0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Не понял формат.\n\n"
                "Напиши название и три числа через пробел:\n"
                "`творог 5 18 3`\n"
                "`курица 200г 2 30 0`\n"
                "`кофе с молоком 150мл 1 1 3`",
                parse_mode="Markdown")
        return

    # ========================
    # ПОИСК ПРОДУКТА
    # ========================
    if text in ["🔍 Поиск продукта", "🔍 Искать снова"]:
        set_state(uid, "search_food")
        bot.send_message(msg.chat.id,
            "🔍 Напиши название продукта:\n\n"
            "🇷🇺 `творог`, `курица`, `гречка`\n"
            "🇬🇧 `salmon`, `chicken`, `avocado`",
            parse_mode="Markdown")
        return

    if state == "search_food":
        bot.send_message(msg.chat.id, f"🔍 Ищу *{text}*...", parse_mode="Markdown")
        results = search_food(text)
        translations = {
            "колбаса": "sausage", "творог": "cottage cheese",
            "гречка": "buckwheat", "курица": "chicken",
            "говядина": "beef", "свинина": "pork",
            "рыба": "fish", "картошка": "potato",
            "рис": "rice", "овсянка": "oatmeal",
        }
        if not results:
            eng = translations.get(text.lower())
            if eng:
                results = search_food(eng)
        if not results:
            bot.send_message(msg.chat.id,
                "❌ Не найдено. Попробуй по-английски или введи вручную.",
                reply_markup=food_kb())
            set_state(uid, "food")
            return
        u["search_results"] = results
        resp = f"✅ *Найдено {len(results)} продуктов* (на 100г):\n\n"
        for i, p in enumerate(results, 1):
            warn = "⚠️" if p["carbs"] > 10 else "✅"
            resp += (f"*{i}.* {p['name']}\n"
                     f"   🟠{p['fat']}г 🔵{p['protein']}г {warn}{p['carbs']}г 🔥{p['cal']}ккал\n\n")
        resp += "Напиши номер чтобы добавить:"
        set_state(uid, "choose_food")
        bot.send_message(msg.chat.id, resp, parse_mode="Markdown",
                         reply_markup=choice_kb(len(results)))
        return

    if state == "choose_food":
        if text.isdigit():
            idx = int(text) - 1
            results = u.get("search_results", [])
            if 0 <= idx < len(results):
                u["pending_search_food"] = results[idx]
                set_state(uid, "ask_food_grams")
                food = results[idx]
                bot.send_message(msg.chat.id,
                    f"✅ *{food['name'][:40]}*\n\n"
                    f"На 100г: 🟠{food['fat']}г 🔵{food['protein']}г 🟡{food['carbs']}г 🔥{food['cal']}ккал\n\n"
                    f"Сколько грамм съел?\n\n"
                    f"Напиши число, например: `150`",
                    parse_mode="Markdown")
        return

    if state == "ask_food_grams":
        try:
            grams = float(text.replace("г","").replace("гр","").strip())
            food = u.get("pending_search_food", {})
            ratio = grams / 100
            fat     = round(food["fat"]     * ratio, 1)
            protein = round(food["protein"] * ratio, 1)
            carbs   = round(food["carbs"]   * ratio, 1)
            cal     = round(food["cal"]     * ratio)
            u["fat"]      += fat
            u["protein"]  += protein
            u["carbs"]    += carbs
            u["calories"] += cal
            u["meals"].append(f"{food['name'][:25]} ({int(grams)}г | {cal}ккал)")
            carbs_left = u["carbs_target"] - u["carbs"]
            warn = "\n⚠️ Лимит углеводов близко!" if carbs_left < 5 else ""
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{food['name'][:40]}* — {int(grams)}г добавлено!\n\n"
                f"🟠 Жиры: +{fat}г\n"
                f"🔵 Белки: +{protein}г\n"
                f"🟡 Углеводы: +{carbs}г\n"
                f"🔥 Калории: +{cal} ккал{warn}\n\n"
                f"Осталось углеводов: *{max(round(u['carbs_target'] - u['carbs']), 0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Введи количество грамм числом, например: `150`",
                parse_mode="Markdown")
        return

    # ========================
    # БЫСТРЫЕ ПРОДУКТЫ
    # ========================
    if text in FOOD_DB:
        food = FOOD_DB[text]
        u["fat"] += food["fat"]; u["protein"] += food["protein"]
        u["carbs"] += food["carbs"]; u["calories"] += food["cal"]
        u["meals"].append(f"{food['name']} (Ж{food['fat']} Б{food['protein']} У{food['carbs']} | {food['cal']}ккал)")
        carbs_left = u["carbs_target"] - u["carbs"]
        bot.send_message(msg.chat.id,
            f"✅ *{food['name']}* добавлено!\n"
            f"🟠+{food['fat']}г 🔵+{food['protein']}г 🟡+{food['carbs']}г 🔥+{food['cal']}ккал\n"
            f"Осталось углеводов: *{max(carbs_left, 0)}г*",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ========================
    # ПОДТВЕРЖДЕНИЕ ФОТО
    # ========================
    if state == "confirm_photo":
        if text == "✅ Добавить в дневник":
            food = u.get("pending_food")
            if food:
                u["fat"] += food["fat"]; u["protein"] += food["protein"]
                u["carbs"] += food["carbs"]; u["calories"] += food["calories"]
                dishes = ", ".join(food["dishes"][:2])
                u["meals"].append(f"{dishes[:25]} (фото | {food['calories']}ккал)")
                carbs_left = u["carbs_target"] - u["carbs"]
                u["pending_food"] = None
                set_state(uid, "menu")
                bot.send_message(msg.chat.id,
                    f"✅ *Добавлено в дневник!*\n🔥 +{food['calories']} ккал\n"
                    f"Осталось углеводов: *{max(carbs_left, 0)}г*",
                    parse_mode="Markdown", reply_markup=main_kb())
            return
        if text == "✏️ Скорректировать":
            food = u.get("pending_food")
            set_state(uid, "correct_photo")
            bot.send_message(msg.chat.id,
                f"Текущие значения:\n"
                f"🟠 Жиры: {food['fat']}г | 🔵 Белки: {food['protein']}г\n"
                f"🟡 Углеводы: {food['carbs']}г | 🔥 {food['calories']} ккал\n\n"
                f"Введи исправленные:\n*Название, жиры, белки, углеводы*\n\n"
                f"Пример: `Рыба с овощами, 12, 25, 8`",
                parse_mode="Markdown")
            return
        if text == "❌ Отмена":
            u["pending_food"] = None
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, "Отменено.", reply_markup=main_kb())
            return

    if state == "correct_photo":
        try:
            parts = text.split(",")
            name    = parts[0].strip()
            fat     = int(parts[1].strip())
            protein = int(parts[2].strip())
            carbs   = int(parts[3].strip())
            cal = fat * 9 + protein * 4 + carbs * 4
            u["fat"] += fat; u["protein"] += protein
            u["carbs"] += carbs; u["calories"] += cal
            u["meals"].append(f"{name} (Ж{fat} Б{protein} У{carbs} | {cal}ккал)")
            u["pending_food"] = None
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}* добавлено!\n"
                f"🟠 {fat}г | 🔵 {protein}г | 🟡 {carbs}г | 🔥 {cal}ккал",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Пример: `Рыба с овощами, 12, 25, 8`",
                parse_mode="Markdown")
        return

    # ========================
    # КЕТОНЫ
    # ========================
    if text == "🧪 Ввести кетоны":
        set_state(uid, "ketones")
        bot.send_message(msg.chat.id,
            "Введи уровень кетонов (ммоль/л)\nНапример: *1.8*",
            parse_mode="Markdown")
        return

    if state == "ketones":
        try:
            val = float(text.replace(",", "."))
            u["ketones"] = val
            if val < 0.5:   s = "❌ Не в кетозе\n💡 Сократи углеводы до 20г/день"
            elif val < 1.5: s = "🟡 Лёгкий кетоз\n💡 Уменьши углеводы ещё на 5г"
            elif val < 3.0: s = "✅ Оптимальный кетоз!\n💡 Продолжай в том же духе"
            else:           s = "🔥 Глубокий кетоз\n💡 Пей воду + электролиты"
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"🧪 *{val} ммоль/л*\n\n{s}",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Введи число: *1.8*", parse_mode="Markdown")
        return

    # ========================
    # АЛКОГОЛЬ
    # ========================
    if text == "🍷 Выпил алкоголь":
        set_state(uid, "choose_alcohol")
        bot.send_message(msg.chat.id,
            "🍷 *Что пил?*\nВыбери из списка или введи вручную:",
            parse_mode="Markdown", reply_markup=alcohol_kb())
        return

    if state == "choose_alcohol":
        if text == "✏️ Ввести вручную":
            set_state(uid, "manual_alcohol")
            bot.send_message(msg.chat.id,
                "Введи через запятую:\n*название, количество мл, углеводы г*\n\n"
                "Пример: `Пиво крафтовое, 500, 20`",
                parse_mode="Markdown")
            return
        drink = ALCOHOL_DB.get(text)
        if drink:
            u["pending_alcohol"] = drink
            set_state(uid, "ask_alcohol_amount")
            bot.send_message(msg.chat.id,
                f"Выбрано: *{drink['name']}*\nСколько порций?",
                parse_mode="Markdown", reply_markup=portions_kb())
        return

    if state == "ask_alcohol_amount":
        drink = u.get("pending_alcohol", {})
        try:
            if "1" in text:   qty = 1
            elif "2" in text: qty = 2
            elif "3" in text: qty = 3
            else:             qty = 1
            total_ml    = drink["ml"] * qty
            total_carbs = drink["carbs"] * qty
            u["carbs"]    += total_carbs
            u["calories"] += total_carbs * 4
            u["meals"].append(f"🍷 {drink['name']} x{qty} ({total_carbs}г углев.)")
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                alcohol_recovery_text(drink["name"], total_ml, total_carbs),
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, "Используй кнопки 👇", reply_markup=main_kb())
        return

    if state == "manual_alcohol":
        try:
            parts = text.split(",")
            name  = parts[0].strip()
            ml    = int(parts[1].strip())
            carbs = int(parts[2].strip())
            u["carbs"]    += carbs
            u["calories"] += carbs * 4
            u["meals"].append(f"🍷 {name} ({ml}мл, {carbs}г углев.)")
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                alcohol_recovery_text(name, ml, carbs),
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Пример: `Пиво крафтовое, 500, 20`",
                parse_mode="Markdown")
        return

    # ========================
    # СПОРТ
    # ========================
    if text == "⚡ Спортивный режим":
        set_state(uid, "sport")
        bot.send_message(msg.chat.id, "⚡ Выбери активность:", reply_markup=sport_kb())
        return

    if text in ["🔄 План возврата в кетоз", "🔄 Возврат в кетоз"]:
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            recovery_text(u.get("last_gel_carbs", 60)),
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "🏋️ Силовая":
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            "🏋️ *Силовая на кето*\n\n"
            "До: MCT масло + кофе\n"
            "Во время: вода + соль\n"
            "После: 30-40г белка за 30 мин",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text in ["🏃 Трейл/Бег", "🚴 Велогонка", "🏊 Триатлон", "⛷️ Лыжи"]:
        u["sport_type_race"] = text
        set_state(uid, "ask_distance")
        bot.send_message(msg.chat.id,
            "Дистанция или время?\nПример: *42 км* или *3 часа*",
            parse_mode="Markdown")
        return

    if state == "ask_distance":
        try:
            t = text.lower()
            if "час" in t:
                hours = float(''.join(c for c in t if c.isdigit() or c == '.'))
            elif "км" in t:
                hours = float(''.join(c for c in t if c.isdigit() or c == '.')) / 10
            else:
                hours = 2
            gels  = max(1, int(hours / 1.5))
            total = gels * 20
            u["last_gel_carbs"] = total
            resp = f"⚡ *Протокол гелей*\n📍 {text} (~{int(hours)}ч)\n💊 Гелей: {gels} шт\n\n"
            times = [0, 0.4, 0.7, 0.9]
            for i in range(gels):
                t_min = int(hours * times[min(i, 3)] * 60)
                label = "За 30 мин до старта" if i == 0 else f"Через {t_min} мин"
                resp += f"🟡 *{label}:* Гель #{i+1} — 20г\n"
            resp += (
                f"\n📊 Итого: *{total}г углеводов*\n"
                f"⏱ Возврат в кетоз: *~{max(4, int(total/15))} часов*\n\n"
                f"🏁 После финиша нажми:\n👉 *🔄 План возврата в кетоз*"
            )
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, resp, parse_mode="Markdown",
                             reply_markup=after_gel_kb())
        except:
            bot.send_message(msg.chat.id,
                "Напиши: *42 км* или *3 часа*", parse_mode="Markdown")
        return

    # ========================
    # СЕМЬЯ
    # ========================
    if text == "👨‍👩‍👧 Семья":
        meals = u["meals"]
        meals_text = "\n".join(f"  • {m}" for m in meals) if meals else "  Пока нет блюд"
        bot.send_message(msg.chat.id,
            f"👨‍👩‍👧 *Семейный режим*\n\n"
            f"Пригласи партнёра:\n`https://t.me/ketOSzoneBot?start=family_{uid}`\n\n"
            f"📋 *Твой рацион сегодня:*\n{meals_text}",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ========================
    # НАСТРОЙКИ
    # ========================
    if text == "⚙️ Настройки":
        keto_level = u.get("keto_level") or "🟡 Нормальное кето"
        bot.send_message(msg.chat.id,
            f"⚙️ *Настройки*\n\n"
            f"👤 {u.get('name','—')}\n"
            f"⚖️ {u.get('weight','—')}кг | 📏 {u.get('height','—')}см | 🎂 {int(u.get('age', 0))}лет\n"
            f"🏃 {u.get('sport_type','—')} | 🎯 {u.get('goal','—')}\n"
            f"🥗 Режим: {keto_level}\n\n"
            f"📊 *Текущие цели:*\n"
            f"🔥 {u['cal_target']} ккал | 🟠 {u['fat_target']}г | "
            f"🔵 {u['protein_target']}г | 🟡 {u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=settings_kb())
        return

    if text == "🥗 Изменить режим питания":
        set_state(uid, "change_keto_level")
        bot.send_message(msg.chat.id,
            "Выбери новый режим питания:\n\n"
            "🔴 *Строгое кето* — до 20г углеводов\n"
            "🟡 *Нормальное кето* — до 30г углеводов\n"
            "🟢 *Низкоуглеводная* — до 80г углеводов\n"
            "✏️ *Ручной ввод*",
            parse_mode="Markdown", reply_markup=keto_level_kb())
        return

    if state == "change_keto_level":
        if text == "✏️ Ручной ввод":
            set_state(uid, "edit_targets")
            bot.send_message(msg.chat.id,
                f"Введи цели через запятую:\n*калории, жиры, белки, углеводы*\n\nПример: `1800, 140, 110, 20`",
                parse_mode="Markdown")
            return
        if text in ["🔴 Строгое кето", "🟡 Нормальное кето", "🟢 Низкоуглеводная диета"]:
            apply_keto_level(u, text)
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ Режим изменён: {text}\n\n"
                f"🟠 Жиры: *{u['fat_target']}г* | 🔵 Белки: *{u['protein_target']}г* | 🟡 Углеводы: *{u['carbs_target']}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "⚖️ Изменить вес/рост/возраст":
        set_state(uid, "edit_weight")
        bot.send_message(msg.chat.id,
            "Введи через запятую:\n*вес, рост, возраст*\n\nПример: `68, 172, 35`",
            parse_mode="Markdown")
        return

    if state == "edit_weight":
        try:
            parts = text.split(",")
            u["weight"] = float(parts[0].strip())
            u["height"] = float(parts[1].strip())
            u["age"]    = float(parts[2].strip())
            macros = calc_macros(u)
            u["cal_target"] = macros["calories"]
            apply_keto_level(u, u.get("keto_level", "🟡 Нормальное кето"))
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ Данные обновлены и цели пересчитаны!\n\n"
                f"⚖️ {u['weight']}кг | 📏 {u['height']}см | 🎂 {int(u['age'])}лет\n\n"
                f"🔥 {u['cal_target']} ккал | 🟠 {u['fat_target']}г | "
                f"🔵 {u['protein_target']}г | 🟡 {u['carbs_target']}г",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Пример: `68, 172, 35`", parse_mode="Markdown")
        return

    if text == "🎯 Изменить цели вручную":
        set_state(uid, "edit_targets")
        bot.send_message(msg.chat.id,
            f"Текущие цели:\n🔥 {u['cal_target']} | 🟠 {u['fat_target']}г | "
            f"🔵 {u['protein_target']}г | 🟡 {u['carbs_target']}г\n\n"
            f"Введи новые через запятую:\n*калории, жиры, белки, углеводы*\n\nПример: `1800, 140, 110, 20`",
            parse_mode="Markdown")
        return

    if state == "edit_targets":
        try:
            parts = text.split(",")
            u["cal_target"]     = int(parts[0].strip())
            u["fat_target"]     = int(parts[1].strip())
            u["protein_target"] = int(parts[2].strip())
            u["carbs_target"]   = int(parts[3].strip())
            u["keto_level"] = "✏️ Ручной ввод"
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ Цели обновлены!\n"
                f"🔥 {u['cal_target']} ккал | 🟠 {u['fat_target']}г | "
                f"🔵 {u['protein_target']}г | 🟡 {u['carbs_target']}г",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Пример: `1800, 140, 110, 20`", parse_mode="Markdown")
        return

    if text == "🔄 Пересчитать автоматически":
        macros = calc_macros(u)
        u["cal_target"] = macros["calories"]
        apply_keto_level(u, u.get("keto_level", "🟡 Нормальное кето"))
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            f"✅ Цели пересчитаны!\n\n"
            f"🔥 *{u['cal_target']} ккал* | 🟠 *{u['fat_target']}г* | "
            f"🔵 *{u['protein_target']}г* | 🟡 *{u['carbs_target']}г*",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "🗑 Сбросить день":
        u["fat"] = u["protein"] = u["carbs"] = u["calories"] = 0
        u["meals"] = []
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "✅ Данные дня сброшены!", reply_markup=main_kb())
        return

    # ========================
    # FALLBACK
    # ========================
    set_state(uid, "menu")
    bot.send_message(msg.chat.id, "Используй кнопки 👇", reply_markup=main_kb())


print("🔥 KetOS бот запущен!")
bot.polling(none_stop=True, interval=0, timeout=20)
