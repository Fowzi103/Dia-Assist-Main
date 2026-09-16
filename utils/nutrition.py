"""AI Diet Planner — calorie estimation and sample meal generation."""

import math

ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

GOAL_ADJUST = {
    "maintain": (0, 0, "Weight maintenance"),
    "lose": (-0.1, 0.8, "Gradual weight loss"),
    "gain": (0.1, 1.15, "Gradual weight gain"),
    "wellness": (0, 0, "General wellness"),
}

MACRO_RATIOS = {
    "maintain": (0.30, 0.45, 0.25),
    "lose": (0.35, 0.40, 0.25),
    "gain": (0.25, 0.45, 0.30),
    "wellness": (0.30, 0.45, 0.25),
}


def compute_metrics(age, sex, height_cm, weight_kg, activity, goal):
    """Return dict with BMR, TDEE, goal calories and macros."""
    sex = (sex or "female").lower()
    if sex in ("male", "m"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity = activity or "sedentary"
    factor = ACTIVITY_FACTOR.get(activity, 1.2)
    tdee = bmr * factor

    adj_pct, prot_mult, goal_label = GOAL_ADJUST.get(goal, (0, 1.0, "General wellness"))
    goal_cal = tdee * (1 + adj_pct)
    goal_cal = round(goal_cal / 10) * 10

    p_ratio, c_ratio, f_ratio = MACRO_RATIOS.get(goal, (0.30, 0.45, 0.25))

    protein_g = round((goal_cal * p_ratio) / 4)
    carbs_g = round((goal_cal * c_ratio) / 4)
    fat_g = round((goal_cal * f_ratio) / 9)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "goal_calories": goal_cal,
        "goal_label": goal_label,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "protein_cal": round(goal_cal * p_ratio),
        "carbs_cal": round(goal_cal * c_ratio),
        "fat_cal": round(goal_cal * f_ratio),
    }


def _is_glucose_high(analysis):
    for item in analysis or []:
        if item["key"] in ("glucose", "fasting glucose", "hba1c") and item["status"] in ("HIGH", "BORDERLINE"):
            return True
    return False


def _is_lipid_high(analysis):
    for item in analysis or []:
        if item["key"] in ("ldl", "total cholesterol", "triglycerides") and item["status"] in ("HIGH", "BORDERLINE"):
            return True
    return False


def _is_vitd_low(analysis):
    for item in analysis or []:
        if item["key"] == "vitamin d" and item["status"] in ("LOW", "BORDERLINE"):
            return True
    return False


def _health_notes(analysis):
    """Explain only the extracted report findings that influenced general guidance."""
    notes = []
    nutrition_keys = {"glucose", "fasting glucose", "hba1c", "ldl", "total cholesterol", "triglycerides", "vitamin d", "hemoglobin"}
    relevant = [item for item in (analysis or []) if item.get("key") in nutrition_keys]
    for item in relevant:
        value = item.get("value")
        unit = item.get("unit") or ""
        status = item.get("status", "UNKNOWN").lower()
        finding = f"{item.get('test')}: {value} {unit} ({status})".strip()
        if item.get("key") in ("glucose", "fasting glucose", "hba1c") and item.get("status") in ("HIGH", "BORDERLINE"):
            notes.append(f"{finding} influenced this plan: choose high-fiber foods, moderate refined carbohydrates, and limit sugary drinks.")
        elif item.get("key") in ("ldl", "total cholesterol", "triglycerides") and item.get("status") in ("HIGH", "BORDERLINE"):
            notes.append(f"{finding} influenced this plan: emphasize vegetables, fruits, whole grains, and fiber while moderating saturated fat.")
        elif item.get("key") == "vitamin d" and item.get("status") in ("LOW", "BORDERLINE"):
            notes.append(f"{finding} was found in the report. Discuss Vitamin D management with a clinician; no supplement or dose is prescribed here.")
        elif item.get("key") == "hemoglobin" and item.get("status") in ("LOW", "BORDERLINE"):
            notes.append(f"{finding} was found in the report. Discuss iron and nutrition questions with a clinician before changing supplements.")
    if not notes and relevant:
        notes.append("The selected report contains no flagged nutrition-related values. This remains a general wellness plan based on the extracted report data and your preferences.")
    if not notes:
        notes.append("No analyzed report was selected, so this is not a report-informed plan. Upload and analyze a report to connect nutrition guidance to extracted findings.")
    return notes


