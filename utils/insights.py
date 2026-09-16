"""Educational wellness insights derived only from detected report values."""

from collections import defaultdict

ABNORMAL = ("HIGH", "LOW", "BORDERLINE")


def _value_text(item):
    value = item.get("value")
    unit = item.get("unit") or ""
    if value is None:
        return "unknown"
    if isinstance(value, (int, float)):
        return f"{value:g} {unit}".strip()
    return f"{value} {unit}".strip()


def _range_text(item):
    low, high = item.get("ref_low"), item.get("ref_high")
    unit = item.get("unit") or ""
    if low is not None and high is not None:
        return f"{low:g}-{high:g} {unit}".strip()
    if high is not None:
        return f"below {high:g} {unit}".strip()
    if low is not None:
        return f"above {low:g} {unit}".strip()
    return "the report's range"


def priority_groups(analysis):
    groups = {
        "Priority Attention": [],
        "Needs Attention": [],
        "Within Report Range": [],
        "Unknown / Not Available": [],
    }
    for item in analysis or []:
        status = item.get("status", "UNKNOWN")
        bucket = (
            "Priority Attention" if status in ("HIGH", "LOW") else
            "Needs Attention" if status == "BORDERLINE" else
            "Within Report Range" if status == "NORMAL" else
            "Unknown / Not Available"
        )
        groups[bucket].append(item)
    return groups


def quick_summary(analysis, language="en"):
    analysis = analysis or []
    if not analysis:
        return "No readable lab values were detected in this report."
    abnormal = [item for item in analysis if item.get("status") in ABNORMAL]
    normal = [item for item in analysis if item.get("status") == "NORMAL"]
    unknown = [item for item in analysis if item.get("status") == "UNKNOWN"]
    opening = {
        "kn": f"ಈ ವರದಿಯಿಂದ {len(analysis)} ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳು ಪತ್ತೆಯಾಗಿವೆ.",
        "te": f"ఈ నివేదికలో {len(analysis)} పరీక్షా ఫలితాలు గుర్తించబడ్డాయి.",
        "hi": f"इस रिपोर्ट में {len(analysis)} जांच परिणाम मिले हैं।",
    }.get(language, f"{len(analysis)} test result(s) were detected from this report.")
    parts = [opening]
    if abnormal:
        findings = "; ".join(
            f"{item['test']} is {_value_text(item)} ({item['status'].lower()} against {_range_text(item)})"
            for item in abnormal[:4]
        )
        parts.append({
            "kn": f"ಪ್ರಮುಖ ಅಂಶಗಳು: {findings}. ಇವು ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಚರ್ಚಿಸಬೇಕಾದ ವಿಷಯಗಳನ್ನು ಸೂಚಿಸಬಹುದು.",
            "te": f"ముఖ్యమైన ఫలితాలు: {findings}. ఇవి ఆరోగ్య నిపుణుడితో చర్చించాల్సిన విషయాలను సూచించవచ్చు.",
            "hi": f"महत्वपूर्ण परिणाम: {findings}। ये स्वास्थ्य पेशेवर से चर्चा के विषय हो सकते हैं।",
        }.get(language, f"Important findings first: {findings}. These may indicate areas to discuss with a healthcare professional."))
    if normal:
        parts.append({"kn": f"{len(normal)} ಫಲಿತಾಂಶಗಳು ಲಭ್ಯವಿರುವ ವರದಿ ಮಿತಿಯೊಳಗೆ ಇವೆ.", "te": f"{len(normal)} ఫలితాలు అందుబాటులో ఉన్న నివేదిక పరిధిలో ఉన్నాయి.", "hi": f"{len(normal)} परिणाम उपलब्ध रिपोर्ट सीमा में हैं।"}.get(language, f"{len(normal)} detected result(s) are within the report ranges available."))
    if unknown:
        parts.append({"kn": f"{len(unknown)} ಫಲಿತಾಂಶಗಳನ್ನು ವರ್ಗೀಕರಿಸಲು ಸಾಕಷ್ಟು ಉಲ್ಲೇಖ ಮಾಹಿತಿ ಇಲ್ಲ.", "te": f"{len(unknown)} ఫలితాలను వర్గీకరించడానికి తగిన రిఫరెన్స్ సమాచారం లేదు.", "hi": f"{len(unknown)} परिणामों के वर्गीकरण के लिए पर्याप्त संदर्भ जानकारी नहीं है।"}.get(language, f"{len(unknown)} detected result(s) did not have enough reference information for classification."))
    return " ".join(parts)


