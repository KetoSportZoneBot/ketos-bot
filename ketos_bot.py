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

# ============================================================
# USER
# ============================================================

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "name": "", "weight": 70.0, "height": 170.0, "age": 30.0,
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

# ============================================================
# CALC
# ============================================================

def calc_macros(u):
    w = float(u.get("weight", 70))
    h = float(u.get("height", 170))
    a = float(u.get("age", 30))
    coef = float(u.get("activity_coef", 1.55))
    gender = u.get("gender", "female")
    bmr = (10*w + 6.25*h - 5*a + 5) if gender == "male" else (10*w + 6.25*h - 5*a - 161)
    tdee = round(bmr * coef)
    goal = u.get("goal", "")
    if "loss" in goal.lower() or "худ" in goal.lower():
        cal = tdee - 500
    elif "gain" in goal.lower() or "набор" in goal.lower():
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
# KEYBOARDS  — NO PROBLEMATIC EMOJI IN BUTTON TEXT
# ============================================================

def main_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("My status", "Food diary")
        kb.row("Photo meal", "Add food")
        kb.row("Search product", "Sport")
        kb.row("Alcohol", "Ketones")
        kb.row("AI Adviser")
        kb.row("Family", "Settings")
        kb.row("Language", "Restart")
    else:
        kb.row("Мой статус", "Дневник")
        kb.row("Фото блюда", "Ввести еду")
        kb.row("Поиск продукта", "Спорт")
        kb.row("Алкоголь", "Кетоны")
        kb.row("ИИ Советник")
        kb.row("Семья", "Настройки")
        kb.row("Язык / Language", "Перезапуск")
    return kb

def gender_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Female", "Male")
        kb.row("Main menu")
    else:
        kb.row("Женский", "Мужской")
        kb.row("Главное меню")
    return kb

def weight_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("50", "55", "60", "65")
    kb.row("70", "75", "80", "85")
    kb.row("90", "95", "100", "110")
    if lang == "en":
        kb.row("Main menu")
    else:
        kb.row("Главное меню")
    return kb

def height_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("155", "160", "165", "170")
    kb.row("175", "180", "185", "190")
    return kb

def age_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("20", "25", "30", "35")
    kb.row("40", "45", "50", "55")
    return kb

def activity_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Sedentary")
        kb.row("Light (1-3x/week)")
        kb.row("Moderate (3-5x/week)")
        kb.row("High (6-7x/week)")
        kb.row("Pro athlete")
    else:
        kb.row("Минимум (сидячий)")
        kb.row("Лёгкая (1-3 раза/нед)")
        kb.row("Умеренная (3-5 раз/нед)")
        kb.row("Высокая (6-7 раз/нед)")
        kb.row("Проф. спорт")
    return kb

