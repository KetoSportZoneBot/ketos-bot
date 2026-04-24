import telebot
from telebot import types
import requests
import os
import re
import threading

TOKEN = os.environ.get("TOKEN", "8758161336:AAF3cFGkiBWThibk9rfCWdMj8-2RDh4EvB4")
LOGMEAL_TOKEN = os.environ.get("LOGMEAL_TOKEN", "a50507ce2019da95e0341da750d887449d40df54")
bot = telebot.TeleBot(TOKEN)

users = {}
states = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "name": "", "weight": 70, "height": 170, "age": 30,
            "gender": "female",
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
            "lang": "ru",
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
    gender = u.get("gender", "female")

    # Mifflin-St Jeor — золотой стандарт
    if gender == "male":
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    # TDEE = BMR × коэффициент активности
    tdee = round(bmr * coef)

    # Калории под цель
    goal = u.get("goal", "")
    if "Похудение" in goal or "Weight loss" in goal:
        cal = tdee - 500   # дефицит 500 ккал = -0.5 кг/нед
    elif "Набор" in goal or "Muscle" in goal:
        cal = tdee + 300   # профицит 300 ккал
    else:
        cal = tdee         # поддержание = TDEE

    cal = max(cal, 1200)   # минимум безопасный порог

    # Кето-макросы под выбранный режим
    level = u.get("keto_level", "🟡 Нормальное кето")
    if "Строгое" in level or "Strict" in level:
        fat     = round(cal * 0.75 / 9)
        protein = round(cal * 0.20 / 4)
        carbs   = round(cal * 0.05 / 4)
    elif "Низко" in level or "Low-carb" in level:
        fat     = round(cal * 0.50 / 9)
        protein = round(cal * 0.30 / 4)
        carbs   = round(cal * 0.20 / 4)
    else:  # Нормальное кето / Standard
        fat     = round(cal * 0.70 / 9)
        protein = round(cal * 0.25 / 4)
        carbs   = round(cal * 0.05 / 4)

    return {
        "calories": cal,
        "fat":      fat,
        "protein":  protein,
        "carbs":    carbs,
        "tdee":     tdee,
        "bmr":      round(bmr),
    }

def apply_keto_level(u, level):
    u["keto_level"] = level
    macros = calc_macros(u)
    u["cal_target"]     = macros["calories"]
    u["fat_target"]     = macros["fat"]
    u["protein_target"] = macros["protein"]
    u["carbs_target"]   = macros["carbs"]

# ============================================================
# LANGUAGE SYSTEM
# ============================================================

def t(u, ru, en):
    """Return text in user's language"""
    return en if u.get("lang") == "en" else ru

def lang_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🇷🇺 Русский", "🇬🇧 English")
    return kb

# ============================================================
# AI ADVISOR
# ============================================================

# Food suggestions database (per 100g)
FOOD_SUGGESTIONS = [
    {"name": {"ru": "Авокадо (200г)",       "en": "Avocado (200g)"},      "fat": 21, "protein": 2,  "carbs": 2,  "cal": 200},
    {"name": {"ru": "Стейк говяжий (150г)", "en": "Beef steak (150g)"},   "fat": 14, "protein": 23, "carbs": 0,  "cal": 210},
    {"name": {"ru": "Лосось (150г)",         "en": "Salmon (150g)"},       "fat": 14, "protein": 28, "carbs": 0,  "cal": 240},
    {"name": {"ru": "Яйца варёные (2шт)",    "en": "Boiled eggs (2pc)"},   "fat": 10, "protein": 12, "carbs": 1,  "cal": 140},
    {"name": {"ru": "Сыр твёрдый (50г)",     "en": "Hard cheese (50g)"},   "fat": 14, "protein": 12, "carbs": 0,  "cal": 180},
    {"name": {"ru": "Миндаль (30г)",          "en": "Almonds (30g)"},       "fat": 15, "protein": 6,  "carbs": 3,  "cal": 170},
    {"name": {"ru": "Бекон (3 полоски)",      "en": "Bacon (3 strips)"},    "fat": 12, "protein": 9,  "carbs": 0,  "cal": 140},
    {"name": {"ru": "Куриная грудка (150г)", "en": "Chicken breast (150g)"},"fat": 4, "protein": 35, "carbs": 0,  "cal": 165},
    {"name": {"ru": "Творог 5% (150г)",      "en": "Cottage cheese (150g)"},"fat": 8, "protein": 18, "carbs": 3,  "cal": 155},
    {"name": {"ru": "Тунец в масле (100г)",  "en": "Tuna in oil (100g)"},  "fat": 10, "protein": 26, "carbs": 0,  "cal": 200},
    {"name": {"ru": "Грецкие орехи (30г)",   "en": "Walnuts (30g)"},       "fat": 20, "protein": 5,  "carbs": 4,  "cal": 196},
    {"name": {"ru": "Брокколи+масло (200г)", "en": "Broccoli+oil (200g)"}, "fat": 10, "protein": 5,  "carbs": 8,  "cal": 148},
    {"name": {"ru": "Сметана 20% (50г)",     "en": "Sour cream 20% (50g)"},"fat": 10, "protein": 2,  "carbs": 2,  "cal": 105},
    {"name": {"ru": "Семечки тыквы (30г)",   "en": "Pumpkin seeds (30g)"}, "fat": 15, "protein": 9,  "carbs": 3,  "cal": 168},
]

def ai_advisor(u):
    lang = u.get("lang", "ru")
    fat_left     = max(0, u["fat_target"]     - u["fat"])
    protein_left = max(0, u["protein_target"] - u["protein"])
    carbs_left   = max(0, u["carbs_target"]   - u["carbs"])
    cal_left     = max(0, u["cal_target"]      - u["calories"])

    if lang == "en":
        if cal_left <= 50:
            return "✅ *Daily goal reached!* Great job today 💪\n\nDrink water and get some rest 🌙"
        header = (
            f"🤖 *AI Adviser — Meal Plan*\n\n"
            f"*Remaining:*\n"
            f"🔥 {cal_left} kcal | 🟠 Fat: {fat_left}g | 🔵 Protein: {protein_left}g | 🟡 Carbs: {carbs_left}g\n\n"
            f"*Suggested meal plan for the rest of the day:*\n"
        )
    else:
        if cal_left <= 50:
            return "✅ *Дневная норма выполнена!* Отличная работа 💪\n\nПей воду и отдыхай 🌙"
        header = (
            f"🤖 *ИИ Советник — Рацион*\n\n"
            f"*Осталось:*\n"
            f"🔥 {cal_left} ккал | 🟠 Жиры: {fat_left}г | 🔵 Белки: {protein_left}г | 🟡 Углеводы: {carbs_left}г\n\n"
            f"*Рекомендуемый рацион на остаток дня:*\n"
        )

    # Build meal plan to fill remaining macros
    remaining_fat = fat_left
    remaining_protein = protein_left
    remaining_carbs = carbs_left
    remaining_cal = cal_left

    meal_plan = []

    # Priority pool sorted by what's most needed
    pool = list(FOOD_SUGGESTIONS)

    # Score and pick foods that fill the gaps without exceeding carbs
    for _ in range(4):  # max 4 items
        if remaining_cal <= 50:
            break
        best_score = -999
        best_food = None
        for food in pool:
            if food in [m[0] for m in meal_plan]:
                continue
            # Skip if adds too many carbs
            if food["carbs"] > remaining_carbs + 3:
                continue
            score = 0
            if remaining_fat > 5:     score += min(food["fat"], remaining_fat) * 2
            if remaining_protein > 5: score += min(food["protein"], remaining_protein) * 3
            if food["cal"] <= remaining_cal: score += 5
            else: score -= 20
            if best_score < score:
                best_score = score
                best_food = food
        if best_food and best_score > 0:
            meal_plan.append((best_food, best_score))
            remaining_fat     -= best_food["fat"]
            remaining_protein -= best_food["protein"]
            remaining_carbs   -= best_food["carbs"]
            remaining_cal     -= best_food["cal"]
            pool.remove(best_food)

    if not meal_plan:
        return header + (
            "No suitable options — you're almost at your goal! 🎯" if lang=="en"
            else "Подходящих вариантов нет — ты почти у цели! 🎯"
        )

    result = header
    total_fat = total_prot = total_carbs = total_cal = 0
    for i, (food, _) in enumerate(meal_plan, 1):
        name = food["name"]["en"] if lang=="en" else food["name"]["ru"]
        kcal = "kcal" if lang=="en" else "ккал"
        result += f"\n*{i}.* {name}\n   🟠{food['fat']}г 🔵{food['protein']}г 🟡{food['carbs']}г 🔥{food['cal']}{kcal}\n"
        total_fat   += food["fat"]
        total_prot  += food["protein"]
        total_carbs += food["carbs"]
        total_cal   += food["cal"]

    if lang == "en":
        result += (
            f"\n📊 *Plan total:*\n"
            f"🔥 {total_cal} kcal | 🟠 {total_fat}g | 🔵 {total_prot}g | 🟡 {total_carbs}g\n\n"
        )
        after_fat  = max(0, fat_left - total_fat)
        after_prot = max(0, protein_left - total_prot)
        after_carbs= max(0, carbs_left - total_carbs)
        after_cal  = max(0, cal_left - total_cal)
        if after_cal <= 100:
            result += "✅ *Goal will be reached!* 🎯"
        else:
            result += f"*Still remaining after plan:*\n🔥{after_cal} kcal | 🟠{after_fat}g | 🔵{after_prot}g | 🟡{after_carbs}g"
    else:
        result += (
            f"\n📊 *Итого по плану:*\n"
            f"🔥 {total_cal} ккал | 🟠 {total_fat}г | 🔵 {total_prot}г | 🟡 {total_carbs}г\n\n"
        )
        after_fat  = max(0, fat_left - total_fat)
        after_prot = max(0, protein_left - total_prot)
        after_carbs= max(0, carbs_left - total_carbs)
        after_cal  = max(0, cal_left - total_cal)
        if after_cal <= 100:
            result += "✅ *Норма будет выполнена!* 🎯"
        else:
            result += f"*Останется после плана:*\n🔥{after_cal} ккал | 🟠{after_fat}г | 🔵{after_prot}г | 🟡{after_carbs}г"

    return result

