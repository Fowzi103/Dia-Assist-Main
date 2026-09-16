"""Rule-based local assistant ("Ask Dia") — no external AI/API required."""

import re
from datetime import datetime

CAUTION = "This is general educational information only. Discuss your results with a healthcare professional."


class DiaAssistant:
    def __init__(self, analysis=None, patient=None, language="en", skin_context=None):
        self.analysis = analysis or []
        self.patient = patient or {}
        self.language = language if language in ("en", "kn", "te", "hi") else "en"
        self.skin_context = skin_context or {}

    # -- helpers ----------------------------------------------------------
    def _find(self, *keys):
        for item in self.analysis:
            if item["key"] in keys:
                return item
        return None

    def _report_brief(self):
        lines = []
        for item in self.analysis:
            s = item["status"]
            badge = {"HIGH": "high", "LOW": "low", "BORDERLINE": "borderline",
                     "NORMAL": "normal", "UNKNOWN": "unknown"}.get(s, s.lower())
            ref = ""
            if item.get("ref_low") is not None or item.get("ref_high") is not None:
                if item["ref_low"] is not None and item["ref_high"] is not None:
                    ref = f" (ref: {item['ref_low']:g}–{item['ref_high']:g})"
                elif item["ref_high"] is not None:
                    ref = f" (ref: < {item['ref_high']:g})"
                else:
                    ref = f" (ref: > {item['ref_low']:g})"
            val = item.get("value", "?")
            lines.append(f"{item['test']}: {val} {item.get('unit', '')} — {badge}{ref}")
        if not lines:
            return "No lab results are currently loaded. Upload a medical report first."
        return "\n".join(lines)

    # -- routing ----------------------------------------------------------
    def answer(self, question):
        q = (question or "").lower().strip()
        if not q:
            return "Please type a question for me to help with."

        if self.skin_context and any(term in q for term in ("skin", "redness", "dryness", "oiliness", "acne", "spots", "ಚರ್ಮ", "ಕೆಂಪು", "ಒಣ", "त्वचा", "लालिमा", "सूखापन", "చర్మం", "ఎరుపు", "పొడిబారడం")):
            return self._skin_answer()

        if ((self.language == "kn" and any(term in q for term in ("ವರದಿಯನ್ನು ವಿವರಿಸಿ", "ವರದಿ ವಿವರಿಸಿ"))) or
                (self.language == "te" and any(term in q for term in ("రిపోర్ట్‌ను వివరించండి", "రిపోర్ట్ వివరించండి"))) or
                (self.language == "hi" and any(term in q for term in ("मेरी रिपोर्ट समझाइए", "रिपोर्ट समझाइए")))):
            return self._explain_report()

        if re.search(r"\b(hi|hello|hey)\b", q, re.IGNORECASE):
            return self._greeting(q)
        if any(w in q for w in ("thank", "thanks")):
            return "You're welcome! I'm here to help you understand your report in a general way."
        if any(w in q for w in ("abnormal results", "abnormal values", "flagged results", "what is abnormal")):
            return self._abnormal_results()
        if any(w in q for w in ("explain my report", "my report", "explain report")):
            return self._explain_report()
        if any(w in q for w in ("glucose", "sugar", "hba1c", "a1c", "blood sugar")):
            return self._glucose(q)
        if any(w in q for w in ("cholesterol", "ldl", "hdl", "triglyceride")):
            return self._lipids(q)
        if any(w in q for w in ("vitamin d", "vit d")):
            return self._vitd()
        if any(w in q for w in ("tsh", "thyroid")):
            return self._tsh()
        if any(w in q for w in ("creatinine", "kidney")):
            return self._creatinine()
        if any(w in q for w in ("food", "diet", "eat", "vegetarian", "meal")):
            return self._diet(q)
        if any(w in q for w in ("doctor", "discuss", "dermatolog")):
            return self._doctor()
        if any(w in q for w in ("what is", "what does", "meaning", "means", "explain")):
            return self._explain_term(q)
        if any(w in q for w in ("medicine", "medication", "dose", "drug")):
            return self._no_prescription()
        if any(w in q for w in ("hello", "help", "what can you", "who are you")):
            return self._help()
        return ("I don't have enough information in your uploaded report to answer that accurately. "
                "Please ask about the results in your report — for example glucose, HbA1c, cholesterol, "
                "LDL, HDL, triglycerides, Vitamin D, TSH, creatinine, your diet, or what to discuss "
                "with your doctor.")

    # -- answers ----------------------------------------------------------
    def _greeting(self, q):
        name = self.patient.get("name") or "there"
        return (f"Hello {name}! I'm Dia. I can help explain the results in your uploaded medical report "
                f"and give general wellness guidance. Try asking things like 'Explain my report' or "
                "'What foods should I avoid?'")

    def _explain_report(self):
        brief = self._report_brief()
        abnormal = [i for i in self.analysis if i["status"] in ("HIGH", "LOW", "BORDERLINE")]
        if self.language == "kn":
            if abnormal:
                return f"ನಿಮ್ಮ ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ವರದಿಯ ಸಾರಾಂಶ ಇಲ್ಲಿದೆ:\n\n{brief}\n\nಹೆಚ್ಚು, ಕಡಿಮೆ ಅಥವಾ ಗಡಿ ಮಟ್ಟದಲ್ಲಿ ಕಂಡ ಫಲಿತಾಂಶಗಳು: {', '.join(i['test'] for i in abnormal)}. ಇವು ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸಬೇಕಾದ ವಿಷಯಗಳನ್ನು ಸೂಚಿಸಬಹುದು; ಇದು ಖಚಿತ ರೋಗನಿರ್ಣಯವಲ್ಲ."
            return f"ನಿಮ್ಮ ವರದಿಯಲ್ಲಿ ಕಂಡ ಫಲಿತಾಂಶಗಳು ಇಲ್ಲಿವೆ:\n\n{brief}\n\nಲಭ್ಯವಿರುವ ವರದಿ ಮಿತಿಗಳೊಳಗೆ ಫಲಿತಾಂಶಗಳು ಕಂಡುಬಂದಿವೆ. ಸಂಪೂರ್ಣ ವರದಿಯನ್ನು ವೈದ್ಯರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
        if self.language == "te":
            if abnormal:
                return f"మీ అప్‌లోడ్ చేసిన నివేదిక సారాంశం:\n\n{brief}\n\nఅధికం, తక్కువ లేదా సరిహద్దు ఫలితాలు: {', '.join(i['test'] for i in abnormal)}. ఇవి ఆరోగ్య నిపుణుడితో చర్చించాల్సిన విషయాలను సూచించవచ్చు; ఇది ఖచ్చితమైన నిర్ధారణ కాదు."
            return f"మీ నివేదికలో గుర్తించిన ఫలితాలు:\n\n{brief}\n\nఅందుబాటులో ఉన్న నివేదిక పరిధిలో ఫలితాలు ఉన్నాయి. పూర్తి నివేదికను వైద్యుడితో సమీక్షించండి."
        if self.language == "hi":
            if abnormal:
                return f"आपकी अपलोड की गई रिपोर्ट का सारांश:\n\n{brief}\n\nउच्च, कम या सीमांत परिणाम: {', '.join(i['test'] for i in abnormal)}। ये स्वास्थ्य पेशेवर से चर्चा के विषय हो सकते हैं; यह निश्चित निदान नहीं है।"
            return f"आपकी रिपोर्ट में मिले परिणाम:\n\n{brief}\n\nउपलब्ध रिपोर्ट सीमा के अनुसार परिणाम सामान्य हैं। पूरी रिपोर्ट डॉक्टर से साझा करें।"
        if abnormal:
            names = ", ".join(i["test"] for i in abnormal)
            return (f"Here's a summary of your uploaded report:\n\n{brief}\n\n"
                    f"Values flagged as high, low or borderline: {names}. "
                    f"These are not diagnoses — they may indicate areas to discuss with your "
                    f"healthcare professional.")
        return (f"Here's a summary of your uploaded report:\n\n{brief}\n\n"
                f"All detected values appear within their reference ranges shown. "
                f"Keep sharing your results with your doctor for a complete review.")

    def _glucose(self, q):
        keys = ("hba1c",) if any(term in q for term in ("hba1c", "a1c")) else ("glucose", "fasting glucose")
        item = self._find(*keys)
        if not item:
            return ("I don't see any glucose or HbA1c result in your uploaded report, so I can't "
                    "comment on it. Upload a report that includes these values.")
        ref = self._range_str(item)
        if item["status"] in ("HIGH", "BORDERLINE"):
            return (f"{item['test']} in your report is {self._value_str(item)}, {item['status'].lower()} "
                    f"compared to the reference {ref}. Higher glucose / HbA1c can be associated with "
                    f"elevated average blood sugar. This DOES NOT mean you have diabetes. It may indicate "
                    f"elevated blood sugar and should be discussed with a healthcare professional. "
                    f"Meanwhile, general suggestions include staying hydrated, choosing high-fiber foods, "
                    f"moderating refined carbs and sugary drinks. {CAUTION}")
        return (f"{item['test']} in your report is {self._value_str(item)}, within the reference {ref}. "
                f"Generally reassuring, but keep monitoring with your doctor.")

    def _lipids(self, q):
        keys = []
        if "ldl" in q:
            keys = ["ldl"]
        elif "hdl" in q:
            keys = ["hdl"]
        elif "triglyceride" in q:
            keys = ["triglycerides"]
        else:
            keys = ["total cholesterol", "ldl", "hdl", "triglycerides"]
        found = [i for i in self.analysis if i["key"] in keys]
        if not found:
            return ("I don't see those cholesterol-related results in your uploaded report, so I can't "
                    "answer accurately. Upload a report that includes total cholesterol, HDL, LDL, or triglycerides.")
        lines = []
        for it in found:
            status = it["status"].lower()
            lines.append(f"{it['test']}: {self._value_str(it)} — {status}")
        notes = ""
        if any(i["status"] in ("HIGH", "BORDERLINE") for i in found):
            notes = (" Some of these are above the reference ranges shown. Elevated LDL/total cholesterol "
                     "can be associated with cardiovascular risk. General suggestions: emphasize fiber-rich "
                     "foods, vegetables, fruits, whole grains, and moderate foods high in saturated/trans fats, and "
                     "keep up regular physical activity. Discuss the results with your doctor.")
        return "\n".join(lines) + notes + f" {CAUTION}"

    def _vitd(self):
        item = self._find("vitamin d")
        if not item:
            return ("I don't see a Vitamin D result in your uploaded report. Upload one that "
                    "includes Vitamin D to get an answer.")
        if item["status"] in ("LOW", "BORDERLINE"):
            return (f"Your Vitamin D result is {self._value_str(item)} — below the reference "
                    f"({self._range_str(item)}) in your report. This can be associated with bone health "
                    f"considerations. Management options (including any supplements or doses) should be "
                    f"discussed with your clinician — I do not prescribe supplements or dosages.")
        return (f"Your Vitamin D result is {self._value_str(item)}, which is within the reference "
                f"({self._range_str(item)}).")

    def _tsh(self):
        item = self._find("tsh")
        if not item:
            return "I don't see a TSH result in your report. Upload a report with TSH for an answer."
        return (f"Your TSH is {self._value_str(item)}, {item['status'].lower()} relative to the reference "
                f"{self._range_str(item)}. TSH changes can be associated with thyroid function. This is not "
                f"a diagnosis — discuss with your healthcare professional.")

    def _creatinine(self):
        item = self._find("creatinine")
        if not item:
            return "I don't see a creatinine result in your report."
        return (f"Your creatinine is {self._value_str(item)}, {item['status'].lower()} relative to the "
                f"reference {self._range_str(item)}. Creatinine can be associated with kidney function. "
                f"Discuss with your doctor if it falls outside the reference range.")

    def _diet(self, q):
        veggie = "vegetarian" in q
        lines = []
        if veggie:
            lines.append("Here are sample vegetarian-friendly choices (educational):")
        else:
            lines.append("Here are sample general choices (educational):")
        lines += [
            "Breakfast: oats with milk & berries, or a veggie omelette with toast",
            "Snacks: fresh fruit, a handful of nuts, or yogurt",
            "Lunch: dal with brown rice/rotis and a large salad (or grilled chicken/fish if non-vegetarian)",
            "Dinner: a light vegetable stir-fry or soup with whole grains",
            "Drink: water; limit sugary beverages"
        ]
        if self._find("glucose", "fasting glucose", "hba1c") and \
                self._find("glucose", "fasting glucose", "hba1c")["status"] in ("HIGH", "BORDERLINE"):
            lines.append("Your report shows elevated glucose-related values, so prefer high-fiber foods, "
                         "moderate refined carbs and avoid sugary drinks.")
        lipid_keys = ("ldl", "total cholesterol", "triglycerides")
        if any(self._find(key) and self._find(key)["status"] in ("HIGH", "BORDERLINE") for key in lipid_keys):
            lines.append("Your report shows an elevated lipid-related value, so emphasize fiber-rich foods, vegetables, fruits and whole grains, and moderate foods high in saturated fat.")
        lines.append(CAUTION)
        return "\n".join(lines)

    def _doctor(self):
        abnormal = [i for i in self.analysis if i["status"] in ("HIGH", "LOW", "BORDERLINE")]
        if abnormal:
            items = "\n".join(f"• {i['test']} — {i['status'].title()}" for i in abnormal)
            return (f"Based on your uploaded report, you may want to discuss the following with your "
                    f"doctor:\n{items}\n\nAsk about what these values may indicate and whether any "
                    f"further testing or follow-up is appropriate. {CAUTION}")
        return ("Currently I don't see any abnormal values in your uploaded report, but it's always a "
                f"good idea to review your full report with your doctor. {CAUTION}")

    def _abnormal_results(self):
        abnormal = [item for item in self.analysis if item.get("status") in ("HIGH", "LOW", "BORDERLINE")]
        if self.language == "kn":
            return "ಪ್ರಸ್ತುತ ವರದಿಯಲ್ಲಿ ಅಸಾಮಾನ್ಯ ಫಲಿತಾಂಶಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಇದು ರೋಗನಿರ್ಣಯವಲ್ಲ; ಸಂಪೂರ್ಣ ವರದಿಯನ್ನು ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ." if not abnormal else "ಪ್ರಸ್ತುತ ವರದಿಯಲ್ಲಿ ಗಮನಿಸಬೇಕಾದ ಫಲಿತಾಂಶಗಳು:\n" + "\n".join(f"• {i['test']}: {self._value_str(i)} — {i['status']}" for i in abnormal) + "\n\nಇವು ವೃತ್ತಿಪರ ಅನುಸರಣೆ ಅಗತ್ಯವಿರುವ ವಿಷಯಗಳನ್ನು ಸೂಚಿಸಬಹುದು."
        if self.language == "te":
            return "ప్రస్తుత నివేదికలో అసాధారణ ఫలితాలు కనిపించలేదు. ఇది నిర్ధారణ కాదు; పూర్తి నివేదికను ఆరోగ్య నిపుణుడితో సమీక్షించండి." if not abnormal else "ప్రస్తుత నివేదికలో గమనించాల్సిన ఫలితాలు:\n" + "\n".join(f"• {i['test']}: {self._value_str(i)} — {i['status']}" for i in abnormal) + "\n\nఇవి నిపుణుల అనుసరణ అవసరమైన విషయాలను సూచించవచ్చు."
        if self.language == "hi":
            return "वर्तमान रिपोर्ट में कोई असामान्य परिणाम नहीं दिखता। यह निदान नहीं है; पूरी रिपोर्ट स्वास्थ्य पेशेवर से साझा करें।" if not abnormal else "वर्तमान रिपोर्ट में ध्यान देने योग्य परिणाम:\n" + "\n".join(f"• {i['test']}: {self._value_str(i)} — {i['status']}" for i in abnormal) + "\n\nये पेशेवर फॉलो-अप के विषय हो सकते हैं।"
        if not abnormal:
            return "I do not see any values flagged high, low, or borderline in the currently loaded report. This is not a diagnosis; review the complete report with a healthcare professional."
        lines = [f"{item['test']}: {self._value_str(item)} — {item['status'].lower()} against {self._range_str(item)}" for item in abnormal]
        return "The currently loaded report flags:\n" + "\n".join(f"• {line}" for line in lines) + "\n\nThese findings may indicate topics for professional follow-up, not a definitive diagnosis."

    def _no_prescription(self):
        return ("I'm an educational assistant and I do not prescribe medicine, medication doses, or tell "
                "you to stop any medication. Please discuss all medication decisions with your healthcare "
                "professional. NEVER stop or change medication without their guidance.")

    def _help(self):
        return ("I can help with questions like:\n• 'Explain my report'\n• 'Why is my glucose high?'\n"
                "• 'What foods should I avoid?'\n• 'Explain HbA1c'\n• 'Create a vegetarian diet plan'\n"
                "• 'What does LDL mean?'\n• 'Which results should I discuss with my doctor?'")

    def _skin_answer(self):
        concerns = self.skin_context.get("concerns", [])
        names = ", ".join(item.get("concern", "visible feature") for item in concerns)
        if self.language == "kn":
            return f"ನಿಮ್ಮ ಚರ್ಮದ ಚಿತ್ರದಲ್ಲಿ ಕಾಣಬಹುದಾದ ಅಂಶಗಳು: {names}. ಇವು ದೃಶ್ಯ ಸೂಚನೆಗಳು ಮಾತ್ರ; ಖಚಿತ ರೋಗನಿರ್ಣಯವಲ್ಲ. ಮೃದುವಾದ ಆರೈಕೆ ಕ್ರಮವನ್ನು ಅನುಸರಿಸಿ ಮತ್ತು ಬದಲಾವಣೆ ಮುಂದುವರಿದರೆ ಚರ್ಮರೋಗ ತಜ್ಞರೊಂದಿಗೆ ಚರ್ಚಿಸಿ."
        if self.language == "te":
            return f"మీ చర్మ చిత్రంలో కనిపించే అంశాలు: {names}. ఇవి దృశ్య సూచనలు మాత్రమే; ఖచ్చితమైన నిర్ధారణ కాదు. మృదువైన సంరక్షణను కొనసాగించి మార్పులు ఉంటే చర్మ నిపుణుడితో చర్చించండి."
        if self.language == "hi":
            return f"आपकी त्वचा की तस्वीर में दिखाई देने वाले संकेत: {names}। ये केवल दृश्य संकेत हैं, निश्चित निदान नहीं। त्वचा की देखभाल को सरल रखें और बदलाव बने रहने पर त्वचा विशेषज्ञ से चर्चा करें।"
        return f"Your image shows these visible features: {names}. These are visual observations only, not a definitive diagnosis. Keep care gentle and discuss persistent changes with a dermatologist."

    def _explain_term(self, q):
        terms = {
            "hba1c": "HbA1c is a measure of your average blood sugar over the past ~2–3 months. "
                     "A high value can be associated with elevated average glucose; it is not by itself "
                     "a diabetes diagnosis.",
            "ldl": "LDL (low-density lipoprotein) is often called 'bad' cholesterol. High LDL can be "
                   "associated with cholesterol building up in blood vessels over time.",
            "hdl": "HDL (high-density lipoprotein) is often called 'good' cholesterol. Higher HDL is "
                   "generally considered favorable.",
            "triglycerides": "Triglycerides are a type of fat in the blood. High levels can be "
                             "associated with cardiovascular risk.",
            "creatinine": "Creatinine is a waste product from muscle metabolism. It gives a rough idea "
                          "of kidney filtering function.",
            "tsh": "TSH (thyroid stimulating hormone) regulates thyroid hormone release. Abnormal TSH "
                   "can relate to thyroid function.",
            "vitamin d": "Vitamin D supports bone health and other functions. Low levels can be "
                         "associated with bone health concerns.",
            "hemoglobin": "Hemoglobin carries oxygen in red blood cells. Low levels can be associated "
                          "with anemia.",
        }
        for key, defn in terms.items():
            if key in q:
                return f"{defn} {CAUTION}"
        return ("I don't recognize that term from your report or common lab values. "
                "I'd rather not guess — ask me about glucose, HbA1c, cholesterol, LDL, HDL, "
                "triglycerides, Vitamin D, TSH, creatinine, or hemoglobin.")

    # -- formatting helpers ----------------------------------------------
    @staticmethod
    def _value_str(item):
        val = item.get("value")
        if val is None:
            return "unknown"
        if isinstance(val, (int, float)):
            return f"{val:g} {item.get('unit', '')}".strip()
        return f"{val} {item.get('unit', '')}".strip()

    @staticmethod
    def _range_str(item):
        lo, hi = item.get("ref_low"), item.get("ref_high")
        unit = item.get("unit", "")
        if lo is not None and hi is not None:
            return f"{lo:g}–{hi:g} {unit}".strip()
        if hi is not None:
            return f"< {hi:g} {unit}".strip()
        if lo is not None:
            return f"> {lo:g} {unit}".strip()
        return "no reference range provided"


def chat_response(question, analysis=None, patient=None, current_date=None, language="en", skin_context=None):
    return DiaAssistant(analysis, patient, language=language, skin_context=skin_context).answer(question)