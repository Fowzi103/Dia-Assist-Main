"""Lab value extraction and analysis from medical report text."""

import re
from datetime import datetime

# ---------------------------------------------------------------------------
# General-purpose reference ranges (used ONLY when the report gives no range).
# Each entry: test -> [low, high] (None means open-ended)
# ---------------------------------------------------------------------------
GENERAL_REFERENCE = {
    "glucose": (70, 99),
    "fasting glucose": (70, 99),
    "hba1c": (4.0, 5.6),
    "total cholesterol": (125, 200),
    "hdl": (40, 60),
    "ldl": (0, 100),
    "triglycerides": (0, 150),
    "hemoglobin": (12.0, 16.0),
    "vitamin d": (30, 100),
    "tsh": (0.4, 4.0),
    "creatinine": (0.6, 1.1),
    "alt": (7, 35),
    "ast": (8, 33),
}

# Canonical display names
TEST_LABELS = {
    "glucose": "Glucose",
    "fasting glucose": "Fasting Glucose",
    "hba1c": "HbA1c",
    "total cholesterol": "Total Cholesterol",
    "hdl": "HDL Cholesterol",
    "ldl": "LDL Cholesterol",
    "triglycerides": "Triglycerides",
    "hemoglobin": "Hemoglobin",
    "vitamin d": "Vitamin D",
    "tsh": "TSH",
    "creatinine": "Creatinine",
    "alt": "ALT",
    "ast": "AST",
    "blood pressure": "Blood Pressure",
}

# Ordered list of keys we attempt to locate (blood pressure handled separately)
TESTS = [k for k in TEST_LABELS.keys() if k != "blood pressure"]


