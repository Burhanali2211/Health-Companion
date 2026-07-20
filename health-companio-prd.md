# WATAN SEHAT — Complete Product Requirements Document
## Raspberry Pi Pitch Demo Build | End-to-End Specification

**Version:** 1.0  
**Status:** Implementation Ready  
**Platform:** Raspberry Pi 5 + 7" HDMI Touch Display (800×480) + Mic + Speaker  
**Dev Environment:** Windows + WSL2 → Transfer to Pi  
**Stack:** Python + FastAPI + React + Vite + Tailwind + SQLite + Whisper + Coqui TTS

---

## 0. Document Purpose

This PRD covers everything from Step 3 (after WSL2 + project scaffold is set up) through to a fully deployed, demo-ready kiosk running on Raspberry Pi. It is the single source of truth for the entire build. Every feature, every file, every screen, every API endpoint, every content entry, every Pi configuration setting is specified here. Nothing is left to assumption.

---

## 1. Project Summary

Watan Sehat is a Kashmir-specific offline-first health companion running as a kiosk application on a Raspberry Pi 5 with a 7" touch display. It demonstrates seasonal health intelligence, a voice-activated companion, diet guidance rooted in Kashmiri tradition, age-adaptive content, and full Koshur/Urdu language support — all functioning without internet connectivity.

**Primary purpose of this build:** Investor pitch demonstration.  
**Secondary purpose:** Proof of concept that validates the product vision end-to-end.

---

## 2. Hardware Specification

| Component | Spec | Notes |
|---|---|---|
| SBC | Raspberry Pi 5 (4GB or 8GB) | 8GB preferred for TTS model |
| Display | 7" HDMI LCD Touch, 800×480 | Capacitive touch, HDMI + USB for touch |
| Microphone | USB microphone | Position 30-60cm from speaker |
| Speaker | USB or 3.5mm speaker | Minimum 3W for clear voice output |
| Storage | 32GB+ microSD (Class 10 / A2) | Samsung or SanDisk recommended |
| OS | Raspberry Pi OS Bookworm (64-bit) | Desktop version |
| Power | Official Pi 5 27W USB-C PSU | Unstable power = random crashes in demo |

---

## 3. Repository Structure — Complete

```
watan-sehat/
│
├── backend/
│   ├── main.py                        # FastAPI app, all routes
│   ├── seasonal_engine.py             # Kashmir calendar + district logic
│   ├── companion.py                   # Rule engine + Anthropic API fallback
│   ├── diet_engine.py                 # Diet plan selector by season + age
│   ├── exercise_engine.py             # Exercise selector by season + age
│   ├── voice/
│   │   ├── stt.py                     # Whisper speech-to-text
│   │   └── tts.py                     # Coqui TTS text-to-speech
│   ├── data/
│   │   ├── seasons.json               # Kashmir seasonal calendar (embedded)
│   │   ├── diet_plans.json            # All diet content — season × age
│   │   ├── exercises.json             # Exercise library — season × age
│   │   ├── companion_rules.json       # 60 rule-based companion responses
│   │   ├── koshur_phrases.json        # Koshur UI strings
│   │   └── kangri_safety.json         # Kangri CO safety content
│   ├── database/
│   │   ├── init_db.py                 # Schema creation script
│   │   └── watan.db                   # SQLite database (auto-created)
│   ├── requirements.txt
│   └── .env                           # ANTHROPIC_API_KEY (optional)
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                    # Root with router
│   │   ├── store/
│   │   │   └── appStore.js            # Zustand global state
│   │   ├── hooks/
│   │   │   ├── useSeasonData.js       # Season API hook
│   │   │   ├── useVoice.js            # Mic recording hook
│   │   │   └── useOnlineStatus.js     # Network detection hook
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── TopBar.jsx
│   │   │   │   └── NavBar.jsx
│   │   │   ├── ui/
│   │   │   │   ├── SeasonCard.jsx
│   │   │   │   ├── NetworkBadge.jsx
│   │   │   │   ├── AgeModeToggle.jsx
│   │   │   │   ├── TouchButton.jsx
│   │   │   │   └── KangriAlert.jsx
│   │   │   └── companion/
│   │   │       ├── VoiceOrb.jsx
│   │   │       ├── ResponseCard.jsx
│   │   │       └── QuickPrompts.jsx
│   │   └── pages/
│   │       ├── Home.jsx               # Season dashboard
│   │       ├── Companion.jsx          # Voice companion interface
│   │       ├── Diet.jsx               # Dastarkhwan module
│   │       ├── Exercise.jsx           # Kasrat module
│   │       └── Buzurg.jsx             # Dedicated elderly interface
│   └── public/
│       └── assets/
│           ├── fonts/                 # Noto Nastaliq Urdu (local)
│           ├── icons/                 # SVG icons
│           └── illustrations/         # Kashmiri visual assets
│
├── pi-setup/
│   ├── setup.sh                       # One-command Pi setup
│   ├── kiosk.sh                       # Chromium kiosk launcher
│   ├── watan-sehat.service            # Systemd backend service
│   └── config-additions.txt           # Lines to add to /boot/config.txt
│
├── content/
│   └── content-spec.md               # All content written out for data files
│
├── CLAUDE.md                          # Master prompt for AI continuation
└── README.md
```

---

## 4. Application Screens — Complete Specification

### 4.1 Screen Dimensions and Layout Grid

