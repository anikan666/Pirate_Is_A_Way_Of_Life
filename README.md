# 🎙️ Why Should I Pay For ElevenLabs

A free, professional text-to-speech application with 300+ neural voices powered by Microsoft Edge TTS.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0-orange.svg)

## ✨ Features

- **300+ Neural Voices** - High-quality Microsoft Edge TTS voices
- **Multiple Languages** - Support for 50+ languages and accents
- **Local TTS** - Windows SAPI offline voices (master branch only)
- **Speed & Volume Control** - Fine-tune your audio output
- **Save to File** - Download generated audio as MP3
- **File Management** - Rename, play, and delete saved files
- **Modern UI** - Clean, responsive interface with dark gradient design

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/anikan666/text-to-speech.git
   cd text-to-speech
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open in browser**
   ```
   http://localhost:5000
   ```

## 📁 Project Structure

```
text-to-speech/
├── app.py              # Flask backend with TTS logic
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend UI
├── audio_output/       # Generated audio files (gitignored)
├── .env.example        # Environment variables template
└── Procfile           # Production deployment config
```

## 🌿 Branches

| Branch | Description |
|--------|-------------|
| `master` | Full version with offline (pyttsx3) + online (Edge TTS) voices |
| `production` | Streamlined version with Edge TTS only (for web deployment) |

## 🔧 Configuration

Copy `.env.example` to `.env` and configure as needed:
```bash
cp .env.example .env
```

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application UI |
| `/api/voices` | GET | List all available voices |
| `/api/speak` | POST | Generate and play speech |
| `/api/save` | POST | Generate and save to file |
| `/api/history` | GET | List saved audio files |
| `/api/download/<filename>` | GET | Download audio file |
| `/api/delete/<filename>` | DELETE | Delete audio file |
| `/api/rename/<filename>` | POST | Rename audio file |

## 🚢 Deployment

For production deployment, use the `production` branch:
```bash
git checkout production
```

Deploy to platforms like Render, Railway, or Heroku using the included `Procfile`.

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- [Microsoft Edge TTS](https://github.com/rany2/edge-tts) - Neural voice synthesis
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) - Offline TTS engine

---

**Made with ❤️ by [anikan666](https://github.com/anikan666)**