# ============================================================
# KEYBOARDS
# ============================================================

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Мой статус", "📋 Дневник питания")
    kb.row("📸 КБЖУ по фото", "✏️ Ввести еду вручную")
    kb.row("🔍 Поиск продукта", "⚡ Спортивный режим")
    kb.row("🍷 Выпил алкоголь", "🧪 Ввести кетоны")
    kb.row("🤖 ИИ Советник / AI Adviser")
    kb.row("👨‍👩‍👧 Семья", "⚙️ Настройки")
    kb.row("🌍 Язык / Language", "🔄 Перезапуск")
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
    kb.row("👤 Изменить пол / Change gender")
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
    kb.row(*[str(i) for i in range(1, n+1)])
    kb.row("🔍 Искать снова", "◀️ Главное меню")
    return kb

# ============================================================
# FOOD DATABASE
# ============================================================

FOOD_DB = {
    "🥑 Авокадо 200г":  {"name": "Авокадо (200г)",      "fat": 21, "protein": 2,  "carbs": 2, "cal": 200},
    "🥩 Стейк 200г":    {"name": "Стейк говяжий (200г)", "fat": 18, "protein": 30, "carbs": 0, "cal": 280},
    "🥚 Яйца 2шт":      {"name": "Яйца (2 шт)",          "fat": 10, "protein": 12, "carbs": 1, "cal": 140},
    "🐟 Лосось 150г":   {"name": "Лосось (150г)",         "fat": 14, "protein": 28, "carbs": 0, "cal": 240},
    "🥗 Салат+масло":   {"name": "Салат + оливк. масло",  "fat": 14, "protein": 2,  "carbs": 3, "cal": 145},
    "🧀 Сыр 50г":       {"name": "Сыр твёрдый (50г)",     "fat": 14, "protein": 12, "carbs": 0, "cal": 180},
    "🥜 Миндаль 30г":   {"name": "Миндаль (30г)",          "fat": 15, "protein": 6,  "carbs": 3, "cal": 170},
    "🫐 Черника 80г":   {"name": "Черника (80г)",           "fat": 0,  "protein": 1,  "carbs": 9, "cal": 45},
    "🍳 Бекон 3шт":     {"name": "Бекон (3 полоски)",       "fat": 12, "protein": 9,  "carbs": 0, "cal": 140},
}

ALCOHOL_DB = {
    "🍷 Сухое вино (150мл)":        {"name": "Сухое вино",       "ml": 150, "carbs": 4},
    "🍷 Полусухое вино (150мл)":    {"name": "Полусухое вино",   "ml": 150, "carbs": 8},
    "🍺 Пиво светлое (330мл)":      {"name": "Пиво светлое",     "ml": 330, "carbs": 13},
    "🍺 Пиво тёмное (330мл)":       {"name": "Пиво тёмное",      "ml": 330, "carbs": 18},
    "🥃 Виски/Водка/Коньяк (50мл)": {"name": "Крепкий алкоголь", "ml": 50,  "carbs": 0},
    "🍹 Коктейль (200мл)":          {"name": "Коктейль",         "ml": 200, "carbs": 25},
    "🍾 Шампанское (150мл)":        {"name": "Шампанское",       "ml": 150, "carbs": 6},
    "🍻 Несколько пив (700мл)":     {"name": "Несколько пив",    "ml": 700, "carbs": 28},
}

# ============================================================
# FALLBACK MACROS (per 100g)
# ============================================================