# Simple food database: (name, protein g, carbs g, fat g, cal)
FOODS = {
    "vegetarian": {
        "breakfast": [
            ("Oats with milk & berries", 12, 45, 8, 300),
            ("Whole-wheat toast with peanut butter & banana", 14, 50, 12, 380),
            ("Veggie omelette with 2 eggs & whole-wheat toast", 20, 35, 16, 380),
        ],
        "snack_m": [
            ("Apple with a handful of almonds", 6, 22, 8, 180),
            ("Greek yogurt with honey", 14, 15, 3, 150),
            ("Mixed fruit bowl", 3, 35, 1, 150),
        ],
        "lunch": [
            ("Dal, rice/brown rice, green salad & curd", 18, 70, 10, 450),
            ("Chickpea & vegetable stir-fry with roti", 20, 65, 12, 460),
            ("Vegetable khichdi with yogurt salad", 16, 70, 8, 420),
        ],
        "snack_e": [
            ("Roasted makhana (fox nuts)", 8, 20, 2, 130),
            ("Hummus with veggie sticks", 6, 20, 6, 160),
            ("Peanut butter rice cakes", 5, 22, 6, 170),
        ],
        "dinner": [
            ("Tofu/soy stir-fry with brown rice & steamed greens", 24, 60, 14, 460),
            ("Paneer veggie curry with roti", 22, 60, 16, 480),
            ("Vegetable pulao with curd & salad", 12, 70, 9, 420),
        ],
    },
    "nonvegetarian": {
        "breakfast": [
            ("Egg white omelette with whole-wheat toast", 24, 35, 10, 330),
            ("Egg scramble with vegetables & milk", 22, 22, 15, 340),
            ("Oats with milk, banana & almonds", 15, 45, 8, 320),
        ],
        "snack_m": [
            ("Boiled egg with a small fruit", 12, 15, 6, 140),
            ("Greek yogurt with berries", 14, 15, 3, 150),
            ("Veggie & chicken strip roll (whole wheat)", 16, 25, 9, 240),
        ],
        "lunch": [
            ("Grilled chicken, brown rice & salad", 35, 55, 14, 500),
            ("Fish curry with vegetables & whole-wheat roti", 30, 50, 16, 490),
            ("Chicken & vegetable stir-fry with rice", 33, 55, 13, 470),
        ],
        "snack_e": [
            ("Grilled chicken strips", 30, 2, 4, 170),
            ("Roasted makhanas", 8, 20, 2, 130),
            ("Cottage cheese (paneer) cubes with mint", 15, 4, 10, 170),
        ],
        "dinner": [
            ("Grilled fish with steamed vegetables", 34, 18, 14, 350),
            ("Chicken curry with roti & salad", 32, 45, 14, 440),
            ("Chicken & vegetable soup with whole-wheat bread", 28, 40, 10, 370),
        ],
    },
}

FOODS["vegan"] = {
    "breakfast": [("Oats with fortified soy milk & berries", 14, 45, 8, 320), ("Tofu scramble with whole-wheat toast", 19, 35, 12, 350), ("Peanut butter banana oats", 12, 50, 14, 360)],
    "snack_m": [("Apple with almonds", 6, 22, 8, 180), ("Fortified soy yogurt with berries", 8, 20, 4, 150), ("Mixed fruit bowl", 3, 35, 1, 150)],
    "lunch": [("Lentil bowl with brown rice and greens", 20, 70, 10, 460), ("Chickpea and vegetable stir-fry with roti", 20, 65, 12, 460), ("Tofu vegetable grain bowl", 22, 60, 13, 440)],
    "snack_e": [("Roasted makhana", 8, 20, 2, 130), ("Hummus with vegetable sticks", 6, 20, 6, 160), ("Peanut butter rice cakes", 5, 22, 6, 170)],
    "dinner": [("Tofu stir-fry with brown rice and greens", 24, 60, 14, 460), ("Bean and vegetable chili with quinoa", 22, 58, 12, 430), ("Vegetable curry with chickpeas and roti", 18, 65, 13, 450)],
}

MEAL_NAMES = {
    "breakfast": "Breakfast",
    "snack_m": "Morning Snack",
    "lunch": "Lunch",
    "snack_e": "Evening Snack",
    "dinner": "Dinner",
}


def _pick_food(food_list, allergies, idx):
    """Choose a food item respecting allergies (best effort)."""
    allergy_lower = [a.strip().lower() for a in (allergies or []) if a.strip()]
    candidates = food_list
    if allergy_lower:
        filtered = []
        for item in candidates:
            lowered = ", ".join(str(part) for part in item).lower()
            if not any(a in lowered for a in allergy_lower):
                filtered.append(item)
        if filtered:
            candidates = filtered
    return candidates[idx % len(candidates)]