def sport_kb_onboard(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Running / Trail", "Cycling")
        kb.row("Swimming", "Strength")
        kb.row("Skiing / Triathlon", "Other")
    else:
        kb.row("Бег / Трейл", "Велоспорт")
        kb.row("Плавание", "Силовые")
        kb.row("Лыжи / Триатлон", "Другое")
    return kb

def goal_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Weight loss", "Muscle gain")
        kb.row("Performance", "Maintenance")
    else:
        kb.row("Похудение", "Набор мышц")
        kb.row("Производительность", "Поддержание")
    return kb

def keto_level_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Strict keto")
        kb.row("Normal keto")
        kb.row("Low-carb")
        kb.row("Manual input")
    else:
        kb.row("Строгое кето")
        kb.row("Нормальное кето")
        kb.row("Низкоуглеводная")
        kb.row("Ручной ввод")
    return kb

def sport_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Trail / Run", "Cycling race")
        kb.row("Triathlon", "Skiing")
        kb.row("Strength", "Back to ketosis")
        kb.row("Alcohol", "Main menu")
    else:
        kb.row("Трейл / Бег", "Велогонка")
        kb.row("Триатлон", "Лыжи")
        kb.row("Силовая", "Возврат в кетоз")
        kb.row("Алкоголь", "Главное меню")
    return kb

def after_gel_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Ketosis recovery plan")
        kb.row("My status", "Main menu")
    else:
        kb.row("План возврата в кетоз")
        kb.row("Мой статус", "Главное меню")
    return kb

def confirm_photo_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Add to diary", "Correct")
        kb.row("Cancel")
    else:
        kb.row("Добавить в дневник", "Скорректировать")
        kb.row("Отмена")
    return kb

def settings_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Change weight / height / age")
        kb.row("Change goal")
        kb.row("Change gender")
        kb.row("Change diet mode")
        kb.row("Change targets manually")
        kb.row("Recalculate automatically")
        kb.row("Reset day")
        kb.row("Main menu")
    else:
        kb.row("Изменить вес / рост / возраст")
        kb.row("Изменить цель")
        kb.row("Изменить пол")
        kb.row("Изменить режим питания")
        kb.row("Изменить цели вручную")
        kb.row("Пересчитать автоматически")
        kb.row("Сбросить день")
        kb.row("Главное меню")
    return kb

def alcohol_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("Dry wine 150ml")
        kb.row("Semi-dry wine 150ml")
        kb.row("Light beer 330ml")
        kb.row("Dark beer 330ml")
        kb.row("Whisky / Vodka / Cognac 50ml")
        kb.row("Cocktail 200ml")
        kb.row("Champagne 150ml")
        kb.row("Several beers 700ml")
        kb.row("Enter manually")
        kb.row("Main menu")
    else:
        kb.row("Сухое вино 150мл")
        kb.row("Полусухое вино 150мл")
        kb.row("Пиво светлое 330мл")
        kb.row("Пиво тёмное 330мл")
        kb.row("Виски / Водка / Коньяк 50мл")
        kb.row("Коктейль 200мл")
        kb.row("Шампанское 150мл")
        kb.row("Несколько пив 700мл")
        kb.row("Ввести вручную")
        kb.row("Главное меню")
    return kb

def portions_kb(lang="ru"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("1 serving", "2 servings", "3 servings")
        kb.row("Main menu")
    else:
        kb.row("1 порция", "2 порции", "3 порции")
        kb.row("Главное меню")
    return kb

def choice_kb(n):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(*[str(i) for i in range(1, n+1)])
    kb.row("Искать снова / Search again", "Главное меню / Main menu")
    return kb

def lang_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Русский", "English")
    return kb

# ============================================================
# FOOD DB
# ============================================================

FOOD_DB = {
    "Авокадо 200г":    {"name": "Авокадо (200г)",      "fat": 21, "protein": 2,  "carbs": 2, "cal": 200},
    "Стейк 200г":      {"name": "Стейк говяжий (200г)", "fat": 18, "protein": 30, "carbs": 0, "cal": 280},
    "Яйца 2шт":        {"name": "Яйца (2 шт)",          "fat": 10, "protein": 12, "carbs": 1, "cal": 140},
    "Лосось 150г":     {"name": "Лосось (150г)",         "fat": 14, "protein": 28, "carbs": 0, "cal": 240},
    "Салат+масло":     {"name": "Салат+оливковое масло", "fat": 14, "protein": 2,  "carbs": 3, "cal": 145},
    "Сыр 50г":         {"name": "Сыр твёрдый (50г)",     "fat": 14, "protein": 12, "carbs": 0, "cal": 180},
    "Миндаль 30г":     {"name": "Миндаль (30г)",          "fat": 15, "protein": 6,  "carbs": 3, "cal": 170},
    "Черника 80г":     {"name": "Черника (80г)",           "fat": 0,  "protein": 1,  "carbs": 9, "cal": 45},
    "Бекон 3шт":       {"name": "Бекон (3 полоски)",       "fat": 12, "protein": 9,  "carbs": 0, "cal": 140},
}

ALCOHOL_DB = {
    "Сухое вино 150мл":          {"name": "Сухое вино",       "ml": 150, "carbs": 4},
    "Полусухое вино 150мл":      {"name": "Полусухое вино",   "ml": 150, "carbs": 8},
    "Пиво светлое 330мл":        {"name": "Пиво светлое",     "ml": 330, "carbs": 13},
    "Пиво тёмное 330мл":         {"name": "Пиво тёмное",      "ml": 330, "carbs": 18},
    "Виски / Водка / Коньяк 50мл":{"name": "Крепкий алкоголь","ml": 50,  "carbs": 0},
    "Коктейль 200мл":             {"name": "Коктейль",         "ml": 200, "carbs": 25},
    "Шампанское 150мл":           {"name": "Шампанское",       "ml": 150, "carbs": 6},
    "Несколько пив 700мл":        {"name": "Несколько пив",    "ml": 700, "carbs": 28},
}

ACTIVITY_MAP = {
    "Минимум (сидячий)": 1.2,    "Sedentary": 1.2,
    "Лёгкая (1-3 раза/нед)": 1.375, "Light (1-3x/week)": 1.375,
    "Умеренная (3-5 раз/нед)": 1.55, "Moderate (3-5x/week)": 1.55,
    "Высокая (6-7 раз/нед)": 1.725,  "High (6-7x/week)": 1.725,
    "Проф. спорт": 1.9,          "Pro athlete": 1.9,
}

KETO_LEVEL_MAP = {
    "Строгое кето": "Strict keto",   "Strict keto": "Strict keto",
    "Нормальное кето": "Normal keto", "Normal keto": "Normal keto",
    "Низкоуглеводная": "Low-carb",    "Low-carb": "Low-carb",
    "Ручной ввод": "Manual",          "Manual input": "Manual",
}

FOOD_SUGGESTIONS = [
    {"ru": "Авокадо (200г)",       "en": "Avocado (200g)",       "fat": 21, "protein": 2,  "carbs": 2,  "cal": 200},
    {"ru": "Стейк говяжий (150г)", "en": "Beef steak (150g)",    "fat": 14, "protein": 23, "carbs": 0,  "cal": 210},
    {"ru": "Лосось (150г)",        "en": "Salmon (150g)",         "fat": 14, "protein": 28, "carbs": 0,  "cal": 240},
    {"ru": "Яйца варёные (2шт)",   "en": "Boiled eggs (2pc)",    "fat": 10, "protein": 12, "carbs": 1,  "cal": 140},
    {"ru": "Сыр твёрдый (50г)",    "en": "Hard cheese (50g)",    "fat": 14, "protein": 12, "carbs": 0,  "cal": 180},
    {"ru": "Миндаль (30г)",        "en": "Almonds (30g)",         "fat": 15, "protein": 6,  "carbs": 3,  "cal": 170},
    {"ru": "Бекон (3 полоски)",    "en": "Bacon (3 strips)",      "fat": 12, "protein": 9,  "carbs": 0,  "cal": 140},
    {"ru": "Куриная грудка (150г)","en": "Chicken breast (150g)", "fat": 4,  "protein": 35, "carbs": 0,  "cal": 165},
    {"ru": "Творог 5% (150г)",     "en": "Cottage cheese (150g)", "fat": 8,  "protein": 18, "carbs": 3,  "cal": 155},
    {"ru": "Тунец в масле (100г)", "en": "Tuna in oil (100g)",   "fat": 10, "protein": 26, "carbs": 0,  "cal": 200},
    {"ru": "Грецкие орехи (30г)",  "en": "Walnuts (30g)",         "fat": 20, "protein": 5,  "carbs": 4,  "cal": 196},
    {"ru": "Брокколи+масло (200г)","en": "Broccoli+oil (200g)",  "fat": 10, "protein": 5,  "carbs": 8,  "cal": 148},
]

# ============================================================
# FALLBACK MACROS
# ============================================================

FALLBACK_MACROS = {
    "pumpkin seed": {"fat":49,"protein":30,"carbs":11,"cal":559},
    "pistachio":    {"fat":45,"protein":20,"carbs":28,"cal":562},
    "almond":       {"fat":50,"protein":21,"carbs":22,"cal":579},
    "walnut":       {"fat":65,"protein":15,"carbs":14,"cal":654},
    "cashew":       {"fat":44,"protein":18,"carbs":30,"cal":553},
    "nut":          {"fat":50,"protein":18,"carbs":20,"cal":580},
    "seed":         {"fat":45,"protein":20,"carbs":15,"cal":540},
    "egg":          {"fat":10,"protein":13,"carbs":1, "cal":143},
    "fish":         {"fat":10,"protein":20,"carbs":0, "cal":170},
    "salmon":       {"fat":13,"protein":20,"carbs":0, "cal":200},
    "chicken":      {"fat":7, "protein":27,"carbs":0, "cal":165},
    "beef":         {"fat":15,"protein":26,"carbs":0, "cal":250},
    "steak":        {"fat":15,"protein":26,"carbs":0, "cal":240},
    "bacon":        {"fat":42,"protein":12,"carbs":0, "cal":417},
    "avocado":      {"fat":15,"protein":2, "carbs":9, "cal":160},
    "cheese":       {"fat":25,"protein":20,"carbs":2, "cal":300},
    "salad":        {"fat":5, "protein":2, "carbs":5, "cal":70},
    "soup":         {"fat":3, "protein":4, "carbs":6, "cal":65},
    "rice":         {"fat":1, "protein":3, "carbs":28,"cal":130},
    "pasta":        {"fat":2, "protein":5, "carbs":30,"cal":157},
    "bread":        {"fat":3, "protein":8, "carbs":50,"cal":265},
    "pizza":        {"fat":10,"protein":11,"carbs":33,"cal":266},
    "burger":       {"fat":16,"protein":15,"carbs":24,"cal":295},
    "sushi":        {"fat":3, "protein":8, "carbs":20,"cal":140},
    "broccoli":     {"fat":0, "protein":3, "carbs":7, "cal":35},
    "butter":       {"fat":81,"protein":1, "carbs":1, "cal":717},
}

def get_fallback_macros(dish_names):
    fat = prot = carbs = cal = found = 0
    for dish in dish_names:
        dl = dish.lower()
        for key, m in FALLBACK_MACROS.items():
            if key in dl or any(key in w for w in dl.split()):
                fat += m["fat"]; prot += m["protein"]
                carbs += m["carbs"]; cal += m["cal"]; found += 1; break
    if found == 0:
        return None
    return {"fat": round(fat/found,1), "protein": round(prot/found,1),
            "carbs": round(carbs/found,1), "cal": round(cal/found)}

# ============================================================
# API
# ============================================================

def analyze_photo(image_bytes):
    try:
        headers = {"Authorization": f"Bearer {LOGMEAL_TOKEN}"}
        files = {"image": ("food.jpg", image_bytes, "image/jpeg")}
        r1 = requests.post("https://api.logmeal.com/v2/image/segmentation/complete",
                           headers=headers, files=files, timeout=30)
        print(f"LM1: {r1.status_code} {r1.text[:200]}")
        if r1.status_code != 200:
            return None
        d1 = r1.json(); image_id = d1.get("imageId")
        dish_names = [rec.get("name","") for seg in d1.get("segmentation_results",[])
                      for rec in seg.get("recognition_results",[]) if rec.get("name")]
        if not image_id:
            return None
        fat = prot = carbs = cal = 0
        r2 = requests.post("https://api.logmeal.com/v2/nutrition/recipe/nutritionalInfo",
                           headers=headers, json={"imageId": image_id}, timeout=15)
        print(f"LM2: {r2.status_code} {r2.text[:200]}")
        if r2.status_code == 200:
            n = r2.json().get("nutritional_info") or r2.json().get("nutrition") or r2.json()
            fat  = float(n.get("totalFat",0) or n.get("fat",0) or 0)
            prot = float(n.get("proteins",0) or n.get("protein",0) or 0)
            carbs= float(n.get("totalCarbs",0) or n.get("carbs",0) or 0)
            cal  = float(n.get("calories",0) or 0)
        if fat == 0 and prot == 0 and carbs == 0:
            r3 = requests.post("https://api.logmeal.com/v2/nutrition/recipe/ingredients",
                               headers=headers, json={"imageId": image_id}, timeout=15)
            if r3.status_code == 200:
                for ing in r3.json().get("ingredients",[]):
                    n = ing.get("nutritional_info",{})
                    fat += float(n.get("totalFat",0) or 0)
                    prot+= float(n.get("proteins",0) or 0)
                    carbs+=float(n.get("totalCarbs",0) or 0)
                    cal += float(n.get("calories",0) or 0)
        from_fallback = False
        if fat == 0 and prot == 0 and carbs == 0:
            fb = get_fallback_macros(dish_names)
            if fb:
                fat=fb["fat"]; prot=fb["protein"]; carbs=fb["carbs"]
                if cal == 0: cal = fb["cal"]
                from_fallback = True
        return {"dishes": dish_names or ["Блюдо"], "calories": round(cal),
                "fat": round(fat,1), "protein": round(prot,1), "carbs": round(carbs,1),
                "from_fallback": from_fallback}
    except Exception as e:
        print(f"LogMeal error: {e}"); return None

def search_food(query):
    try:
        headers = {"User-Agent": "KetOSBot/1.0"}
        params = {"search_terms": query, "search_simple": 1, "action": "process",
                  "json": 1, "page_size": 20, "fields": "product_name,nutriments,brands"}
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl",
                         params=params, headers=headers, timeout=15)
        results = []
        for p in r.json().get("products",[]):
            name = p.get("product_name","").strip()
            if not name or len(name) < 2: continue
            n = p.get("nutriments",{})
            fat  = round(float(n.get("fat_100g") or 0),1)
            prot = round(float(n.get("proteins_100g") or 0),1)
            carbs= round(float(n.get("carbohydrates_100g") or 0),1)
            cal  = round(float(n.get("energy-kcal_100g") or 0))
            if fat==0 and prot==0 and carbs==0: continue
            brand = p.get("brands","").strip()
            display = name + (f" — {brand}" if brand and brand.lower() not in name.lower() else "")
            results.append({"name": display[:50], "fat": fat, "protein": prot, "carbs": carbs, "cal": cal})
            if len(results) >= 5: break
        return results
    except Exception as e:
        print(f"Search error: {e}"); return []

# ============================================================
# TEXTS
# ============================================================

def recovery_text(u, total_carbs):
    h = max(4, int(total_carbs/15))
    if u.get("lang") == "en":
        return (f"Recovery plan after {total_carbs}g carbs\n\n"
                f"0-2h: Water, salt, electrolytes\n"
                f"2-3h: 1 tbsp MCT oil\n"
                f"3-5h: Fast + light walk\n"
                f"~{h}h: Fatty meat + vegetables\n\n"
                f"Back in ketosis in {h}-{h+2} hours!\nMeasure ketones in {h}h")
    return (f"План возврата в кетоз после {total_carbs}г углеводов\n\n"
            f"0-2ч: Вода, соль, электролиты\n"
            f"2-3ч: 1 ст.л. MCT масла\n"
            f"3-5ч: Голодай + лёгкая прогулка\n"
            f"~{h}ч: Жирное мясо + овощи\n\n"
            f"Снова в кетозе через {h}-{h+2} часов!\nИзмерь кетоны через {h}ч")

def alcohol_text(u, name, ml, carbs):
    d = round(ml/50*1.5); h = d + (8 if carbs<10 else 16 if carbs<30 else 24)
    sev = ("Умеренное" if carbs<10 else "Значительное" if carbs<30 else "Сильное")
    if u.get("lang") == "en":
        sev_en = ("Moderate" if carbs<10 else "Significant" if carbs<30 else "High")
        return (f"Recovery after alcohol\n{name} {ml}ml — {carbs}g carbs\n{sev_en} impact\n\n"
                f"Alcohol out in ~{d}h | Ketosis back in ~{h}h\n\n"
                f"Now: Water 2-3L + electrolytes\n"
                f"Morning: Coffee + MCT oil, skip breakfast\n"
                f"First meal: Eggs/meat/fish, zero carbs\n"
                f"30min walk speeds recovery\n\nMeasure ketones in {h}h!")
    return (f"Возврат в кетоз после алкоголя\n{name} {ml}мл — {carbs}г углеводов\n{sev} влияние\n\n"
            f"Алкоголь выйдет через ~{d}ч | Кетоз вернётся через ~{h}ч\n\n"
            f"Сейчас: Вода 2-3л + электролиты\n"
            f"Утром: Кофе + MCT масло, пропусти завтрак\n"
            f"Первый приём: Яйца/мясо/рыба, ноль углеводов\n"
            f"Прогулка 30мин ускорит возврат\n\nИзмерь кетоны через {h}ч!")

def ai_advisor_text(u):
    lang = u.get("lang","ru")
    fl = max(0, u["fat_target"] - u["fat"])
    pl = max(0, u["protein_target"] - u["protein"])
    cl = max(0, u["carbs_target"] - u["carbs"])
    kl = max(0, u["cal_target"] - u["calories"])
    if kl <= 50:
        return ("Daily goal reached! Great job today" if lang=="en"
                else "Дневная норма выполнена! Отличная работа")
    pool = list(FOOD_SUGGESTIONS); plan = []
    rem_fat=fl; rem_prot=pl; rem_carbs=cl; rem_cal=kl
    for _ in range(4):
        if rem_cal <= 50: break
        best_s=-999; best_f=None
        for f in pool:
            if f in [x[0] for x in plan]: continue
            if f["carbs"] > rem_carbs+3: continue
            s = 0
            if rem_fat>5:  s += min(f["fat"], rem_fat)*2
            if rem_prot>5: s += min(f["protein"], rem_prot)*3
            if f["cal"] <= rem_cal: s+=5
            else: s-=20
            if s > best_s: best_s=s; best_f=f
        if best_f and best_s>0:
            plan.append((best_f, best_s))
            rem_fat-=best_f["fat"]; rem_prot-=best_f["protein"]
            rem_carbs-=best_f["carbs"]; rem_cal-=best_f["cal"]
            pool.remove(best_f)
    if lang=="en":
        lines = [f"AI Adviser — Meal Plan\n\nRemaining: {kl}kcal | Fat:{fl}g | Prot:{pl}g | Carbs:{cl}g\n\nSuggested:\n"]
        tf=tp=tc=tcal=0
        for i,(f,_) in enumerate(plan,1):
            lines.append(f"{i}. {f['en']}\n   Fat:{f['fat']}g Prot:{f['protein']}g Carbs:{f['carbs']}g {f['cal']}kcal\n")
            tf+=f["fat"]; tp+=f["protein"]; tc+=f["carbs"]; tcal+=f["cal"]
        lines.append(f"\nPlan total: {tcal}kcal | Fat:{tf}g | Prot:{tp}g | Carbs:{tc}g")
        after = kl-tcal
        lines.append("\nGoal reached!" if after<=100 else f"\nStill needed: {after}kcal")
    else:
        lines = [f"ИИ Советник — Рацион\n\nОсталось: {kl}ккал | Ж:{fl}г | Б:{pl}г | У:{cl}г\n\nРекомендую:\n"]
        tf=tp=tc=tcal=0
        for i,(f,_) in enumerate(plan,1):
            lines.append(f"{i}. {f['ru']}\n   Ж:{f['fat']}г Б:{f['protein']}г У:{f['carbs']}г {f['cal']}ккал\n")
            tf+=f["fat"]; tp+=f["protein"]; tc+=f["carbs"]; tcal+=f["cal"]
        lines.append(f"\nИтого по плану: {tcal}ккал | Ж:{tf}г | Б:{tp}г | У:{tc}г")
        after = kl-tcal
        lines.append("\nНорма будет выполнена!" if after<=100 else f"\nОстанется: {after}ккал")
    return "".join(lines)

def profile_text(u, m):
    g = "Мужской" if u.get("gender")=="male" else "Женский"
    lang = u.get("lang","ru")
    if lang=="en":
        g = "Male" if u.get("gender")=="male" else "Female"
        return (f"Profile created!\n\n"
                f"{u['name']} | {g} | {u['weight']}kg | {u['height']}cm | {int(u['age'])}y\n"
                f"Sport: {u.get('sport_type','—')} | Goal: {u.get('goal','—')}\n"
                f"Mode: {u.get('keto_level','—')}\n\n"
                f"Daily targets:\n"
                f"Calories: {m['calories']} kcal\n"
                f"Fat: {m['fat']}g | Protein: {m['protein']}g | Carbs: {m['carbs']}g\n\n"
                f"BMR: {m['bmr']} kcal | TDEE: {m['tdee']} kcal\n\nLet's go!")
    return (f"Профиль готов!\n\n"
            f"{u['name']} | {g} | {u['weight']}кг | {u['height']}см | {int(u['age'])}лет\n"
            f"Спорт: {u.get('sport_type','—')} | Цель: {u.get('goal','—')}\n"
            f"Режим: {u.get('keto_level','—')}\n\n"
            f"Цели на день:\n"
            f"Калории: {m['calories']} ккал\n"
            f"Жиры: {m['fat']}г | Белки: {m['protein']}г | Углеводы: {m['carbs']}г\n\n"
            f"BMR: {m['bmr']} ккал | TDEE: {m['tdee']} ккал\n\nПоехали!")

# ============================================================
# PHOTO HANDLER
# ============================================================

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    bot.send_message(msg.chat.id, L(u,"Фото получено! Анализирую блюдо... (10-20 сек)",
                                      "Photo received! Analyzing... (10-20 sec)"))
    try:
        fi = bot.get_file(msg.photo[-1].file_id)
        image_bytes = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fi.file_path}", timeout=10).content
    except Exception as e:
        print(f"DL error: {e}")
        bot.send_message(msg.chat.id, L(u,"Ошибка загрузки фото","Photo download error"), reply_markup=main_kb(u.get("lang","ru")))
        return

    def do():
        try:
            result = analyze_photo(image_bytes)
            if not result or (result["calories"]==0 and result["fat"]==0 and result["protein"]==0):
                bot.send_message(msg.chat.id,
                    L(u,"Не удалось распознать блюдо. Введи вручную.",
                        "Could not recognize the dish. Enter manually."),
                    reply_markup=main_kb(u.get("lang","ru")))
                set_state(uid,"menu"); return
            u["pending_food"] = result
            set_state(uid,"confirm_photo")
            dishes = ", ".join(result["dishes"][:3])
            warn = L(u,"Много углеводов!","High carbs!") if result["carbs"]>10 else L(u,"Кето-дружественно","Keto-friendly")
            note = L(u,"\n\nМакросы примерные — скорректируй если нужно",
                       "\n\nMacros are approximate — correct if needed") if result.get("from_fallback") else ""
            bot.send_message(msg.chat.id,
                f"{L(u,'Результат анализа','Analysis result')}:\n\n"
                f"{L(u,'Блюдо','Dish')}: {dishes}\n\n"
                f"Calories: {result['calories']} kcal\n"
                f"Fat: {result['fat']}g | Protein: {result['protein']}g | Carbs: {result['carbs']}g\n\n"
                f"{warn}{note}\n\n{L(u,'Всё верно?','Is this correct?')}",
                reply_markup=confirm_photo_kb(u.get("lang","ru")))
        except Exception as e:
            print(f"Photo thread error: {e}")
            bot.send_message(msg.chat.id, L(u,"Ошибка анализа. Попробуй ещё раз.","Analysis error. Try again."), reply_markup=main_kb(u.get("lang","ru")))
            set_state(uid,"menu")

    threading.Thread(target=do, daemon=True).start()

