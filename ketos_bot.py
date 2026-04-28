import telebot
from telebot import types
import requests
import os
import re
import threading

TOKEN = os.environ.get("TOKEN", "")
LOGMEAL_TOKEN = os.environ.get("LOGMEAL_TOKEN", "a50507ce2019da95e0341da750d887449d40df54")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
bot = telebot.TeleBot(TOKEN)

users = {}
states = {}

# ============================================================
# HELPERS
# ============================================================

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "name": "", "weight": 0.0, "height": 0.0, "age": 0.0,
            "gender": "female", "goal": "", "activity": "",
            "activity_coef": 1.55, "keto_level": "Normal keto",
            "sport_type": "", "ketones": 0.0,
            "fat": 0, "protein": 0, "carbs": 0, "calories": 0,
            "fat_target": 130, "protein_target": 110,
            "carbs_target": 25, "cal_target": 1600,
            "meals": [], "last_gel_carbs": 0,
            "search_results": [], "pending_food": None,
            "pending_alcohol": None, "pending_search_food": None,
            "lang": "ru",
        }
    return users[uid]

def set_state(uid, s):
    states[uid] = s

def get_state(uid):
    return states.get(uid, "menu")

def L(u, ru, en):
    return en if u.get("lang") == "en" else ru

def is_registered(u):
    return u.get("weight", 0) > 0 and u.get("height", 0) > 0

# ============================================================
# CALCS
# ============================================================

def calc_macros(u):
    w = float(u.get("weight") or 70)
    h = float(u.get("height") or 170)
    a = float(u.get("age") or 30)
    coef = float(u.get("activity_coef") or 1.55)
    gender = u.get("gender", "female")
    bmr = (10*w + 6.25*h - 5*a + 5) if gender == "male" else (10*w + 6.25*h - 5*a - 161)
    tdee = round(bmr * coef)
    goal = u.get("goal", "").lower()
    if any(x in goal for x in ["худ", "loss", "похуд"]):
        cal = tdee - 500
    elif any(x in goal for x in ["набор", "gain", "muscle"]):
        cal = tdee + 300
    else:
        cal = tdee
    cal = max(cal, 1200)
    level = u.get("keto_level", "Normal keto")
    if "Strict" in level or "Строг" in level:
        fat = round(cal*0.75/9); prot = round(cal*0.20/4); carbs = round(cal*0.05/4)
    elif "Low" in level or "Низко" in level:
        fat = round(cal*0.50/9); prot = round(cal*0.30/4); carbs = round(cal*0.20/4)
    else:
        fat = round(cal*0.70/9); prot = round(cal*0.25/4); carbs = round(cal*0.05/4)
    return {"calories": cal, "fat": fat, "protein": prot, "carbs": carbs,
            "tdee": tdee, "bmr": round(bmr)}

def apply_macros(u):
    m = calc_macros(u)
    u["cal_target"] = m["calories"]
    u["fat_target"] = m["fat"]
    u["protein_target"] = m["protein"]
    u["carbs_target"] = m["carbs"]
    return m

def bar(done, target):
    pct = min(int(done / max(target, 1) * 10), 10)
    return "▓" * pct + "░" * (10 - pct)

# ============================================================
# KEYBOARDS — back button everywhere
# ============================================================

BACK_RU = "◀ Главное меню"
BACK_EN = "◀ Main menu"

def back_btn(lang):
    return BACK_EN if lang == "en" else BACK_RU

def main_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("My status", "Food diary")
        kb.row("Photo meal", "Add food")
        kb.row("Search product", "Sport")
        kb.row("Alcohol", "Ketones")
        kb.row("Keto Adviser")
        kb.row("Family", "Settings")
        kb.row("Language", "Restart")
    else:
        kb.row("Мой статус", "Дневник")
        kb.row("Фото блюда", "Ввести еду")
        kb.row("Поиск продукта", "Спорт")
        kb.row("Алкоголь", "Кетоны")
        kb.row("Кето Советник")
        kb.row("Семья", "Настройки")
        kb.row("Язык / Language", "Перезапуск")
    return kb