**Canvas:** 800px × 480px. Fixed. No scroll. No zoom.  
**Safe zones:** 16px padding on all sides.  
**Top bar:** 48px height.  
**Content area:** 416px height (480 - 48 topbar - 16 bottom padding).  
**Touch target minimum:** 44×44px. Preferred: 56×56px.

---

### 4.2 Screen 1: Home (Season Dashboard)

**Route:** `/` (default)  
**Purpose:** First thing investors see. Must be beautiful, information-dense, immediately understandable.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐ 48px
│ [وطن صحت] [Watan Sehat]   [بچہ][جوان][بزرگ]   [●Online]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │ 140px
│  │  ❄️  چلہ کلاں          Day 14    Srinagar -4°/2° │   │
│  │  "The harshest 40 days of Kashmir winter"        │   │
│  │  ⚠ شدید سردی۔ صبح 9 بجے سے پہلے باہر نہ جائیں │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐          │ 200px
│  │    🍲    │  │    🎙️        │  │    🏃    │          │
│  │ دسترخوان │  │  صحت ساتھی  │  │   کسرت   │          │
│  │  Diet    │  │  Companion   │  │ Exercise │          │
│  └──────────┘  └──────────────┘  └──────────┘          │
│                                                          │
│  [🔥 کانگڑی احتیاط — Kangri Safety Alert today]        │ 56px
└─────────────────────────────────────────────────────────┘
```

**Components rendered:**
- `TopBar` with app name, age mode toggle, network badge
- `SeasonCard` showing season name (Urdu + English), day number, district, temperature range, daily alert in Urdu
- Three `NavTile` components for Diet, Companion, Exercise
- `KangriAlert` strip — shown only during Chilla Kalan, Chilla Khurd, Chilla Bachha, Early Winter

**Data source:** `GET /api/context/{district}` — falls back to embedded seasonal engine if offline.

**State managed:** `ageMode` (bacha/jawaan/buzurg), `district`, font scaling for buzurg mode.

---

### 4.3 Screen 2: Health Companion (Voice Companion)

**Route:** `/companion`  
**Purpose:** The demo centerpiece. Investor speaks. App responds intelligently. Offline.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐ 48px
│ [← Back]  صحت ساتھی — Health Companion    [●Offline]   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │ 180px
│  │                                                  │   │
│  │          [RESPONSE TEXT APPEARS HERE]            │   │
│  │           In Urdu / Koshur / English             │   │
│  │           depending on active age mode           │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│         ┌────────────────────────────────┐              │
│         │  [  🎙️  TAP TO SPEAK  ]       │  56px        │
│         │  Listening... / Processing...  │              │
│         └────────────────────────────────┘              │
│                                                          │
│  Quick prompts (tap to ask):                            │
│  [سردی میں کیا کھائیں؟] [آج کی ورزش؟] [بزرگوں کا خیال]  │
└─────────────────────────────────────────────────────────┘
```

**Voice flow:**
1. User taps the orb → mic activates → visual pulse animation
2. Whisper STT transcribes speech → text appears in input display
3. Rule engine checks transcribed text → matches intent
4. If online + no rule match → Anthropic API call with Kashmir health system prompt
5. Response text displays on screen
6. Coqui TTS synthesizes response → plays through speaker
7. Orb returns to idle state

**Companion states (visual):**
- `idle` — soft pulse, "بات کریں" (Speak)
- `listening` — active pulse, red indicator, "سن رہا ہوں..." (Listening)
- `processing` — spinner, "سوچ رہا ہوں..." (Thinking)
- `speaking` — wave animation, "جواب دے رہا ہوں" (Responding)
- `error` — gentle error, "دوبارہ کوشش کریں" (Try again)

**Quick prompts (pre-set, tap without speaking):**
- "چلہ کلاں میں کیا کھائیں؟" — What to eat in Chilla Kalan
- "آج کی ورزش بتائیں" — Today's exercise
- "بزرگوں کا خیال کیسے رکھیں" — How to care for elderly
- "کانگڑی محفوظ استعمال" — Safe Kangri use
- "قوت مدافعت کیسے بڑھائیں" — How to boost immunity

**Age mode effect on companion:**
- Bacha: response simplified, shorter sentences, friendly tone, English mixed in
- Jawaan: balanced Urdu-English, practical advice, direct
- Buzurg: full Koshur, larger response text (buzurg-lg), slower TTS speed, warmer TTS voice profile

---

### 4.4 Screen 3: Dastarkhwan (Diet Module)