FALLBACK_MACROS = {
    "pumpkin seed":   {"fat": 49, "protein": 30, "carbs": 11, "cal": 559},
    "pumpkin seeds":  {"fat": 49, "protein": 30, "carbs": 11, "cal": 559},
    "pistachio":      {"fat": 45, "protein": 20, "carbs": 28, "cal": 562},
    "pistachios":     {"fat": 45, "protein": 20, "carbs": 28, "cal": 562},
    "almond":         {"fat": 50, "protein": 21, "carbs": 22, "cal": 579},
    "almonds":        {"fat": 50, "protein": 21, "carbs": 22, "cal": 579},
    "walnut":         {"fat": 65, "protein": 15, "carbs": 14, "cal": 654},
    "cashew":         {"fat": 44, "protein": 18, "carbs": 30, "cal": 553},
    "peanut":         {"fat": 49, "protein": 26, "carbs": 16, "cal": 567},
    "sunflower seed": {"fat": 51, "protein": 21, "carbs": 20, "cal": 584},
    "nut":            {"fat": 50, "protein": 18, "carbs": 20, "cal": 580},
    "nuts":           {"fat": 50, "protein": 18, "carbs": 20, "cal": 580},
    "seed":           {"fat": 45, "protein": 20, "carbs": 15, "cal": 540},
    "seeds":          {"fat": 45, "protein": 20, "carbs": 15, "cal": 540},
    "boiled egg":     {"fat": 10, "protein": 13, "carbs": 1,  "cal": 143},
    "egg salad":      {"fat": 11, "protein": 8,  "carbs": 2,  "cal": 140},
    "egg":            {"fat": 10, "protein": 13, "carbs": 1,  "cal": 143},
    "custard":        {"fat": 4,  "protein": 4,  "carbs": 18, "cal": 122},
    "fried fish":     {"fat": 12, "protein": 18, "carbs": 5,  "cal": 200},
    "fried dumpling": {"fat": 8,  "protein": 9,  "carbs": 25, "cal": 210},
    "dumpling":       {"fat": 6,  "protein": 8,  "carbs": 22, "cal": 180},
    "schnitzel":      {"fat": 14, "protein": 22, "carbs": 10, "cal": 250},
    "fish":           {"fat": 10, "protein": 20, "carbs": 0,  "cal": 170},
    "salmon":         {"fat": 13, "protein": 20, "carbs": 0,  "cal": 200},
    "tuna":           {"fat": 5,  "protein": 25, "carbs": 0,  "cal": 144},
    "shrimp":         {"fat": 1,  "protein": 20, "carbs": 1,  "cal": 99},
    "chicken":        {"fat": 7,  "protein": 27, "carbs": 0,  "cal": 165},
    "beef":           {"fat": 15, "protein": 26, "carbs": 0,  "cal": 250},
    "pork":           {"fat": 21, "protein": 20, "carbs": 0,  "cal": 270},
    "steak":          {"fat": 15, "protein": 26, "carbs": 0,  "cal": 240},
    "bacon":          {"fat": 42, "protein": 12, "carbs": 0,  "cal": 417},
    "avocado":        {"fat": 15, "protein": 2,  "carbs": 9,  "cal": 160},
    "cheese":         {"fat": 25, "protein": 20, "carbs": 2,  "cal": 300},
    "yogurt":         {"fat": 3,  "protein": 5,  "carbs": 7,  "cal": 60},
    "omelette":       {"fat": 11, "protein": 10, "carbs": 1,  "cal": 145},
    "salad":          {"fat": 5,  "protein": 2,  "carbs": 5,  "cal": 70},
    "soup":           {"fat": 3,  "protein": 4,  "carbs": 6,  "cal": 65},
    "rice":           {"fat": 1,  "protein": 3,  "carbs": 28, "cal": 130},
    "pasta":          {"fat": 2,  "protein": 5,  "carbs": 30, "cal": 157},
    "bread":          {"fat": 3,  "protein": 8,  "carbs": 50, "cal": 265},
    "pancake":        {"fat": 5,  "protein": 5,  "carbs": 30, "cal": 185},
    "pizza":          {"fat": 10, "protein": 11, "carbs": 33, "cal": 266},
    "burger":         {"fat": 16, "protein": 15, "carbs": 24, "cal": 295},
    "sushi":          {"fat": 3,  "protein": 8,  "carbs": 20, "cal": 140},
    "noodle":         {"fat": 2,  "protein": 5,  "carbs": 25, "cal": 138},
    "curry":          {"fat": 8,  "protein": 12, "carbs": 10, "cal": 160},
    "broccoli":       {"fat": 0,  "protein": 3,  "carbs": 7,  "cal": 35},
    "spinach":        {"fat": 0,  "protein": 3,  "carbs": 4,  "cal": 23},
    "tomato":         {"fat": 0,  "protein": 1,  "carbs": 4,  "cal": 18},
    "cucumber":       {"fat": 0,  "protein": 1,  "carbs": 4,  "cal": 16},
    "mushroom":       {"fat": 0,  "protein": 3,  "carbs": 3,  "cal": 22},
    "butter":         {"fat": 81, "protein": 1,  "carbs": 1,  "cal": 717},
    "olive oil":      {"fat": 100,"protein": 0,  "carbs": 0,  "cal": 884},
    "cream":          {"fat": 20, "protein": 2,  "carbs": 3,  "cal": 200},
    "chocolate":      {"fat": 32, "protein": 5,  "carbs": 56, "cal": 546},
    "apple":          {"fat": 0,  "protein": 0,  "carbs": 14, "cal": 52},
    "banana":         {"fat": 0,  "protein": 1,  "carbs": 23, "cal": 89},
    "berry":          {"fat": 0,  "protein": 1,  "carbs": 12, "cal": 50},
    "strawberry":     {"fat": 0,  "protein": 1,  "carbs": 8,  "cal": 32},
}

def get_fallback_macros(dish_names):
    fat = protein = carbs = cal = 0
    found = 0
    for dish in dish_names:
        dish_lower = dish.lower()
        matched = False
        # Точное совпадение фразы
        for key, m in FALLBACK_MACROS.items():
            if key in dish_lower:
                fat += m["fat"]; protein += m["protein"]
                carbs += m["carbs"]; cal += m["cal"]
                found += 1; matched = True; break
        # По отдельным словам
        if not matched:
            for word in dish_lower.split():
                for key, m in FALLBACK_MACROS.items():
                    if word == key or word in key or key in word:
                        fat += m["fat"]; protein += m["protein"]
                        carbs += m["carbs"]; cal += m["cal"]
                        found += 1; matched = True; break
                if matched:
                    break
    if found == 0:
        return None
    return {"fat": round(fat/found,1), "protein": round(protein/found,1),
            "carbs": round(carbs/found,1), "cal": round(cal/found)}

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
        print(f"LogMeal step1: {r1.status_code} {r1.text[:300]}")
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

        fat = protein = carbs = calories = 0

        # Попытка 1: nutritionalInfo
        r2 = requests.post(
            "https://api.logmeal.com/v2/nutrition/recipe/nutritionalInfo",
            headers=headers, json={"imageId": image_id}, timeout=15)
        print(f"LogMeal step2: {r2.status_code} {r2.text[:300]}")
        if r2.status_code == 200:
            data2 = r2.json()
            n = data2.get("nutritional_info") or data2.get("nutrition") or data2
            fat      = float(n.get("totalFat", 0) or n.get("fat", 0) or 0)
            protein  = float(n.get("proteins", 0) or n.get("protein", 0) or 0)
            carbs    = float(n.get("totalCarbs", 0) or n.get("carbs", 0) or 0)
            calories = float(n.get("calories", 0) or n.get("energy", 0) or 0)

        # Попытка 2: ingredients
        if fat == 0 and protein == 0 and carbs == 0:
            r3 = requests.post(
                "https://api.logmeal.com/v2/nutrition/recipe/ingredients",
                headers=headers, json={"imageId": image_id}, timeout=15)
            print(f"LogMeal step3: {r3.status_code} {r3.text[:300]}")
            if r3.status_code == 200:
                for ing in r3.json().get("ingredients", []):
                    n = ing.get("nutritional_info", {})
                    fat      += float(n.get("totalFat", 0) or 0)
                    protein  += float(n.get("proteins", 0) or 0)
                    carbs    += float(n.get("totalCarbs", 0) or 0)
                    calories += float(n.get("calories", 0) or 0)

        # Попытка 3: резервная база
        from_fallback = False
        if fat == 0 and protein == 0 and carbs == 0:
            fallback = get_fallback_macros(dish_names)
            if fallback:
                fat = fallback["fat"]; protein = fallback["protein"]
                carbs = fallback["carbs"]
                if calories == 0:
                    calories = fallback["cal"]
                from_fallback = True

        return {
            "dishes": dish_names if dish_names else ["Блюдо"],
            "calories": round(calories),
            "fat": round(fat, 1),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "from_fallback": from_fallback,
        }
    except Exception as e:
        print(f"LogMeal error: {e}")
        return None

def search_food(query):
    try:
        headers = {"User-Agent": "KetOSBot/1.0"}
        params = {"search_terms": query, "search_simple": 1, "action": "process",
                  "json": 1, "page_size": 20, "fields": "product_name,nutriments,brands"}
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl",
                         params=params, headers=headers, timeout=15)
        results = []
        for p in r.json().get("products", []):
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

# ============================================================
# TEXT BUILDERS
# ============================================================

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

def alcohol_recovery_text(name, ml, carbs):
    std_doses = ml / 50
    detox_hours = round(std_doses * 1.5)
    if carbs < 10:
        keto_hours = detox_hours + 8; severity = "🟡 Умеренное влияние"
        tip = "Сухое вино и чистый алкоголь — меньший удар по кетозу."
    elif carbs < 30:
        keto_hours = detox_hours + 16; severity = "🟠 Значительное влияние"
        tip = "Пиво и сладкие коктейли сильно выбивают из кетоза."
    else:
        keto_hours = detox_hours + 24; severity = "🔴 Сильное влияние"
        tip = "Сладкие напитки — самый долгий выход из кетоза."
    return (
        f"🍷 *План возврата после алкоголя*\n\n"
        f"🥃 {name} — {ml}мл | ~{carbs}г углеводов\n{severity}\n\n"
        f"⏱ Алкоголь выведется: ~{detox_hours} ч\n"
        f"✅ Кетоз восстановится: ~{keto_hours} ч\n\n"
        f"🚰 *Сейчас:* Вода 2-3л + электролиты\n"
        f"🌅 *Утром:* Кофе + MCT масло + пропусти завтрак\n"
        f"🥩 *Первый приём:* Яйца/мясо/рыба, ноль углеводов\n"
        f"🏃 *Прогулка 30 мин* ускорит возврат\n\n"
        f"💡 {tip}\n🧪 Измерь кетоны через {keto_hours} ч!"
    )

