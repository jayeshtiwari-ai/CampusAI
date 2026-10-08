# CampusAI 🤖🏫

> **An Autonomous, Multilingual Voice-Enabled College Reception Robot powered by Free Cloud AI & Multi-Agent RAG Architecture.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Groq Cloud](https://img.shields.io/badge/Groq-Cloud-orange.svg)](https://groq.com/)

---

## 💡 Why CampusAI? (Problem Statement)

College receptions and administrative helpdesks face repetitive visitor queries daily regarding admissions, fee structures, faculty room numbers, exam timetables, and campus directions. Human staff are often overwhelmed, leading to long queues and delayed responses, while static noticeboards fail to provide interactive guidance.

**CampusAI** solves this by providing a zero-cost, intelligent talking robot that acts as a 24/7 college receptionist. It listens to spoken queries in **English, Hindi, Marathi, and Hinglish**, retrieves ground-truth verified information from official college documents using RAG, queries structured SQLite databases for real-time timetables, and responds out loud with natural neural voices—all for an estimated hardware cost of **~₹2,000–₹3,000** using an ESP32 microcontroller body.

---

## ✨ Key Features

- 🎯 **Zero-Hallucination Verified Answers (Confidence-Gated RAG)**: Answers are strictly grounded in ingested college documents via FAISS vector search. If confidence is low, it refuses to guess.
- 🗣️ **Multilingual Voice Loop (EN, HI, MR, Hinglish)**: Real-time speech recognition (Groq Whisper STT) and edge-tts neural voice output with natural Indian accents (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`, `mr-IN-AarohiNeural`).
- ⚡ **Low Latency Sentence-Pipelined TTS & Fillers**: Plays the first sentence instantly while background threads synthesize sentence $N+1$. Automatically triggers acoustic filler phrases (*"Ek minute, main check karta hoon"*) if latency exceeds 1.5 seconds.
- 🧠 **Multi-Agent Orchestrator & Domain Agents**: Specialized agents for Admissions, Student Records, Faculty Directory, Navigation, and Reception.
- 🗄️ **Structured SQLite Database**: Fast relational SQL tools for courses, fees, faculty cabins, timetables, exam schedules, and room availability.
- 🚨 **Human Escalation**: Automatically detects personal evaluation requests or complex edge cases and routes them to human staff.
- 🗺️ **Campus Navigation & QR Code**: Generates step-by-step directions and scannable QR codes for indoor building routes.
- 🛡️ **Half-Duplex Mic Control & Noise Filtering**: Prevents mic self-echo feedback with a 400 ms post-speech pause and filters Whisper hallucination artifacts.

---

## 🏗️ System Architecture

```
                       +-----------------------------------+
                       |    Visitor (Microphone & Speaker) |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       |   Groq Whisper STT (Audio -> Text) |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       |  Language & Intent Router Agent  |
                       +--------+--------+--------+--------+
                                |        |        |
        +-----------------------+        |        +-----------------------+
        |                                v                                |
+-------v-------+               +--------+--------+               +-------v-------+
|  RAG Engine   |               |  SQLite DB      |               |  Escalation   |
| (FAISS Index) |               | (Courses/Rooms) |               | (Human Staff) |
+-------+-------+               +--------+--------+               +-------+-------+
        |                                |                                |
        +-----------------------+        |        +-----------------------+
                                |        v        |
                       +--------+-----------------+--------+
                       |    Multi-Agent Orchestrator       |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       | Pipelined Edge-TTS / PyGame Speaker|
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       | Spoken Reply + Terminal/Kiosk UI  |
                       +-----------------------------------+
```

---

## 🛠️ Tech Stack (100% Free Tools)

| Component | Technology / Library | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn | REST & WebSocket API Server |
| **LLM Inference** | Groq Cloud (`llama-3.3-70b-versatile` / `gpt-oss-20b`) | Ultra-fast LLM generation |
| **Speech Recognition** | Groq Whisper API (`whisper-large-v3-turbo`) | Low-latency multilingual Speech-to-Text |
| **Text-to-Speech** | `edge-tts` + `pygame.mixer` (Fallback: `pyttsx3`) | Neural speech synthesis & sentence streaming |
| **VAD & Audio Filtering** | `webrtcvad-wheels`, `pydub`, `sounddevice` | Auto-stop speech recording on silence |
| **Vector Database** | FAISS (`faiss-cpu`) | Local fast vector similarity search |
| **Embeddings** | `intfloat/multilingual-e5-small` | Multilingual vector embeddings |
| **Relational DB** | SQLite3 | Structured courses, fees, rooms, & timetables |
| **Navigation & QR** | `qrcode[pil]` | QR code image generation for maps |

---

## 📁 Project Directory Structure

```
CampusAI/
├── backend/
│   ├── agents/            # Multi-agent architecture (Router, Admission, Student, Faculty, Nav)
│   ├── api/               # FastAPI route endpoints (/chat, /voice, /kiosk)
│   ├── database/          # SQLite database schema, db helper, and seed data
│   ├── llm/               # Groq LLM client wrapper & system prompts
│   ├── rag/               # Document loaders, FAISS vector store, & Retriever
│   ├── speech/            # Groq Whisper STT, Edge-TTS, VAD, & Speaker engine
│   ├── utils/             # Config loader, logger, language detection, & standard phrases
│   ├── config.py          # Centralized configuration management
│   └── main.py            # FastAPI application entrypoint
├── data/                  # Persisted runtime data (FAISS index & audio cache; gitignored)
│   ├── audio_cache/
│   └── index/
├── knowledge_base/        # Official college documents (.txt, .pdf, .docx)
│   ├── academics/
│   ├── admission/
│   ├── departments/
│   ├── facilities/
│   └── notices/
├── tests/                 # Integration & evaluation scripts
│   ├── agent_eval.py      # Multi-agent routing evaluator
│   ├── rag_eval.py        # RAG accuracy & hallucination evaluation (17/20 suite)
│   └── voice_loop.py      # Terminal interactive voice loop
├── .env.example           # Environment template file
├── .gitignore             # Git ignore file
├── LICENSE                # MIT License
├── README.md              # Documentation
└── requirements.txt       # Production dependencies
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.11+** installed
- **Groq API Key**: Obtain a free API key from [console.groq.com](https://console.groq.com)
- **ffmpeg** (Optional, recommended for `pydub` audio processing):
  - *Windows*: Install via `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org).

### 2. Clone Repository & Setup Virtual Environment

```powershell
# Clone the repository
git clone https://github.com/jayeshtiwari-ai/CampusAI.git
cd CampusAI

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and enter your Groq API key:

```powershell
copy .env.example .env
```

Open `.env` and set:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

---

## 📚 Adding College Data & Database Initialization

### 1. Add Documents to Knowledge Base
Place official college documents (`.pdf`, `.txt`, `.docx`) into the appropriate subfolders under `knowledge_base/`:
- `knowledge_base/academics/` (Syllabus, grading policies)
- `knowledge_base/admission/` (Cutoffs, fee structures, eligibility)
- `knowledge_base/facilities/` (Hostels, canteen, library rules)

### 2. Ingest Vector RAG Index

```powershell
python -m backend.rag.ingest --rebuild
```

### 3. Seed Structured SQLite Database

```powershell
python -m backend.database.seed
```

---

## 🏃 Running CampusAI

### Option A: Interactive Talking Robot Voice Loop (Terminal)

Experience hands-free interactive voice dialog directly through your laptop microphone and speakers:

```powershell
python tests/voice_loop.py
```

### Option B: FastAPI Web Backend Server

Launch the REST and WebSocket API server:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
- API Documentation (Swagger UI): `http://localhost:8000/docs`

### Option C: Run Evaluation Test Suites

```powershell
# Test RAG retrieval accuracy and hallucination defense
python tests/rag_eval.py

# Test Multi-Agent routing accuracy
python tests/agent_eval.py
```

---

## 💬 Usage & Query Examples

1. **English Admission Query**:
   > **Visitor**: *"What is the eligibility for B.Tech Computer Engineering?"*  
   > **CampusAI**: *"The eligibility requirement for B.Tech Computer Engineering is a minimum of 50 percent marks in 12th standard with Physics, Chemistry, and Mathematics."*

2. **Hinglish Fee Query**:
   > **Visitor**: *"B.Tech CS ki total fee kitni hai per year?"*  
   > **CampusAI**: *"B.Tech Computer Engineering ki total tuition fee 85,000 Rupees per year hai, aur development fee 15,000 Rupees hai."*

3. **Marathi Navigation Query**:
   > **Visitor**: *"संगणक शास्त्र विभाग कुठे आहे?"*  
   > **CampusAI**: *"संगणक शास्त्र विभाग इमारत बी मध्ये दुसर‍या मजल्यावर आहे."*

4. **Structured DB Timetable Search**:
   > **Visitor**: *"Where is Prof. Sharma's lecture right now?"*  
   > **CampusAI**: *"Prof. Sharma is currently in Room 302 conducting the Data Structures lecture."*

5. **Out-of-Scope Protection (Strict Refusal)**:
   > **Visitor**: *"Who will win the IPL cricket match tonight?"*  
   > **CampusAI**: *"I don't have verified information for that right now."*

---

## 🗓️ Project Roadmap & Progress Checklist

- [x] **Phase 1: Software Brain Core** (FastAPI backend, Groq LLM client, prompt templates)
- [x] **Phase 2: RAG & Confidence Gating** (FAISS vector store, multilingual embeddings, confidence evaluator)
- [x] **Phase 3: Multilingual Voice Pipeline** (Groq Whisper STT, Edge-TTS, VAD recording, sentence streaming)
- [x] **Phase 3.5: Talking Robot Upgrades** (Sentence pipelining, non-repeating fillers, half-duplex mic timing)
- [x] **Phase 4: SQLite Database & Multi-Agent Architecture** (Router, Admission, Student, Faculty, Nav agents)
- [ ] **Phase 5: Human Escalation & Staff Dashboard** (Telegram admin alerts & web review interface)
- [ ] **Phase 6: Kiosk Web UI & Avatar** (Interactive touch UI with 3D animated talking avatar)
- [ ] **Phase 7: Hardware Gateway & WebSocket Bridge** (ESP32 micro-controller RPC bridge)
- [ ] **Phase 8: Production Hardening & Field Testing** (Deployment, rate limiting, logging)
- [ ] **Phase 9: Physical ESP32 Robot Body** (3D printed enclosure, servo head tilt, sensors)

---

## 🔌 Planned Hardware Bill of Materials (BoM ~₹2,500)

| Component | Model | Purpose | Estimated Cost |
|---|---|---|---|
| **Microcontroller** | ESP32-S3 Dual-Core N16R8 | Main Wi-Fi / Bluetooth IoT Gateway | ₹650 |
| **Microphone** | INMP441 I2S Digital Mic | High-clarity voice recording | ₹180 |
| **Audio Amplifier** | MAX98357A I2S DAC Amp | Speaker audio playback driver | ₹220 |
| **Speaker** | 4Ω 3W Cavity Speaker | Spoken audio output | ₹150 |
| **Motion Sensor** | PIR HC-SR501 | Auto-wakes robot when visitor approaches | ₹90 |
| **Servo Motor** | SG90 Micro Servo | Pan/tilt head movement | ₹120 |
| **Display / LEDs** | WS2812B RGB Ring | Visual status lights (Listening/Thinking) | ₹150 |
| **Enclosure** | 3D Printed Chassis | Desktop robot body housing | ₹800 |

---

## 🔒 Privacy & Data Notice

CampusAI is committed to data privacy:
- **No Private Data**: This public repository contains **only sample placeholder documents** and mock database records.
- **Local Vectors**: Vector indices and local SQLite databases are generated locally on your machine and are automatically excluded from Git commits via `.gitignore`.
- **API Security**: No API keys or tokens are stored in source code.

---

## 🐛 Limitations & Known Issues

- **Internet Dependency**: Groq Cloud STT/LLM requires an active internet connection. If offline, the robot uses `pyttsx3` fallback for local spoken notices.
- **Audio Overlap**: Requires half-duplex operation; speaking while the robot is outputting audio is muted for 400 ms post-playback to prevent microphone self-triggering.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for bug fixes and feature suggestions.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

---

## 👤 Author

**Jayesh Tiwari**  
- GitHub: [@jayeshtiwari-ai](https://github.com/jayeshtiwari-ai)  
- Project Repository: [https://github.com/jayeshtiwari-ai/CampusAI](https://github.com/jayeshtiwari-ai/CampusAI)