**Route:** `/diet`  
**Purpose:** Show season-appropriate, age-appropriate, culturally authentic Kashmiri diet guidance.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ [← Back]  دسترخوان — Diet Guide     [Season: چلہ کلاں] │
├─────────────────────────────────────────────────────────┤
│  [Morning] [Afternoon] [Evening]  [Immunity] [Avoid]   │ 44px tabs
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────┐  ┌────────────────────┐        │
│  │  🍲 حریسہ         │  │  ☕ نون چائے       │        │
│  │  Harissa           │  │  Noon Chai          │        │
│  │  High protein      │  │  Electrolytes +     │        │
│  │  Internal heat     │  │  Warming spices     │        │
│  │  [Why this?]       │  │  [Why this?]        │        │
│  └────────────────────┘  └────────────────────┘        │
│                                                          │
│  ┌────────────────────┐  ┌────────────────────┐        │
│  │  🥜 خشک میوے      │  │  🌿 کہوا            │        │
│  │  Dry Fruits        │  │  Kehwa              │        │
│  │  Vitamin E + heat  │  │  Anti-inflammatory  │        │
│  │  [Why this?]       │  │  [Why this?]        │        │
│  └────────────────────┘  └────────────────────┘        │
│                                                          │
│  ⚠ آج سے پرہیز: ٹھنڈے مشروبات، کچی سبزیاں           │
└─────────────────────────────────────────────────────────┘
```

**Tabs:** Morning / Afternoon / Evening / Immunity Focus / Avoid Today

**Food card contains:**
- Name in Urdu + English
- 1-line health reason (why this food in this season)
- Icon
- "Why this?" expander — shows the science-tradition bridge text

**Age-mode variation:**
- Bacha: calcium emphasis, school lunch suggestions, portions for children
- Jawaan: energy density, protein, work performance framing
- Buzurg: soft foods flag, easy digestion badge, medication interaction warnings

**Data source:** `GET /api/diet/{season}/{age_mode}/{meal_time}`

---

### 4.5 Screen 4: Kasrat (Exercise Module)

**Route:** `/exercise`  
**Purpose:** Show offline, equipment-free, culturally appropriate exercise guidance.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ [← Back]  کسرت — Exercise       [Indoor 🔒 Chilla Mode] │
├─────────────────────────────────────────────────────────┤
│  [Indoor] [Outdoor*] [Elderly] [Breathing] [Morning]   │ 44px tabs
│           *Locked during Chilla Kalan                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Exercise 1 of 6                    [▶ Start]   │   │
│  │                                                  │   │
│  │  [ILLUSTRATION: Person doing seated stretch      │   │
│  │   in traditional Kashmiri clothing]              │   │
│  │                                                  │   │
│  │  گھٹنوں کی ورزش — Knee Circulation              │   │
│  │  ⏱ 3 minutes  |  💺 Seated  |  👴 Safe for all  │   │
│  │                                                  │   │
│  │  بیٹھ کر گھٹنوں کو آہستہ آہستہ گھمائیں...      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│              [← Previous]    [Next →]                   │
└─────────────────────────────────────────────────────────┘
```

**Season locking logic:**
- Chilla Kalan → Outdoor tab shows lock icon + "Too cold for outdoor exercise" message
- Chilla Khurd → Outdoor tab unlocked 10 AM–2 PM only (time-aware)
- Grind/Wahaar → All tabs available

**Exercise card contains:**
- Illustration (SVG — offline, no image dependency)
- Name Urdu + English
- Duration, position (seated/standing), safety level
- Step-by-step instructions in Urdu
- Buzurg-safe badge if appropriate

**Data source:** `GET /api/exercise/{season}/{age_mode}/{type}`

---

### 4.6 Screen 5: Buzurg Mode (Dedicated Elderly Interface)

**Route:** `/buzurg` (accessed by holding Buzurg toggle for 2 seconds)  
**Purpose:** Completely simplified interface specifically for elderly users. Jumbo text, Koshur, voice-forward.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│                    وطن صحت                              │
│                 بزرگ ساتھی                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│     السلام علیکم                                        │
│     آج آپ کیسا محسوس کر رہے ہیں؟                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  الحمدللہ   │  │  تھوڑا تھکا  │  │  ٹھیک نہیں   │  │
│  │    اچھا ہوں  │  │   محسوس ہے  │  │    لگ رہا    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│          [🆘 مدد چاہیے — EMERGENCY]                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Behaviors:**
- On open: TTS speaks the greeting in Koshur automatically
- Three response buttons branch to different daily health content
- Emergency button sends SMS to pre-configured family number (via system SMS, offline-capable)
- No navigation bar — only back gesture or button
- Font: buzurg-xl throughout

---

## 5. Backend API — Complete Endpoint Specification

### Base URL: `http://localhost:8000`

| Endpoint | Method | Description | Offline |
|---|---|---|---|
| `/` | GET | Health check | ✅ |
| `/api/context/{district}` | GET | Current season + health context | ✅ |
| `/api/districts` | GET | All Kashmir districts | ✅ |
| `/api/diet/{season}/{age}/{meal}` | GET | Diet recommendations | ✅ |
| `/api/exercise/{season}/{age}/{type}` | GET | Exercise list | ✅ |
| `/api/companion/ask` | POST | Process companion query | ✅ (rules) / 🌐 (API) |
| `/api/voice/stt` | POST | Speech to text (audio file) | ✅ |
| `/api/voice/tts` | POST | Text to speech (returns audio) | ✅ |
| `/api/kangri/safety` | GET | Current Kangri safety status | ✅ |
| `/api/sync/check` | GET | Check for content updates | 🌐 |

### Request/Response Schemas

**GET /api/context/{district}**
```json
{
  "season": {
    "name_en": "Chilla Kalan",
    "name_ur": "چلہ کلاں",
    "name_koshur": "چلہ کلان",
    "icon": "❄️",
    "severity": "extreme",
    "context_en": "The harshest 40 days of Kashmir winter",
    "daily_alert_ur": "شدید سردی۔ صبح 9 بجے سے پہلے باہر نہ جائیں۔"
  },
  "day_number": 14,
  "district": {
    "name": "Srinagar",
    "altitude": 1585,
    "coldFactor": 1.0
  },
  "temp_min": -4,
  "temp_max": 2,
  "kangri_alert": true,
  "outdoor_exercise_safe": false,
  "timestamp": "2024-01-04T09:30:00"
}
```