def profile_done_text(u, macros):
    gender_icon = "👨" if u.get("gender") == "male" else "👩"
    lang = u.get("lang", "ru")
    if lang == "en":
        return (
            f"✅ *Profile created!*\n\n"
            f"{gender_icon} {u['name']} | ⚖️ {u['weight']}kg | 📏 {u['height']}cm | 🎂 {int(u['age'])} y.o.\n"
            f"🏃 {u.get('sport_type','—')} | 🎯 {u.get('goal','—')}\n"
            f"🥗 Mode: {u.get('keto_level','—')}\n\n"
            f"📊 *Daily targets:*\n"
            f"🔥 Calories: *{macros['calories']} kcal*\n"
            f"🟠 Fat: *{macros['fat']}g*\n"
            f"🔵 Protein: *{macros['protein']}g*\n"
            f"🟡 Carbs: *{macros['carbs']}g*\n\n"
            f"_BMR: {macros.get('bmr','—')} kcal | TDEE: {macros.get('tdee','—')} kcal_\n\n"
            f"Let's go! 🚀"
        )
    return (
        f"✅ *Профиль готов!*\n\n"
        f"{gender_icon} {u['name']} | ⚖️ {u['weight']}кг | 📏 {u['height']}см | 🎂 {int(u['age'])}лет\n"
        f"🏃 {u.get('sport_type','—')} | 🎯 {u.get('goal','—')}\n"
        f"🥗 Режим: {u.get('keto_level','—')}\n\n"
        f"📊 *Цели на день:*\n"
        f"🔥 Калории: *{macros['calories']} ккал*\n"
        f"🟠 Жиры: *{macros['fat']}г*\n"
        f"🔵 Белки: *{macros['protein']}г*\n"
        f"🟡 Углеводы: *{macros['carbs']}г*\n\n"
        f"_Базовый обмен (BMR): {macros.get('bmr','—')} ккал_\n"
        f"_С учётом активности (TDEE): {macros.get('tdee','—')} ккал_\n\n"
        f"Поехали! 🚀"
    )

# ============================================================
# PHOTO HANDLER
# ============================================================

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    bot.send_message(msg.chat.id,
        "📸 *Фото получено!*\n🤖 Анализирую блюдо... ⏳\n_(обычно 10-20 секунд)_",
        parse_mode="Markdown")
    try:
        file_info = bot.get_file(msg.photo[-1].file_id)
        image_bytes = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}", timeout=10).content
    except Exception as e:
        print(f"Download error: {e}")
        bot.send_message(msg.chat.id, "❌ Ошибка загрузки фото. Попробуй ещё раз.", reply_markup=main_kb())
        return

    def do_analysis():
        try:
            result = analyze_photo(image_bytes)
            if not result or (result["calories"] == 0 and result["fat"] == 0 and result["protein"] == 0):
                bot.send_message(msg.chat.id,
                    "❌ Не удалось распознать блюдо.\n\n"
                    "Попробуй:\n• Сфотографировать ближе\n"
                    "• Улучшить освещение\n"
                    "• Или введи вручную ✏️",
                    reply_markup=main_kb())
                set_state(uid, "menu")
                return
            u["pending_food"] = result
            set_state(uid, "confirm_photo")
            dishes_text = ", ".join(result["dishes"][:3])
            warn = "⚠️ Много углеводов!" if result["carbs"] > 10 else "✅ Кето-дружественно"
            note = "\n\n_⚠️ Макросы примерные — рекомендую скорректировать_" if result.get("from_fallback") else ""
            bot.send_message(msg.chat.id,
                f"🤖 *Результат анализа:*\n\n"
                f"🍽 *Блюдо:* {dishes_text}\n\n"
                f"🔥 Калории: *{result['calories']} ккал*\n"
                f"🟠 Жиры: *{result['fat']}г*\n"
                f"🔵 Белки: *{result['protein']}г*\n"
                f"🟡 Углеводы: *{result['carbs']}г*\n\n"
                f"{warn}{note}\n\nВсё верно?",
                parse_mode="Markdown", reply_markup=confirm_photo_kb())
        except Exception as e:
            print(f"Photo thread error: {e}")
            bot.send_message(msg.chat.id,
                "❌ Ошибка анализа. Попробуй ещё раз или введи вручную.",
                reply_markup=main_kb())
            set_state(uid, "menu")

    t = threading.Thread(target=do_analysis)
    t.daemon = True
    t.start()