def insights(analysis, language="en"):
    analysis = analysis or []
    abnormal = [item for item in analysis if item.get("status") in ABNORMAL]
    normal = [item for item in analysis if item.get("status") == "NORMAL"]
    important = [
        f"{item['test']}: {_value_text(item)} is {item['status'].lower()} compared with {_range_text(item)}."
        for item in abnormal
    ]
    positive = [f"{item['test']} is within the report range ({_value_text(item)})." for item in normal]
    next_steps = [
        ({"kn": "ಗುರುತಿಸಲಾದ ಮೌಲ್ಯಗಳು ಮತ್ತು ವರದಿ ಉಲ್ಲೇಖ ಮಿತಿಗಳನ್ನು ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ.", "te": "గుర్తించిన విలువలు మరియు నివేదిక రిఫరెన్స్ పరిధిని ఆరోగ్య నిపుణుడితో సమీక్షించండి.", "hi": "चिह्नित परिणामों और रिपोर्ट की संदर्भ सीमा को स्वास्थ्य पेशेवर के साथ देखें।"}.get(language, "Review flagged values and the report's reference ranges with a healthcare professional.") if abnormal else {"kn": "ನಿಮ್ಮ ವರದಿಯನ್ನು ಉಳಿಸಿ ಮತ್ತು ಮುಂದಿನ ನಿಯಮಿತ ಭೇಟಿಯಲ್ಲಿ ಸಂಪೂರ್ಣ ಫಲಿತಾಂಶಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.", "te": "మీ నివేదికను ఉంచి తదుపరి సాధారణ సందర్శనలో పూర్తి ఫలితాలను సమీక్షించండి.", "hi": "अपनी रिपोर्ट रखें और अगली नियमित मुलाकात में पूरे परिणाम देखें।"}.get(language, "Keep your report and review the complete results at your next routine appointment.")),
        {"kn": "ಆಹಾರ ಯೋಜಕವನ್ನು ಸಾಮಾನ್ಯ ಕ್ಷೇಮದ ಮಾದರಿ ಯೋಜನೆಯಾಗಿ ಮಾತ್ರ ಬಳಸಿ; ಚಿಕಿತ್ಸೆಯಾಗಿ ಅಲ್ಲ.", "te": "ఆహార ప్లానర్‌ను సాధారణ ఆరోగ్య నమూనా ప్రణాళికగా మాత్రమే ఉపయోగించండి; చికిత్సగా కాదు.", "hi": "डाइट प्लानर को केवल सामान्य वेलनेस नमूना योजना के रूप में उपयोग करें, उपचार के रूप में नहीं।"}.get(language, "Use the diet planner as a sample general wellness plan, not as treatment."),
        {"kn": "ತೀವ್ರ ಲಕ್ಷಣಗಳು ಅಥವಾ ವೈದ್ಯರು ತುರ್ತು ಎಂದು ಹೇಳಿದ ಫಲಿತಾಂಶಗಳಿದ್ದರೆ ತಕ್ಷಣ ವೃತ್ತಿಪರ ಆರೈಕೆ ಪಡೆಯಿರಿ.", "te": "తీవ్రమైన లక్షణాలు లేదా వైద్యుడు అత్యవసరంగా గుర్తించిన ఫలితం ఉంటే వెంటనే నిపుణుల సంరక్షణ పొందండి.", "hi": "गंभीर लक्षणों या डॉक्टर द्वारा urgent बताए गए परिणामों पर तुरंत पेशेवर देखभाल लें।"}.get(language, "Seek prompt professional care for severe symptoms or a clinician-identified urgent result."),
    ]
    return {
        "important": important or ["No results were flagged outside the available report ranges."],
        "positive": positive or ["No within-range results were available to summarize."],
        "next_steps": next_steps,
    }