class LabAnalyzer:
    """Structured extraction & analysis of medical lab values."""

    def __init__(self, text):
        self.text = text or ""

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _to_float(value_text):
        if value_text is None:
            return None
        value_text = value_text.strip()
        if not value_text:
            return None
        # normalize comma decimal separators
        value_text = value_text.replace(",", ".")
        match = re.search(r"-?\d+(?:\.\d+)?", value_text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    # -- patient info -----------------------------------------------------
    def extract_patient(self):
        info = {
            "name": None,
            "age": None,
            "sex": None,
            "date": None,
        }
        text = self.text

        # Name — stop at newline/colon so we don't swallow the next label
        m = re.search(
            r"(?:patient\s*name|name)\s*[:\-]?\s*([A-Za-z][A-Za-z .\-]{1,60})",
            text,
            re.IGNORECASE,
        )
        if m:
            cand = re.sub(r"\s+", " ", m.group(1)).strip().strip(":|,-")
            if 2 <= len(cand) <= 60:
                info["name"] = cand

        # Age
        m = re.search(
            r"(?:age|DOB|born)\s*[:\-]?\s*(\d{1,3})\s*(?:y(?:ears)?|yr|yo)?",
            text,
            re.IGNORECASE,
        )
        if m:
            age = self._to_float(m.group(1))
            if age is not None and 0 <= age <= 120:
                info["age"] = int(age)

        # Sex / gender
        m = re.search(
            r"(?:sex|gender)\s*[:\-]?\s*(male|female|m|f)",
            text,
            re.IGNORECASE,
        )
        if m:
            g = m.group(1).lower()
            info["sex"] = "Male" if g in ("male", "m") else "Female"

        # Date of report
        m = re.search(
            r"(?:report\s*date|date\s*of\s*report|collected\s*on|sample(?:d)?\s*(?:date)?|date)\s*[:\-]?\s*"
            r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[-\s](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
            r"[a-z]*[-\s,]+(?:20)?\d{2}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-\s,]\s*\d{1,2},?\s*(?:20)?\d{2}\b)",
            text,
            re.IGNORECASE,
        )
        if m:
            info["date"] = m.group(1).strip()
            # Normalize to ISO when possible
            parsed = self._normalize_date(info["date"])
            if parsed:
                info["date"] = parsed

        return info

    @staticmethod
    def _normalize_date(date_str):
        fmt_in = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y", "%Y-%m-%d",
                  "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d %b %y"]
        for fmt in fmt_in:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    # -- extraction helpers ----------------------------------------------
    def _extract_test(self, key):
        """Find (value, unit, [ref_low, ref_high]) for a given canonical key."""
        text = self.text
        value = None
        unit = None
        ref_low = None
        ref_high = None

        # Build regex patterns — several aliases per test.
        aliases = self._aliases(key)
        alias_pat = "|".join(re.escape(a) for a in aliases)
        if key == "glucose":
            # Do not match the "Glucose" part of "Fasting Glucose"
            alias_pat = "(?<!fasting\\s)" + alias_pat

        # Case 1: "HbA1c : 6.8 %" (value, optional unit, optional reference)
        pattern = (
            r"(?i)(?P<label>"
            + alias_pat
            + r")\s*[:\-–]\s*"
            r"(?P<val>[-+]?\d+(?:\.\d+)?|<?\s*\d+(?:\.\d+)?)\s*"
            r"(?P<unit>mg/dL|mg/dl|mmol/L|mmol/l|g/dL|g/dl|ng/mL|ng/ml|mIU/L|mIU/l|mU/L|U/L|u/L|IU/L|IU/ml|µg/mL|pg/mL|%|mmol/mol)?"
        )
        m = re.search(pattern, text)
        if m:
            val_raw = re.sub(r"[<>]", "", m.group("val"))
            value = self._to_float(val_raw)
            unit = m.group("unit") or ""
            # Try to find a reference range after this test line
            unit = unit or ""
            f_low, f_high = self._reference_after(m.end())
            if f_low is not None or f_high is not None:
                ref_low, ref_high = f_low, f_high

        # Case 2: glucose 128 mg/dl (REF 70–99)
        if value is None:
            pattern2 = (
                r"(?i)(?P<label>"
                + alias_pat
                + r")\s+"
                r"(?P<val>\d+(?:\.\d+)?)\s*"
                r"(?P<unit>mg/dL|mg/dl|mmol/L|mmol/l|g/dL|g/dl|ng/mL|ng/ml|mIU/L|U/L|%|mmol/mol)?"
            )
            m2 = re.search(pattern2, text)
            if m2:
                value = self._to_float(m2.group("val"))
                unit = m2.group("unit") or ""
                f_low, f_high = self._reference_after(m2.end())
                if f_low is not None or f_high is not None:
                    ref_low, ref_high = f_low, f_high
        return value, unit or "", ref_low, ref_high

    def _aliases(self, key):
        a = {
            "glucose": ["glucose", "fbs", "sugar", "blood sugar"],
            "fasting glucose": ["fasting glucose", "glucose fasting", "fbs"],
            "hba1c": ["hba1c", "glycated hemoglobin", "a1c", "hemoglobin a1c", "hba1c %"],
            "total cholesterol": ["total cholesterol", "cholesterol total", "t. cholesterol", "serum cholesterol"],
            "hdl": ["hdl", "hdl cholesterol", "high-density lipoprotein", "hdl-c"],
            "ldl": ["ldl", "ldl cholesterol", "low-density lipoprotein", "ldl-c"],
            "triglycerides": ["triglycerides", "triglyceride", "tg"],
            "hemoglobin": ["hemoglobin", "hgb", "hb", "haemoglobin"],
            "vitamin d": ["vitamin d", "25-oh vitamin d", "vit d", "25 hydroxyvitamin d", "25 (oh)d"],
            "tsh": ["tsh", "thyroid stimulating hormone", "thyrotropin"],
            "creatinine": ["creatinine", "serum creat", "creat"],
            "alt": ["alt", "alanine aminotransferase", "sgpt", "alanine transaminase"],
            "ast": ["ast", "aspartate aminotransferase", "sgot", "aspartate transaminase"],
            "blood pressure": ["blood pressure", "bp"],
        }
        return a.get(key, [key])

    def _reference_after(self, start_pos):
        """Scan a short window after start_pos for a reference range like 70 - 99 or < 200 or > 40.

        Only inspects the remainder of the current line plus up to two following
        lines (typical formats), so it cannot pick up a range belonging to the
        next test.
        """
        window = self.text[start_pos : start_pos + 220]
        lines = [ln for ln in window.splitlines() if ln.strip()]
        scan = "\n".join(lines[:3])
        if not scan:
            return None, None

        # Multi-number range: "Ref: 70 - 99", "Reference Range: 12–16", "RR 70-99"
        m = re.search(
            r"(?i)(?:ref(?:erence)?\s*(?:range)?|rr|rm|range)\s*[:\-]\s*"
            r"<?\s*(\d+(?:\.\d+)?)\s*[-––to]+\s*<?\s*(\d+(?:\.\d+)?)",
            scan,
        )
        if m:
            return self._to_float(m.group(1)), self._to_float(m.group(2))
        # Single-sided: "< 200" or "> 40"
        m = re.search(
            r"(?i)(?:ref(?:erence)?\s*(?:range)?|rr|rm)\s*[:\-]\s*(<|>)\s*(\d+(?:\.\d+)?)",
            scan,
        )
        if m:
            compare, val = m.group(1), self._to_float(m.group(2))
            if compare == "<":
                return None, val
            return val, None
        # Bare range on the same line (table-style reports): "128 | 70-99"
        m = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", scan)
        if m:
            return self._to_float(m.group(1)), self._to_float(m.group(2))
        return None, None

    # -- public API -------------------------------------------------------
    def detect_tests(self):
        detected = []
        for key in TESTS:
            value, unit, rlow, rhigh = self._extract_test(key)
            if value is not None:
                detected.append({
                    "key": key,
                    "test": TEST_LABELS[key],
                    "value": value,
                    "unit": unit,
                    "ref_low": rlow,
                    "ref_high": rhigh,
                })
        # Always attempt blood pressure (special format)
        self._extract_bp(detected)
        return detected

    def _extract_bp(self, detected):
        m = re.search(
            r"(?i)(?:blood\s*pressure|bp)\s*[:\-]\s*(\d{2,3})\s*/\s*(\d{2,3})",
            self.text,
        )
        if m:
            sys_v = self._to_float(m.group(1))
            dia_v = self._to_float(m.group(2))
            if sys_v and dia_v:
                detected.append({
                    "key": "blood pressure",
                    "test": "Blood Pressure",
                    "value_sys": sys_v,
                    "value_dia": dia_v,
                    "value": f"{sys_v:g}/{dia_v:g}",
                    "unit": "mmHg",
                    "ref_low": None,
                    "ref_high": None,
                    "is_bp": True,
                })

    def analyze(self):
        """Return full analysis list."""
        results = []
        for t in self.detect_tests():
            results.append(self._classify(t))
        return results

    def _classify(self, t):
        status = "UNKNOWN"
        explanation = ""
        significance = ""
        using_general = False

        if t.get("is_bp"):
            status, explanation, significance = self._bp_classify(t)
            return {**t, "status": status, "explanation": explanation,
                    "possible_significance": significance, "using_general": False}

        value = t["value"]
        ref_low, ref_high = t["ref_low"], t["ref_high"]
        key = t["key"].lower()

        if ref_low is None and ref_high is None and key in GENERAL_REFERENCE:
            ref_low, ref_high = GENERAL_REFERENCE[key]
            using_general = True
            t["ref_low"], t["ref_high"] = ref_low, ref_high

        if ref_low is None and ref_high is None:
            status = "UNKNOWN"
        elif ref_high is not None and ref_low is not None:
            if ref_low <= value <= ref_high:
                status = "NORMAL"
            else:
                span = (ref_high - ref_low) or (ref_high * 0.1)
                band_lo = ref_low - 0.1 * span
                band_hi = ref_high + 0.1 * span
                if band_lo <= value <= band_hi:
                    status = "BORDERLINE"
                elif value > ref_high:
                    status = "HIGH"
                else:
                    status = "LOW"
        elif ref_high is not None and value > ref_high:
            status = "HIGH"
        elif ref_low is not None and value < ref_low:
            status = "LOW"
        elif ref_high is not None or ref_low is not None:
            status = "NORMAL"

        explanation, significance = self._medical_explanation(t, status, using_general)
        return {**t, "status": status, "explanation": explanation,
                "possible_significance": significance, "using_general": using_general}

    def _bp_classify(self, t):
        sys_v = t.get("value_sys", 120)
        dia_v = t.get("value_dia", 80)
        if sys_v > 140 or dia_v > 90:
            return (
                "HIGH",
                "This blood pressure reading is above the commonly used threshold (≥130/80–140/90 mmHg). "
                "This may indicate elevated blood pressure and should be discussed with a healthcare professional.",
                "Elevated readings can be associated with increased cardiovascular risk.",
            )
        if sys_v >= 120 or dia_v >= 80:
            return (
                "BORDERLINE",
                "This reading is slightly raised relative to commonly used targets (~120/80 mmHg). "
                "Please confirm with your healthcare professional.",
                "Could be associated with early blood pressure elevation.",
            )
        return (
            "NORMAL",
            "This blood pressure reading is within the commonly accepted normal range (~120/80 mmHg).",
            "Generally healthy levels.",
        )

    def _medical_explanation(self, t, status, using_general):
        key = t["key"].lower()
        name = TEST_LABELS.get(key, key)
        unit = t["unit"] or ""
        value = t["value"]
        ref_txt = ""
        if t["ref_low"] is not None or t["ref_high"] is not None:
            if t["ref_low"] is not None and t["ref_high"] is not None:
                ref_txt = f"{t['ref_low']:g} – {t['ref_high']:g}"
            elif t["ref_high"] is not None:
                ref_txt = f"< {t['ref_high']:g}"
            else:
                ref_txt = f"> {t['ref_low']:g}"
            ref_txt += f" {unit}".strip()
        else:
            ref_txt = "no reference range available"

        src = "shown in your report" if not using_general else "a general reference range"

        base_norm = (
            f"{name} is {value:g} {unit} ".strip()
            + f"and falls inside the reference range ({ref_txt}) "
            + f"indicated in the report. This may be considered within expected limits."
        )
        base_high = (
            f"This result ({value:g} {unit}) is above the reference range shown in the report "
            + f"({ref_txt}). "
        )
        if using_general:
            base_high = (
                f"This result ({value:g} {unit}) is above the general reference range we used "
                + f"({ref_txt}). Please verify with your report. "
            )
        base_low = (
            f"This result ({value:g} {unit}) is below the reference range shown in the report "
            + f"({ref_txt}). "
        )
        if using_general:
            base_low = (
                f"This result ({value:g} {unit}) is below the general reference range we used "
                + f"({ref_txt}). Please verify with your report. "
            )

        significance = {
            "glucose": "A higher glucose can be associated with elevated blood sugar levels.",
            "fasting glucose": "A higher fasting glucose may indicate elevated fasting blood sugar.",
            "hba1c": "Higher HbA1c can be associated with elevated average blood glucose over recent months.",
            "total cholesterol": "Higher total cholesterol can be associated with increased cardiovascular risk.",
            "hdl": "Higher HDL is often considered favorable; lower HDL can be associated with increased risk.",
            "ldl": "Higher LDL cholesterol can be associated with increased cardiovascular risk.",
            "triglycerides": "Higher triglycerides can be associated with increased cardiovascular risk.",
            "hemoglobin": "Low hemoglobin can be associated with anemia; high hemoglobin may relate to other factors.",
            "vitamin d": "Low Vitamin D can be associated with bone health concerns and should be reviewed by a clinician.",
            "tsh": "Abnormal TSH can be associated with thyroid function changes.",
            "creatinine": "Abnormal creatinine can be associated with kidney function changes.",
            "alt": "Elevated ALT can be associated with liver enzyme changes.",
            "ast": "Elevated AST can be associated with liver enzyme changes.",
        }.get(key, "Review this result with your healthcare professional to understand its meaning.")

        specific = {
            ("hba1c", "HIGH"): "This may indicate elevated blood sugar and should be discussed with a healthcare professional.",
            ("glucose", "HIGH"): "This may indicate elevated blood sugar and should be discussed with a healthcare professional.",
            ("fasting glucose", "HIGH"): "This may indicate elevated fasting blood sugar and should be discussed with a healthcare professional.",
            ("ldl", "HIGH"): "This may indicate elevated LDL cholesterol and should be discussed with a healthcare professional.",
            ("triglycerides", "HIGH"): "This may indicate elevated triglycerides and should be discussed with a healthcare professional.",
            ("vitamin d", "LOW"): "This result is below the report's reference range. Management options should be discussed with a clinician.",
            ("hdl", "LOW"): "Lower HDL cholesterol should be discussed with a healthcare professional.",
            ("hemoglobin", "LOW"): "This may be associated with anemia and should be discussed with a healthcare professional.",
        }

        if status == "HIGH":
            ex = base_high + significance + " " + specific.get((key, "HIGH"), "")
        elif status == "LOW":
            ex = base_low + significance + " " + specific.get((key, "LOW"), "")
        elif status == "BORDERLINE":
            ex = (
                f"{name} is {value:g} {unit} — borderline relative to the reference range ({ref_txt}). "
                + "This is slightly outside typical values; discuss it with your healthcare professional."
            )
        else:
            ex = base_norm

        return ex.strip(), significance


def build_analysis(text):
    return LabAnalyzer(text).analyze()