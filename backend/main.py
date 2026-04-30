from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

# Load API keys
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({"status": "backend running"}), 200


@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get("message", "")
    language = data.get("language", "en")

    # Temporary placeholder response (we will replace with NLP)
    return jsonify({
        "reply": f"Received your message: {user_message}",
        "language": language
    })


@app.route('/doctors', methods=['POST'])
def doctors():
    data = request.get_json()

    lat = data.get("lat")
    lon = data.get("lon")

    GEO_KEY = os.getenv("GEOAPIFY_KEY")

    if not GEO_KEY:
        return jsonify({"error": "Geoapify key missing"}), 500

    url = f"https://api.geoapify.com/v2/places?categories=healthcare&filter=circle:{lon},{lat},5000&limit=20&apiKey={GEO_KEY}"

    response = requests.get(url)
    return jsonify(response.json())


if __name__ == "__main__":
    app.run(debug=True)