def doctor_questions(analysis, language="en"):
    questions = []
    for item in analysis or []:
        if item.get("status") in ABNORMAL:
            questions.extend({
                "kn": [f"ನನ್ನ {item['test']} ಫಲಿತಾಂಶ {_value_text(item)} ಕುರಿತು ಅನುಸರಣೆ ಬೇಕೇ?", f"ಈ {item['test']} ಮೌಲ್ಯವನ್ನು ಎಷ್ಟು ಬಾರಿ ಪರಿಶೀಲಿಸಬೇಕು?", "ಜೀವನಶೈಲಿ ಅಂಶಗಳು ಈ ಫಲಿತಾಂಶದ ಮೇಲೆ ಪರಿಣಾಮ ಬೀರುತ್ತವೆಯೇ ಮತ್ತು ಹೆಚ್ಚುವರಿ ಪರೀಕ್ಷೆಗಳು ಸೂಕ್ತವೇ?"],
                "te": [f"నా {item['test']} ఫలితం {_value_text(item)} గురించి ఫాలో-అప్ అవసరమా?", f"ఈ {item['test']} విలువను ఎంత తరచుగా పర్యవేక్షించాలి?", "జీవనశైలి అంశాలు ఈ ఫలితాన్ని ప్రభావితం చేయగలవా మరియు అదనపు పరీక్షలు సరైనవా?"],
                "hi": [f"क्या मेरे {item['test']} परिणाम {_value_text(item)} पर फॉलो-अप जरूरी है?", f"इस {item['test']} मान की कितनी बार निगरानी करनी चाहिए?", "क्या जीवनशैली इस परिणाम को प्रभावित कर सकती है और क्या अतिरिक्त जांच उचित है?"],
            }.get(language, [f"Should I follow up on my {item['test']} result of {_value_text(item)}?", f"How often should this {item['test']} value be monitored?", "Could lifestyle factors affect this result, and are additional tests appropriate?"]))
    return questions[:12]


def wellness_goals(analysis, language="en"):
    keys = {item.get("key") for item in analysis or [] if item.get("status") in ABNORMAL}
    goals = []
    if keys.intersection({"glucose", "fasting glucose", "hba1c"}):
        goals.append(({"kn": "ಆಹಾರ", "te": "పోషణ", "hi": "पोषण"}.get(language, "Nutrition"), {"kn": "ಹೆಚ್ಚು ನಾರಿನ ಆಹಾರ ಆರಿಸಿ ಮತ್ತು ಸಂಸ್ಕರಿತ ಕಾರ್ಬೋಹೈಡ್ರೇಟ್‌ಗಳನ್ನು ಮಿತಿಗೊಳಿಸಿ.", "te": "ఎక్కువ ఫైబర్ ఉన్న ఆహారాన్ని ఎంచుకుని శుద్ధి చేసిన కార్బోహైడ్రేట్లను పరిమితం చేయండి.", "hi": "अधिक फाइबर वाले भोजन चुनें और रिफाइंड कार्बोहाइड्रेट सीमित करें।"}.get(language, "Choose more high-fiber foods and moderate refined carbohydrates.")))
    if keys.intersection({"ldl", "total cholesterol", "triglycerides"}):
        goals.append(({"kn": "ಹೃದಯ ಸ್ನೇಹಿ ಆಯ್ಕೆಗಳು", "te": "హృదయానికి అనుకూల ఎంపికలు", "hi": "हृदय के लिए अच्छे विकल्प"}.get(language, "Heart-friendly choices"), {"kn": "ತರಕಾರಿಗಳು, ಹಣ್ಣುಗಳು ಮತ್ತು ಸಂಪೂರ್ಣ ಧಾನ್ಯಗಳನ್ನು ಸೇರಿಸಿ; ಸ್ಯಾಚುರೇಟೆಡ್ ಕೊಬ್ಬನ್ನು ಮಿತಿಗೊಳಿಸಿ.", "te": "కూరగాయలు, పండ్లు మరియు సంపూర్ణ ధాన్యాలను చేర్చండి; సంతృప్త కొవ్వు అధికంగా ఉన్న ఆహారాన్ని పరిమితం చేయండి.", "hi": "सब्जियां, फल और साबुत अनाज लें; संतृप्त वसा वाले भोजन सीमित करें।"}.get(language, "Include vegetables, fruits and whole grains; moderate foods high in saturated fat.")))
    goals.extend([
        ({"kn": "ದೈಹಿಕ ಚಟುವಟಿಕೆ", "te": "శారీరక చలనం", "hi": "शारीरिक गतिविधि"}.get(language, "Physical activity"), {"kn": "ನಿಮಗೆ ಅನುಕೂಲವಾದ ನಿಯಮಿತ, ಮಧ್ಯಮ ಚಟುವಟಿಕೆಯನ್ನು ವಾರದಲ್ಲಿ ಸೇರಿಸಿ.", "te": "మీకు అనుకూలంగా సాధారణ మితమైన చలనాన్ని వారంలో చేర్చండి.", "hi": "अपनी सुविधा के अनुसार नियमित, मध्यम गतिविधि करें।"}.get(language, "Build regular, moderate movement into your week as comfortable.")),
        ({"kn": "ನಿದ್ರೆ", "te": "నిద్ర", "hi": "नींद"}.get(language, "Sleep"), {"kn": "ನಿಯಮಿತ ನಿದ್ರೆ ಕ್ರಮವನ್ನು ಕಾಪಾಡಿ ಮತ್ತು ವಿಶ್ರಾಂತಿಗೆ ಸಮಯ ನೀಡಿ.", "te": "స్థిరమైన నిద్ర అలవాటును ఉంచి విశ్రాంతికి సమయం కేటాయించండి.", "hi": "नियमित नींद की दिनचर्या रखें और आराम के लिए समय दें।"}.get(language, "Keep a consistent sleep routine and protect time for rest.")),
        ({"kn": "ಅನುಸರಣೆ", "te": "ఫాలో-అప్", "hi": "फॉलो-अप"}.get(language, "Follow-up"), {"kn": "ಗುರುತಿಸಲಾದ ಫಲಿತಾಂಶಗಳು ಮತ್ತು ಮೇಲ್ವಿಚಾರಣೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಚರ್ಚಿಸಿ.", "te": "గుర్తించిన ఫలితాలు మరియు పర్యవేక్షణ ప్రశ్నలను ఆరోగ్య నిపుణుడితో చర్చించండి.", "hi": "चिह्नित परिणामों और निगरानी के सवालों पर स्वास्थ्य पेशेवर से चर्चा करें।"}.get(language, "Discuss flagged findings and monitoring questions with a healthcare professional.")),
    ])
    return [{"name": name, "text": text, "progress": 0} for name, text in goals[:5]]