**POST /api/companion/ask**
```json
// Request
{
  "query": "چلہ کلاں میں کیا کھائیں؟",
  "age_mode": "buzurg",
  "district": "srinagar",
  "language": "ur"
}

// Response
{
  "response_text": "چلہ کلاں میں حریسہ سب سے بہترین ہے...",
  "response_koshur": "چلہ کلانس منز حریسہ سب سے وَکھ چھُہ...",
  "source": "rule",
  "navigate_to": "diet",
  "confidence": 0.95
}
```

**POST /api/voice/stt**
```json
// Request: multipart/form-data with audio file
// Response
{
  "transcript": "چلہ کلاں میں کیا کھائیں",
  "language_detected": "ur",
  "confidence": 0.89
}
```

**POST /api/voice/tts**
```json
// Request
{
  "text": "چلہ کلاں میں حریسہ سب سے بہترین ہے",
  "age_mode": "buzurg",
  "language": "ur"
}
// Response: audio/wav binary
```

---

## 6. Data File Specifications — Content to Build

### 6.1 companion_rules.json Structure

60 rules minimum. Each rule:
```json
{
  "id": "rule_001",
  "intent": "winter_diet",
  "triggers_ur": ["کھانا", "کھائیں", "غذا", "سردی میں کھانا"],
  "triggers_en": ["eat", "food", "diet", "what to eat"],
  "season_filter": ["chilla_kalan", "chilla_khurd", "chilla_bachha"],
  "age_filter": null,
  "response_ur": "چلہ کلاں میں حریسہ، نون چائے اور خشک میوے سب سے بہترین ہیں۔ یہ جسم کو اندر سے گرم رکھتے ہیں اور قوت مدافعت بڑھاتے ہیں۔",
  "response_koshur": "چلہ کلانس منز حریسہ، نون چھائے تہ خوشکہ میوہ چھہِ سبہ ووتہ وَکھ۔",
  "response_en": "During Chilla Kalan, Harissa, Noon Chai and dry fruits are the best. They keep the body warm internally and boost immunity.",
  "navigate_to": "diet",
  "priority": 1
}
```

**Required rule categories (10 rules each minimum):**
1. Winter diet questions (season-specific)
2. Exercise questions (indoor/outdoor/elderly)
3. Clothing and layering guidance
4. Kangri safety queries
5. Elderly care questions
6. Children health questions (school/cold)
7. Immunity and prevention
8. General seasonal greetings and small talk
9. Emergency and unwell responses
10. App navigation help

### 6.2 diet_plans.json Structure

```json
{
  "chilla_kalan": {
    "bacha": {
      "morning": [
        {
          "id": "ck_b_m_001",
          "name_ur": "حریسہ",
          "name_en": "Harissa",
          "icon": "🍲",
          "reason_ur": "پروٹین سے بھرپور — بچوں کو سکول میں توانائی دیتا ہے",
          "reason_en": "High protein — sustained energy for school in cold weather",
          "science_bridge": "Harissa's slow-digesting mutton protein provides 6-8 hours of sustained energy, critical when children are cold and their bodies burn more calories to maintain temperature.",
          "portion_guidance": "1 cup with 1 roti — sufficient for a child",
          "avoid_with": null
        }
      ],
      "afternoon": [],
      "evening": [],
      "immunity": [],
      "avoid": []
    },
    "jawaan": {},
    "buzurg": {}
  },
  "sonth": {},
  "wahaar": {},
  "grind": {},
  "harud": {},
  "early_winter": {},
  "chilla_khurd": {},
  "chilla_bachha": {}
}
```

### 6.3 exercises.json Structure

```json
{
  "chilla_kalan": {
    "indoor": {
      "bacha": [],
      "jawaan": [
        {
          "id": "ck_j_in_001",
          "name_ur": "گھر میں اسکواٹ",
          "name_en": "Indoor Squats",
          "duration_minutes": 5,
          "sets": 3,
          "reps": 12,
          "position": "standing",
          "equipment": "none",
          "space_required": "2x2 feet",
          "buzurg_safe": false,
          "steps_ur": [
            "سیدھے کھڑے ہوں، پیر کندھوں کی چوڑائی پر",
            "آہستہ آہستہ بیٹھنے کی پوزیشن میں جائیں",
            "گھٹنے پیروں کی انگلیوں سے آگے نہ جائیں",
            "واپس کھڑے ہوں"
          ],
          "illustration_id": "squat_indoor_01",
          "winter_benefit": "Leg circulation in cold weather, prevents joint stiffness"
        }
      ],
      "buzurg": []
    },
    "outdoor": null,
    "breathing": {},
    "morning": {}
  }
}
```

### 6.4 koshur_phrases.json — UI Strings

