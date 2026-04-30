import re

# -------------------------------
# Extract symptoms function
# -------------------------------
def detect_multiple_symptoms(text):
    symptom_keywords = [
        "fever", "cough", "cold", "headache", "vomiting", "pain",
        "nausea", "fatigue", "dizziness", "diarrhea", "sore throat",
        "chest pain", "shortness of breath", "rash", "bleeding",
        "stomach pain", "body pain"
    ]

    text = text.lower()
    found = []

    for s in symptom_keywords:
        if s in text:
            found.append(s)

    return list(set(found))


# -------------------------------
# Doctor matching function
# -------------------------------
def match_doctor_specialization(symptoms, doctor_db):
    matched_doctors = []

    for doc in doctor_db:
        spec_symptoms = doc.get("symptoms", [])

        score = len([s for s in symptoms if s.lower() in [x.lower() for x in spec_symptoms]])

        if score > 0:
            matched_doctors.append({
                "specialization": doc["specialization"],
                "doctor_name": doc.get("doctor_name", ""),
                "match_score": score
            })

    matched_doctors = sorted(matched_doctors, key=lambda x: x["match_score"], reverse=True)

    return matched_doctors[:3]