def diet_guidance(analysis, language="en"):
    keys = {item.get("key") for item in analysis or [] if item.get("status") in ("HIGH", "BORDERLINE")}
    notes = []
    if keys.intersection({"glucose", "fasting glucose", "hba1c"}):
        notes.extend({"kn": ["ತರಕಾರಿಗಳು, ಬೇಳೆಕಾಳುಗಳು ಮತ್ತು ಸಂಪೂರ್ಣ ಧಾನ್ಯಗಳಂತಹ ನಾರಿನ ಆಹಾರ ಆರಿಸಿ.", "ಸಂಸ್ಕರಿತ ಕಾರ್ಬೋಹೈಡ್ರೇಟ್‌ಗಳನ್ನು ಮಿತಿಗೊಳಿಸಿ ಮತ್ತು ಸಕ್ಕರೆ ಪಾನೀಯಗಳನ್ನು ಕಡಿಮೆ ಮಾಡಿ."], "te": ["కూరగాయలు, పప్పులు మరియు సంపూర్ణ ధాన్యాల వంటి అధిక ఫైబర్ ఆహారాన్ని ఎంచుకోండి.", "శుద్ధి చేసిన కార్బోహైడ్రేట్లను పరిమితం చేసి చక్కెర పానీయాలను తగ్గించండి."], "hi": ["सब्जियां, दालें और साबुत अनाज जैसे फाइबर वाले भोजन चुनें।", "रिफाइंड कार्बोहाइड्रेट सीमित करें और मीठे पेय कम करें।"]}.get(language, ["Choose high-fiber foods such as vegetables, legumes and whole grains.", "Moderate refined carbohydrates and reduce sugary drinks."]))
    if keys.intersection({"ldl", "total cholesterol", "triglycerides"}):
        notes.extend({"kn": ["ನಾರಿನ ಆಹಾರ, ತರಕಾರಿಗಳು, ಹಣ್ಣುಗಳು ಮತ್ತು ಸೂಕ್ತ ಸಂಪೂರ್ಣ ಧಾನ್ಯಗಳಿಗೆ ಆದ್ಯತೆ ನೀಡಿ.", "ಸ್ಯಾಚುರೇಟೆಡ್ ಮತ್ತು ಟ್ರಾನ್ಸ್ ಕೊಬ್ಬು ಅಧಿಕವಾಗಿರುವ ಆಹಾರವನ್ನು ಮಿತಿಗೊಳಿಸಿ."], "te": ["ఫైబర్ ఉన్న ఆహారం, కూరగాయలు, పండ్లు మరియు సరైన సంపూర్ణ ధాన్యాలకు ప్రాధాన్యం ఇవ్వండి.", "సంతృప్త మరియు ట్రాన్స్ కొవ్వులు అధికంగా ఉన్న ఆహారాన్ని పరిమితం చేయండి."], "hi": ["फाइबर वाले भोजन, सब्जियों, फलों और साबुत अनाज को प्राथमिकता दें।", "संतृप्त और ट्रांस वसा वाले भोजन सीमित करें।"]}.get(language, ["Emphasize fiber-rich foods, vegetables, fruits and appropriate whole grains.", "Moderate foods high in saturated and trans fats."]))
    return notes or [{"kn": "ತರಕಾರಿಗಳು, ಹಣ್ಣುಗಳು, ಸಂಪೂರ್ಣ ಧಾನ್ಯಗಳು ಮತ್ತು ಸಾಕಷ್ಟು ನೀರಿನೊಂದಿಗೆ ಸಮತೋಲಿತ ಆಹಾರ ಕ್ರಮವನ್ನು ಕಾಪಾಡಿ.", "te": "కూరగాయలు, పండ్లు, సంపూర్ణ ధాన్యాలు మరియు తగినంత నీటితో సమతుల్య ఆహారాన్ని కొనసాగించండి.", "hi": "सब्जियों, फलों, साबुत अनाज और पर्याप्त पानी वाला संतुलित भोजन रखें।"}.get(language, "Maintain a varied, balanced eating pattern with vegetables, fruits, whole grains and adequate hydration.")]