```json
{
  "app_name": "وطن صحت",
  "tagline": "کشمیریوں کا صحت ساتھی",
  "nav": {
    "home": "گھر",
    "diet": "دسترخوان",
    "companion": "صحت ساتھی",
    "exercise": "کسرت",
    "back": "واپس"
  },
  "companion": {
    "greeting": "السلام علیکم",
    "tap_to_speak": "بات کرنے کے لیے دبائیں",
    "listening": "سن رہا ہوں...",
    "processing": "سوچ رہا ہوں...",
    "speaking": "جواب دے رہا ہوں",
    "error": "دوبارہ کوشش کریں"
  },
  "buzurg": {
    "morning_greeting": "السلام علیکم — آج آپ کیسا محسوس کر رہے ہیں؟",
    "feeling_good": "الحمدللہ — اچھا ہوں",
    "feeling_tired": "تھوڑا تھکا محسوس ہے",
    "feeling_unwell": "ٹھیک نہیں لگ رہا",
    "emergency": "مدد چاہیے"
  },
  "network": {
    "online": "آن لائن",
    "offline": "آف لائن — تمام خدمات دستیاب"
  },
  "seasons": {
    "chilla_kalan": "چلہ کلاں",
    "chilla_khurd": "چلہ خرد",
    "chilla_bachha": "چلہ بچہ",
    "sonth": "سونتھ",
    "wahaar": "وہار",
    "grind": "گرند",
    "harud": "ہرد",
    "early_winter": "ابتدائی سردی"
  }
}
```

---

## 7. Voice System — Technical Specification

### 7.1 Speech-to-Text (Whisper)

**Model:** `openai/whisper-tiny` for Pi (39MB), `whisper-base` for laptop testing  
**Language support:** Urdu (`ur`), English (`en`), auto-detect  
**Processing mode:** Local inference, no API call  
**Audio format input:** 16kHz mono WAV  
**Max recording duration:** 8 seconds  
**Silence detection threshold:** -40dB for 1.5 seconds = auto-stop

```python
# backend/voice/stt.py — Complete implementation
import whisper
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import os

class WhisperSTT:
    def __init__(self, model_size="tiny"):
        self.model = whisper.load_model(model_size)
        self.sample_rate = 16000
        self.silence_threshold = 0.01
        self.silence_duration = 1.5

    def record_until_silence(self, max_duration=8) -> str:
        """Record audio, stop on silence, return transcript."""
        audio_chunks = []
        silence_frames = 0
        frames_per_chunk = int(self.sample_rate * 0.1)
        silence_limit = int(self.silence_duration / 0.1)

        with sd.InputStream(samplerate=self.sample_rate,
                            channels=1, dtype='float32') as stream:
            for _ in range(int(max_duration / 0.1)):
                chunk, _ = stream.read(frames_per_chunk)
                audio_chunks.append(chunk)
                rms = np.sqrt(np.mean(chunk**2))
                if rms < self.silence_threshold:
                    silence_frames += 1
                    if silence_frames >= silence_limit:
                        break
                else:
                    silence_frames = 0

        audio = np.concatenate(audio_chunks, axis=0).flatten()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, self.sample_rate, audio)
            result = self.model.transcribe(f.name, language=None)
            os.unlink(f.name)

        return result["text"].strip(), result.get("language", "ur")

    def transcribe_file(self, filepath: str) -> dict:
        result = self.model.transcribe(filepath, language=None)
        return {
            "transcript": result["text"].strip(),
            "language": result.get("language", "ur")
        }
```

### 7.2 Text-to-Speech (Coqui TTS)

**Model:** `tts_models/ur/cv/vits` (Urdu) — 45MB  
**Fallback:** `tts_models/en/ljspeech/tacotron2-DDC` (English)  
**Speed modifier:** 
- jawaan: 1.0x
- buzurg: 0.85x (slower, clearer)
- bacha: 1.05x

```python
# backend/voice/tts.py — Complete implementation
from TTS.api import TTS
import tempfile
import os

class CoquiTTS:
    def __init__(self):
        # Primary Urdu model
        self.tts_ur = TTS("tts_models/ur/cv/vits", gpu=False)
        # English fallback
        self.tts_en = TTS("tts_models/en/ljspeech/tacotron2-DDC", gpu=False)

    def synthesize(self, text: str, language: str = "ur",
                   age_mode: str = "jawaan") -> str:
        """Synthesize text, return path to WAV file."""
        speed_map = {"bacha": 1.05, "jawaan": 1.0, "buzurg": 0.85}
        speed = speed_map.get(age_mode, 1.0)

        tts = self.tts_ur if language == "ur" else self.tts_en

        with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir="/tmp") as f:
            tts.tts_to_file(text=text, file_path=f.name, speed=speed)
            return f.name
```

### 7.3 Frontend Voice Hook

```javascript
// frontend/src/hooks/useVoice.js
import { useState, useRef, useCallback } from "react"
import axios from "axios"

const API = "http://localhost:8000"

export function useVoice(ageMode = "jawaan") {
  const [state, setState] = useState("idle")
  // idle | listening | processing | speaking | error
  const [transcript, setTranscript] = useState("")
  const [response, setResponse] = useState(null)
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])

  const startListening = useCallback(async () => {
    setState("listening")
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.current = new MediaRecorder(stream)
    audioChunks.current = []

    mediaRecorder.current.ondataavailable = e => {
      audioChunks.current.push(e.data)
    }

    mediaRecorder.current.onstop = async () => {
      setState("processing")
      const blob = new Blob(audioChunks.current, { type: "audio/wav" })
      const form = new FormData()
      form.append("audio", blob, "recording.wav")

      try {
        const sttRes = await axios.post(`${API}/api/voice/stt`, form)
        const text = sttRes.data.transcript
        setTranscript(text)

        const askRes = await axios.post(`${API}/api/companion/ask`, {
          query: text,
          age_mode: ageMode,
          district: "srinagar",
          language: "ur"
        })

        setResponse(askRes.data)
        setState("speaking")

        // Play TTS audio
        const ttsRes = await axios.post(
          `${API}/api/voice/tts`,
          { text: askRes.data.response_ur, age_mode: ageMode, language: "ur" },
          { responseType: "blob" }
        )
        const audio = new Audio(URL.createObjectURL(ttsRes.data))
        audio.onended = () => setState("idle")
        audio.play()

      } catch {
        setState("error")
        setTimeout(() => setState("idle"), 3000)
      }

      stream.getTracks().forEach(t => t.stop())
    }

    mediaRecorder.current.start()
    setTimeout(() => {
      if (mediaRecorder.current?.state === "recording") {
        mediaRecorder.current.stop()
      }
    }, 8000)

  }, [ageMode])

  const stopListening = useCallback(() => {
    if (mediaRecorder.current?.state === "recording") {
      mediaRecorder.current.stop()
    }
  }, [])

  return { state, transcript, response, startListening, stopListening }
}
```

