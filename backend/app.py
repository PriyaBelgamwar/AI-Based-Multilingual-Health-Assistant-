from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json, re, requests, difflib
import torch
from transformers import MarianMTModel, MarianTokenizer

# -------- GEOAPIFY API KEY --------
GEOAPIFY_API_KEY = "8a5448acede24df8bba4185b6401310f"

# -------- TRANSLATION LOADING --------
translation_models = {}

def get_translation_model(src_lang):
    if src_lang in translation_models:
        return translation_models[src_lang]
    if src_lang == "hi":
        model_name = "Helsinki-NLP/opus-mt-hi-en"
    elif src_lang == "mr":
        model_name = "Helsinki-NLP/opus-mt-mr-en"
    else:
        return None
    tok = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    translation_models[src_lang] = (tok, model)
    return tok, model

def translate_text(text: str, src_lang: str) -> str:
    tm = get_translation_model(src_lang)
    if not tm:
        return text.lower()
    tok, model = tm
    tokens = tok([text], return_tensors="pt", padding=True)
    with torch.no_grad():
        out = model.generate(**tokens)
    return tok.decode(out[0], skip_special_tokens=True).lower()

# -------- LANGUAGE DETECTION ----------
def detect_language(text: str) -> str:
    if re.search(r'[\u0900-\u097F]', text):
        if re.search(r'\b(आहे|आहेत|नाही)\b', text):
            return "mr"
        return "hi"
    return "en"

def tokenize_words(s: str):
    return re.findall(r"\w+", s.lower())

# ======================================================
# LOAD SYMPTOM DATASET
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYMPTOM_FILE = os.path.join(BASE_DIR, "symptoms_db.json")

if not os.path.exists(SYMPTOM_FILE):
    raise FileNotFoundError(f"Dataset not found at {SYMPTOM_FILE}")

with open(SYMPTOM_FILE, "r", encoding="utf-8") as f:
    SYMPTOM_DATA = json.load(f)

SYMPTOM_ALIASES = {}
for key, info in SYMPTOM_DATA.items():
    k = key.lower()
    aliases = set()

    for a in info.get("symptoms", {}).get("en", []):
        if a:
            aliases.add(a.lower())

    for d in info.get("diseases", []):
        aliases.add(d.lower())

    aliases.add(k)

    SYMPTOM_ALIASES[k] = {
        "eng": sorted(list(aliases)),
        "native": info.get("symptoms", {})
    }

# ======================================================
# MULTI-SYMPTOM MATCHING
# ======================================================
def detect_multiple_symptoms(text: str, original="", threshold=0.30):
    text = text.lower()
    tokens = set(tokenize_words(text))
    scores = {}

    for sym, data in SYMPTOM_ALIASES.items():
        best = 0
        for alias in data["eng"]:
            if alias in text:
                best = 1.0
            alias_tokens = set(tokenize_words(alias))
            if alias_tokens:
                overlap = len(tokens & alias_tokens) / len(alias_tokens)
                best = max(best, 0.2 + 0.6 * overlap)
        if best >= threshold:
            scores[sym] = best

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [s for s, sc in sorted_items], dict(sorted_items)

# ======================================================
# GEOAPIFY NEARBY DOCTORS
# ======================================================
def get_nearby_doctors(lat, lon, radius=5000):
    url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=healthcare.doctor,healthcare.hospital,healthcare.clinic&"
        f"filter=circle:{lon},{lat},{radius}&"
        f"bias=proximity:{lon},{lat}&limit=20&apiKey={GEOAPIFY_API_KEY}"
    )
    res = requests.get(url).json()
    out = []

    for r in res.get("features", []):
        p = r.get("properties", {})
        out.append({
            "name": p.get("name", "Not Available"),
            "address": p.get("address_line1", ""),
            "distance_meters": p.get("distance", 0),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "maps_url": f"https://www.google.com/maps?q={p.get('lat')},{p.get('lon')}"
        })
    return out

# ======================================================
# FASTAPI APP
# ======================================================
app = FastAPI(title="Unified Symptom Checker", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ------------------ MODELS ------------------
class Query(BaseModel):
    text: str
    lang: str = "en"

class LocationQuery(BaseModel):
    lat: float
    lon: float
    radius: int = 5000

# ======================================================
# CHAT ENDPOINT
# ======================================================
@app.post("/chat")
def chat(query: Query):
    original = query.text.strip()
    lang = query.lang.lower()

    translated = translate_text(original, lang) if lang != "en" else original.lower()
    keys, scores = detect_multiple_symptoms(translated, original)

    if not keys:
        return {
            "translated_text": translated,
            "symptoms": [],
            "advice": "Sorry, I could not detect any symptoms.",
            "doctor_types": [],
            "urgency_levels": []
        }

    advice = []
    doctors = []
    urg = []

    for s in keys:
        item = SYMPTOM_DATA.get(s, {})
        if "advice" in item:
            advice.append(item["advice"].get(lang) or item["advice"].get("en", ""))
        if "doctor_type" in item and item["doctor_type"] not in doctors:
            doctors.append(item["doctor_type"])
        if "urgency" in item and item["urgency"] not in urg:
            urg.append(item["urgency"])

    return {
        "translated_text": translated,
        "symptoms": keys,
        "scores": scores,
        "advice": " ".join(advice),
        "doctor_types": doctors,
        "urgency_levels": urg
    }

# ======================================================
# NEARBY DOCTORS ENDPOINT
# ======================================================
@app.post("/nearby-doctors")
def nearby_doctors_api(q: LocationQuery):
    return {"status": "success", "doctors": get_nearby_doctors(q.lat, q.lon, q.radius)}
