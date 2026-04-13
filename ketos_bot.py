import telebot
from telebot import types

TOKEN = "8758161336:AAF3cFGkiBWThibk9rfCWdMj8-2RDh4EvB4"
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
            "sport_type": "", "last_gel_carbs": 0
        }
    return users[uid]

def set_state(uid, state):
    states[uid] = state

def get_state(uid):
    return states.get(uid, "menu")

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Мой статус", "🍽 Добавить еду")
    kb.row("⚡ Спортивный режим", "👨‍👩‍👧 Семья")
    kb.row("🧪 Ввести кетоны", "⚙️ Настройки")
    kb.row("🔄 Перезапуск")
    return kb

def food_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🥑 Авокадо", "🥩 Стейк")
    kb.row("🥚 Яйца", "🐟 Лосось")
    kb.row("🥗 Салат+масло", "🧀 Сыр")
    kb.row("🥜 Миндаль", "🫐 Черника")
    kb.row("🍳 Бекон", "✏️ Ввести вручную")
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

FOOD_DB = {
    "🥑 Авокадо": {"name": "Авокадо (1 шт)", "fat": 21, "protein": 2, "carbs": 2, "cal": 200},
    "🥩 Стейк": {"name": "Стейк (200г)", "fat": 18, "protein": 30, "carbs": 0, "cal": 280},
    "🥚 Яйца": {"name": "Яйца (2 шт)", "fat": 10, "protein": 12, "carbs": 1, "cal": 140},
    "🐟 Лосось": {"name": "Лосось (150г)", "fat": 14, "protein": 28, "carbs": 0, "cal": 240},
    "🥗 Салат+масло": {"name": "Салат+масло", "fat": 14, "protein": 2, "carbs": 3, "cal": 145},
    "🧀 Сыр": {"name": "Сыр (50г)", "fat": 14, "protein": 12, "carbs": 0, "cal": 180},
    "🥜 Миндаль": {"name": "Миндаль (30г)", "fat": 15, "protein": 6, "carbs": 3, "cal": 170},
    "🫐 Черника": {"name": "Черника (80г)", "fat": 0, "protein": 1, "carbs": 9, "cal": 45},
    "🍳 Бекон": {"name": "Бекон (3 шт)", "fat": 12, "protein": 9, "carbs": 0, "cal": 140},
}

def bar(done, target):
    pct = min(int(done / max(target, 1) * 10), 10)
    return "▓" * pct + "░" * (10 - pct)