---

## 8. Global State Management

```javascript
// frontend/src/store/appStore.js
import { create } from "zustand"

export const useAppStore = create((set) => ({
  // Core state
  ageMode: "jawaan",          // bacha | jawaan | buzurg
  district: "srinagar",
  isOnline: navigator.onLine,
  currentSeason: null,
  healthContext: null,

  // Actions
  setAgeMode: (mode) => set({ ageMode: mode }),
  setDistrict: (d) => set({ district: d }),
  setOnline: (v) => set({ isOnline: v }),
  setHealthContext: (ctx) => set({ healthContext: ctx, currentSeason: ctx?.season }),
}))
```

---

## 9. Design System — Watan Sehat Visual Identity

### 9.1 Color Tokens

| Token | Hex | Usage |
|---|---|---|
| `watan-saffron` | #E8821A | Primary accent, season name, CTA |
| `watan-chinar` | #C0392B | Alerts, Kangri warning, urgent |
| `watan-dal` | #2E86AB | Companion module, water, calm |
| `watan-walnut` | #3D2B1F | Card backgrounds, warmth |
| `watan-snow` | #F4F1EC | Primary text on dark |
| `watan-pine` | #2D5016 | Exercise module, nature |
| `watan-gold` | #D4AC0D | Elderly mode accent |
| `watan-night` | #1A1A2E | App background |

### 9.2 Typography

| Context | Size | Weight | Font |
|---|---|---|---|
| Season name | 22px | 700 | Noto Nastaliq Urdu |
| Body text | 15px | 400 | Noto Nastaliq Urdu |
| Buzurg body | 20px | 400 | Noto Nastaliq Urdu |
| Buzurg heading | 32px | 700 | Noto Nastaliq Urdu |
| English labels | 13px | 500 | Inter |
| Temperature | 28px | 700 | Inter |

### 9.3 Animation Tokens

| Animation | Duration | Easing | Usage |
|---|---|---|---|
| Screen transition | 200ms | ease-out | Page changes |
| Touch feedback | 150ms | ease | Button press |
| Voice orb pulse | 1.5s | ease-in-out | Listening state |
| Card entrance | 300ms | spring | Content load |
| Network badge | 500ms | ease | Status change |

### 9.4 Illustration Style

All exercise and food illustrations are SVG-based (no external images). Style is flat design with warm Kashmir-inspired palette. Clothing in illustrations respects cultural norms — all figures are modestly dressed. Female figures included in exercise illustrations in appropriate traditional/modest clothing showing exercises can be done fully clothed.

---

## 10. Raspberry Pi Deployment — Complete Setup

### 10.1 /boot/config.txt Additions

```ini
# 7-inch HDMI LCD Touch Display
hdmi_group=2
hdmi_mode=87
hdmi_cvt=800 480 60 6 0 0 0
hdmi_drive=1
display_rotate=0

# Audio
dtparam=audio=on
audio_pwm_mode=2

# GPU memory for smooth UI
gpu_mem=128

# Disable overscan (fills screen edge to edge)
disable_overscan=1
```

### 10.2 Pi Setup Script (pi-setup/setup.sh)

```bash
#!/bin/bash
set -e

echo "=== Watan Sehat Pi Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
  python3 python3-pip python3-venv \
  nodejs npm \
  chromium-browser \
  unclutter \           # Hides mouse cursor in kiosk
  xdotool \            # Window management
  portaudio19-dev \    # Audio input
  libportaudio2 \
  alsa-utils \
  fonts-liberation \
  fonts-noto           # For Urdu script rendering

# Install Python dependencies
cd /home/pi/watan-sehat/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd ../frontend
npm install
npm run build

# Copy built frontend to be served by backend
cp -r dist/* ../backend/static/

# Initialize database
cd ../backend
python3 database/init_db.py

# Set up systemd service
sudo cp ../pi-setup/watan-sehat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable watan-sehat
sudo systemctl start watan-sehat

# Set up kiosk autostart
mkdir -p /home/pi/.config/autostart
cp ../pi-setup/kiosk.desktop /home/pi/.config/autostart/

echo "=== Setup Complete. Rebooting in 5 seconds... ==="
sleep 5
sudo reboot
```

### 10.3 Systemd Service (pi-setup/watan-sehat.service)

```ini
[Unit]
Description=Watan Sehat Backend API
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/watan-sehat/backend
Environment=PATH=/home/pi/watan-sehat/backend/venv/bin
ExecStart=/home/pi/watan-sehat/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 10.4 Kiosk Launcher (pi-setup/kiosk.sh)

```bash
#!/bin/bash
# Wait for backend to start
sleep 8

