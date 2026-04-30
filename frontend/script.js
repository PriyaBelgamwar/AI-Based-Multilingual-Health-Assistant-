// ---------- AI Symptom Chatbot Frontend + Hybrid Map System ----------

document.addEventListener('DOMContentLoaded', () => {

  // ---------- DOM References ----------
  const chatToggle = document.getElementById('chat-toggle');
  const chatCard = document.getElementById('chatbot-card');
  const closeChat = document.getElementById('close-chat');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const chatBox = document.getElementById('chat-box');
  const languageSelect = document.getElementById('language');
  const heroStart = document.getElementById('hero-start');
  const showMapBtn = document.getElementById("showMapBtn");
  const mapDiv = document.getElementById("map");

  const API_URL = "http://10.20.235.201:8000/chat";

  // ---------- Shortcut Nearby Hospitals (Manual Real List) ----------
  const FIXED_HOSPITALS = [
    { name: "Ruby Hall Clinic", lat: 18.4822, lng: 73.8937 },
    { name: "Vedanta Hospital", lat: 18.4860, lng: 73.8901 },
    { name: "Jehangir Hospital", lat: 18.5285, lng: 73.8760 },
    { name: "City Care Clinic", lat: 18.4878, lng: 73.8941 },
    { name: "Sahyadri Hospital Bibwewadi", lat: 18.4625, lng: 73.8669 }
  ];

  // ---------- Force Location = Bibwewadi VIT ----------
  const DEFAULT_LOCATION = { lat: 18.4639, lng: 73.8674 };

  function correctCoordinates(lat, lng) {
    const dist = Math.sqrt(
      Math.pow(lat - DEFAULT_LOCATION.lat, 2) +
      Math.pow(lng - DEFAULT_LOCATION.lng, 2)
    );

    if (dist > 0.05) {
      console.warn("⚠ Laptop GPS wrong → forcing Bibwewadi VIT");
      return DEFAULT_LOCATION;
    }

    return { lat, lng };
  }

  // ---------- Chat Toggle ----------
  function openChat() {
    chatCard.classList.add('open');
    if (!chatBox.querySelector('.bot-message')) showWelcome();
  }
  function closeChatFn() { chatCard.classList.remove('open'); }

  chatToggle?.addEventListener('click', () => {
    chatCard.classList.contains('open') ? closeChatFn() : openChat();
  });

  closeChat?.addEventListener('click', closeChatFn);
  heroStart?.addEventListener('click', openChat);

  // ---------- Chat UI ----------
  function appendMessage(sender, text, meta = {}) {
    const msg = document.createElement('div');
    msg.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');

    const content = document.createElement('div');
    content.classList.add('msg-content');
    content.innerText = text;
    msg.appendChild(content);

    if (meta.translated_text) {
      const trans = document.createElement('div');
      trans.style.fontSize = '12px';
      trans.style.color = '#555';
      trans.innerText = `Translated: ${meta.translated_text}`;
      msg.appendChild(trans);
    }

    if (meta.symptoms?.length) {
      const sym = document.createElement('div');
      sym.style.fontSize = "12px";
      sym.innerHTML = `🩺 Detected symptoms: <b>${meta.symptoms.join(", ")}</b>`;
      msg.appendChild(sym);
    }

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function showTyping() {
    const t = document.createElement('div');
    t.classList.add('typing-indicator');
    t.innerText = '⏳ Bot is typing...';
    chatBox.appendChild(t);
    return t;
  }

  // ---------- BACKEND ----------
  async function fetchBackendReply(message, lang) {
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: message, lang })
      });
      if (!response.ok) return null;
      return await response.json();
    } catch (e) {
      console.warn("Backend fetch failed:", e);
      return null;
    }
  }

  async function getFinalResponse(msg, lang) {
    const server = await fetchBackendReply(msg, lang);

    if (server && server.translated_text) {
      return {
        reply: server.advice || "I have analyzed your symptoms.",
        symptoms: server.symptoms || [],
        translated_text: server.translated_text
      };
    }

    return {
      reply: "I am not sure. But you can check nearby hospitals.",
      symptoms: [],
      translated_text: null
    };
  }

  // ---------- SEND MESSAGE ----------
  async function sendMessage() {
    const input = userInput.value.trim();
    if (!input) return;

    const lang = languageSelect.value;
    appendMessage('user', input);
    userInput.value = "";

    const typing = showTyping();

    const { reply, symptoms, translated_text } = await getFinalResponse(input, lang);

    typing.remove();
    appendMessage('bot', reply, { symptoms, translated_text });

    speak(reply);

    if (/doctor|hospital|clinic|physician/i.test(reply)) {
      getUserLocation(coords => showFixedHospitals(coords));
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

  // ---------- SPEECH ----------
  function startListening() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return alert("Speech not supported.");
    const rec = new SR();
    rec.lang = languageSelect.value + "-IN";
    rec.start();
    rec.onresult = e => {
      userInput.value = e.results[0][0].transcript;
      sendMessage();
    };
  }
  window.startListening = startListening;

  function speak(text) {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = languageSelect.value + "-IN";
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }

  // ---------- GOOGLE MAP + FIXED HOSPITALS ----------
  let map;
  let userMarker;
  let placeMarkers = [];

  function getUserLocation(callback) {
    if (!navigator.geolocation) {
      alert("Your browser does not support location.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      pos => {
        let coords = correctCoordinates(pos.coords.latitude, pos.coords.longitude);
        callback(coords);
      },
      () => {
        callback(DEFAULT_LOCATION);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  function initGoogleMap(coords) {
    mapDiv.style.display = "block";

    if (!map) {
      map = new google.maps.Map(document.getElementById("map"), {
        center: coords,
        zoom: 14,
      });
    } else {
      map.setCenter(coords);
    }

    if (userMarker) userMarker.setMap(null);

    userMarker = new google.maps.Marker({
      position: coords,
      map: map,
      title: "You are here",
      icon: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png"
    });
  }

  function showFixedHospitals(coords) {
    initGoogleMap(coords);

    placeMarkers.forEach(m => m.setMap(null));
    placeMarkers = [];

    FIXED_HOSPITALS.forEach(h => {
      const marker = new google.maps.Marker({
        position: { lat: h.lat, lng: h.lng },
        map,
        title: h.name
      });

      const info = new google.maps.InfoWindow({
        content: `
          <b>${h.name}</b><br><br>
          <a href="https://www.google.com/maps/dir/${coords.lat},${coords.lng}/${h.lat},${h.lng}"
          target="_blank" style="color:blue;text-decoration:underline;">
            📍 Get Directions
          </a>
        `
      });

      marker.addListener("click", () => info.open(map, marker));
      placeMarkers.push(marker);
    });

    appendMessage('bot', `🗺️ Showing nearby hospitals on the map.`);
  }

  if (showMapBtn) {
    showMapBtn.addEventListener("click", () => {
      getUserLocation(coords => showFixedHospitals(coords));
    });
  }

  // ---------- Welcome ----------
  function showWelcome() {
    appendMessage('bot', "Hello! I’m your Health Assistant. Tell me your symptoms.");
  }

  showWelcome();
});