def generate_plan(age, sex, height_cm, weight_kg, activity, diet_type, goal, allergies, analysis, preferences="", meals_per_day=5):
    """Generate full sample diet plan."""
    metrics = compute_metrics(age, sex, height_cm, weight_kg, activity, goal)
    diet_type = (diet_type or "vegetarian").lower()
    if diet_type not in ("vegetarian", "nonvegetarian", "vegan"):
        diet_type = "vegetarian"
    db = FOODS[diet_type]

    # Deterministic rotation seed
    seed = int(round(weight_kg * 3 + height_cm))
    plan = []
    total_cal = 0
    total_p = total_c = total_f = 0

    meal_count = int(meals_per_day or 5)
    meal_keys = {3: ["breakfast", "lunch", "dinner"], 4: ["breakfast", "snack_m", "lunch", "dinner"], 5: ["breakfast", "snack_m", "lunch", "snack_e", "dinner"]}.get(meal_count, ["breakfast", "snack_m", "lunch", "snack_e", "dinner"])
    for i, key in enumerate(meal_keys):
        foods = db[key]
        preferred = [food for food in foods if any(word in food[0].lower() for word in preferences.lower().split() if len(word) > 3)]
        name, p, c, f, cal = _pick_food(preferred or foods, allergies, (seed + i) % len(preferred or foods))
        total_cal += cal
        total_p += p
        total_c += c
        total_f += f
        plan.append({
            "meal": MEAL_NAMES[key],
            "foods": name,
            "calories": cal,
            "protein": p,
            "carbs": c,
            "fats": f,
        })

    notes = _health_notes(analysis)
    return {
        "metrics": metrics,
        "meals": plan,
        "totals": {
            "calories": total_cal,
            "protein": total_p,
            "carbs": total_c,
            "fats": total_f,
        },
        "notes": notes,
        "disclaimer": "SAMPLE GENERAL WELLNESS PLAN — educational only, not a medical prescription. "
                      "Adapt portion sizes and confirm with your healthcare professional.",
    }


def validate_diet_form(form):
    """Return (errors, cleaned_kwargs)."""
    errors = {}
    try:
        age = int(form.get("age", ""))
        if not 10 <= age <= 100:
            errors["age"] = "Please enter a valid age (10–100)."
    except (TypeError, ValueError):
        errors["age"] = "Please enter a valid age."
        age = None

    sex = (form.get("sex") or "").strip().lower()
    if sex not in ("male", "female"):
        errors["sex"] = "Please select biological sex."

    try:
        height = float(form.get("height", "").replace(",", "."))
        if not 100 <= height <= 250:
            errors["height"] = "Height should be 100–250 cm."
    except (TypeError, ValueError):
        errors["height"] = "Please enter a valid height in cm."
        height = None

    try:
        weight = float(form.get("weight", "").replace(",", "."))
        if not 30 <= weight <= 250:
            errors["weight"] = "Weight should be 30–250 kg."
    except (TypeError, ValueError):
        errors["weight"] = "Please enter a valid weight in kg."
        weight = None

    activity = (form.get("activity") or "").strip()
    if activity not in ACTIVITY_FACTOR:
        errors["activity"] = "Please select an activity level."

    diet_type = (form.get("diet") or "").strip().lower()
    if diet_type == "vegan":
        diet_type = "vegetarian"
    if diet_type not in ("vegetarian", "nonvegetarian", "vegan"):
        errors["diet"] = "Please select vegetarian or non-vegetarian."

    goal = (form.get("goal") or "").strip()
    if goal not in GOAL_ADJUST:
        errors["goal"] = "Please select a goal."

    allergies_raw = (form.get("allergies") or "").strip()
    allergies = [a.strip().strip(",") for a in re_split(allergies_raw)]

    try:
        meals_per_day = int(form.get("meals_per_day", "5"))
        if meals_per_day not in (3, 4, 5):
            raise ValueError
    except (TypeError, ValueError):
        errors["meals_per_day"] = "Choose 3, 4, or 5 meals per day."
        meals_per_day = 5

    return errors, {
        "age": age, "sex": sex, "height_cm": height, "weight_kg": weight,
        "activity": activity, "diet_type": diet_type, "goal": goal,
        "allergies": [a for a in allergies if a],
        "analysis": None,
        "preferences": (form.get("preferences") or "").strip(),
        "meals_per_day": meals_per_day,
    }


def re_split(val):
    return [x for x in (v.strip() for v in val.split(",")) if x]