def recovery_text(total_carbs):
    hours = max(4, int(total_carbs / 15))
    return (
        f"🔄 *План возврата в кетоз*\n"
        f"После {total_carbs}г углеводов из гелей\n\n"
        f"⏱ *0–2 часа после финиша:*\n"
        f"• Только вода и соль\n"
        f"• Электролиты (магний, калий)\n"
        f"• Никакой еды!\n\n"
        f"⏱ *2–3 часа:*\n"
        f"• 1 ст.л. MCT масла\n"
        f"• Запустит синтез кетонов в печени\n\n"
        f"⏱ *3–5 часов:*\n"
        f"• Продолжай голодать\n"
        f"• Лёгкая прогулка 20–30 мин ускорит процесс\n\n"
        f"⏱ *~{hours} часов — первый приём пищи:*\n"
        f"• Жирное мясо или рыба\n"
        f"• Некрахмальные овощи (брокколи, шпинат)\n"
        f"• Авокадо + оливковое масло\n"
        f"• Ноль углеводов!\n\n"
        f"✅ *Через {hours}–{hours+2} часов ты снова в кетозе!*\n\n"
        f"💡 Измерь кетоны через {hours} часов и введи результат в боте 🧪"
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

    # ПРОФИЛЬ
    if state == "ask_name":
        u["name"] = text
        set_state(uid, "ask_weight")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("50-60 кг", "60-70 кг")
        kb.row("70-80 кг", "80-90 кг")
        kb.row("90-100 кг", "100+ кг")
        bot.send_message(msg.chat.id, f"Привет, *{text}*! 💪\nКакой у тебя вес?",
            parse_mode="Markdown", reply_markup=kb)
        return

    if state == "ask_weight":
        u["weight"] = text
        set_state(uid, "ask_activity")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🏃 Бег/Трейл", "🚴 Велоспорт")
        kb.row("🏊 Плавание", "🏋️ Силовые")
        kb.row("⛷️ Лыжи/Триатлон", "🚶 Лёгкая активность")
        bot.send_message(msg.chat.id, "Твой вид спорта?", reply_markup=kb)
        return

    if state == "ask_activity":
        u["activity"] = text
        set_state(uid, "ask_goal")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🔥 Похудение", "💪 Набор мышц")
        kb.row("⚡ Производительность", "🎯 Поддержание")
        bot.send_message(msg.chat.id, "Твоя главная цель?", reply_markup=kb)
        return

    if state == "ask_goal":
        u["goal"] = text
        if "Похудение" in text: cal = 1600
        elif "Набор" in text: cal = 2400
        elif "Производительность" in text: cal = 2200
        else: cal = 1900
        u["fat_target"] = round(cal * 0.70 / 9)
        u["protein_target"] = round(cal * 0.25 / 4)
        u["carbs_target"] = round(cal * 0.05 / 4)
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            f"✅ *Профиль готов!*\n\n"
            f"👤 {u['name']} | ⚖️ {u['weight']}\n"
            f"🏃 {u['activity']} | 🎯 {u['goal']}\n\n"
            f"📊 *Макросы на день:*\n"
            f"🟠 Жиры: *{u['fat_target']}г*\n"
            f"🔵 Белки: *{u['protein_target']}г*\n"
            f"🟡 Углеводы: *{u['carbs_target']}г*\n\nПоехали! 🚀",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    # СТАТУС
    if text == "📊 Мой статус":
        k = u["ketones"]
        if k == 0: ks = "❓ Не измерено"
        elif k < 0.5: ks = "❌ Не в кетозе"
        elif k < 1.5: ks = "🟡 Лёгкий кетоз"
        elif k < 3.0: ks = "✅ Оптимальный кетоз!"
        else: ks = "🔥 Глубокий кетоз"
        meals = u["meals"]
        meals_text = "\n".join(f"  • {m}" for m in meals[-5:]) if meals else "  Пока ничего"
        bot.send_message(msg.chat.id,
            f"📊 *Статус на сегодня*\n\n"
            f"🧪 {ks} ({k} ммоль/л)\n\n"
            f"🟠 Жиры:     {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}г\n"
            f"🔵 Белки:    {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}г\n"
            f"🟡 Углеводы: {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}г\n\n"
            f"🍽 *Съедено:*\n{meals_text}",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    # ЕДА
    if text == "🍽 Добавить еду":
        set_state(uid, "food")
        bot.send_message(msg.chat.id, "Что добавляем?", reply_markup=food_kb())
        return

    if text == "✏️ Ввести вручную":
        set_state(uid, "manual_food")
        bot.send_message(msg.chat.id,
            "Напиши: *Название, жиры, белки, углеводы*\n\nПример: `Творог 5%, 5, 18, 3`",
            parse_mode="Markdown"
        )
        return

    if text in FOOD_DB:
        food = FOOD_DB[text]
        u["fat"] += food["fat"]
        u["protein"] += food["protein"]
        u["carbs"] += food["carbs"]
        u["calories"] += food["cal"]
        u["meals"].append(f"{food['name']} ({food['cal']} ккал)")
        carbs_left = u["carbs_target"] - u["carbs"]
        warn = "\n⚠️ Лимит близко!" if carbs_left < 5 else ""
        set_state(uid, "food")
        bot.send_message(msg.chat.id,
            f"✅ *{food['name']}* добавлено!\n"
            f"🟠+{food['fat']}г 🔵+{food['protein']}г 🟡+{food['carbs']}г{warn}\n"
            f"Осталось углеводов: *{max(carbs_left,0)}г*\n\nДобавить ещё?",
            parse_mode="Markdown", reply_markup=food_kb()
        )
        return

    if state == "manual_food":
        try:
            parts = text.split(",")
            name = parts[0].strip()
            fat = int(parts[1].strip())
            protein = int(parts[2].strip())
            carbs = int(parts[3].strip())
            cal = fat*9 + protein*4 + carbs*4
            u["fat"] += fat; u["protein"] += protein
            u["carbs"] += carbs; u["calories"] += cal
            u["meals"].append(f"{name} ({cal}ккал)")
            carbs_left = u["carbs_target"] - u["carbs"]
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}* добавлено!\nЖ:{fat}г Б:{protein}г У:{carbs}г ({cal}ккал)\n"
                f"Осталось углеводов: *{max(carbs_left,0)}г*",
                parse_mode="Markdown", reply_markup=main_kb()
            )
        except:
            bot.send_message(msg.chat.id,
                "❌ Нужны запятые!\nПример: `Творог 5%, 5, 18, 3`",
                parse_mode="Markdown"
            )
        return

    # КЕТОНЫ
    if text == "🧪 Ввести кетоны":
        set_state(uid, "ketones")
        bot.send_message(msg.chat.id,
            "Введи уровень кетонов (ммоль/л)\nНапример: *1.8*",
            parse_mode="Markdown"
        )
        return

    if state == "ketones":
        try:
            val = float(text.replace(",", "."))
            u["ketones"] = val
            if val < 0.5: s = "❌ Не в кетозе\n💡 Сократи углеводы до 20г/день"
            elif val < 1.5: s = "🟡 Лёгкий кетоз\n💡 Уменьши углеводы ещё на 5г"
            elif val < 3.0: s = "✅ Оптимальный кетоз!\n💡 Продолжай в том же духе"
            else: s = "🔥 Глубокий кетоз\n💡 Пей больше воды + электролиты"
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"🧪 *{val} ммоль/л*\n\n{s}",
                parse_mode="Markdown", reply_markup=main_kb()
            )
        except:
            bot.send_message(msg.chat.id, "❌ Введи число: *1.8*", parse_mode="Markdown")
        return

    # СПОРТ
    if text == "⚡ Спортивный режим":
        set_state(uid, "sport")
        bot.send_message(msg.chat.id, "⚡ Выбери активность:", reply_markup=sport_kb())
        return

    # ПЛАН ВОЗВРАТА — кнопка после гелей
    if text == "🔄 План возврата в кетоз":
        total = u.get("last_gel_carbs", 60)
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            recovery_text(total),
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    # ВОЗВРАТ из спорт меню
    if text == "🔄 Возврат в кетоз":
        total = u.get("last_gel_carbs", 60)
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            recovery_text(total),
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    if text == "🏋️ Силовая":
        set_state(uid, "menu")
        bot.send_message(msg.chat.id,
            "🏋️ *Силовая на кето*\n\n"
            "До: MCT масло + кофе\n"
            "Во время: вода + соль\n"
            "После: 30-40г белка за 30 мин",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    if text in ["🏃 Трейл/Бег", "🚴 Велогонка", "🏊 Триатлон", "⛷️ Лыжи"]:
        u["sport_type"] = text
        set_state(uid, "ask_distance")
        bot.send_message(msg.chat.id,
            "Дистанция или время?\nПример: *42 км* или *3 часа*",
            parse_mode="Markdown"
        )
        return

    if state == "ask_distance":
        try:
            t = text.lower()
            if "час" in t:
                hours = float(''.join(c for c in t if c.isdigit() or c == '.'))
            elif "км" in t:
                km = float(''.join(c for c in t if c.isdigit() or c == '.'))
                hours = km / 10
            else:
                hours = 2
            gels = max(1, int(hours / 1.5))
            total = gels * 20
            u["last_gel_carbs"] = total
            resp = f"⚡ *Протокол гелей*\n📍 {text} (~{int(hours)}ч)\n💊 Гелей: {gels} шт\n\n"
            times = [0, 0.4, 0.7, 0.9]
            for i in range(gels):
                t_min = int(hours * times[min(i,3)] * 60)
                label = "За 30 мин до старта" if i==0 else f"Через {t_min} мин"
                resp += f"🟡 *{label}:* Гель #{i+1} — 20г\n"
            resp += (
                f"\n📊 Итого: *{total}г углеводов*\n"
                f"⏱ Возврат в кетоз: *~{max(4,int(total/15))} часов*\n\n"
                f"🏁 После финиша нажми:\n👉 *🔄 План возврата в кетоз*"
            )
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, resp, parse_mode="Markdown", reply_markup=after_gel_kb())
        except:
            bot.send_message(msg.chat.id, "Напиши: *42 км* или *3 часа*", parse_mode="Markdown")
        return

    # СЕМЬЯ
    if text == "👨‍👩‍👧 Семья":
        link = f"https://t.me/ketOSzoneBot?start=family_{uid}"
        meals = u["meals"]
        meals_text = "\n".join(f"  • {m}" for m in meals) if meals else "  Пока нет блюд"
        bot.send_message(msg.chat.id,
            f"👨‍👩‍👧 *Семейный режим*\n\nПригласи партнёра:\n`{link}`\n\n"
            f"📋 *Твой рацион:*\n{meals_text}",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        return

    # НАСТРОЙКИ
    if text == "⚙️ Настройки":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🔄 Сбросить день")
        kb.row("◀️ Главное меню")
        bot.send_message(msg.chat.id,
            f"⚙️ *Настройки*\n\n"
            f"👤 {u.get('name','—')} | ⚖️ {u.get('weight','—')}\n"
            f"🏃 {u.get('activity','—')} | 🎯 {u.get('goal','—')}\n\n"
            f"🟠 Жиры: {u['fat_target']}г\n"
            f"🔵 Белки: {u['protein_target']}г\n"
            f"🟡 Углеводы: {u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=kb
        )
        return

    if text == "🔄 Сбросить день":
        u["fat"] = u["protein"] = u["carbs"] = u["calories"] = 0
        u["meals"] = []
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, "✅ День сброшен!", reply_markup=main_kb())
        return

    set_state(uid, "menu")
    bot.send_message(msg.chat.id, "Используй кнопки 👇", reply_markup=main_kb())

print("🔥 KetOS бот запущен! Открой @ketOSzoneBot и напиши /start")
bot.polling(none_stop=True, interval=0, timeout=20)