# ============================================================
# MAIN HANDLER
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    set_state(uid, "ask_lang")
    bot.send_message(msg.chat.id,
        "🔥 *KetOS* — Keto diet for athletes 💪\n\n"
        "Choose your language / Выбери язык:",
        parse_mode="Markdown",
        reply_markup=lang_kb())

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    text = msg.text
    state = get_state(uid)

    if text in ["🔄 Перезапуск", "◀️ Главное меню", "/start"]:
        set_state(uid, "menu")
        bot.send_message(msg.chat.id, t(u,"✅ Главное меню:","✅ Main menu:"), reply_markup=main_kb())
        return

    # ======================== ЯЗЫК ========================
    if state == "ask_lang" or text in ["🇷🇺 Русский", "🇬🇧 English"]:
        if text == "🇬🇧 English":
            u["lang"] = "en"
            set_state(uid, "ask_name")
            bot.send_message(msg.chat.id,
                "🔥 *Welcome to KetOS!*\n\nKeto diet for athletes 💪\n\nWhat's your name?",
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        else:
            u["lang"] = "ru"
            set_state(uid, "ask_name")
            bot.send_message(msg.chat.id,
                "🔥 *Добро пожаловать в KetOS!*\n\nКето-диета для спортсменов 💪\n\nКак тебя зовут?",
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        return

    # ======================== СМЕНА ЯЗЫКА ========================
    if text == "🌍 Язык / Language":
        set_state(uid, "switch_lang")
        bot.send_message(msg.chat.id,
            "Choose language / Выбери язык:",
            reply_markup=lang_kb())
        return

    if state == "switch_lang":
        if text == "🇬🇧 English":
            u["lang"] = "en"
            bot.send_message(msg.chat.id, "✅ Language changed to English!", reply_markup=main_kb())
        else:
            u["lang"] = "ru"
            bot.send_message(msg.chat.id, "✅ Язык изменён на русский!", reply_markup=main_kb())
        set_state(uid, "menu")
        return

    # ======================== AI СОВЕТНИК ========================
    if text == "🤖 ИИ Советник / AI Adviser":
        advice = ai_advisor(u)
        bot.send_message(msg.chat.id, advice, parse_mode="Markdown", reply_markup=main_kb())
        return

    # ======================== ОНБОРДИНГ ========================
    if state == "ask_name":
        u["name"] = text
        set_state(uid, "ask_gender")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("♀️ Женский / Female", "♂️ Мужской / Male")
        bot.send_message(msg.chat.id,
            t(u, f"Привет, *{text}*! 💪\nТвой пол?",
                 f"Hi, *{text}*! 💪\nYour gender?"),
            parse_mode="Markdown", reply_markup=kb)
        return

    if state == "ask_gender":
        if "Мужской" in text or "Male" in text or "♂️" in text:
            u["gender"] = "male"
        else:
            u["gender"] = "female"
        set_state(uid, "ask_weight")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("50","55","60","65"); kb.row("70","75","80","85"); kb.row("90","95","100","110")
        bot.send_message(msg.chat.id,
            t(u, "Введи свой вес в кг:", "Enter your weight in kg:"),
            reply_markup=kb)
        return

    if state == "ask_weight":
        try:
            u["weight"] = float(text.replace("кг","").replace("kg","").strip())
            set_state(uid, "ask_height")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("155","160","165","170"); kb.row("175","180","185","190")
            bot.send_message(msg.chat.id, t(u,"Твой рост в см:","Your height in cm:"), reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, t(u,"Введи число, например: *65*","Enter a number, e.g.: *65*"), parse_mode="Markdown")
        return

    if state == "ask_height":
        try:
            u["height"] = float(text.replace("см","").replace("cm","").strip())
            set_state(uid, "ask_age")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("20","25","30","35"); kb.row("40","45","50","55")
            bot.send_message(msg.chat.id, t(u,"Твой возраст:","Your age:"), reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, t(u,"Введи число, например: *170*","Enter a number, e.g.: *170*"), parse_mode="Markdown")
        return

    if state == "ask_age":
        try:
            u["age"] = float(text.replace("лет","").strip())
            set_state(uid, "ask_activity")
            if u.get("lang") == "en":
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                kb.row("🛋 Sedentary"); kb.row("🚶 Light (1-3x/week)")
                kb.row("🏃 Moderate (3-5x/week)"); kb.row("💪 High (6-7x/week)")
                kb.row("🏆 Very high (pro sport)")
                bot.send_message(msg.chat.id, "Physical activity level:", reply_markup=kb)
            else:
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                kb.row("🛋 Минимум (сидячий)"); kb.row("🚶 Лёгкая (1-3 раза/нед)")
                kb.row("🏃 Умеренная (3-5 раз/нед)"); kb.row("💪 Высокая (6-7 раз/нед)")
                kb.row("🏆 Очень высокая (проф. спорт)")
                bot.send_message(msg.chat.id, "Уровень физической активности:", reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, t(u,"Введи число, например: *30*","Enter a number, e.g.: *30*"), parse_mode="Markdown")
        return

    if state == "ask_activity":
        coef = {
            "🛋 Минимум (сидячий)":1.2, "🛋 Sedentary":1.2,
            "🚶 Лёгкая (1-3 раза/нед)":1.375, "🚶 Light (1-3x/week)":1.375,
            "🏃 Умеренная (3-5 раз/нед)":1.55, "🏃 Moderate (3-5x/week)":1.55,
            "💪 Высокая (6-7 раз/нед)":1.725, "💪 High (6-7x/week)":1.725,
            "🏆 Очень высокая (проф. спорт)":1.9, "🏆 Very high (pro sport)":1.9,
        }
        u["activity"] = text; u["activity_coef"] = coef.get(text, 1.55)
        set_state(uid, "ask_sport")
        if u.get("lang") == "en":
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🏃 Running/Trail","🚴 Cycling")
            kb.row("🏊 Swimming","🏋️ Strength")
            kb.row("⛷️ Skiing/Triathlon","🚶 Other")
            bot.send_message(msg.chat.id, "Main sport:", reply_markup=kb)
        else:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🏃 Бег/Трейл","🚴 Велоспорт"); kb.row("🏊 Плавание","🏋️ Силовые")
            kb.row("⛷️ Лыжи/Триатлон","🚶 Другое")
            bot.send_message(msg.chat.id, "Основной вид спорта:", reply_markup=kb)
        return

    if state == "ask_sport":
        u["sport_type"] = text; set_state(uid, "ask_goal")
        if u.get("lang") == "en":
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🔥 Weight loss","💪 Muscle gain"); kb.row("⚡ Performance","🎯 Maintenance")
            bot.send_message(msg.chat.id, "Main goal:", reply_markup=kb)
        else:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🔥 Похудение","💪 Набор мышц"); kb.row("⚡ Производительность","🎯 Поддержание")
            bot.send_message(msg.chat.id, "Главная цель:", reply_markup=kb)
        return

    if state == "ask_goal":
        u["goal"] = text
        macros = calc_macros(u); u["cal_target"] = macros["calories"]
        set_state(uid, "ask_keto_level")
        if u.get("lang") == "en":
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row("🔴 Strict keto"); kb.row("🟡 Standard keto")
            kb.row("🟢 Low-carb diet"); kb.row("✏️ Manual input")
            bot.send_message(msg.chat.id,
                f"Calculated calories: *{macros['calories']} kcal/day*\n\n"
                f"Choose diet mode:\n\n"
                f"🔴 *Strict keto* — up to 20g carbs\n"
                f"🟡 *Standard keto* — up to 30g carbs\n"
                f"🟢 *Low-carb* — up to 80g carbs\n"
                f"✏️ *Manual* — set your own",
                parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(msg.chat.id,
                f"Рассчитанные калории: *{macros['calories']} ккал/день*\n\n"
                f"Выбери режим питания:\n\n"
                f"🔴 *Строгое кето* — до 20г углеводов\n"
                f"🟡 *Нормальное кето* — до 30г углеводов\n"
                f"🟢 *Низкоуглеводная* — до 80г углеводов\n"
                f"✏️ *Ручной ввод* — задашь сам",
                parse_mode="Markdown", reply_markup=keto_level_kb())
        return

    if state == "ask_keto_level":
        level_map = {
            "🔴 Strict keto": "🔴 Строгое кето",
            "🟡 Standard keto": "🟡 Нормальное кето",
            "🟢 Low-carb diet": "🟢 Низкоуглеводная диета",
        }
        mapped = level_map.get(text, text)
        if text in ["✏️ Ручной ввод", "✏️ Manual input"]:
            set_state(uid, "manual_targets_onboard")
            macros = calc_macros(u)
            bot.send_message(msg.chat.id,
                t(u, f"Расчётные калории: *{macros['calories']} ккал*\n\nВведи через пробел:\n*калории жиры белки углеводы*\n\nПример: `1800 140 110 20`",
                     f"Calculated: *{macros['calories']} kcal*\n\nEnter separated by spaces:\n*calories fat protein carbs*\n\nExample: `1800 140 110 20`"),
                parse_mode="Markdown")
            return
        if mapped in ["🔴 Строгое кето","🟡 Нормальное кето","🟢 Низкоуглеводная диета"]:
            apply_keto_level(u, mapped)
            macros = calc_macros(u); set_state(uid, "menu")
            bot.send_message(msg.chat.id, profile_done_text(u, macros), parse_mode="Markdown", reply_markup=main_kb())
        return

    if state == "manual_targets_onboard":
        try:
            parts = text.split(); nums = [int(p) for p in parts if p.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]; u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="✏️ Ручной ввод"; set_state(uid, "menu")
            macros = {"tdee": u["cal_target"]}
            bot.send_message(msg.chat.id, profile_done_text(u, macros), parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, t(u,"❌ Пример: `1800 140 110 20`","❌ Example: `1800 140 110 20`"), parse_mode="Markdown")
        return

    # ======================== СТАТУС ========================
    if text == "📊 Мой статус":
        k = u["ketones"]
        ks = "❓ Не измерено" if k==0 else "❌ Не в кетозе" if k<0.5 else "🟡 Лёгкий кетоз" if k<1.5 else "✅ Оптимальный кетоз!" if k<3 else "🔥 Глубокий кетоз"
        bot.send_message(msg.chat.id,
            f"📊 *Статус на сегодня*\n\n🧪 {ks} ({k} ммоль/л)\n\n"
            f"🔥 Калории:  {bar(u['calories'],u['cal_target'])} {u['calories']}/{u['cal_target']} ккал\n"
            f"🟠 Жиры:     {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}г\n"
            f"🔵 Белки:    {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}г\n"
            f"🟡 Углеводы: {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "📋 Дневник питания":
        meals = u["meals"]
        meals_text = "\n".join(f"  {i+1}. {m}" for i,m in enumerate(meals)) if meals else "  Пока ничего"
        bot.send_message(msg.chat.id,
            f"📋 *Дневник питания*\n\n{meals_text}\n\n"
            f"🔥 {u['calories']} ккал | 🟠 {u['fat']}г | 🔵 {u['protein']}г | 🟡 {u['carbs']}г",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ======================== ФОТО ========================
    if text == "📸 КБЖУ по фото":
        set_state(uid, "waiting_photo")
        bot.send_message(msg.chat.id, "📸 *Отправь фото своего блюда!*\n\nAI посчитает КБЖУ. Просто прикрепи фото 👇", parse_mode="Markdown")
        return

    # ======================== ЕДА ВРУЧНУЮ ========================
    if text == "✏️ Ввести еду вручную":
        set_state(uid, "manual_food")
        bot.send_message(msg.chat.id,
            "✏️ *Ввод еды вручную*\n\n"
            "Напиши название и три числа через пробел:\n"
            "*название жиры белки углеводы*\n\n"
            "Можно добавить граммы:\n"
            "*название количество_г жиры белки углеводы*\n\n"
            "Примеры:\n`творог 5 18 3`\n`курица 200г 2 30 0`\n`кофе с молоком 150мл 1 1 3`",
            parse_mode="Markdown")
        return

    if state == "manual_food":
        try:
            parts = text.strip().split()
            numbers = []; name_parts = []; amount_str = ""
            for part in parts:
                clean = re.sub(r'[гГмлМ]+$', '', part)
                if clean.replace('.','').isdigit():
                    if any(part.lower().endswith(s) for s in ['г','мл','г.','мл.']):
                        amount_str = part
                    else:
                        numbers.append(int(float(clean)))
                else:
                    name_parts.append(part)
            if len(numbers) < 3: raise ValueError("need 3 numbers")
            name = " ".join(name_parts) if name_parts else "Блюдо"
            name = name[0].upper() + name[1:] if name else "Блюдо"
            fat=numbers[0]; protein=numbers[1]; carbs=numbers[2]
            cal = fat*9 + protein*4 + carbs*4
            amount_label = f" {amount_str}" if amount_str else ""
            u["fat"]+=fat; u["protein"]+=protein; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name}{amount_label} (Ж{fat} Б{protein} У{carbs} | {cal}ккал)")
            carbs_left = u["carbs_target"] - u["carbs"]
            warn = "\n⚠️ Лимит углеводов близко!" if carbs_left < 5 else ""
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}{amount_label}* добавлено!\n"
                f"🟠 +{fat}г | 🔵 +{protein}г | 🟡 +{carbs}г | 🔥 +{cal} ккал{warn}\n\n"
                f"Осталось углеводов: *{max(carbs_left,0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Не понял формат.\nПример: `творог 5 18 3` или `курица 200г 2 30 0`",
                parse_mode="Markdown")
        return

    # ======================== ПОИСК ========================
    if text in ["🔍 Поиск продукта","🔍 Искать снова"]:
        set_state(uid, "search_food")
        bot.send_message(msg.chat.id, "🔍 Напиши название:\n🇷🇺 `творог`, `курица`\n🇬🇧 `salmon`, `chicken`", parse_mode="Markdown")
        return

    if state == "search_food":
        bot.send_message(msg.chat.id, f"🔍 Ищу *{text}*...", parse_mode="Markdown")
        results = search_food(text)
        translations = {"колбаса":"sausage","творог":"cottage cheese","гречка":"buckwheat","курица":"chicken","говядина":"beef","рыба":"fish","картошка":"potato","рис":"rice"}
        if not results:
            eng = translations.get(text.lower())
            if eng: results = search_food(eng)
        if not results:
            bot.send_message(msg.chat.id, "❌ Не найдено. Попробуй по-английски или введи вручную.", reply_markup=main_kb())
            set_state(uid, "menu"); return
        u["search_results"] = results
        resp = f"✅ *Найдено {len(results)} продуктов* (на 100г):\n\n"
        for i,p in enumerate(results,1):
            warn = "⚠️" if p["carbs"]>10 else "✅"
            resp += f"*{i}.* {p['name']}\n   🟠{p['fat']}г 🔵{p['protein']}г {warn}{p['carbs']}г 🔥{p['cal']}ккал\n\n"
        resp += "Напиши номер чтобы добавить:"
        set_state(uid, "choose_food")
        bot.send_message(msg.chat.id, resp, parse_mode="Markdown", reply_markup=choice_kb(len(results)))
        return

    if state == "choose_food":
        if text.isdigit():
            idx = int(text)-1
            results = u.get("search_results",[])
            if 0 <= idx < len(results):
                u["pending_search_food"] = results[idx]
                set_state(uid, "ask_food_grams")
                food = results[idx]
                bot.send_message(msg.chat.id,
                    f"✅ *{food['name'][:40]}*\n\nНа 100г: 🟠{food['fat']}г 🔵{food['protein']}г 🟡{food['carbs']}г 🔥{food['cal']}ккал\n\nСколько грамм съел?\nНапример: `150`",
                    parse_mode="Markdown")
        return

    if state == "ask_food_grams":
        try:
            grams = float(text.replace("г","").replace("гр","").strip())
            food = u.get("pending_search_food",{})
            ratio = grams/100
            fat=round(food["fat"]*ratio,1); protein=round(food["protein"]*ratio,1)
            carbs=round(food["carbs"]*ratio,1); cal=round(food["cal"]*ratio)
            u["fat"]+=fat; u["protein"]+=protein; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{food['name'][:25]} ({int(grams)}г | {cal}ккал)")
            carbs_left = u["carbs_target"]-u["carbs"]
            warn = "\n⚠️ Лимит близко!" if carbs_left<5 else ""
            set_state(uid, "menu")
            bot.send_message(msg.chat.id,
                f"✅ *{food['name'][:40]}* — {int(grams)}г\n🟠+{fat}г 🔵+{protein}г 🟡+{carbs}г 🔥+{cal}ккал{warn}\nОсталось: *{max(round(u['carbs_target']-u['carbs']),0)}г*",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id, "❌ Введи число, например: `150`", parse_mode="Markdown")
        return

    # ======================== БЫСТРЫЕ ПРОДУКТЫ ========================
    if text in FOOD_DB:
        food = FOOD_DB[text]
        u["fat"]+=food["fat"]; u["protein"]+=food["protein"]; u["carbs"]+=food["carbs"]; u["calories"]+=food["cal"]
        u["meals"].append(f"{food['name']} (Ж{food['fat']} Б{food['protein']} У{food['carbs']} | {food['cal']}ккал)")
        carbs_left = u["carbs_target"]-u["carbs"]
        bot.send_message(msg.chat.id,
            f"✅ *{food['name']}* добавлено!\n🟠+{food['fat']}г 🔵+{food['protein']}г 🟡+{food['carbs']}г 🔥+{food['cal']}ккал\nОсталось: *{max(carbs_left,0)}г*",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    # ======================== ПОДТВЕРЖДЕНИЕ ФОТО ========================
    if state == "confirm_photo":
        if text == "✅ Добавить в дневник":
            food = u.get("pending_food")
            if food:
                u["fat"]+=food["fat"]; u["protein"]+=food["protein"]
                u["carbs"]+=food["carbs"]; u["calories"]+=food["calories"]
                dishes = ", ".join(food["dishes"][:2])
                u["meals"].append(f"{dishes[:25]} (фото | {food['calories']}ккал)")
                carbs_left = u["carbs_target"]-u["carbs"]
                u["pending_food"]=None; set_state(uid,"menu")
                bot.send_message(msg.chat.id,
                    f"✅ *Добавлено!*\n🔥 +{food['calories']} ккал\nОсталось: *{max(carbs_left,0)}г*",
                    parse_mode="Markdown", reply_markup=main_kb())
            return
        if text == "✏️ Скорректировать":
            food = u.get("pending_food")
            set_state(uid, "correct_photo")
            bot.send_message(msg.chat.id,
                f"Текущие значения:\n🟠{food['fat']}г 🔵{food['protein']}г 🟡{food['carbs']}г 🔥{food['calories']}ккал\n\n"
                f"Напиши название и три числа через пробел:\n`название жиры белки углеводы`\n\n"
                f"Примеры:\n`яйцо варёное 7 6 0`\n`рыба с овощами 12 25 8`\n\nИли нажми *❌ Отмена*",
                parse_mode="Markdown", reply_markup=confirm_photo_kb())
            return
        if text == "❌ Отмена":
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id, "Отменено.", reply_markup=main_kb())
            return

    if state == "correct_photo":
        if text == "❌ Отмена":
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id, "Отменено.", reply_markup=main_kb())
            return
        try:
            parts = text.strip().split()
            numbers=[]; name_parts=[]
            for part in parts:
                clean = re.sub(r'[гГмлМ,]+$','',part)
                if clean.replace('.','').isdigit(): numbers.append(int(float(clean)))
                else: name_parts.append(part)
            if len(numbers)<3: raise ValueError()
            name=" ".join(name_parts) if name_parts else "Блюдо"
            name=name[0].upper()+name[1:] if name else "Блюдо"
            fat=numbers[0]; protein=numbers[1]; carbs=numbers[2]
            cal=fat*9+protein*4+carbs*4
            u["fat"]+=fat; u["protein"]+=protein; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name} (Ж{fat} Б{protein} У{carbs} | {cal}ккал)")
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"✅ *{name}* добавлено!\n🟠{fat}г 🔵{protein}г 🟡{carbs}г 🔥{cal}ккал",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                "❌ Пример: `яйцо варёное 7 6 0`\nИли нажми *❌ Отмена*", parse_mode="Markdown")
        return

    # ======================== КЕТОНЫ ========================
    if text == "🧪 Ввести кетоны":
        set_state(uid,"ketones")
        bot.send_message(msg.chat.id,"Введи уровень кетонов (ммоль/л)\nНапример: *1.8*",parse_mode="Markdown")
        return

    if state == "ketones":
        try:
            val=float(text.replace(",","."))
            u["ketones"]=val
            s=("❌ Не в кетозе\n💡 Сократи углеводы" if val<0.5 else
               "🟡 Лёгкий кетоз\n💡 Уменьши углеводы на 5г" if val<1.5 else
               "✅ Оптимальный кетоз!\n💡 Продолжай!" if val<3 else
               "🔥 Глубокий кетоз\n💡 Пей воду + электролиты")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,f"🧪 *{val} ммоль/л*\n\n{s}",parse_mode="Markdown",reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,"❌ Введи число: *1.8*",parse_mode="Markdown")
        return

    # ======================== АЛКОГОЛЬ ========================
    if text == "🍷 Выпил алкоголь":
        set_state(uid,"choose_alcohol")
        bot.send_message(msg.chat.id,"🍷 *Что пил?*\nВыбери из списка:",parse_mode="Markdown",reply_markup=alcohol_kb())
        return

    if state == "choose_alcohol":
        if text == "✏️ Ввести вручную":
            set_state(uid,"manual_alcohol")
            bot.send_message(msg.chat.id,"Введи через пробел:\n*название количество_мл углеводы_г*\n\nПример: `Пиво крафтовое 500 20`",parse_mode="Markdown")
            return
        drink = ALCOHOL_DB.get(text)
        if drink:
            u["pending_alcohol"]=drink; set_state(uid,"ask_alcohol_amount")
            bot.send_message(msg.chat.id,f"Выбрано: *{drink['name']}*\nСколько порций?",parse_mode="Markdown",reply_markup=portions_kb())
        return

    if state == "ask_alcohol_amount":
        drink = u.get("pending_alcohol",{})
        try:
            qty = 2 if "2" in text else 3 if "3" in text else 1
            total_ml=drink["ml"]*qty; total_carbs=drink["carbs"]*qty
            u["carbs"]+=total_carbs; u["calories"]+=total_carbs*4
            u["meals"].append(f"🍷 {drink['name']} x{qty} ({total_carbs}г углев.)")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,alcohol_recovery_text(drink["name"],total_ml,total_carbs),parse_mode="Markdown",reply_markup=main_kb())
        except:
            set_state(uid,"menu"); bot.send_message(msg.chat.id,"Используй кнопки 👇",reply_markup=main_kb())
        return

    if state == "manual_alcohol":
        try:
            parts=text.split(); name=parts[0]; ml=int(parts[1]); carbs=int(parts[2])
            u["carbs"]+=carbs; u["calories"]+=carbs*4
            u["meals"].append(f"🍷 {name} ({ml}мл, {carbs}г углев.)")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,alcohol_recovery_text(name,ml,carbs),parse_mode="Markdown",reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,"❌ Пример: `Пиво крафтовое 500 20`",parse_mode="Markdown")
        return

    # ======================== СПОРТ ========================
    if text == "⚡ Спортивный режим":
        set_state(uid,"sport"); bot.send_message(msg.chat.id,"⚡ Выбери активность:",reply_markup=sport_kb())
        return

    if text in ["🔄 План возврата в кетоз","🔄 Возврат в кетоз"]:
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,recovery_text(u.get("last_gel_carbs",60)),parse_mode="Markdown",reply_markup=main_kb())
        return

    if text == "🏋️ Силовая":
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,"🏋️ *Силовая на кето*\n\nДо: MCT масло + кофе\nВо время: вода + соль\nПосле: 30-40г белка за 30 мин",parse_mode="Markdown",reply_markup=main_kb())
        return

    if text in ["🏃 Трейл/Бег","🚴 Велогонка","🏊 Триатлон","⛷️ Лыжи"]:
        u["sport_type_race"]=text; set_state(uid,"ask_distance")
        bot.send_message(msg.chat.id,"Дистанция или время?\nПример: *42 км* или *3 часа*",parse_mode="Markdown")
        return

    if state == "ask_distance":
        try:
            t=text.lower()
            if "час" in t: hours=float(''.join(c for c in t if c.isdigit() or c=='.'))
            elif "км" in t: hours=float(''.join(c for c in t if c.isdigit() or c=='.'))/10
            else: hours=2
            gels=max(1,int(hours/1.5)); total=gels*20; u["last_gel_carbs"]=total
            resp=f"⚡ *Протокол гелей*\n📍 {text} (~{int(hours)}ч)\n💊 Гелей: {gels} шт\n\n"
            times=[0,0.4,0.7,0.9]
            for i in range(gels):
                t_min=int(hours*times[min(i,3)]*60)
                label="За 30 мин до старта" if i==0 else f"Через {t_min} мин"
                resp+=f"🟡 *{label}:* Гель #{i+1} — 20г\n"
            resp+=(f"\n📊 Итого: *{total}г углеводов*\n⏱ Возврат: *~{max(4,int(total/15))} часов*\n\n"
                   f"🏁 После финиша нажми:\n👉 *🔄 План возврата в кетоз*")
            set_state(uid,"menu"); bot.send_message(msg.chat.id,resp,parse_mode="Markdown",reply_markup=after_gel_kb())
        except:
            bot.send_message(msg.chat.id,"Напиши: *42 км* или *3 часа*",parse_mode="Markdown")
        return

    # ======================== СЕМЬЯ ========================
    if text == "👨‍👩‍👧 Семья":
        meals=u["meals"]; meals_text="\n".join(f"  • {m}" for m in meals) if meals else "  Пока нет блюд"
        bot.send_message(msg.chat.id,
            f"👨‍👩‍👧 *Семейный режим*\n\nПригласи партнёра:\n`https://t.me/ketOSzoneBot?start=family_{uid}`\n\n📋 *Рацион:*\n{meals_text}",
            parse_mode="Markdown",reply_markup=main_kb())
        return

    # ======================== НАСТРОЙКИ ========================
    if text == "⚙️ Настройки":
        keto_level = u.get("keto_level") or "🟡 Нормальное кето"
        gender_icon = "👨 " + t(u,"Мужской","Male") if u.get("gender")=="male" else "👩 " + t(u,"Женский","Female")
        bot.send_message(msg.chat.id,
            f"⚙️ *{t(u,'Настройки','Settings')}*\n\n"
            f"👤 {u.get('name','—')} | {gender_icon}\n"
            f"⚖️ {u.get('weight','—')}кг | 📏 {u.get('height','—')}см | 🎂 {int(u.get('age',0))}лет\n"
            f"🏃 {u.get('sport_type','—')} | 🎯 {u.get('goal','—')}\n"
            f"🥗 {t(u,'Режим','Mode')}: {keto_level}\n\n"
            f"📊 *{t(u,'Цели','Targets')}:*\n"
            f"🔥 {u['cal_target']} {t(u,'ккал','kcal')} | 🟠 {u['fat_target']}г | 🔵 {u['protein_target']}г | 🟡 {u['carbs_target']}г",
            parse_mode="Markdown", reply_markup=settings_kb())
        return

    if text == "🥗 Изменить режим питания":
        set_state(uid,"change_keto_level")
        bot.send_message(msg.chat.id,
            "Выбери режим:\n\n🔴 Строгое кето\n🟡 Нормальное кето\n🟢 Низкоуглеводная диета\n✏️ Ручной ввод",
            reply_markup=keto_level_kb())
        return

    if state == "change_keto_level":
        if text == "✏️ Ручной ввод": set_state(uid,"edit_targets"); bot.send_message(msg.chat.id,"Введи через пробел:\n*калории жиры белки углеводы*\n\nПример: `1800 140 110 20`",parse_mode="Markdown"); return
        if text in ["🔴 Строгое кето","🟡 Нормальное кето","🟢 Низкоуглеводная диета"]:
            apply_keto_level(u,text); set_state(uid,"menu")
            bot.send_message(msg.chat.id,f"✅ Режим: {text}\n🟠{u['fat_target']}г 🔵{u['protein_target']}г 🟡{u['carbs_target']}г",reply_markup=main_kb())
        return

    if text == "👤 Изменить пол / Change gender":
        set_state(uid, "change_gender")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("♀️ Женский / Female", "♂️ Мужской / Male")
        kb.row("◀️ Главное меню")
        gender_now = "♀️ Женский" if u.get("gender","female") == "female" else "♂️ Мужской"
        bot.send_message(msg.chat.id,
            t(u,
              f"Текущий пол: {gender_now}\n\nВыбери новый:",
              f"Current gender: {gender_now}\n\nSelect new:"),
            reply_markup=kb)
        return

    if state == "change_gender":
        if "Мужской" in text or "Male" in text or "♂️" in text:
            u["gender"] = "male"
            icon = "♂️"
        else:
            u["gender"] = "female"
            icon = "♀️"
        macros = calc_macros(u)
        u["cal_target"]     = macros["calories"]
        u["fat_target"]     = macros["fat"]
        u["protein_target"] = macros["protein"]
        u["carbs_target"]   = macros["carbs"]
        set_state(uid, "menu")
        kcal = t(u, "ккал", "kcal")
        bot.send_message(msg.chat.id,
            f"✅ {icon} {t(u,'Пол обновлён и калории пересчитаны!','Gender updated and calories recalculated!')}\n\n"
            f"🔥 {macros['calories']} {kcal}\n"
            f"🟠 {macros['fat']}г | 🔵 {macros['protein']}г | 🟡 {macros['carbs']}г\n\n"
            f"_BMR: {macros['bmr']} {kcal} | TDEE: {macros['tdee']} {kcal}_",
            parse_mode="Markdown", reply_markup=main_kb())
        return

    if text == "⚖️ Изменить вес/рост/возраст":
        set_state(uid, "edit_weight")
        bot.send_message(msg.chat.id,
            t(u,
              "Введи через пробел:\n*вес рост возраст* (и пол: м или ж — необязательно)\n\n"
              "Примеры:\n`68 166 49`\n`68 166 49 ж`\n`85 180 40 м`",
              "Enter separated by spaces:\n*weight height age* (gender: m or f — optional)\n\n"
              "Examples:\n`68 166 49`\n`68 166 49 f`\n`85 180 40 m`"),
            parse_mode="Markdown")
        return

    if state == "edit_weight":
        try:
            parts = text.split()
            # Нужно минимум 3 числа
            nums = []
            gender_str = None
            for p in parts:
                clean = p.replace("кг","").replace("kg","").replace("см","").replace("cm","")
                if clean.replace(".","").isdigit():
                    nums.append(float(clean))
                elif p.lower() in ["м","m","male","мужской","муж"]:
                    gender_str = "male"
                elif p.lower() in ["ж","f","female","женский","жен"]:
                    gender_str = "female"

            if len(nums) < 3:
                raise ValueError("need 3 numbers")

            u["weight"] = nums[0]
            u["height"] = nums[1]
            u["age"]    = nums[2]
            if gender_str:
                u["gender"] = gender_str

            macros = calc_macros(u)
            u["cal_target"]     = macros["calories"]
            u["fat_target"]     = macros["fat"]
            u["protein_target"] = macros["protein"]
            u["carbs_target"]   = macros["carbs"]
            set_state(uid, "menu")

            gender_icon = "👨" if u["gender"] == "male" else "👩"
            kcal = t(u, "ккал", "kcal")
            bot.send_message(msg.chat.id,
                f"✅ {t(u,'Обновлено и пересчитано!','Updated and recalculated!')}\n\n"
                f"{gender_icon} ⚖️{u['weight']}кг 📏{u['height']}см 🎂{int(u['age'])}лет\n\n"
                f"🔥 {macros['calories']} {kcal}\n"
                f"🟠 {t(u,'Жиры','Fat')}: {macros['fat']}г | "
                f"🔵 {t(u,'Белки','Protein')}: {macros['protein']}г | "
                f"🟡 {t(u,'Углеводы','Carbs')}: {macros['carbs']}г\n\n"
                f"_BMR: {macros['bmr']} {kcal} | TDEE: {macros['tdee']} {kcal}_",
                parse_mode="Markdown", reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,
                t(u,
                  "❌ Введи минимум 3 числа через пробел:\n`68 166 49`",
                  "❌ Enter at least 3 numbers:\n`68 166 49`"),
                parse_mode="Markdown")
        return

    if text == "🎯 Изменить цели вручную":
        set_state(uid,"edit_targets")
        bot.send_message(msg.chat.id,f"Текущие: 🔥{u['cal_target']} 🟠{u['fat_target']}г 🔵{u['protein_target']}г 🟡{u['carbs_target']}г\n\nВведи через пробел:\n*калории жиры белки углеводы*\n\nПример: `1800 140 110 20`",parse_mode="Markdown")
        return

    if state == "edit_targets":
        try:
            parts=text.split(); nums=[int(p) for p in parts if p.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]; u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="✏️ Ручной ввод"; set_state(uid,"menu")
            bot.send_message(msg.chat.id,f"✅ Цели обновлены!\n🔥{u['cal_target']}ккал 🟠{u['fat_target']}г 🔵{u['protein_target']}г 🟡{u['carbs_target']}г",reply_markup=main_kb())
        except:
            bot.send_message(msg.chat.id,"❌ Пример: `1800 140 110 20`",parse_mode="Markdown")
        return

    if text == "🔄 Пересчитать автоматически":
        macros=calc_macros(u); u["cal_target"]=macros["calories"]
        apply_keto_level(u,u.get("keto_level","🟡 Нормальное кето"))
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,f"✅ Пересчитано!\n🔥{u['cal_target']}ккал 🟠{u['fat_target']}г 🔵{u['protein_target']}г 🟡{u['carbs_target']}г",reply_markup=main_kb())
        return

    if text == "🗑 Сбросить день":
        u["fat"]=u["protein"]=u["carbs"]=u["calories"]=0; u["meals"]=[]
        set_state(uid,"menu"); bot.send_message(msg.chat.id,"✅ День сброшен!",reply_markup=main_kb())
        return

    set_state(uid,"menu")
    bot.send_message(msg.chat.id,"Используй кнопки 👇",reply_markup=main_kb())

print("🔥 KetOS бот запущен!")
bot.polling(none_stop=True, interval=0, timeout=20)