def back_kb(lang="ru"):
    """Single back button"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(back_btn(lang))
    return kb

def gender_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Female", "Male")
        kb.row("◀ Main menu")
    else:
        kb.row("Женский", "Мужской")
        kb.row("◀ Главное меню")
    return kb

def weight_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("50","55","60","65")
    kb.row("70","75","80","85")
    kb.row("90","95","100","110")
    kb.row("◀ Главное меню" if lang != "en" else "◀ Main menu")
    return kb

def height_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("155","160","165","170")
    kb.row("175","180","185","190")
    kb.row("◀ Главное меню" if lang != "en" else "◀ Main menu")
    return kb

def age_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("20","25","30","35")
    kb.row("40","45","50","55")
    kb.row("◀ Главное меню" if lang != "en" else "◀ Main menu")
    return kb

def activity_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Sedentary"); kb.row("Light (1-3x/week)")
        kb.row("Moderate (3-5x/week)"); kb.row("High (6-7x/week)")
        kb.row("Pro athlete")
    else:
        kb.row("Минимум (сидячий)"); kb.row("Лёгкая (1-3 раза/нед)")
        kb.row("Умеренная (3-5 раз/нед)"); kb.row("Высокая (6-7 раз/нед)")
        kb.row("Проф. спорт")
    kb.row(back_btn(lang))
    return kb

def sport_onboard_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Running / Trail", "Cycling")
        kb.row("Swimming", "Strength")
        kb.row("Skiing / Triathlon", "Other")
    else:
        kb.row("Бег / Трейл", "Велоспорт")
        kb.row("Плавание", "Силовые")
        kb.row("Лыжи / Триатлон", "Другое")
    kb.row(back_btn(lang))
    return kb

def goal_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Weight loss", "Muscle gain")
        kb.row("Performance", "Maintenance")
    else:
        kb.row("Похудение", "Набор мышц")
        kb.row("Производительность", "Поддержание")
    kb.row(back_btn(lang))
    return kb

def keto_level_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Strict keto"); kb.row("Normal keto")
        kb.row("Low-carb"); kb.row("Manual input")
    else:
        kb.row("Строгое кето"); kb.row("Нормальное кето")
        kb.row("Низкоуглеводная"); kb.row("Ручной ввод")
    kb.row(back_btn(lang))
    return kb

def confirm_photo_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Add to diary", "Correct")
        kb.row("Cancel", back_btn(lang))
    else:
        kb.row("Добавить в дневник", "Скорректировать")
        kb.row("Отмена", back_btn(lang))
    return kb

def sport_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Trail / Run", "Cycling race")
        kb.row("Triathlon", "Skiing")
        kb.row("Strength", "Back to ketosis")
        kb.row("Alcohol", back_btn(lang))
    else:
        kb.row("Трейл / Бег", "Велогонка")
        kb.row("Триатлон", "Лыжи")
        kb.row("Силовая", "Возврат в кетоз")
        kb.row("Алкоголь", back_btn(lang))
    return kb

def after_gel_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Ketosis recovery plan", back_btn(lang))
    else:
        kb.row("План возврата в кетоз", back_btn(lang))
    return kb

def settings_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Change weight / height / age")
        kb.row("Change goal"); kb.row("Change gender")
        kb.row("Change diet mode"); kb.row("Change targets manually")
        kb.row("Recalculate automatically"); kb.row("Reset day")
        kb.row(back_btn(lang))
    else:
        kb.row("Изменить вес / рост / возраст")
        kb.row("Изменить цель"); kb.row("Изменить пол")
        kb.row("Изменить режим питания"); kb.row("Изменить цели вручную")
        kb.row("Пересчитать автоматически"); kb.row("Сбросить день")
        kb.row(back_btn(lang))
    return kb

def alcohol_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Сухое вино 150мл"); kb.row("Полусухое вино 150мл")
    kb.row("Пиво светлое 330мл"); kb.row("Пиво тёмное 330мл")
    kb.row("Виски / Водка / Коньяк 50мл")
    kb.row("Коктейль 200мл"); kb.row("Шампанское 150мл")
    kb.row("Несколько пив 700мл"); kb.row("Ввести вручную")
    kb.row(back_btn(lang))
    return kb

def portions_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("1", "2", "3")
    kb.row(back_btn(lang))
    return kb

def choice_kb(n, lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(*[str(i) for i in range(1, n+1)])
    kb.row(back_btn(lang))
    return kb

def lang_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Русский", "English")
    return kb

def ai_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("What to eat today?")
        kb.row("How to speed up ketosis?")
        kb.row("Training tips on keto")
        kb.row(back_btn(lang))
    else:
        kb.row("Что съесть сегодня?")
        kb.row("Как ускорить вход в кетоз?")
        kb.row("Советы для тренировки на кето")
        kb.row(back_btn(lang))
    return kb

def ai_after_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Ask another question", back_btn(lang))
    else:
        kb.row("Задать ещё вопрос", back_btn(lang))
    return kb

# ============================================================
# DATA
# ============================================================

ALCOHOL_DB = {
    "Сухое вино 150мл":           {"name": "Сухое вино",        "ml": 150, "carbs": 4},
    "Полусухое вино 150мл":       {"name": "Полусухое вино",    "ml": 150, "carbs": 8},
    "Пиво светлое 330мл":         {"name": "Пиво светлое",      "ml": 330, "carbs": 13},
    "Пиво тёмное 330мл":          {"name": "Пиво тёмное",       "ml": 330, "carbs": 18},
    "Виски / Водка / Коньяк 50мл":{"name": "Крепкий алкоголь",  "ml": 50,  "carbs": 0},
    "Коктейль 200мл":             {"name": "Коктейль",          "ml": 200, "carbs": 25},
    "Шампанское 150мл":           {"name": "Шампанское",        "ml": 150, "carbs": 6},
    "Несколько пив 700мл":        {"name": "Несколько пив",     "ml": 700, "carbs": 28},
}

ACTIVITY_MAP = {
    "Минимум (сидячий)": 1.2,      "Sedentary": 1.2,
    "Лёгкая (1-3 раза/нед)": 1.375,"Light (1-3x/week)": 1.375,
    "Умеренная (3-5 раз/нед)": 1.55,"Moderate (3-5x/week)": 1.55,
    "Высокая (6-7 раз/нед)": 1.725, "High (6-7x/week)": 1.725,
    "Проф. спорт": 1.9,             "Pro athlete": 1.9,
}

KETO_MAP = {
    "Строгое кето": "Strict keto",   "Strict keto": "Strict keto",
    "Нормальное кето": "Normal keto", "Normal keto": "Normal keto",
    "Низкоуглеводная": "Low-carb",    "Low-carb": "Low-carb",
    "Ручной ввод": "Manual",          "Manual input": "Manual",
}

FOOD_SUGGESTIONS = [
    {"ru":"Авокадо (200г)",       "en":"Avocado (200g)",        "fat":21,"protein":2, "carbs":2, "cal":200},
    {"ru":"Стейк говяжий (150г)", "en":"Beef steak (150g)",     "fat":14,"protein":23,"carbs":0, "cal":210},
    {"ru":"Лосось (150г)",        "en":"Salmon (150g)",          "fat":14,"protein":28,"carbs":0, "cal":240},
    {"ru":"Яйца варёные (2шт)",   "en":"Boiled eggs (2pc)",     "fat":10,"protein":12,"carbs":1, "cal":140},
    {"ru":"Сыр твёрдый (50г)",    "en":"Hard cheese (50g)",     "fat":14,"protein":12,"carbs":0, "cal":180},
    {"ru":"Миндаль (30г)",        "en":"Almonds (30g)",          "fat":15,"protein":6, "carbs":3, "cal":170},
    {"ru":"Бекон (3 полоски)",    "en":"Bacon (3 strips)",       "fat":12,"protein":9, "carbs":0, "cal":140},
    {"ru":"Куриная грудка (150г)","en":"Chicken breast (150g)", "fat":4, "protein":35,"carbs":0, "cal":165},
    {"ru":"Творог 5% (150г)",     "en":"Cottage cheese (150g)", "fat":8, "protein":18,"carbs":3, "cal":155},
    {"ru":"Тунец в масле (100г)", "en":"Tuna in oil (100g)",    "fat":10,"protein":26,"carbs":0, "cal":200},
    {"ru":"Грецкие орехи (30г)",  "en":"Walnuts (30g)",          "fat":20,"protein":5, "carbs":4, "cal":196},
]

FALLBACK_MACROS = {
    "pumpkin seed":{"fat":49,"protein":30,"carbs":11,"cal":559},
    "pistachio":   {"fat":45,"protein":20,"carbs":28,"cal":562},
    "almond":      {"fat":50,"protein":21,"carbs":22,"cal":579},
    "walnut":      {"fat":65,"protein":15,"carbs":14,"cal":654},
    "cashew":      {"fat":44,"protein":18,"carbs":30,"cal":553},
    "nut":         {"fat":50,"protein":18,"carbs":20,"cal":580},
    "seed":        {"fat":45,"protein":20,"carbs":15,"cal":540},
    "egg":         {"fat":10,"protein":13,"carbs":1, "cal":155},
    "fish":        {"fat":10,"protein":20,"carbs":0, "cal":170},
    "salmon":      {"fat":13,"protein":20,"carbs":0, "cal":200},
    "chicken":     {"fat":7, "protein":27,"carbs":0, "cal":165},
    "beef":        {"fat":15,"protein":26,"carbs":0, "cal":250},
    "steak":       {"fat":15,"protein":26,"carbs":0, "cal":240},
    "bacon":       {"fat":42,"protein":12,"carbs":0, "cal":417},
    "pork":        {"fat":20,"protein":22,"carbs":0, "cal":270},
    "shrimp":      {"fat":2, "protein":20,"carbs":1, "cal":100},
    "tofu":        {"fat":5, "protein":8, "carbs":2, "cal":80},
    "avocado":     {"fat":15,"protein":2, "carbs":9, "cal":160},
    "cheese":      {"fat":25,"protein":20,"carbs":2, "cal":300},
    "coconut":     {"fat":24,"protein":2, "carbs":6, "cal":230},
    "salad":       {"fat":5, "protein":2, "carbs":5, "cal":70},
    "broccoli":    {"fat":0, "protein":3, "carbs":7, "cal":35},
    "vegetable":   {"fat":1, "protein":2, "carbs":8, "cal":45},
    "congee":      {"fat":2, "protein":5, "carbs":25,"cal":130},
    "rice soup":   {"fat":3, "protein":8, "carbs":22,"cal":145},
    "noodle soup": {"fat":5, "protein":8, "carbs":25,"cal":180},
    "vegetable soup":{"fat":3,"protein":5,"carbs":12,"cal":95},
    "tom yum":     {"fat":5, "protein":12,"carbs":6, "cal":120},
    "tom kha":     {"fat":14,"protein":10,"carbs":8, "cal":195},
    "soup":        {"fat":4, "protein":6, "carbs":12,"cal":110},
    "rice":        {"fat":1, "protein":3, "carbs":28,"cal":130},
    "fried rice":  {"fat":6, "protein":5, "carbs":28,"cal":185},
    "pad thai":    {"fat":8, "protein":12,"carbs":35,"cal":265},
    "noodle":      {"fat":3, "protein":6, "carbs":28,"cal":165},
    "curry":       {"fat":12,"protein":15,"carbs":10,"cal":210},
    "pizza":       {"fat":10,"protein":11,"carbs":33,"cal":266},
    "burger":      {"fat":16,"protein":15,"carbs":24,"cal":295},
    "sushi":       {"fat":3, "protein":8, "carbs":20,"cal":140},
    "bread":       {"fat":3, "protein":8, "carbs":50,"cal":265},
    "butter":      {"fat":81,"protein":1, "carbs":1, "cal":717},
}

def get_fallback(dish_names):
    fat=prot=carbs=cal=found=0
    for dish in dish_names:
        dl = dish.lower()
        best=None; best_len=0
        for key,m in FALLBACK_MACROS.items():
            if key in dl and len(key)>best_len:
                best=m; best_len=len(key)
        if not best:
            for w in dl.split():
                for key,m in FALLBACK_MACROS.items():
                    if w==key or (len(w)>4 and w in key):
                        best=m; break
                if best: break
        if best:
            fat+=best["fat"]; prot+=best["protein"]
            carbs+=best["carbs"]; cal+=best["cal"]; found+=1
    if found==0: return None
    return {"fat":round(fat/found,1),"protein":round(prot/found,1),
            "carbs":round(carbs/found,1),"cal":round(cal/found)}

# ============================================================
# API
# ============================================================

def analyze_photo(image_bytes):
    """Use Claude Vision for accurate food analysis"""
    try:
        import base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # Use Claude Vision if API key available
        if ANTHROPIC_API_KEY:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 300,
                    "system": "You are a nutrition expert. Analyze food photos and give accurate macro estimates.",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                }
                            },
                            {
                                "type": "text",
                                "text": (
                                    "You are a professional nutritionist. Carefully analyze ALL ingredients visible in this photo.\n\n"
                                    "1. Look for EVERY component: proteins (meat, fish, eggs), carbs (rice, noodles, bread), "
                                    "vegetables, sauces, oils, toppings\n"
                                    "2. Estimate the TOTAL portion size in grams\n"
                                    "3. Calculate macros for the ENTIRE dish shown\n\n"
                                    "Common Asian dishes guide:\n"
                                    "- Rice congee/porridge with egg+chicken (400g): ~320kcal F:8g P:18g C:45g\n"
                                    "- Chicken curry with rice (400g): ~520kcal F:14g P:28g C:65g\n"
                                    "- Pad thai (350g): ~490kcal F:16g P:22g C:62g\n"
                                    "- Tom yum soup (400ml): ~120kcal F:4g P:12g C:8g\n\n"
                                    "Reply ONLY in this exact format:\n"
                                    "DISH_EN: [full dish description including ALL main ingredients in English]\n"
                                    "DISH_RU: [полное описание блюда со ВСЕМИ основными ингредиентами на русском]\n"
                                    "CALORIES: [number]\n"
                                    "FAT: [number]\n"
                                    "PROTEIN: [number]\n"
                                    "CARBS: [number]"
                                )
                            }
                        ]
                    }]
                },
                timeout=30
            )
            print(f"Claude Vision: {r.status_code}")
            if r.status_code == 200:
                response_text = r.json()["content"][0]["text"]
                print(f"Claude Vision response: {response_text}")

                # Parse response
                lines = response_text.strip().split('\n')
                dish_en = "Dish"
                dish_ru = "Блюдо"
                calories = fat = protein = carbs = 0

                for line in lines:
                    line = line.strip()
                    if line.startswith("DISH_EN:"):
                        dish_en = line.replace("DISH_EN:", "").strip()
                    elif line.startswith("DISH_RU:"):
                        dish_ru = line.replace("DISH_RU:", "").strip()
                    elif line.startswith("DISH:"):
                        dish_en = line.replace("DISH:", "").strip()
                        dish_ru = dish_en
                    elif line.startswith("CALORIES:"):
                        try: calories = float(re.sub(r'[^\d.]', '', line.split(':')[1]))
                        except: pass
                    elif line.startswith("FAT:"):
                        try: fat = float(re.sub(r'[^\d.]', '', line.split(':')[1]))
                        except: pass
                    elif line.startswith("PROTEIN:"):
                        try: protein = float(re.sub(r'[^\d.]', '', line.split(':')[1]))
                        except: pass
                    elif line.startswith("CARBS:"):
                        try: carbs = float(re.sub(r'[^\d.]', '', line.split(':')[1]))
                        except: pass

                if calories > 0 or fat > 0 or protein > 0:
                    calc_cal = fat*9 + protein*4 + carbs*4
                    if calc_cal > 50:
                        calories = calc_cal
                    return {
                        "dishes": [dish_ru, dish_en],  # [0]=RU, [1]=EN
                        "dish_ru": dish_ru,
                        "dish_en": dish_en,
                        "calories": round(calories),
                        "fat": round(fat, 1),
                        "protein": round(protein, 1),
                        "carbs": round(carbs, 1),
                        "from_fallback": False
                    }

        # Fallback to LogMeal if no Claude key
        headers = {"Authorization": f"Bearer {LOGMEAL_TOKEN}"}
        files = {"image": ("food.jpg", image_bytes, "image/jpeg")}
        r1 = requests.post("https://api.logmeal.com/v2/image/segmentation/complete",
                           headers=headers, files=files, timeout=30)
        if r1.status_code != 200: return None
        d1 = r1.json(); image_id = d1.get("imageId")
        dish_names = [rec.get("name","") for seg in d1.get("segmentation_results",[])
                      for rec in seg.get("recognition_results",[]) if rec.get("name")]
        if not image_id: return None
        fat=prot=carbs=cal=0
        r2 = requests.post("https://api.logmeal.com/v2/nutrition/recipe/nutritionalInfo",
                           headers=headers, json={"imageId": image_id}, timeout=15)
        if r2.status_code == 200:
            n = r2.json().get("nutritional_info") or {}
            fat=float(n.get("totalFat",0) or 0); prot=float(n.get("proteins",0) or 0)
            carbs=float(n.get("totalCarbs",0) or 0); cal=float(n.get("calories",0) or 0)
        calc_cal = fat*9+prot*4+carbs*4
        if calc_cal > 0: cal = calc_cal
        from_fallback = False
        if fat==0 and prot==0 and carbs==0:
            fb = get_fallback(dish_names)
            if fb:
                fat=fb["fat"]; prot=fb["protein"]; carbs=fb["carbs"]
                cal=round(fat*9+prot*4+carbs*4); from_fallback=True
        return {"dishes": dish_names or ["Dish"], "calories": round(cal),
                "fat": round(fat,1), "protein": round(prot,1), "carbs": round(carbs,1),
                "from_fallback": from_fallback}
    except Exception as e:
        print(f"Photo analysis error: {e}"); return None

def search_food(query):
    try:
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl",
            params={"search_terms":query,"search_simple":1,"action":"process",
                    "json":1,"page_size":20,"fields":"product_name,nutriments,brands"},
            headers={"User-Agent":"KetOSBot/1.0"}, timeout=15)
        results=[]
        for p in r.json().get("products",[]):
            name=p.get("product_name","").strip()
            if not name or len(name)<2: continue
            n=p.get("nutriments",{})
            fat=round(float(n.get("fat_100g") or 0),1)
            prot=round(float(n.get("proteins_100g") or 0),1)
            carbs=round(float(n.get("carbohydrates_100g") or 0),1)
            cal=round(float(n.get("energy-kcal_100g") or 0))
            if fat==0 and prot==0 and carbs==0: continue
            brand=p.get("brands","").strip()
            display=name+(f" — {brand}" if brand and brand.lower() not in name.lower() else "")
            results.append({"name":display[:50],"fat":fat,"protein":prot,"carbs":carbs,"cal":cal})
            if len(results)>=5: break
        return results
    except Exception as e:
        print(f"Search error: {e}"); return []

def ask_claude(u, question):
    lang = u.get("lang","ru")
    fl=max(0,u["fat_target"]-u["fat"])
    pl=max(0,u["protein_target"]-u["protein"])
    cl=max(0,u["carbs_target"]-u["carbs"])
    kl=max(0,u["cal_target"]-u["calories"])

    if lang=="en":
        system=(
            f"You are KetOS — an expert keto diet and sports nutrition coach. "
            f"Answer ANY question about keto, nutrition, health, or sport. "
            f"Be specific, practical, use numbers. Max 300 words. Use bullet points.\n\n"
            f"User profile: {u.get('gender','?')}, {u.get('weight','?')}kg, "
            f"{u.get('height','?')}cm, {u.get('age','?')}y, "
            f"sport: {u.get('sport_type','?')}, goal: {u.get('goal','?')}, "
            f"keto mode: {u.get('keto_level','?')}, ketones: {u.get('ketones',0)} mmol/L\n"
            f"Today remaining: {kl}kcal | Fat:{fl}g | Protein:{pl}g | Carbs:{cl}g\n\n"
            f"Answer in English. Be direct and helpful."
        )
    else:
        system=(
            f"Ты KetOS — эксперт по кето-диете и спортивному питанию. "
            f"Отвечай на ЛЮБЫЕ вопросы про кето, питание, здоровье, спорт. "
            f"Давай конкретные ответы с цифрами. Максимум 300 слов. Используй маркированный список.\n\n"
            f"Профиль пользователя: {u.get('gender','?')}, {u.get('weight','?')}кг, "
            f"{u.get('height','?')}см, {u.get('age','?')}лет, "
            f"спорт: {u.get('sport_type','?')}, цель: {u.get('goal','?')}, "
            f"режим: {u.get('keto_level','?')}, кетоны: {u.get('ketones',0)} ммоль/л\n"
            f"Остаток сегодня: {kl}ккал | Ж:{fl}г | Б:{pl}г | У:{cl}г\n\n"
            f"Отвечай на русском. Будь конкретным и полезным."
        )

    # Try models in order
    for model in ["claude-haiku-4-5-20251001", "claude-haiku-20240307"]:
        try:
            r=requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 600,
                    "system": system,
                    "messages": [{"role":"user","content": question}]
                },
                timeout=30
            )
            print(f"Claude [{model}]: {r.status_code} | {r.text[:200]}")
            if r.status_code == 200:
                return r.json()["content"][0]["text"]
            elif r.status_code == 400:
                # Try next model
                continue
        except Exception as e:
            print(f"Claude exc: {e}")
    return None

def keto_advice_text(u, question):
    lang = u.get("lang","ru")
    q = question.lower()
    fl = max(0, u["fat_target"] - u["fat"])
    pl = max(0, u["protein_target"] - u["protein"])
    cl = max(0, u["carbs_target"] - u["carbs"])

    is_electrolytes = any(x in q for x in ["магний","magnesium","калий","potassium","электролит","electrolyte","натрий","sodium","продуктах","sources","соль","salt","зачем соль","why salt","почему соль"])
    is_ketosis  = any(x in q for x in ["кетоз","ketosis","войти","enter","ускор","speed","саун","sauna","голод","fasting","быстро","fast","24","48"])
    is_plateau  = any(x in q for x in ["плато","plateau","вес не","не худею","not losing","стоит вес","застрял","stuck"])
    is_fatigue  = any(x in q for x in ["устал","fatigue","слабост","weakness","нет энергии","no energy","нет сил","tired","вялост","кето грипп","keto flu"])
    is_training = any(x in q for x in ["трениров","train","спорт","sport","workout","упражн","exercise","силов","кардио","cardio","бег","run"])
    is_alcohol  = any(x in q for x in ["алкоголь","alcohol","вино","wine","пиво","beer","водк","whisky"])
    is_products = any(x in q for x in ["список продукт","food list","что можно","can i eat","что нельзя","forbidden","что кушать","что покупать"])
    is_food     = any(x in q for x in ["съесть сегодня","eat today","что съесть","what to eat today","план питания","meal plan","рацион на сегодня"])

    if is_electrolytes:
        if lang == "en":
            return (
                "💊 Electrolytes on Keto — Where to Find\n\n"
                "🟡 MAGNESIUM (target: 300-400mg/day):\n"
                "• Pumpkin seeds 30g → 150mg ✅\n"
                "• Almonds 30g → 80mg ✅\n"
                "• Spinach 100g → 80mg\n"
                "• Avocado 200g → 60mg\n"
                "• Supplement: Mg glycinate 200-400mg at night\n\n"
                "🔵 POTASSIUM (target: 3000-4000mg/day):\n"
                "• Avocado 200g → 900mg ✅\n"
                "• Salmon 150g → 700mg ✅\n"
                "• Spinach 100g → 500mg\n"
                "• Mushrooms 100g → 400mg\n\n"
                "🔴 SODIUM (target: 3000-5000mg/day):\n"
                "• Salt every meal (1 tsp = 2300mg)\n"
                "• Bone broth 1 cup → 900mg\n\n"
                "💡 Quick fix: bone broth + pinch of salt = instant electrolytes!"
            )
        else:
            return (
                "💊 Электролиты на кето — где взять\n\n"
                "🟡 МАГНИЙ (норма: 300-400мг/день):\n"
                "• Семечки тыквы 30г → 150мг ✅\n"
                "• Миндаль 30г → 80мг ✅\n"
                "• Шпинат 100г → 80мг\n"
                "• Авокадо 200г → 60мг\n"
                "• Добавка: Mg глицинат 200-400мг на ночь\n\n"
                "🔵 КАЛИЙ (норма: 3000-4000мг/день):\n"
                "• Авокадо 200г → 900мг ✅\n"
                "• Лосось 150г → 700мг ✅\n"
                "• Шпинат 100г → 500мг\n"
                "• Грибы 100г → 400мг\n\n"
                "🔴 НАТРИЙ (норма: 3000-5000мг/день):\n"
                "• Соль к каждому блюду (1 ч.л. = 2300мг)\n"
                "• Костный бульон 1 кружка → 900мг\n\n"
                "💡 Быстро: кружка бульона + щепотка соли = мгновенные электролиты!"
            )

    elif is_ketosis:
        if lang == "en":
            return (
                "🚀 Fast Ketosis Entry Plan (24-48h)\n\n"
                "⏰ HOUR 0-16: FASTING\n"
                "• Water, black coffee, herbal tea only\n"
                "• Zero calories — depletes glycogen\n"
                "• Add salt to water!\n\n"
                "🏃 HOUR 3-4: EXERCISE\n"
                "• 45-60 min cardio (run/bike/swim)\n"
                "• Or HIIT: 8×20 sec sprint + 40 sec rest\n\n"
                "🧖 HOUR 6-8: SAUNA\n"
                "• 3 rounds × 15 min at 80-90°C\n"
                "• Cold shower between rounds\n\n"
                "🥩 FIRST MEAL (after 16h):\n"
                "• Eggs + bacon + avocado\n"
                "• Zero carbs! MCT oil in coffee\n\n"
                "📊 Ketones: 12-24h | Optimal (1.5+): 24-48h\n\n"
                "💊 MUST: Salt + magnesium + potassium daily!"
            )
        else:
            return (
                "🚀 Быстрый вход в кетоз (24-48ч)\n\n"
                "⏰ ЧАСЫ 0-16: ГОЛОДАНИЕ\n"
                "• Вода, чёрный кофе, травяной чай\n"
                "• Ноль калорий — опустошает гликоген\n"
                "• Соль в воду!\n\n"
                "🏃 ЧАСЫ 3-4: ТРЕНИРОВКА\n"
                "• 45-60 мин кардио (бег/велик/плавание)\n"
                "• Или ВИИТ: 8×20 сек спринт + 40 сек отдых\n\n"
                "🧖 ЧАСЫ 6-8: САУНА\n"
                "• 3 захода × 15 мин при 80-90°C\n"
                "• Холодный душ между заходами\n\n"
                "🥩 ПЕРВЫЙ ПРИЁМ (после 16ч):\n"
                "• Яйца + бекон + авокадо\n"
                "• Ноль углеводов! MCT масло в кофе\n\n"
                "📊 Кетоны: через 12-24ч | Оптимальный: через 24-48ч\n\n"
                "💊 ОБЯЗАТЕЛЬНО: Соль + магний + калий каждый день!"
            )

    elif is_plateau:
        if lang == "en":
            return (
                "📉 Breaking Keto Plateau\n\n"
                "1. Check hidden carbs (sauces, spices)\n"
                "2. Fat fast 2-3 days (80% fat, 1200 kcal)\n"
                "3. Add 30 min walk daily\n"
                "4. Try 16:8 fasting (eat 12:00-20:00)\n"
                "5. Check sleep — cortisol blocks fat loss!\n"
                "6. Reduce dairy"
            )
        else:
            return (
                "📉 Как сломать плато на кето\n\n"
                "1. Проверь скрытые углеводы (соусы, специи)\n"
                "2. Жировое голодание 2-3 дня (80% жир, 1200 ккал)\n"
                "3. Добавь 30 мин прогулки каждый день\n"
                "4. Попробуй 16:8 (ешь 12:00-20:00)\n"
                "5. Проверь сон — кортизол блокирует жиросжигание!\n"
                "6. Сократи молочное"
            )

    elif is_fatigue:
        if lang == "en":
            return (
                "⚡ Fatigue on Keto\n\n"
                "MOST LIKELY: Electrolyte deficiency!\n\n"
                "✅ RIGHT NOW: Bone broth + salt + 300mg magnesium\n"
                "✅ FIRST 2 WEEKS: Normal (keto flu, lasts 3-7 days)\n"
                "✅ BEFORE WORKOUT: Coffee + MCT oil\n"
                "✅ LONG-TERM: Eat enough calories? Add more fat"
            )
        else:
            return (
                "⚡ Усталость на кето\n\n"
                "ПРИЧИНА: Нехватка электролитов!\n\n"
                "✅ ПРЯМО СЕЙЧАС: Бульон + соль + магний 300мг\n"
                "✅ ПЕРВЫЕ 2 НЕДЕЛИ: Нормально (кето-грипп, 3-7 дней)\n"
                "✅ ПЕРЕД ТРЕНИРОВКОЙ: Кофе + MCT масло\n"
                "✅ ДОЛГОСРОЧНО: Достаточно калорий? Добавь жира"
            )

    elif is_training:
        if lang == "en":
            return (
                "🏋️ Training on Keto\n\n"
                "BEFORE: Coffee + MCT oil or 2 eggs\n"
                "DURING: Water + salt + magnesium\n"
                "AFTER: 30-40g protein (chicken/fish/eggs)\n\n"
                "✅ BEST: Long cardio 60+ min, heavy strength training\n"
                "❌ First 2 weeks: avoid max intensity"
            )
        else:
            return (
                "🏋️ Тренировки на кето\n\n"
                "ДО: Кофе + MCT масло или 2 яйца\n"
                "ВО ВРЕМЯ: Вода + соль + магний\n"
                "ПОСЛЕ: 30-40г белка (курица/рыба/яйца)\n\n"
                "✅ ЛУЧШЕЕ: Длинное кардио 60+ мин, тяжёлые силовые\n"
                "❌ Первые 2 недели: избегай макс. интенсивности"
            )

    elif is_alcohol:
        if lang == "en":
            return (
                "🍷 Alcohol on Keto\n\n"
                "✅ OK: Dry wine 150ml=4g, Vodka/Whisky 50ml=0g\n"
                "❌ NO: Beer (13g+), sweet cocktails, liqueurs\n\n"
                "Rules: Eat fat+protein before, drink water\n"
                "Recovery to ketosis: 8-24h"
            )
        else:
            return (
                "🍷 Алкоголь на кето\n\n"
                "✅ МОЖНО: Сухое вино 150мл=4г, Водка/Виски 50мл=0г\n"
                "❌ НЕЛЬЗЯ: Пиво (13г+), сладкие коктейли, ликёры\n\n"
                "Правила: Ешь жир+белок до, пей воду\n"
                "Возврат в кетоз: 8-24ч"
            )

    elif is_food:
        return meal_plan_text(u)

    elif is_products:
        if lang == "en":
            return (
                "🥩 Keto Food List\n\n"
                "✅ EAT FREELY:\n"
                "• Meat: beef, pork, chicken, lamb\n"
                "• Fish: salmon, tuna, mackerel, sardines\n"
                "• Eggs (unlimited!)\n"
                "• Cheese, butter, heavy cream\n"
                "• Avocado, olives, coconut oil\n"
                "• Nuts: almonds, walnuts, macadamia\n"
                "• Greens: spinach, broccoli, zucchini\n\n"
                "⚠️ LIMIT (count carbs):\n"
                "• Berries max 80g\n"
                "• Dark chocolate 85%+ max 20g\n\n"
                "❌ AVOID:\n"
                "• Sugar, bread, pasta, rice\n"
                "• Potatoes, corn, bananas\n"
                "• Sweet drinks, juices, beer\n"
                "• Low-fat products (contain sugar!)"
            )
        else:
            return (
                "🥩 Список продуктов на кето\n\n"
                "✅ ЕШЬ СВОБОДНО:\n"
                "• Мясо: говядина, свинина, курица, баранина\n"
                "• Рыба: лосось, тунец, скумбрия, сардины\n"
                "• Яйца (без ограничений!)\n"
                "• Сыр, масло, жирные сливки\n"
                "• Авокадо, оливки, кокосовое масло\n"
                "• Орехи: миндаль, грецкие, макадамия\n"
                "• Зелень: шпинат, брокколи, кабачки\n\n"
                "⚠️ ОГРАНИЧЬ (считай углеводы):\n"
                "• Ягоды максимум 80г\n"
                "• Горький шоколад 85%+ максимум 20г\n\n"
                "❌ ИСКЛЮЧИ:\n"
                "• Сахар, хлеб, макароны, рис\n"
                "• Картошка, кукуруза, бананы\n"
                "• Сладкие напитки, соки, пиво\n"
                "• Обезжиренные продукты (содержат сахар!)"
            )

    else:
        # Smart universal answer - analyze any keto question
        if lang == "en":
            return (
                f"🤖 Keto Adviser\n\n"
                f"I didn't fully recognize your question: «{question[:50]}»\n\n"
                f"I can answer:\n"
                f"• Why salt on keto → ask 'why salt'\n"
                f"• How to enter ketosis fast\n"
                f"• Magnesium and potassium sources\n"
                f"• Training on keto\n"
                f"• Weight plateau\n"
                f"• Fatigue on keto\n"
                f"• Alcohol on keto\n"
                f"• What foods to eat\n"
                f"• What to eat today\n\n"
                f"Try rephrasing your question!"
            )
        else:
            return (
                f"🤖 Кето Советник\n\n"
                f"Я не до конца понял вопрос: «{question[:50]}»\n\n"
                f"Попробуй спросить:\n"
                f"• Зачем соль на кето?\n"
                f"• Как быстро войти в кетоз?\n"
                f"• Магний и калий в каких продуктах?\n"
                f"• Советы для тренировки на кето\n"
                f"• Как сломать плато веса?\n"
                f"• Усталость на кето — что делать?\n"
                f"• Алкоголь на кето\n"
                f"• Список продуктов на кето\n"
                f"• Что съесть сегодня?\n\n"
                f"Или переформулируй вопрос — отвечу!"
            )

def meal_plan_text(u):
    """Suggest foods based on remaining macros"""
    lang = u.get("lang","ru")
    fl=max(0,u["fat_target"]-u["fat"])
    pl=max(0,u["protein_target"]-u["protein"])
    cl=max(0,u["carbs_target"]-u["carbs"])
    kl=max(0,u["cal_target"]-u["calories"])
    if kl<=50:
        return L(u,"✅ Норма выполнена! Отличная работа!","✅ Daily goal reached! Great job!")
    pool=list(FOOD_SUGGESTIONS); plan=[]; rf=fl; rp=pl; rc=cl; rk=kl
    for _ in range(4):
        if rk<=50: break
        best=None; bs=-999
        for f in pool:
            if f in [x[0] for x in plan]: continue
            if f["carbs"]>rc+3: continue
            s=0
            if rf>5: s+=min(f["fat"],rf)*2
            if rp>5: s+=min(f["protein"],rp)*3
            if f["cal"]<=rk: s+=5
            else: s-=20
            if s>bs: bs=s; best=f
        if best and bs>0:
            plan.append((best,bs))
            rf-=best["fat"]; rp-=best["protein"]; rc-=best["carbs"]; rk-=best["cal"]
            pool.remove(best)
    if not plan:
        return L(u,"Ты уже почти у цели!","Almost at your goal!")
    if lang=="en":
        lines=[f"🥗 Meal Plan\n\nRemaining: {kl}kcal F:{fl}g P:{pl}g C:{cl}g\n\nSuggested:\n"]
        tf=tp=tc=tcal=0
        for i,(f,_) in enumerate(plan,1):
            lines.append(f"{i}. {f['en']}\n   F:{f['fat']}g P:{f['protein']}g C:{f['carbs']}g {f['cal']}kcal\n")
            tf+=f["fat"]; tp+=f["protein"]; tc+=f["carbs"]; tcal+=f["cal"]
        after=kl-tcal
        lines.append(f"\nTotal: {tcal}kcal F:{tf}g P:{tp}g C:{tc}g")
        lines.append("\n✅ Goal reached!" if after<=100 else f"\nStill needed: {after}kcal")
    else:
        lines=[f"🥗 Рацион на остаток дня\n\nОсталось: {kl}ккал Ж:{fl}г Б:{pl}г У:{cl}г\n\nРекомендую:\n"]
        tf=tp=tc=tcal=0
        for i,(f,_) in enumerate(plan,1):
            lines.append(f"{i}. {f['ru']}\n   Ж:{f['fat']}г Б:{f['protein']}г У:{f['carbs']}г {f['cal']}ккал\n")
            tf+=f["fat"]; tp+=f["protein"]; tc+=f["carbs"]; tcal+=f["cal"]
        after=kl-tcal
        lines.append(f"\nИтого: {tcal}ккал Ж:{tf}г Б:{tp}г У:{tc}г")
        lines.append("\n✅ Норма выполнена!" if after<=100 else f"\nОстанется: {after}ккал")
    return "".join(lines)
    h=max(4,int(total_carbs/15))
    if u.get("lang")=="en":
        return (f"Ketosis Recovery Plan\nAfter {total_carbs}g carbs\n\n"
                f"0-2h: Water, salt, electrolytes\n2-3h: 1 tbsp MCT oil\n"
                f"3-5h: Fast + light walk\n~{h}h: Fatty meat + veggies\n\n"
                f"Back in ketosis in {h}-{h+2}h!\nMeasure ketones in {h}h")
    return (f"Возврат в кетоз\nПосле {total_carbs}г углеводов\n\n"
            f"0-2ч: Вода, соль, электролиты\n2-3ч: MCT масло 1 ст.л.\n"
            f"3-5ч: Голодай + прогулка\n~{h}ч: Жирное мясо + овощи\n\n"
            f"Кетоз через {h}-{h+2}ч!\nИзмерь кетоны через {h}ч")

def alcohol_text(u, name, ml, carbs):
    d=round(ml/50*1.5); h=d+(8 if carbs<10 else 16 if carbs<30 else 24)
    if u.get("lang")=="en":
        sev="Moderate" if carbs<10 else "Significant" if carbs<30 else "High"
        return (f"Alcohol Recovery Plan\n{name} {ml}ml — {carbs}g carbs\n{sev} impact\n\n"
                f"Alcohol out: ~{d}h | Ketosis back: ~{h}h\n\n"
                f"Now: Water 2-3L + electrolytes\nMorning: Coffee + MCT oil\n"
                f"First meal: Eggs/meat/fish, zero carbs\n30min walk speeds recovery\n\nMeasure ketones in {h}h!")
    sev="Умеренное" if carbs<10 else "Значительное" if carbs<30 else "Сильное"
    return (f"Возврат в кетоз после алкоголя\n{name} {ml}мл — {carbs}г углеводов\n{sev} влияние\n\n"
            f"Алкоголь выйдет: ~{d}ч | Кетоз вернётся: ~{h}ч\n\n"
            f"Сейчас: Вода 2-3л + электролиты\nУтром: Кофе + MCT масло\n"
            f"Первый приём: Яйца/мясо/рыба, ноль углеводов\nПрогулка 30мин ускорит\n\nИзмерь кетоны через {h}ч!")

def profile_text(u, m):
    g=L(u,"Мужской" if u.get("gender")=="male" else "Женский",
         "Male" if u.get("gender")=="male" else "Female")
    lang=u.get("lang","ru")
    kcal=L(u,"ккал","kcal")
    if lang=="en":
        return (f"Profile created!\n\n{u['name']} | {g} | {u.get('weight',0)}kg | "
                f"{u.get('height',0)}cm | {int(u.get('age',0))}y\n"
                f"Sport: {u.get('sport_type','—')} | Goal: {u.get('goal','—')}\n"
                f"Mode: {u.get('keto_level','—')}\n\n"
                f"Daily targets:\n{m['calories']} kcal\n"
                f"Fat: {m['fat']}g | Protein: {m['protein']}g | Carbs: {m['carbs']}g\n\n"
                f"BMR: {m['bmr']} kcal | TDEE: {m['tdee']} kcal\n\nLet's go!")
    return (f"Профиль готов!\n\n{u['name']} | {g} | {u.get('weight',0)}кг | "
            f"{u.get('height',0)}см | {int(u.get('age',0))}лет\n"
            f"Спорт: {u.get('sport_type','—')} | Цель: {u.get('goal','—')}\n"
            f"Режим: {u.get('keto_level','—')}\n\n"
            f"Цели на день:\n{m['calories']} {kcal}\n"
            f"Жиры: {m['fat']}г | Белки: {m['protein']}г | Углеводы: {m['carbs']}г\n\n"
            f"BMR: {m['bmr']} {kcal} | TDEE: {m['tdee']} {kcal}\n\nПоехали!")

# ============================================================
# PHOTO HANDLER
# ============================================================

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid=msg.from_user.id; u=get_user(uid)
    bot.send_message(msg.chat.id, L(u,"Фото получено! Анализирую... (10-20 сек)",
                                      "Photo received! Analyzing... (10-20 sec)"))
    try:
        fi=bot.get_file(msg.photo[-1].file_id)
        image_bytes=requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fi.file_path}",timeout=10).content
    except Exception as e:
        print(f"DL err: {e}")
        bot.send_message(msg.chat.id,L(u,"Ошибка загрузки","Download error"),reply_markup=main_kb(u.get("lang","ru")))
        return

    def do():
        try:
            result=analyze_photo(image_bytes)
            if not result or (result["calories"]==0 and result["fat"]==0):
                bot.send_message(msg.chat.id,
                    L(u,"Не удалось распознать. Введи вручную.","Could not recognize. Enter manually."),
                    reply_markup=main_kb(u.get("lang","ru")))
                set_state(uid,"menu"); return
            u["pending_food"]=result; set_state(uid,"confirm_photo")
            # Show dish name in correct language
            if u.get("lang") == "en":
                dish_name = result.get("dish_en") or result["dishes"][1] if len(result["dishes"])>1 else result["dishes"][0]
            else:
                dish_name = result.get("dish_ru") or result["dishes"][0]
            warn=L(u,"Много углеводов!","High carbs!") if result["carbs"]>10 else L(u,"Кето-дружественно","Keto-friendly")
            note=L(u,"\n⚠️ Макросы примерные — скорректируй если нужно",
                     "\n⚠️ Macros approximate — correct if needed") if result.get("from_fallback") else ""
            bot.send_message(msg.chat.id,
                f"{L(u,'Результат анализа','Analysis result')}:\n\n"
                f"{L(u,'Блюдо','Dish')}: {dish_name}\n\n"
                f"{L(u,'Калории','Calories')}: {result['calories']} {L(u,'ккал','kcal')}\n"
                f"{L(u,'Жиры','Fat')}: {result['fat']}г | "
                f"{L(u,'Белки','Protein')}: {result['protein']}г | "
                f"{L(u,'Углеводы','Carbs')}: {result['carbs']}г\n\n"
                f"{warn}{note}\n\n{L(u,'Всё верно?','Is this correct?')}",
                reply_markup=confirm_photo_kb(u.get("lang","ru")))
        except Exception as e:
            print(f"Photo err: {e}")
            bot.send_message(msg.chat.id,L(u,"Ошибка анализа.","Analysis error."),
                             reply_markup=main_kb(u.get("lang","ru")))
            set_state(uid,"menu")
    threading.Thread(target=do, daemon=True).start()

# ============================================================
# MAIN HANDLER
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid=msg.from_user.id; u=get_user(uid)
    set_state(uid,"ask_lang")
    bot.send_message(msg.chat.id,
        "Zona Ketoza — Keto for athletes\n\nChoose language / Выбери язык:",
        reply_markup=lang_kb())

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid=msg.from_user.id; u=get_user(uid)
    text=msg.text.strip() if msg.text else ""
    state=get_state(uid)
    lang=u.get("lang","ru")

    # ===== GLOBAL BACK — works from ANY state =====
    # Check multiple ways - strip all unicode variations
    text_clean = text.replace("◀","").replace("◄","").replace("←","").strip().lower()
    is_back = (text in [BACK_RU, BACK_EN] or
               text_clean in ["главное меню", "main menu", "перезапуск", "restart"] or
               "главное меню" in text.lower() or "main menu" in text.lower())
    if is_back:
        set_state(uid,"menu")
        bot.send_message(msg.chat.id, L(u,"Главное меню:","Main menu:"), reply_markup=main_kb(lang))
        return

    # ===== LANGUAGE — before EN_TO_RU =====
    if text in ["Язык / Language","Language"] or state in ["ask_lang","switch_lang"]:
        if text in ["Язык / Language","Language"]:
            set_state(uid,"switch_lang")
            bot.send_message(msg.chat.id,"Choose / Выбери:",reply_markup=lang_kb()); return
        if text=="English":
            u["lang"]="en"
            if is_registered(u):
                set_state(uid,"menu")
                bot.send_message(msg.chat.id,"Language set to English!",reply_markup=main_kb("en"))
            else:
                set_state(uid,"ask_name")
                bot.send_message(msg.chat.id,"Welcome to Zona Ketoza! What's your name?",reply_markup=types.ReplyKeyboardRemove())
            return
        if text=="Русский":
            u["lang"]="ru"
            if is_registered(u):
                set_state(uid,"menu")
                bot.send_message(msg.chat.id,"Язык изменён на русский!",reply_markup=main_kb("ru"))
            else:
                set_state(uid,"ask_name")
                bot.send_message(msg.chat.id,"Добро пожаловать в Зону Кетоза! 🔥 Как тебя зовут?",reply_markup=types.ReplyKeyboardRemove())
            return
        if state in ["ask_lang","switch_lang"]:
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,L(u,"Главное меню:","Main menu:"),reply_markup=main_kb(lang)); return

    # ===== EN → RU translation =====
    EN_TO_RU = {
        "My status":"Мой статус","Food diary":"Дневник","Photo meal":"Фото блюда",
        "Add food":"Ввести еду","Search product":"Поиск продукта","Sport":"Спорт",
        "Alcohol":"Алкоголь","Ketones":"Кетоны","Keto Adviser":"Кето Советник",
        "Family":"Семья","Settings":"Настройки",
        "Trail / Run":"Трейл / Бег","Cycling race":"Велогонка","Triathlon":"Триатлон",
        "Skiing":"Лыжи","Strength":"Силовая","Back to ketosis":"Возврат в кетоз",
        "Ketosis recovery plan":"План возврата в кетоз",
        "Add to diary":"Добавить в дневник","Correct":"Скорректировать","Cancel":"Отмена",
        "Change weight / height / age":"Изменить вес / рост / возраст",
        "Change goal":"Изменить цель","Change gender":"Изменить пол",
        "Change diet mode":"Изменить режим питания",
        "Change targets manually":"Изменить цели вручную",
        "Recalculate automatically":"Пересчитать автоматически","Reset day":"Сбросить день",
        "Female":"Женский","Male":"Мужской",
        "What to eat today?":"Что съесть сегодня?",
        "How to speed up ketosis?":"Как ускорить вход в кетоз?",
        "Training tips on keto":"Советы для тренировки на кето",
        "Ask another question":"Задать ещё вопрос",
    }
    if text in EN_TO_RU:
        text = EN_TO_RU[text]

    # ===== ONBOARDING =====
    if state=="ask_name":
        u["name"]=text; set_state(uid,"ask_gender")
        bot.send_message(msg.chat.id,
            L(u,f"Привет, {text}! Твой пол?",f"Hi, {text}! Your gender?"),
            reply_markup=gender_kb(lang)); return

    if state=="ask_gender":
        u["gender"]="male" if "Мужской" in text or "Male" in text else "female"
        set_state(uid,"ask_weight")
        bot.send_message(msg.chat.id,L(u,"Вес в кг:","Weight in kg:"),reply_markup=weight_kb(lang)); return

    if state=="ask_weight":
        try:
            u["weight"]=float(re.sub(r'[^\d.]','',text) or '70')
            set_state(uid,"ask_height")
            bot.send_message(msg.chat.id,L(u,"Рост в см:","Height in cm:"),reply_markup=height_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Введи число (например 65)","Enter number (e.g. 65)"))
        return

    if state=="ask_height":
        try:
            u["height"]=float(re.sub(r'[^\d.]','',text) or '170')
            set_state(uid,"ask_age")
            bot.send_message(msg.chat.id,L(u,"Возраст:","Age:"),reply_markup=age_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Введи число (например 170)","Enter number (e.g. 170)"))
        return

    if state=="ask_age":
        try:
            u["age"]=float(re.sub(r'[^\d.]','',text) or '30')
            set_state(uid,"ask_activity")
            bot.send_message(msg.chat.id,L(u,"Уровень активности:","Activity level:"),reply_markup=activity_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Введи число (например 30)","Enter number (e.g. 30)"))
        return

    if state=="ask_activity":
        u["activity"]=text; u["activity_coef"]=ACTIVITY_MAP.get(text,1.55)
        set_state(uid,"ask_sport")
        bot.send_message(msg.chat.id,L(u,"Вид спорта:","Main sport:"),reply_markup=sport_onboard_kb(lang)); return

    if state=="ask_sport":
        u["sport_type"]=text; set_state(uid,"ask_goal")
        bot.send_message(msg.chat.id,L(u,"Главная цель:","Main goal:"),reply_markup=goal_kb(lang)); return

    if state=="ask_goal":
        u["goal"]=text; m=calc_macros(u); u["cal_target"]=m["calories"]
        set_state(uid,"ask_keto_level")
        bot.send_message(msg.chat.id,
            L(u,f"Калории: {m['calories']} ккал/день\n\nВыбери режим:",
                f"Calories: {m['calories']} kcal/day\n\nChoose mode:"),
            reply_markup=keto_level_kb(lang)); return

    if state=="ask_keto_level":
        if text in ["Ручной ввод","Manual input"]:
            set_state(uid,"manual_targets_onboard")
            m=calc_macros(u)
            bot.send_message(msg.chat.id,
                L(u,f"Расчёт: {m['calories']} ккал\nВведи через пробел: калории жиры белки углеводы\nПример: 1600 125 100 20",
                    f"Calculated: {m['calories']} kcal\nEnter: calories fat protein carbs\nExample: 1600 125 100 20"),
                reply_markup=back_kb(lang)); return
        level=KETO_MAP.get(text,"Normal keto")
        u["keto_level"]=level; m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,profile_text(u,m),reply_markup=main_kb(lang)); return

    if state=="manual_targets_onboard":
        try:
            nums=[int(x) for x in text.split() if x.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]
            u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="Manual"; set_state(uid,"menu")
            m={"calories":u["cal_target"],"fat":u["fat_target"],
               "protein":u["protein_target"],"carbs":u["carbs_target"],"bmr":0,"tdee":u["cal_target"]}
            bot.send_message(msg.chat.id,profile_text(u,m),reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: 1600 125 100 20","Example: 1600 125 100 20"))
        return

    # ===== STATUS =====
    if text=="Мой статус":
        k=u["ketones"]
        if k==0:   ks=L(u,"Не измерено","Not measured")
        elif k<0.5:ks=L(u,"Не в кетозе","Not in ketosis")
        elif k<1.5:ks=L(u,"Лёгкий кетоз","Light ketosis")
        elif k<3:  ks=L(u,"Оптимальный кетоз!","Optimal ketosis!")
        else:      ks=L(u,"Глубокий кетоз","Deep ketosis")
        bot.send_message(msg.chat.id,
            f"{L(u,'Статус','Status')}\n\n{ks} ({k} mmol/L)\n\n"
            f"Cal:  {bar(u['calories'],u['cal_target'])} {u['calories']}/{u['cal_target']}\n"
            f"Fat:  {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}g\n"
            f"Prot: {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}g\n"
            f"Carb: {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}g",
            reply_markup=main_kb(lang)); return

    if text=="Дневник":
        meals=u["meals"]
        mt="\n".join(f"{i+1}. {m}" for i,m in enumerate(meals)) if meals else L(u,"Пусто","Empty")
        bot.send_message(msg.chat.id,
            f"{L(u,'Дневник','Food diary')}\n\n{mt}\n\n"
            f"{u['calories']}kcal | F:{u['fat']}g P:{u['protein']}g C:{u['carbs']}g",
            reply_markup=main_kb(lang)); return

    # ===== PHOTO =====
    if text=="Фото блюда":
        set_state(uid,"waiting_photo")
        bot.send_message(msg.chat.id,
            L(u,"Отправь фото блюда — AI посчитает КБЖУ!","Send a photo — AI will calculate macros!"),
            reply_markup=back_kb(lang)); return

    # ===== FOOD INPUT =====
    if text=="Ввести еду":
        set_state(uid,"manual_food")
        bot.send_message(msg.chat.id,
            L(u,"Напиши: название жиры белки углеводы\n\nПримеры:\nтворог 5 18 3\nкурица 200г 2 30 0",
                "Write: name fat protein carbs\n\nExamples:\ncottage cheese 5 18 3\nchicken 200g 2 30 0"),
            reply_markup=back_kb(lang)); return

    if state=="manual_food":
        try:
            parts=text.strip().split(); nums=[]; name_parts=[]; amount=""
            for p in parts:
                clean=re.sub(r'[гГмлМ]+$','',p)
                if clean.replace('.','').isdigit():
                    if any(p.lower().endswith(s) for s in ['г','мл','g','ml']): amount=p
                    else: nums.append(int(float(clean)))
                else: name_parts.append(p)
            if len(nums)<3: raise ValueError()
            name=" ".join(name_parts) or L(u,"Блюдо","Dish")
            name=name[0].upper()+name[1:]
            fat=nums[0]; prot=nums[1]; carbs=nums[2]; cal=fat*9+prot*4+carbs*4
            al=f" {amount}" if amount else ""
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name}{al} F{fat} P{prot} C{carbs} {cal}kcal")
            cl=u["carbs_target"]-u["carbs"]
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{name}{al} {L(u,'добавлено','added')}!\nF+{fat}g P+{prot}g C+{carbs}g {cal}kcal\n"
                f"{L(u,'Осталось углеводов','Carbs left')}: {max(cl,0)}g",
                reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: творог 5 18 3","Example: cottage cheese 5 18 3"))
        return

    # ===== SEARCH =====
    if text=="Поиск продукта":
        set_state(uid,"search_food")
        bot.send_message(msg.chat.id,L(u,"Напиши название продукта:","Enter product name:"),
                         reply_markup=back_kb(lang)); return

    if state=="search_food":
        bot.send_message(msg.chat.id,L(u,f"Ищу {text}...",f"Searching {text}..."))
        results=search_food(text)
        tr={"колбаса":"sausage","творог":"cottage cheese","гречка":"buckwheat",
            "курица":"chicken","говядина":"beef","рыба":"fish","картошка":"potato"}
        if not results:
            eng=tr.get(text.lower())
            if eng: results=search_food(eng)
        if not results:
            bot.send_message(msg.chat.id,L(u,"Не найдено.","Not found."),reply_markup=main_kb(lang))
            set_state(uid,"menu"); return
        u["search_results"]=results
        resp=L(u,f"Найдено {len(results)} (на 100г):\n\n",f"Found {len(results)} (per 100g):\n\n")
        for i,p in enumerate(results,1):
            resp+=f"{i}. {p['name']}\n   F:{p['fat']}g P:{p['protein']}g C:{p['carbs']}g {p['cal']}kcal\n\n"
        resp+=L(u,"Напиши номер:","Enter number:")
        set_state(uid,"choose_food")
        bot.send_message(msg.chat.id,resp,reply_markup=choice_kb(len(results),lang)); return

    if state=="choose_food":
        if text.isdigit():
            idx=int(text)-1; results=u.get("search_results",[])
            if 0<=idx<len(results):
                u["pending_search_food"]=results[idx]; set_state(uid,"ask_food_grams")
                f=results[idx]
                bot.send_message(msg.chat.id,
                    f"{f['name']}\nPer 100g: F:{f['fat']}g P:{f['protein']}g C:{f['carbs']}g {f['cal']}kcal\n\n"
                    f"{L(u,'Сколько грамм?','How many grams?')}",
                    reply_markup=back_kb(lang))
        return

    if state=="ask_food_grams":
        try:
            grams=float(re.sub(r'[^\d.]','',text) or '100')
            f=u.get("pending_search_food",{}); r=grams/100
            fat=round(f["fat"]*r,1); prot=round(f["protein"]*r,1)
            carbs=round(f["carbs"]*r,1); cal=round(f["cal"]*r)
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{f['name'][:25]} {int(grams)}g {cal}kcal")
            cl=u["carbs_target"]-u["carbs"]; set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{f['name'][:40]} {int(grams)}g {L(u,'добавлено','added')}!\n"
                f"F+{fat}g P+{prot}g C+{carbs}g {cal}kcal\n"
                f"{L(u,'Осталось','Left')}: {max(round(cl),0)}g",
                reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Введи число (например 150)","Enter number (e.g. 150)"))
        return

    # ===== PHOTO CONFIRM =====
    if state=="confirm_photo":
        if text in ["Добавить в дневник","Add to diary"]:
            f=u.get("pending_food")
            if f:
                u["fat"]+=f["fat"]; u["protein"]+=f["protein"]
                u["carbs"]+=f["carbs"]; u["calories"]+=f["calories"]
                d=", ".join(f["dishes"][:2])
                u["meals"].append(f"{d[:25]} photo {f['calories']}kcal")
                cl=u["carbs_target"]-u["carbs"]; u["pending_food"]=None; set_state(uid,"menu")
                bot.send_message(msg.chat.id,
                    f"{L(u,'Добавлено!','Added!')} {f['calories']}kcal\n"
                    f"{L(u,'Осталось углеводов','Carbs left')}: {max(cl,0)}g",
                    reply_markup=main_kb(lang))
            return
        if text in ["Скорректировать","Correct"]:
            f=u.get("pending_food"); set_state(uid,"correct_photo")
            bot.send_message(msg.chat.id,
                f"F:{f['fat']}g P:{f['protein']}g C:{f['carbs']}g {f['calories']}kcal\n\n"
                f"{L(u,'Напиши: название жиры белки углеводы','Write: name fat protein carbs')}\n"
                f"{L(u,'Пример: суп 8 12 15','Example: soup 8 12 15')}",
                reply_markup=back_kb(lang)); return
        if text in ["Отмена","Cancel"]:
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id,L(u,"Отменено.","Cancelled."),reply_markup=main_kb(lang)); return

    if state=="correct_photo":
        try:
            parts=text.strip().split(); nums=[]; name_parts=[]
            for p in parts:
                clean=re.sub(r'[гГмлМ,]+$','',p)
                if clean.replace('.','').isdigit(): nums.append(int(float(clean)))
                else: name_parts.append(p)
            if len(nums)<3: raise ValueError()
            name=" ".join(name_parts) or L(u,"Блюдо","Dish")
            name=name[0].upper()+name[1:]
            fat=nums[0]; prot=nums[1]; carbs=nums[2]; cal=fat*9+prot*4+carbs*4
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name} F{fat} P{prot} C{carbs} {cal}kcal")
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{name} {L(u,'добавлено','added')}! F:{fat}g P:{prot}g C:{carbs}g {cal}kcal",
                reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: суп 8 12 15","Example: soup 8 12 15"))
        return

    # ===== KETONES =====
    if text=="Кетоны":
        set_state(uid,"ketones")
        bot.send_message(msg.chat.id,
            L(u,"Введи уровень кетонов (ммоль/л)\nНапример: 1.8","Enter ketone level (mmol/L)\nE.g.: 1.8"),
            reply_markup=back_kb(lang)); return

    if state=="ketones":
        try:
            val=float(text.replace(",","."))
            u["ketones"]=val
            if val<0.5:   s=L(u,"Не в кетозе. Сократи углеводы.","Not in ketosis. Cut carbs.")
            elif val<1.5: s=L(u,"Лёгкий кетоз. Уменьши углеводы.","Light ketosis. Reduce carbs.")
            elif val<3:   s=L(u,"Оптимальный кетоз! Продолжай!","Optimal ketosis! Keep going!")
            else:         s=L(u,"Глубокий кетоз. Пей воду.","Deep ketosis. Drink water.")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,f"{val} mmol/L — {s}",reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Введи число (например 1.8)","Enter number (e.g. 1.8)"))
        return

    # ===== ALCOHOL =====
    if text=="Алкоголь":
        set_state(uid,"choose_alcohol")
        bot.send_message(msg.chat.id,L(u,"Что пил?","What did you drink?"),reply_markup=alcohol_kb(lang)); return

    if state=="choose_alcohol":
        if text=="Ввести вручную":
            set_state(uid,"manual_alcohol")
            bot.send_message(msg.chat.id,
                L(u,"Напиши: название мл углеводы\nПример: Пиво 500 20",
                    "Write: name ml carbs\nExample: Beer 500 20"),
                reply_markup=back_kb(lang)); return
        drink=ALCOHOL_DB.get(text)
        if drink:
            u["pending_alcohol"]=drink; set_state(uid,"ask_alcohol_amount")
            bot.send_message(msg.chat.id,
                f"{drink['name']}\n{L(u,'Сколько порций?','How many servings?')}",
                reply_markup=portions_kb(lang)); return

    if state=="ask_alcohol_amount":
        drink=u.get("pending_alcohol",{})
        try:
            qty=int(re.sub(r'[^\d]','',text) or '1'); qty=max(1,min(qty,5))
            ml=drink["ml"]*qty; carbs=drink["carbs"]*qty
            u["carbs"]+=carbs; u["calories"]+=carbs*4
            u["meals"].append(f"{drink['name']} x{qty} {carbs}g carbs")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,alcohol_text(u,drink["name"],ml,carbs),reply_markup=main_kb(lang))
        except:
            set_state(uid,"menu"); bot.send_message(msg.chat.id,L(u,"Используй кнопки","Use buttons"),reply_markup=main_kb(lang))
        return

    if state=="manual_alcohol":
        try:
            parts=text.split(); name=parts[0]; ml=int(parts[1]); carbs=int(parts[2])
            u["carbs"]+=carbs; u["calories"]+=carbs*4
            u["meals"].append(f"{name} {ml}ml {carbs}g carbs")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,alcohol_text(u,name,ml,carbs),reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: Пиво 500 20","Example: Beer 500 20"))
        return

    # ===== SPORT =====
    if text=="Спорт":
        set_state(uid,"sport")
        bot.send_message(msg.chat.id,L(u,"Выбери активность:","Choose activity:"),reply_markup=sport_kb(lang)); return

    if text in ["Возврат в кетоз","План возврата в кетоз"]:
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,recovery_text(u,u.get("last_gel_carbs",60)),reply_markup=main_kb(lang)); return

    if text=="Силовая":
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            L(u,"Силовая на кето:\nДо: MCT масло + кофе\nВо время: вода + соль\nПосле: 30-40г белка",
                "Strength on keto:\nBefore: MCT oil + coffee\nDuring: water + salt\nAfter: 30-40g protein"),
            reply_markup=main_kb(lang)); return

    if text in ["Трейл / Бег","Велогонка","Триатлон","Лыжи"]:
        u["sport_type_race"]=text; set_state(uid,"ask_distance")
        bot.send_message(msg.chat.id,
            L(u,"Дистанция или время?\nПример: 42 км или 3 часа","Distance or time?\nExample: 42 km or 3 hours"),
            reply_markup=back_kb(lang)); return

    if state=="ask_distance":
        try:
            t2=text.lower()
            if "час" in t2 or "h" in t2: hours=float(''.join(c for c in t2 if c.isdigit() or c=='.'))
            elif "км" in t2 or "km" in t2: hours=float(''.join(c for c in t2 if c.isdigit() or c=='.'))/10
            else: hours=2
            gels=max(1,int(hours/1.5)); total=gels*20; u["last_gel_carbs"]=total
            lines=[L(u,f"Протокол гелей\n{text} (~{int(hours)}ч)\nГелей: {gels}\n",
                       f"Gel protocol\n{text} (~{int(hours)}h)\nGels: {gels}\n")]
            times=[0,0.4,0.7,0.9]
            for i in range(gels):
                tm=int(hours*times[min(i,3)]*60)
                lbl=L(u,"За 30 мин до старта","30 min before") if i==0 else L(u,f"Через {tm} мин",f"At {tm} min")
                lines.append(f"{lbl}: Gel #{i+1} 20g\n")
            lines.append(L(u,f"\nИтого: {total}г\nВозврат: ~{max(4,int(total/15))} часов",
                             f"\nTotal: {total}g\nBack to ketosis: ~{max(4,int(total/15))}h"))
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,"".join(lines),reply_markup=after_gel_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: 42 км или 3 часа","Example: 42 km or 3 hours"))
        return

    # ===== KETO ADVISER =====
    if text=="Кето Советник":
        set_state(uid,"ai_chat")
        bot.send_message(msg.chat.id,
            L(u,"🤖 Кето Советник\n\nЗадай любой вопрос про кето!\nИли выбери готовый:",
                "🤖 Keto Adviser\n\nAsk any keto question!\nOr choose ready:"),
            reply_markup=ai_kb(lang)); return

    if state in ["ai_chat","ai_chat_response"]:
        QUICK = {
            "Что съесть сегодня?": L(u,
                "Что мне съесть сегодня? Дай конкретные продукты с граммами исходя из остатка макросов.",
                "What should I eat today? Give specific foods with grams based on remaining macros."),
            "Как ускорить вход в кетоз?": L(u,
                "Как быстро войти в кетоз за 24-48 часов? Дай конкретный план: голодание (сколько часов), тип тренировки и длительность, сауна (температура и время), что есть. Укажи временные рамки для каждого шага.",
                "How to enter ketosis fast in 24-48 hours? Give specific plan: fasting (hours), exercise type and duration, sauna (temp and time), what to eat. Give timeframe for each step."),
            "Советы для тренировки на кето": L(u,
                "Дай конкретные советы для тренировки на кето. Что есть до и после, какой тип тренировки лучший, как не терять мышцы.",
                "Give specific training tips on keto. What to eat before and after, best workout type, how to preserve muscle."),
        }
        if text in ["Задать ещё вопрос","Ask another question"]:
            set_state(uid,"ai_chat")
            bot.send_message(msg.chat.id,L(u,"Задай вопрос:","Ask your question:"),reply_markup=ai_kb(lang)); return

        actual=QUICK.get(text,text)
        bot.send_message(msg.chat.id,L(u,"⏳ Думаю...","⏳ Thinking..."))

        def do_ai(q=actual, usr=u, uid_=uid, lng=lang):
            try:
                response=None
                if ANTHROPIC_API_KEY:
                    response=ask_claude(usr,q)
                if response:
                    bot.send_message(msg.chat.id,f"🤖 {response}",reply_markup=ai_after_kb(lng))
                    set_state(uid_,"ai_chat_response")
                else:
                    # Use built-in specific advice
                    advice = keto_advice_text(usr, q)
                    bot.send_message(msg.chat.id, advice, reply_markup=ai_after_kb(lng))
                    set_state(uid_,"ai_chat_response")
            except Exception as e:
                print(f"AI err: {e}")
                bot.send_message(msg.chat.id,L(usr,"Ошибка.","Error."),reply_markup=main_kb(lng))
                set_state(uid_,"menu")

        threading.Thread(target=do_ai, daemon=True).start()
        return

    # ===== FAMILY =====
    if text=="Семья":
        meals=u["meals"]; mt="\n".join(f"• {m}" for m in meals) if meals else L(u,"Пусто","Empty")
        bot.send_message(msg.chat.id,
            f"{L(u,'Семейный режим','Family mode')}\nhttps://t.me/ketOSzoneBot?start=family_{uid}\n\n{mt}",
            reply_markup=main_kb(lang)); return

    # ===== SETTINGS =====
    if text=="Настройки":
        g=L(u,"Мужской" if u.get("gender")=="male" else "Женский",
             "Male" if u.get("gender")=="male" else "Female")
        goal_now=u.get("goal") or L(u,"Не указана","Not set")
        bot.send_message(msg.chat.id,
            f"{L(u,'Настройки','Settings')}\n\n{u.get('name','—')} | {g}\n"
            f"{u.get('weight',0)}kg | {u.get('height',0)}cm | {int(u.get('age',0))}y\n"
            f"Goal: {goal_now} | Mode: {u.get('keto_level','—')}\n\n"
            f"{u['cal_target']}kcal | F:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g",
            reply_markup=settings_kb(lang)); return

    if text=="Изменить пол":
        set_state(uid,"change_gender")
        g=L(u,"Мужской" if u.get("gender")=="male" else "Женский",
             "Male" if u.get("gender")=="male" else "Female")
        bot.send_message(msg.chat.id,f"{L(u,'Текущий','Current')}: {g}",reply_markup=gender_kb(lang)); return

    if state=="change_gender":
        u["gender"]="male" if "Мужской" in text or "Male" in text else "female"
        m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Пол обновлён','Gender updated')}!\n{m['calories']}kcal F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g",
            reply_markup=main_kb(lang)); return

    if text=="Изменить вес / рост / возраст":
        set_state(uid,"edit_weight")
        bot.send_message(msg.chat.id,
            L(u,"Введи через пробел: вес рост возраст\nПример: 68 166 49",
                "Enter: weight height age\nExample: 68 166 49"),
            reply_markup=back_kb(lang)); return

    if state=="edit_weight":
        try:
            nums=[float(x) for x in text.split() if re.sub(r'[^\d.]','',x)]
            if len(nums)<3: raise ValueError()
            u["weight"]=nums[0]; u["height"]=nums[1]; u["age"]=nums[2]
            m=apply_macros(u); set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{L(u,'Обновлено','Updated')}! {u['weight']}kg {u['height']}cm {int(u['age'])}y\n"
                f"{m['calories']}kcal F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\nBMR:{m['bmr']} TDEE:{m['tdee']}",
                reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: 68 166 49","Example: 68 166 49"))
        return

    if text=="Изменить цель":
        set_state(uid,"change_goal")
        bot.send_message(msg.chat.id,
            L(u,f"Текущая цель: {u.get('goal','—')}\nВыбери новую:",
                f"Current goal: {u.get('goal','—')}\nChoose new:"),
            reply_markup=goal_kb(lang)); return

    if state=="change_goal":
        u["goal"]=text; m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Цель обновлена','Goal updated')}: {text}\n"
            f"{m['calories']}kcal F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g",
            reply_markup=main_kb(lang)); return

    if text=="Изменить режим питания":
        set_state(uid,"change_keto")
        bot.send_message(msg.chat.id,L(u,"Выбери режим:","Choose mode:"),reply_markup=keto_level_kb(lang)); return

    if state=="change_keto":
        if text in ["Ручной ввод","Manual input"]:
            set_state(uid,"edit_targets"); bot.send_message(msg.chat.id,
                L(u,"Введи: калории жиры белки углеводы\nПример: 1600 125 100 20",
                    "Enter: calories fat protein carbs\nExample: 1600 125 100 20"),
                reply_markup=back_kb(lang)); return
        level=KETO_MAP.get(text)
        if level:
            u["keto_level"]=level; m=apply_macros(u); set_state(uid,"menu")
            bot.send_message(msg.chat.id,f"{level}\nF:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g",
                             reply_markup=main_kb(lang)); return

    if text=="Изменить цели вручную":
        set_state(uid,"edit_targets")
        bot.send_message(msg.chat.id,
            L(u,f"Сейчас: {u['cal_target']} F:{u['fat_target']} P:{u['protein_target']} C:{u['carbs_target']}\nВведи: калории жиры белки углеводы",
                f"Now: {u['cal_target']} F:{u['fat_target']} P:{u['protein_target']} C:{u['carbs_target']}\nEnter: calories fat protein carbs"),
            reply_markup=back_kb(lang)); return

    if state=="edit_targets":
        try:
            nums=[int(x) for x in text.split() if x.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]
            u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="Manual"; set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{L(u,'Цели обновлены','Targets updated')}!\n{u['cal_target']}kcal F:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g",
                reply_markup=main_kb(lang))
        except:
            bot.send_message(msg.chat.id,L(u,"Пример: 1600 125 100 20","Example: 1600 125 100 20"))
        return

    if text=="Пересчитать автоматически":
        if not u.get("goal"):
            set_state(uid,"change_goal")
            bot.send_message(msg.chat.id,L(u,"Выбери цель:","Choose goal:"),reply_markup=goal_kb(lang)); return
        m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Пересчитано','Recalculated')}! {m['calories']}kcal F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\nBMR:{m['bmr']} TDEE:{m['tdee']}",
            reply_markup=main_kb(lang)); return

    if text=="Сбросить день":
        u["fat"]=u["protein"]=u["carbs"]=u["calories"]=0; u["meals"]=[]
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,L(u,"День сброшен!","Day reset!"),reply_markup=main_kb(lang)); return

    # ===== FALLBACK =====
    set_state(uid,"menu")
    bot.send_message(msg.chat.id,L(u,"Используй кнопки меню","Use menu buttons"),reply_markup=main_kb(lang))

print("KetOS bot started!")
bot.polling(none_stop=True, interval=0, timeout=20)