# Hide cursor
unclutter -idle 0.1 -root &

# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Launch Chromium in kiosk mode
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-restore-session-state \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --touch-events=enabled \
  --app=http://localhost:8000 \
  &

# Prevent display sleep
while true; do
  xdotool key ctrl
  sleep 60
done
```

### 10.5 Kiosk Desktop Entry (pi-setup/kiosk.desktop)

```ini
[Desktop Entry]
Type=Application
Name=Watan Sehat Kiosk
Exec=/home/pi/watan-sehat/pi-setup/kiosk.sh
X-GNOME-Autostart-enabled=true
```

---

## 11. Database Schema

```sql
-- backend/database/init_db.py generates this schema

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    age_mode    TEXT NOT NULL DEFAULT 'jawaan',
    district    TEXT NOT NULL DEFAULT 'srinagar',
    started_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,
    query_text      TEXT,
    response_text   TEXT,
    source          TEXT,  -- 'rule' or 'api'
    season          TEXT,
    age_mode        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_checkins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_profile    TEXT DEFAULT 'default',
    feeling         TEXT,  -- 'good' | 'tired' | 'unwell'
    age_mode        TEXT,
    season          TEXT,
    checked_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_version (
    id              INTEGER PRIMARY KEY,
    version         TEXT,
    last_synced     DATETIME
);
```

---

## 12. Build Phases — Week by Week

### Week 1 — Foundation (Laptop)
**Deliverable:** Home screen running with live seasonal data

- [ ] WSL2 + Python + Node setup verified
- [ ] Backend: `seasonal_engine.py` complete with all 8 seasons
- [ ] Backend: `main.py` with `/api/context` endpoint returning correct season
- [ ] Frontend: Tailwind config with Watan color system
- [ ] Frontend: `Home.jsx` displaying SeasonCard + 3 nav tiles
- [ ] Frontend: `NetworkBadge` showing online/offline status
- [ ] Frontend: `AgeModeToggle` switching between 3 modes
- [ ] Test: Disconnect internet → home screen still shows correct season

**Done when:** Home screen visible at localhost:5173, season correct, offline badge appears when disconnected, age mode switches visually.

---

### Week 2 — Content Modules (Laptop)
**Deliverable:** Diet and Exercise screens with full Kashmiri content

- [ ] `data/diet_plans.json` — all 8 seasons × 3 age modes × 5 meal types filled
- [ ] `data/exercises.json` — all 8 seasons × 3 age modes × 4 types filled
- [ ] Backend: `diet_engine.py` with content selector
- [ ] Backend: `exercise_engine.py` with season locking logic
- [ ] Frontend: `Diet.jsx` with tabs + food cards + science bridge text
- [ ] Frontend: `Exercise.jsx` with illustrated guide layout + season lock UI
- [ ] Content: All food names, reasons, science bridges written in Urdu
- [ ] Content: All exercise names, steps written in Urdu
- [ ] Test: Switch age mode → content changes appropriately for each screen

**Done when:** Diet screen shows Chilla Kalan content in all three age modes correctly. Exercise screen shows outdoor lock during winter seasons.

---

### Week 3 — Voice Companion (Laptop)
**Deliverable:** Full voice interaction working end-to-end

- [ ] Install Whisper tiny model, verify mic detection in WSL2
- [ ] `backend/voice/stt.py` complete with silence detection
- [ ] Install Coqui TTS Urdu model, verify speaker output
- [ ] `backend/voice/tts.py` complete with age mode speed control
- [ ] `data/companion_rules.json` — all 60 rules written across 10 categories
- [ ] `backend/companion.py` — rule matcher + Anthropic API fallback
- [ ] Backend: `/api/companion/ask` endpoint
- [ ] Backend: `/api/voice/stt` and `/api/voice/tts` endpoints
- [ ] Frontend: `useVoice.js` hook complete
- [ ] Frontend: `Companion.jsx` with VoiceOrb, states, response display
- [ ] Frontend: Quick prompts pre-loaded for demo
- [ ] Test: Speak "سردی میں کیا کھائیں" → transcript appears → response plays

**Done when:** Voice orb responds correctly in all 5 states. Quick prompts all return accurate responses. Offline mode uses rules only. API fallback triggers for unmatched queries when online.

---

### Week 4 — Koshur Layer + Buzurg Mode (Laptop)
**Deliverable:** Complete bilingual interface with dedicated elderly mode

- [ ] `data/koshur_phrases.json` — all UI strings in Urdu + Koshur
- [ ] `data/kangri_safety.json` — complete Kangri safety content
- [ ] Frontend: All UI strings loaded from phrases file (no hardcoded text)
- [ ] Frontend: `Buzurg.jsx` full-screen elderly interface
- [ ] Frontend: Koshur rendering correct with Nastaliq script
- [ ] Frontend: Buzurg TTS voice slower, warmer pitch
- [ ] Frontend: Emergency button wired to SMS intent (on Pi) / demo trigger (on laptop)
- [ ] Frontend: `KangriAlert` strip showing during winter seasons
- [ ] Test: Elderly mode — font size, language, voice all change correctly

**Done when:** Switching to Buzurg mode changes font to buzurg-xl, triggers Koshur greeting via TTS, shows emergency button prominently.

---

### Week 5 — Pi Deployment + Demo Polish (Pi)
**Deliverable:** Fully deployed, autobooting kiosk demo-ready on Pi

- [ ] Transfer project to Pi via git or USB
- [ ] Run `setup.sh` — verify all dependencies install
- [ ] Test display at 800×480 — all layouts correct
- [ ] Test microphone input at 30cm conversational distance
- [ ] Test speaker volume at demo room level
- [ ] `/boot/config.txt` display settings applied
- [ ] Systemd service verified — backend starts on boot
- [ ] Kiosk script verified — Chromium opens fullscreen on boot
- [ ] Touch input verified on all buttons (minimum 44px targets)
- [ ] Offline demo rehearsed: disconnect ethernet → all features work
- [ ] Reconnect test: connect ethernet → network badge updates
- [ ] Power cycle test: reboot Pi → everything comes up automatically in 30 seconds
- [ ] Demo script rehearsed 5 times with actual Pi in hand

**Done when:** Pi boots cold, displays home screen within 30 seconds, responds to voice within 2 seconds, touch works reliably, offline demo plays perfectly with ethernet unplugged.

---

## 13. Demo Script — For the Pitch Room

**Setup before investors arrive:**
- Pi powered on, home screen displaying
- Internet cable disconnected
- Mic tested, speaker volume set to room level
- Age mode on Jawaan

**Minute 0:00 — The Hook**
Place the Pi on the table. Say nothing for 3 seconds. Let them see it.

"This is Watan Sehat. It's running right now without any internet connection. I disconnected it 30 minutes ago."

Point to amber offline badge.

"It knows we're in [current season], Day [X], in Srinagar, at approximately [temp] degrees tonight. It figured that out from a calendar built into the device."

**Minute 0:45 — The Diet Moment**
Tap Dastarkhwan. Show today's winter diet.

"It's telling this person to eat Harissa this morning. Not because someone entered that today — because it knows Chilla Kalan has started and Harissa is the traditional Kashmiri food that modern nutrition science validates for exactly this cold."

Tap "Why this?" on the Harissa card.

"The science bridge. This is what makes elderly Kashmiris trust the app. It's not telling them something new. It's telling them their grandmother was right — and explaining why."

**Minute 1:30 — The Voice Moment**
Navigate to Health Companion.

"Now ask it something. In Urdu. Or English. Or even Kashmiri."

Hand them the Pi or speak yourself: "بزرگوں کو سردی میں کیا احتیاط کرنی چاہیے؟"

Wait. Response appears. TTS plays.

"That response came from an engine running entirely on this device. No server. No subscription. No internet."

**Minute 2:15 — The Buzurg Moment**
Switch age mode to Buzurg.

"Now watch what happens for elderly users."

Font grows. Language shifts. TTS greeting plays in Koshur.

"This is what an elderly Kashmiri sees. In their script, their language, read aloud to them by a voice that sounds like someone from their village."

Show emergency button.

"One tap sends an SMS to their family member. Works offline. No app required on the other end."

**Minute 3:00 — The Offline Proof**
Pick up the ethernet cable and reconnect it visibly.

"Now I'm connecting internet."

Badge turns green.

"When it's online, it can receive content updates, connect to doctors, get live weather. When it's offline — which is most of Kashmir most of the time — it doesn't care. It keeps working."

"No other health app in India does this. Not for Kashmir. Not in Kashmiri. Not offline. We built it because we're from here and we know what our people actually need."

---

## 14. Failure Modes and Recovery

| Failure | Cause | Recovery |
|---|---|---|
| Backend not starting | Port 8000 in use | `sudo fuser -k 8000/tcp` then restart |
| No mic input | Wrong device index | `python3 -c "import sounddevice; print(sounddevice.query_devices())"` — find correct index |
| TTS no audio | Speaker not default | `aplay -l` find device, set in `~/.asoundrc` |
| Touch not working | USB cable not connected | Connect USB from display to Pi USB port |
| Display wrong resolution | config.txt not applied | Verify `/boot/config.txt` saved correctly, reboot |
| Chromium crash on boot | Backend not up yet | Increase sleep in kiosk.sh from 8 to 15 seconds |
| Voice lag >3 seconds | Pi overheating | Add heatsink, check `vcgencmd measure_temp` |
| Text clipping in Urdu | Font not loaded | Verify `fonts-noto` installed, `fc-list` shows Noto Nastaliq |

---

## 15. Success Criteria — Definition of Done

The demo is production-ready when ALL of the following are true:

- [ ] Pi boots to home screen within 30 seconds without any manual intervention
- [ ] Home screen shows correct Kashmiri season and day number at any date
- [ ] All three age modes switch cleanly with visual changes
- [ ] Diet module shows culturally appropriate Kashmiri food for current season
- [ ] Exercise module locks outdoor activities during Chilla Kalan automatically
- [ ] Voice companion responds to Urdu input within 2 seconds (rule-based)
- [ ] TTS plays response audio clearly at conversational volume
- [ ] Buzurg mode shows enlarged Koshur text and plays Koshur TTS greeting
- [ ] Emergency button is visible in Buzurg mode
- [ ] Offline badge shows amber when ethernet unplugged
- [ ] All features work with ethernet unplugged
- [ ] Network badge turns green when ethernet reconnected
- [ ] Touch targets register reliably on 7" screen without mis-taps
- [ ] Demo script can be run 5 times consecutively without any failure
- [ ] Pi survives a cold reboot and returns to demo-ready state automatically