def trend_series(rows):
    """Build safe, numeric series from persisted report rows."""
    series = defaultdict(list)
    for row in rows or []:
        report_date = row.get("report_date") or row.get("uploaded_at") or ""
        for item in row.get("analysis", []):
            value = item.get("value")
            if isinstance(value, (int, float)) and not item.get("is_bp"):
                series[item["key"]].append({
                    "test": item["test"], "value": value, "unit": item.get("unit", ""),
                    "date": report_date, "filename": row.get("filename", ""),
                })
    result = []
    for key, points in series.items():
        points.sort(key=lambda point: point["date"])
        if len(points) < 2:
            direction = "Stable"
        else:
            delta = points[-1]["value"] - points[0]["value"]
            baseline = max(abs(points[0]["value"]), 1)
            direction = "Stable" if abs(delta) <= baseline * 0.02 else ("Increasing" if delta > 0 else "Decreasing")
        result.append({"key": key, "test": points[0]["test"], "unit": points[0]["unit"], "points": points, "direction": direction})
    return sorted(result, key=lambda item: item["test"])


def compare_reports(previous, current):
    """Compare only numeric tests present in the two supplied reports."""
    previous = {item.get("key"): item for item in (previous or [])}
    changes = []
    for item in current or []:
        key = item.get("key")
        value = item.get("value")
        old = previous.get(key)
        old_value = old.get("value") if old else None
        if not isinstance(value, (int, float)):
            continue
        if not isinstance(old_value, (int, float)):
            direction = "NEW"
            delta = None
        else:
            delta = value - old_value
            baseline = max(abs(old_value), 1)
            direction = "Stable" if abs(delta) <= baseline * 0.02 else ("Increasing" if delta > 0 else "Decreasing")
        changes.append({
            "test": item.get("test"), "unit": item.get("unit", ""),
            "previous": old_value, "current": value, "delta": delta,
            "direction": direction,
        })
    for key, old in previous.items():
        if key not in {item.get("key") for item in (current or [])} and isinstance(old.get("value"), (int, float)):
            changes.append({"test": old.get("test"), "unit": old.get("unit", ""), "previous": old.get("value"), "current": None, "delta": None, "direction": "NOT AVAILABLE"})
    return changes


def build_intelligence(analysis, language="en"):
    groups = priority_groups(analysis)
    return {
        "summary": quick_summary(analysis, language),
        "groups": groups,
        "insights": insights(analysis, language),
        "questions": doctor_questions(analysis, language),
        "goals": wellness_goals(analysis, language),
        "diet_guidance": diet_guidance(analysis, language),
    }