# ============================================================
# MAIN HANDLER
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
    set_state(uid,"ask_lang")
    bot.send_message(msg.chat.id,
        "KetOS — Keto diet for athletes\n\nChoose language / Выбери язык:",
        reply_markup=lang_kb())

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    text = msg.text.strip() if msg.text else ""
    state = get_state(uid)

    # Global resets + all main menu buttons that need lang-aware routing
    if text in ["Перезапуск", "Главное меню", "Main menu", "Restart"]:
        set_state(uid,"menu")
        bot.send_message(msg.chat.id, L(u,"Главное меню:","Main menu:"), reply_markup=main_kb(u.get("lang","ru")))
        return

    # ======================== ЯЗЫК — ПЕРВЫМ, до перевода ========================
    if text in ["Язык / Language", "Language"] or state in ["ask_lang", "switch_lang"]:
        if text in ["Язык / Language", "Language"]:
            set_state(uid, "switch_lang")
            bot.send_message(msg.chat.id, "Choose / Выбери:", reply_markup=lang_kb())
            return
        if text == "English":
            u["lang"] = "en"
            set_state(uid, "menu" if u.get("name") else "ask_name")
            if u.get("name"):
                bot.send_message(msg.chat.id, "Language set to English!", reply_markup=main_kb("en"))
            else:
                bot.send_message(msg.chat.id, "Welcome to KetOS! What's your name?", reply_markup=types.ReplyKeyboardRemove())
            return
        if text == "Русский":
            u["lang"] = "ru"
            set_state(uid, "menu" if u.get("name") else "ask_name")
            if u.get("name"):
                bot.send_message(msg.chat.id, "Язык изменён на русский!", reply_markup=main_kb("ru"))
            else:
                bot.send_message(msg.chat.id, "Добро пожаловать в KetOS! Как тебя зовут?", reply_markup=types.ReplyKeyboardRemove())
            return
        if state in ["ask_lang", "switch_lang"]:
            set_state(uid, "menu")
            bot.send_message(msg.chat.id, L(u,"Главное меню:","Main menu:"), reply_markup=main_kb(u.get("lang","ru")))
            return

    # Map English button texts to Russian equivalents for unified handling
    EN_TO_RU = {
        "My status": "Мой статус",
        "Food diary": "Дневник",
        "Photo meal": "Фото блюда",
        "Add food": "Ввести еду",
        "Search product": "Поиск продукта",
        "Sport": "Спорт",
        "Alcohol": "Алкоголь",
        "Ketones": "Кетоны",
        "AI Adviser": "ИИ Советник",
        "Family": "Семья",
        "Settings": "Настройки",
        "Restart": "Перезапуск",
        "Main menu": "Главное меню",
        "Trail / Run": "Трейл / Бег",
        "Cycling race": "Велогонка",
        "Triathlon": "Триатлон",
        "Skiing": "Лыжи",
        "Strength": "Силовая",
        "Back to ketosis": "Возврат в кетоз",
        "Ketosis recovery plan": "План возврата в кетоз",
        "Add to diary": "Добавить в дневник",
        "Correct": "Скорректировать",
        "Cancel": "Отмена",
        "Change weight / height / age": "Изменить вес / рост / возраст",
        "Change goal": "Изменить цель",
        "Change gender": "Изменить пол",
        "Change diet mode": "Изменить режим питания",
        "Change targets manually": "Изменить цели вручную",
        "Recalculate automatically": "Пересчитать автоматически",
        "Reset day": "Сбросить день",
        "Female": "Женский",
        "Male": "Мужской",
        "Dry wine 150ml": "Сухое вино 150мл",
        "Semi-dry wine 150ml": "Полусухое вино 150мл",
        "Light beer 330ml": "Пиво светлое 330мл",
        "Dark beer 330ml": "Пиво тёмное 330мл",
        "Whisky / Vodka / Cognac 50ml": "Виски / Водка / Коньяк 50мл",
        "Cocktail 200ml": "Коктейль 200мл",
        "Champagne 150ml": "Шампанское 150мл",
        "Several beers 700ml": "Несколько пив 700мл",
        "Enter manually": "Ввести вручную",
        "1 serving": "1 порция",
        "2 servings": "2 порции",
        "3 servings": "3 порции",
        "Искать снова / Search again": "Искать снова",
        "Главное меню / Main menu": "Главное меню",
    }
    if text in EN_TO_RU:
        text = EN_TO_RU[text]

    # ======================== ЯЗЫК (убрано — обработано выше) ========================

    # ======================== ОНБОРДИНГ ========================
    if state == "ask_name":
        u["name"] = text
        set_state(uid,"ask_gender")
        bot.send_message(msg.chat.id,
            L(u,f"Привет, {text}! Твой пол?", f"Hi, {text}! Your gender?"),
            reply_markup=gender_kb(u.get("lang","ru")))
        return

    if state == "ask_gender":
        u["gender"] = "male" if "Мужской" in text or "Male" in text else "female"
        set_state(uid,"ask_weight")
        bot.send_message(msg.chat.id, L(u,"Введи вес в кг:","Enter weight in kg:"), reply_markup=weight_kb(u.get("lang","ru")))
        return

    if state == "ask_weight":
        try:
            u["weight"] = float(re.sub(r'[^\d.]','',text) or '70')
            set_state(uid,"ask_height")
            bot.send_message(msg.chat.id, L(u,"Рост в см:","Height in cm:"), reply_markup=height_kb())
        except:
            bot.send_message(msg.chat.id, L(u,"Введи число (например 65)","Enter number (e.g. 65)"))
        return

    if state == "ask_height":
        try:
            u["height"] = float(re.sub(r'[^\d.]','',text) or '170')
            set_state(uid,"ask_age")
            bot.send_message(msg.chat.id, L(u,"Возраст:","Age:"), reply_markup=age_kb())
        except:
            bot.send_message(msg.chat.id, L(u,"Введи число (например 170)","Enter number (e.g. 170)"))
        return

    if state == "ask_age":
        try:
            u["age"] = float(re.sub(r'[^\d.]','',text) or '30')
            set_state(uid,"ask_activity")
            bot.send_message(msg.chat.id, L(u,"Уровень активности:","Activity level:"), reply_markup=activity_kb(u["lang"]))
        except:
            bot.send_message(msg.chat.id, L(u,"Введи число (например 30)","Enter number (e.g. 30)"))
        return

    if state == "ask_activity":
        u["activity"] = text
        u["activity_coef"] = ACTIVITY_MAP.get(text, 1.55)
        set_state(uid,"ask_sport")
        bot.send_message(msg.chat.id, L(u,"Основной вид спорта:","Main sport:"), reply_markup=sport_kb_onboard(u["lang"]))
        return

    if state == "ask_sport":
        u["sport_type"] = text
        set_state(uid,"ask_goal")
        bot.send_message(msg.chat.id, L(u,"Главная цель:","Main goal:"), reply_markup=goal_kb(u["lang"]))
        return

    if state == "ask_goal":
        u["goal"] = text
        m = calc_macros(u); u["cal_target"] = m["calories"]
        set_state(uid,"ask_keto_level")
        bot.send_message(msg.chat.id,
            L(u, f"Калории: {m['calories']} ккал/день\n\nВыбери режим питания:\n\n"
                 f"Строгое кето — до 20г углеводов (Ж75% Б20% У5%)\n"
                 f"Нормальное кето — до 30г углеводов (Ж70% Б25% У5%)\n"
                 f"Низкоуглеводная — до 80г углеводов (Ж50% Б30% У20%)\n"
                 f"Ручной ввод — задашь сам",
               f"Calories: {m['calories']} kcal/day\n\nChoose diet mode:\n\n"
               f"Strict keto — up to 20g carbs (F75% P20% C5%)\n"
               f"Normal keto — up to 30g carbs (F70% P25% C5%)\n"
               f"Low-carb — up to 80g carbs (F50% P30% C20%)\n"
               f"Manual input — set your own"),
            reply_markup=keto_level_kb(u["lang"]))
        return

    if state == "ask_keto_level":
        if text in ["Ручной ввод","Manual input"]:
            set_state(uid,"manual_targets_onboard")
            m = calc_macros(u)
            bot.send_message(msg.chat.id,
                L(u, f"Расчётные: {m['calories']} ккал\n\nВведи через пробел:\nкалории жиры белки углеводы\n\nПример: 1600 125 100 20",
                     f"Calculated: {m['calories']} kcal\n\nEnter separated by spaces:\ncalories fat protein carbs\n\nExample: 1600 125 100 20"))
            return
        level = KETO_LEVEL_MAP.get(text, "Normal keto")
        u["keto_level"] = level
        m = apply_macros(u)
        set_state(uid,"menu")
        bot.send_message(msg.chat.id, profile_text(u,m), reply_markup=main_kb(u.get("lang","ru")))
        return

    if state == "manual_targets_onboard":
        try:
            nums = [int(x) for x in text.split() if x.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]; u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="Manual"
            m = {"calories":u["cal_target"],"fat":u["fat_target"],"protein":u["protein_target"],
                 "carbs":u["carbs_target"],"bmr":0,"tdee":u["cal_target"]}
            set_state(uid,"menu")
            bot.send_message(msg.chat.id, profile_text(u,m), reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: 1600 125 100 20","Example: 1600 125 100 20"))
        return

    # ======================== СТАТУС ========================
    if text == "Мой статус":
        k = u["ketones"]
        if k==0:   ks=L(u,"Не измерено","Not measured")
        elif k<0.5:ks=L(u,"Не в кетозе","Not in ketosis")
        elif k<1.5:ks=L(u,"Лёгкий кетоз","Light ketosis")
        elif k<3:  ks=L(u,"Оптимальный кетоз!","Optimal ketosis!")
        else:      ks=L(u,"Глубокий кетоз","Deep ketosis")
        bot.send_message(msg.chat.id,
            f"{L(u,'Статус на сегодня','Status today')}\n\n"
            f"Кетоны: {ks} ({k} mmol/L)\n\n"
            f"Calories: {bar(u['calories'],u['cal_target'])} {u['calories']}/{u['cal_target']} kcal\n"
            f"Fat:      {bar(u['fat'],u['fat_target'])} {u['fat']}/{u['fat_target']}g\n"
            f"Protein:  {bar(u['protein'],u['protein_target'])} {u['protein']}/{u['protein_target']}g\n"
            f"Carbs:    {bar(u['carbs'],u['carbs_target'])} {u['carbs']}/{u['carbs_target']}g",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Дневник":
        meals = u["meals"]
        mt = "\n".join(f"{i+1}. {m}" for i,m in enumerate(meals)) if meals else L(u,"Пусто","Empty")
        bot.send_message(msg.chat.id,
            f"{L(u,'Дневник питания','Food diary')}\n\n{mt}\n\n"
            f"{u['calories']} kcal | Fat:{u['fat']}g | Prot:{u['protein']}g | Carbs:{u['carbs']}g",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    # ======================== ФОТО ========================
    if text == "Фото блюда":
        set_state(uid,"waiting_photo")
        bot.send_message(msg.chat.id, L(u,"Отправь фото блюда — AI посчитает КБЖУ!",
                                          "Send a photo of your meal — AI will calculate macros!"))
        return

    # ======================== ВВОД ЕДЫ ========================
    if text == "Ввести еду":
        set_state(uid,"manual_food")
        bot.send_message(msg.chat.id,
            L(u,"Напиши название и три числа через пробел:\nназвание жиры белки углеводы\n\nПримеры:\nтворог 5 18 3\nкурица 200г 2 30 0\nкофе 150мл 1 1 3",
                "Write name and three numbers separated by spaces:\nname fat protein carbs\n\nExamples:\ncottage cheese 5 18 3\nchicken 200g 2 30 0"))
        return

    if state == "manual_food":
        try:
            parts = text.strip().split()
            nums = []; name_parts = []; amount_str = ""
            for p in parts:
                clean = re.sub(r'[гГмлМ]+$','',p)
                if clean.replace('.','').isdigit():
                    if any(p.lower().endswith(s) for s in ['г','мл','g','ml']):
                        amount_str = p
                    else:
                        nums.append(int(float(clean)))
                else:
                    name_parts.append(p)
            if len(nums) < 3: raise ValueError()
            name = " ".join(name_parts) or L(u,"Блюдо","Dish")
            name = name[0].upper()+name[1:]
            fat=nums[0]; prot=nums[1]; carbs=nums[2]
            cal = fat*9+prot*4+carbs*4
            al = f" {amount_str}" if amount_str else ""
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name}{al} (F{fat} P{prot} C{carbs} | {cal}kcal)")
            cl = u["carbs_target"]-u["carbs"]
            warn = L(u," Лимит углеводов близко!"," Carb limit close!") if cl<5 else ""
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{name}{al} {L(u,'добавлено','added')}!\n"
                f"Fat+{fat}g | Prot+{prot}g | Carbs+{carbs}g | {cal}kcal{warn}\n"
                f"{L(u,'Осталось углеводов','Carbs left')}: {max(cl,0)}g",
                reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: творог 5 18 3","Example: cottage cheese 5 18 3"))
        return

    # ======================== ПОИСК ========================
    if text in ["Поиск продукта","Искать снова"]:
        set_state(uid,"search_food")
        bot.send_message(msg.chat.id, L(u,"Напиши название продукта:","Enter product name:"))
        return

    if state == "search_food":
        bot.send_message(msg.chat.id, L(u,f"Ищу {text}...",f"Searching {text}..."))
        results = search_food(text)
        tr = {"колбаса":"sausage","творог":"cottage cheese","гречка":"buckwheat",
              "курица":"chicken","говядина":"beef","рыба":"fish","картошка":"potato"}
        if not results:
            eng = tr.get(text.lower())
            if eng: results = search_food(eng)
        if not results:
            bot.send_message(msg.chat.id, L(u,"Не найдено. Введи вручную.","Not found. Enter manually."), reply_markup=main_kb(u.get("lang","ru")))
            set_state(uid,"menu"); return
        u["search_results"] = results
        resp = L(u,f"Найдено {len(results)} продуктов (на 100г):\n\n",
                   f"Found {len(results)} products (per 100g):\n\n")
        for i,p in enumerate(results,1):
            resp += f"{i}. {p['name']}\n   F:{p['fat']}g P:{p['protein']}g C:{p['carbs']}g {p['cal']}kcal\n\n"
        resp += L(u,"Напиши номер:","Enter number:")
        set_state(uid,"choose_food")
        bot.send_message(msg.chat.id, resp, reply_markup=choice_kb(len(results)))
        return

    if state == "choose_food":
        if text.isdigit():
            idx = int(text)-1
            results = u.get("search_results",[])
            if 0 <= idx < len(results):
                u["pending_search_food"] = results[idx]
                set_state(uid,"ask_food_grams")
                f = results[idx]
                bot.send_message(msg.chat.id,
                    f"{f['name']}\n\nPer 100g: F:{f['fat']}g P:{f['protein']}g C:{f['carbs']}g {f['cal']}kcal\n\n"
                    f"{L(u,'Сколько грамм?','How many grams?')} {L(u,'Например: 150','Example: 150')}")
        return

    if state == "ask_food_grams":
        try:
            grams = float(re.sub(r'[^\d.]','',text) or '100')
            f = u.get("pending_search_food",{})
            r = grams/100
            fat=round(f["fat"]*r,1); prot=round(f["protein"]*r,1)
            carbs=round(f["carbs"]*r,1); cal=round(f["cal"]*r)
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{f['name'][:25]} ({int(grams)}g | {cal}kcal)")
            cl = u["carbs_target"]-u["carbs"]
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{f['name'][:40]} — {int(grams)}g {L(u,'добавлено','added')}!\n"
                f"F+{fat}g P+{prot}g C+{carbs}g {cal}kcal\n"
                f"{L(u,'Осталось углеводов','Carbs left')}: {max(round(cl),0)}g",
                reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Введи число, например: 150","Enter number, e.g.: 150"))
        return

    # ======================== БЫСТРЫЕ ПРОДУКТЫ ========================
    if text in FOOD_DB:
        f = FOOD_DB[text]
        u["fat"]+=f["fat"]; u["protein"]+=f["protein"]; u["carbs"]+=f["carbs"]; u["calories"]+=f["cal"]
        u["meals"].append(f"{f['name']} (F{f['fat']} P{f['protein']} C{f['carbs']} | {f['cal']}kcal)")
        cl = u["carbs_target"]-u["carbs"]
        bot.send_message(msg.chat.id,
            f"{f['name']} {L(u,'добавлено','added')}!\nF+{f['fat']}g P+{f['protein']}g C+{f['carbs']}g {f['cal']}kcal\n"
            f"{L(u,'Осталось','Left')}: {max(cl,0)}g",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    # ======================== ФОТО ПОДТВЕРЖДЕНИЕ ========================
    if state == "confirm_photo":
        if text == "Добавить в дневник":
            f = u.get("pending_food")
            if f:
                u["fat"]+=f["fat"]; u["protein"]+=f["protein"]; u["carbs"]+=f["carbs"]; u["calories"]+=f["calories"]
                d = ", ".join(f["dishes"][:2])
                u["meals"].append(f"{d[:25]} (photo | {f['calories']}kcal)")
                cl = u["carbs_target"]-u["carbs"]
                u["pending_food"]=None; set_state(uid,"menu")
                bot.send_message(msg.chat.id,
                    f"{L(u,'Добавлено!','Added!')} {f['calories']}kcal\n"
                    f"{L(u,'Осталось углеводов','Carbs left')}: {max(cl,0)}g",
                    reply_markup=main_kb(u.get("lang","ru")))
            return
        if text == "Скорректировать":
            f = u.get("pending_food")
            set_state(uid,"correct_photo")
            bot.send_message(msg.chat.id,
                f"{L(u,'Текущие','Current')}: F:{f['fat']}g P:{f['protein']}g C:{f['carbs']}g {f['calories']}kcal\n\n"
                f"{L(u,'Напиши: название жиры белки углеводы','Write: name fat protein carbs')}\n\n"
                f"{L(u,'Пример: рыба с овощами 12 25 8','Example: fish with veggies 12 25 8')}\n\n"
                f"{L(u,'Или нажми Отмена','Or press Отмена')}",
                reply_markup=confirm_photo_kb(u.get("lang","ru")))
            return
        if text == "Отмена":
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id, L(u,"Отменено.","Cancelled."), reply_markup=main_kb(u.get("lang","ru")))
            return

    if state == "correct_photo":
        if text == "Отмена":
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id, L(u,"Отменено.","Cancelled."), reply_markup=main_kb(u.get("lang","ru")))
            return
        try:
            parts = text.strip().split()
            nums=[]; name_parts=[]
            for p in parts:
                clean = re.sub(r'[гГмлМ,]+$','',p)
                if clean.replace('.','').isdigit(): nums.append(int(float(clean)))
                else: name_parts.append(p)
            if len(nums)<3: raise ValueError()
            name=" ".join(name_parts) or L(u,"Блюдо","Dish")
            name=name[0].upper()+name[1:]
            fat=nums[0]; prot=nums[1]; carbs=nums[2]; cal=fat*9+prot*4+carbs*4
            u["fat"]+=fat; u["protein"]+=prot; u["carbs"]+=carbs; u["calories"]+=cal
            u["meals"].append(f"{name} (F{fat} P{prot} C{carbs} | {cal}kcal)")
            u["pending_food"]=None; set_state(uid,"menu")
            bot.send_message(msg.chat.id, f"{name} {L(u,'добавлено','added')}! F:{fat}g P:{prot}g C:{carbs}g {cal}kcal", reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: рыба с овощами 12 25 8","Example: fish 12 25 8"))
        return

    # ======================== КЕТОНЫ ========================
    if text == "Кетоны":
        set_state(uid,"ketones")
        bot.send_message(msg.chat.id, L(u,"Введи уровень кетонов (ммоль/л), например: 1.8",
                                          "Enter ketone level (mmol/L), e.g.: 1.8"))
        return

    if state == "ketones":
        try:
            val = float(text.replace(",","."))
            u["ketones"] = val
            if val<0.5:   s=L(u,"Не в кетозе. Сократи углеводы.","Not in ketosis. Cut carbs.")
            elif val<1.5: s=L(u,"Лёгкий кетоз. Уменьши углеводы на 5г.","Light ketosis. Reduce carbs by 5g.")
            elif val<3:   s=L(u,"Оптимальный кетоз! Продолжай!","Optimal ketosis! Keep going!")
            else:         s=L(u,"Глубокий кетоз. Пей воду + электролиты.","Deep ketosis. Drink water + electrolytes.")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id, f"{val} mmol/L\n{s}", reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Введи число, например: 1.8","Enter number, e.g.: 1.8"))
        return

    # ======================== АЛКОГОЛЬ ========================
    if text == "Алкоголь":
        set_state(uid,"choose_alcohol")
        bot.send_message(msg.chat.id, L(u,"Что пил?","What did you drink?"), reply_markup=alcohol_kb(u.get("lang","ru")))
        return

    if state == "choose_alcohol":
        if text == "Ввести вручную":
            set_state(uid,"manual_alcohol")
            bot.send_message(msg.chat.id, L(u,"Введи через пробел:\nназвание количество_мл углеводы_г\n\nПример: Пиво 500 20",
                                              "Enter separated by spaces:\nname amount_ml carbs_g\n\nExample: Beer 500 20"))
            return
        drink = ALCOHOL_DB.get(text)
        if drink:
            u["pending_alcohol"]=drink; set_state(uid,"ask_alcohol_amount")
            bot.send_message(msg.chat.id, f"{drink['name']}\n{L(u,'Сколько порций?','How many servings?')}", reply_markup=portions_kb(u.get("lang","ru")))
        return

    if state == "ask_alcohol_amount":
        drink = u.get("pending_alcohol",{})
        try:
            qty = 3 if "3" in text else 2 if "2" in text else 1
            ml=drink["ml"]*qty; carbs=drink["carbs"]*qty
            u["carbs"]+=carbs; u["calories"]+=carbs*4
            u["meals"].append(f"{drink['name']} x{qty} ({carbs}g carbs)")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id, alcohol_text(u,drink["name"],ml,carbs), reply_markup=main_kb(u.get("lang","ru")))
        except:
            set_state(uid,"menu"); bot.send_message(msg.chat.id, L(u,"Используй кнопки","Use buttons"), reply_markup=main_kb(u.get("lang","ru")))
        return

    if state == "manual_alcohol":
        try:
            parts=text.split(); name=parts[0]; ml=int(parts[1]); carbs=int(parts[2])
            u["carbs"]+=carbs; u["calories"]+=carbs*4
            u["meals"].append(f"{name} ({ml}ml, {carbs}g carbs)")
            set_state(uid,"menu")
            bot.send_message(msg.chat.id, alcohol_text(u,name,ml,carbs), reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: Пиво 500 20","Example: Beer 500 20"))
        return

    # ======================== СПОРТ ========================
    if text == "Спорт":
        set_state(uid,"sport")
        bot.send_message(msg.chat.id, L(u,"Выбери активность:","Choose activity:"), reply_markup=sport_kb(u.get("lang","ru")))
        return

    if text in ["Возврат в кетоз","План возврата в кетоз"]:
        set_state(uid,"menu")
        bot.send_message(msg.chat.id, recovery_text(u, u.get("last_gel_carbs",60)), reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Силовая":
        set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            L(u,"Силовая на кето:\nДо: MCT масло + кофе\nВо время: вода + соль\nПосле: 30-40г белка за 30 мин",
                "Strength training on keto:\nBefore: MCT oil + coffee\nDuring: water + salt\nAfter: 30-40g protein in 30 min"),
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if text in ["Трейл / Бег","Велогонка","Триатлон","Лыжи"]:
        u["sport_type_race"]=text; set_state(uid,"ask_distance")
        bot.send_message(msg.chat.id, L(u,"Дистанция или время?\nПример: 42 км или 3 часа",
                                          "Distance or time?\nExample: 42 km or 3 hours"))
        return

    if state == "ask_distance":
        try:
            t2=text.lower()
            if "час" in t2 or "h" in t2:
                hours=float(''.join(c for c in t2 if c.isdigit() or c=='.'))
            elif "км" in t2 or "km" in t2:
                hours=float(''.join(c for c in t2 if c.isdigit() or c=='.'))/10
            else: hours=2
            gels=max(1,int(hours/1.5)); total=gels*20; u["last_gel_carbs"]=total
            lines=[L(u,f"Протокол гелей\n{text} (~{int(hours)}ч)\nГелей: {gels} шт\n",
                       f"Gel protocol\n{text} (~{int(hours)}h)\nGels: {gels}\n")]
            times=[0,0.4,0.7,0.9]
            for i in range(gels):
                tm=int(hours*times[min(i,3)]*60)
                lbl=L(u,"За 30 мин до старта","30 min before start") if i==0 else L(u,f"Через {tm} мин",f"After {tm} min")
                lines.append(f"{lbl}: Gel #{i+1} — 20g\n")
            lines.append(L(u,f"\nИтого: {total}г углеводов\nВозврат в кетоз: ~{max(4,int(total/15))} часов\n\nПосле финиша нажми: План возврата в кетоз",
                             f"\nTotal: {total}g carbs\nBack to ketosis: ~{max(4,int(total/15))} hours\n\nAfter finish press: Plan возврата в кетоз"))
            set_state(uid,"menu")
            bot.send_message(msg.chat.id,"".join(lines),reply_markup=after_gel_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: 42 км или 3 часа","Example: 42 km or 3 hours"))
        return

    # ======================== ИИ СОВЕТНИК ========================
    if text == "ИИ Советник":
        bot.send_message(msg.chat.id, ai_advisor_text(u), reply_markup=main_kb(u.get("lang","ru")))
        return

    # ======================== СЕМЬЯ ========================
    if text == "Семья":
        meals=u["meals"]; mt="\n".join(f"• {m}" for m in meals) if meals else L(u,"Пусто","Empty")
        bot.send_message(msg.chat.id,
            f"{L(u,'Семейный режим','Family mode')}\n\n"
            f"{L(u,'Пригласи партнёра:','Invite partner:')}\nhttps://t.me/ketOSzoneBot?start=family_{uid}\n\n"
            f"{L(u,'Твой рацион:','Your meals:')}\n{mt}",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    # ======================== НАСТРОЙКИ ========================
    if text == "Настройки":
        g = L(u,"Мужской" if u.get("gender")=="male" else "Женский",
                "Male" if u.get("gender")=="male" else "Female")
        goal_now = u.get("goal") or L(u,"Не указана","Not set")
        bot.send_message(msg.chat.id,
            f"{L(u,'Настройки','Settings')}\n\n"
            f"{u.get('name','—')} | {g}\n"
            f"{u.get('weight','—')}kg | {u.get('height','—')}cm | {int(u.get('age',0))}y\n"
            f"Sport: {u.get('sport_type','—')}\n"
            f"Goal: {goal_now}\n"
            f"Mode: {u.get('keto_level','—')}\n\n"
            f"Targets: {u['cal_target']}kcal | F:{u['fat_target']}g | P:{u['protein_target']}g | C:{u['carbs_target']}g",
            reply_markup=settings_kb(u.get("lang","ru")))
        return

    if text == "Изменить цель":
        set_state(uid,"change_goal")
        bot.send_message(msg.chat.id,
            L(u,f"Текущая цель: {u.get('goal','Не указана')}\n\nВыбери новую:",
                f"Current goal: {u.get('goal','Not set')}\n\nChoose new:"),
            reply_markup=goal_kb(u["lang"]))
        return

    if state == "change_goal":
        u["goal"] = text
        m = apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Цель изменена','Goal changed')}: {text}\n"
            f"{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\n"
            f"BMR:{m['bmr']} TDEE:{m['tdee']}",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if state == "ask_goal_after_edit":
        u["goal"] = text
        m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Готово!','Done!')} {u['weight']}kg {u['height']}cm {int(u['age'])}y\n"
            f"{L(u,'Цель','Goal')}: {u['goal']}\n"
            f"{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\n"
            f"BMR:{m['bmr']} TDEE:{m['tdee']}",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Изменить пол":
        set_state(uid,"change_gender")
        g = L(u,"Мужской" if u.get("gender")=="male" else "Женский",
                "Male" if u.get("gender")=="male" else "Female")
        bot.send_message(msg.chat.id, f"{L(u,'Текущий пол','Current gender')}: {g}\n{L(u,'Выбери:','Choose:')}",
                         reply_markup=gender_kb(u.get("lang","ru")))
        return

    if state == "change_gender":
        u["gender"] = "male" if "Мужской" in text or "Male" in text else "female"
        m = apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Пол обновлён','Gender updated')}!\n{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\nBMR:{m['bmr']} TDEE:{m['tdee']}",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Изменить вес / рост / возраст":
        set_state(uid,"edit_weight")
        bot.send_message(msg.chat.id,
            L(u,"Введи через пробел: вес рост возраст\n\nПример: 68 166 49",
                "Enter separated by spaces: weight height age\n\nExample: 68 166 49"))
        return

    if state == "edit_weight":
        try:
            nums=[float(x) for x in text.split() if re.sub(r'[^\d.]','',x)]
            if len(nums)<3: raise ValueError()
            u["weight"]=nums[0]; u["height"]=nums[1]; u["age"]=nums[2]
            # Если цель не установлена — спросить
            if not u.get("goal"):
                set_state(uid,"ask_goal_after_edit")
                bot.send_message(msg.chat.id,
                    L(u,"Данные сохранены. Теперь укажи цель:","Data saved. Now choose your goal:"),
                    reply_markup=goal_kb(u["lang"]))
                return
            m=apply_macros(u); set_state(uid,"menu")
            bot.send_message(msg.chat.id,
                f"{L(u,'Обновлено!','Updated!')} {u['weight']}kg {u['height']}cm {int(u['age'])}y\n"
                f"{L(u,'Цель','Goal')}: {u.get('goal','—')}\n"
                f"{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\n"
                f"BMR:{m['bmr']} TDEE:{m['tdee']}",
                reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: 68 166 49","Example: 68 166 49"))
        return

    if state == "ask_goal_after_edit":
        u["goal"] = text
        m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Готово!','Done!')} {u['weight']}kg {u['height']}cm {int(u['age'])}y\n"
            f"{L(u,'Цель','Goal')}: {u['goal']}\n"
            f"{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\n"
            f"BMR:{m['bmr']} TDEE:{m['tdee']}",
            reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Изменить режим питания":
        set_state(uid,"change_keto_level")
        bot.send_message(msg.chat.id, L(u,"Выбери режим:","Choose mode:"), reply_markup=keto_level_kb(u["lang"]))
        return

    if state == "change_keto_level":
        if text in ["Ручной ввод","Manual input"]:
            set_state(uid,"edit_targets"); bot.send_message(msg.chat.id, L(u,"Введи: калории жиры белки углеводы\nПример: 1600 125 100 20","Enter: calories fat protein carbs\nExample: 1600 125 100 20")); return
        level = KETO_LEVEL_MAP.get(text)
        if level:
            u["keto_level"]=level; m=apply_macros(u); set_state(uid,"menu")
            bot.send_message(msg.chat.id, f"{L(u,'Режим изменён','Mode changed')}: {level}\nF:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g", reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Изменить цели вручную":
        set_state(uid,"edit_targets")
        bot.send_message(msg.chat.id, L(u,f"Текущие: {u['cal_target']}ккал F:{u['fat_target']}г P:{u['protein_target']}г C:{u['carbs_target']}г\n\nВведи: калории жиры белки углеводы\nПример: 1600 125 100 20",
                                          f"Current: {u['cal_target']}kcal F:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g\n\nEnter: calories fat protein carbs\nExample: 1600 125 100 20"))
        return

    if state == "edit_targets":
        try:
            nums=[int(x) for x in text.split() if x.isdigit()]
            u["cal_target"]=nums[0]; u["fat_target"]=nums[1]; u["protein_target"]=nums[2]; u["carbs_target"]=nums[3]
            u["keto_level"]="Manual"; set_state(uid,"menu")
            bot.send_message(msg.chat.id, f"{L(u,'Цели обновлены','Targets updated')}!\n{u['cal_target']}kcal F:{u['fat_target']}g P:{u['protein_target']}g C:{u['carbs_target']}g", reply_markup=main_kb(u.get("lang","ru")))
        except:
            bot.send_message(msg.chat.id, L(u,"Пример: 1600 125 100 20","Example: 1600 125 100 20"))
        return

    if text == "Пересчитать автоматически":
        if not u.get("goal"):
            set_state(uid,"ask_goal_after_edit")
            bot.send_message(msg.chat.id, L(u,"Укажи цель:","Choose goal:"), reply_markup=goal_kb(u["lang"]))
            return
        m=apply_macros(u); set_state(uid,"menu")
        bot.send_message(msg.chat.id,
            f"{L(u,'Пересчитано','Recalculated')}!\n"
            f"{L(u,'Цель','Goal')}: {u.get('goal','—')}\n"
            f"{m['calories']}kcal | F:{m['fat']}g P:{m['protein']}g C:{m['carbs']}g\n"
            f"BMR:{m['bmr']} TDEE:{m['tdee']}", reply_markup=main_kb(u.get("lang","ru")))
        return

    if text == "Сбросить день":
        u["fat"]=u["protein"]=u["carbs"]=u["calories"]=0; u["meals"]=[]
        set_state(uid,"menu"); bot.send_message(msg.chat.id, L(u,"День сброшен!","Day reset!"), reply_markup=main_kb(u.get("lang","ru")))
        return

    # fallback
    set_state(uid,"menu")
    bot.send_message(msg.chat.id, L(u,"Используй кнопки меню","Use menu buttons"), reply_markup=main_kb(u.get("lang","ru")))

print("KetOS bot started!")
bot.polling(none_stop=True, interval=0, timeout=20)
