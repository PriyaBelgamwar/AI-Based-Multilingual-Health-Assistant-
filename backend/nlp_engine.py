from langdetect import detect
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util
import json
import re
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load keyword model
kw_model = KeyBERT()

# Load embeddings model
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Load symptoms database
with open("backend/symptoms_db.json", "r", encoding="utf-8") as f:
    SYMPTOM_DB = json.load(f)


# ----------- LANGUAGE DETECTION ----------------------------------

def detect_language(text):
    try:
        lang = detect(text)
        return lang
    except:
        return "en"


# ----------- KEYWORD EXTRACTION ---------------------------------

def extract_keywords(text):
    keywords = kw_model.extract_keywords(text, top_n=5)
    return [kw[0] for kw in keywords]


# ----------- EMBEDDING MATCHING ---------------------------------

def find_best_symptom_match(user_text):
    user_emb = embedder.encode(user_text, convert_to_tensor=True)

    best_match = None
    best_score = -1

    for symptom, details in SYMPTOM_DB.items():
        symptom_emb = embedder.encode(symptom, convert_to_tensor=True)
        sim = float(util.cos_sim(user_emb, symptom_emb))

        if sim > best_score:
            best_score = sim
            best_match = symptom

    return best_match, best_score


# ----------- SEVERITY DETECTION ---------------------------------

def detect_severity(text):
    text = text.lower()

    if any(word in text for word in ["severe", "high", "very bad", "worse"]):
        return "high"
    if any(word in text for word in ["mild", "little", "slight"]):
        return "low"

    return "medium"


# ----------- MAIN NLP FUNCTION ----------------------------------

def process_user_message(message):

    # Step 1 — detect language
    lang = detect_language(message)

    # Step 2 — extract keywords
    keywords = extract_keywords(message)

    # Step 3 — match best symptom
    symptom, score = find_best_symptom_match(message)

    # Step 4 — severity
    severity = detect_severity(message)

    return {
        "language": lang,
        "keywords": keywords,
        "matched_symptom": symptom,
        "similarity_score": round(score, 2),
        "severity": severity
    }