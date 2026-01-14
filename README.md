# Anish Sood - AI Experiments Portfolio

A personal laboratory for building and shipping experimental AI projects. Built with Flask, featuring a modular architecture where each experiment lives as an independent Blueprint.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Live Experiments

| Experiment | Description | Status |
|------------|-------------|--------|
| **Don't Pay For ElevenLabs** | Neural TTS with 300+ voices via Edge-TTS | ✅ Live |
| Voice Cloner | Clone voices with 3 seconds of audio | 🔜 Coming Soon |
| Audio Transcriber | Whisper-powered transcription | 🔜 Coming Soon |
| AI Image Lab | Image generation with diffusion models | 🔜 Coming Soon |

## 🏗️ Architecture

```
├── run.py                    # Main entry point (Flask app factory)
├── core/                     # The Launchpad shell
│   ├── routes.py            # Dashboard routes & experiment registry
│   ├── templates/
│   │   └── index.html       # Portfolio landing page
│   └── static/
│       ├── css/style.css
│       └── js/launcher.js   # Modal/lightbox functionality
├── experiments/              # Modular AI experiments
│   └── tts_pirate/          # Text-to-Speech experiment
│       ├── routes.py        # Blueprint with Edge-TTS
│       └── templates/
│           └── app.html
├── storage.py               # Storage abstraction (local/S3)
└── app.py                   # Legacy standalone TTS app
```

## 🛠️ Tech Stack

- **Backend**: Python Flask with Blueprints
- **Frontend**: Vanilla JS + Tailwind CSS
- **TTS Engine**: Microsoft Edge-TTS (300+ neural voices, web-deployable)
- **Storage**: Local filesystem or AWS S3

## 🏃 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/anikan666/Pirate_Is_A_Way_Of_Life.git
cd Pirate_Is_A_Way_Of_Life

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Run the application
python run.py
```

### Access
- **Portfolio**: http://localhost:5000
- **TTS Experiment**: http://localhost:5000/experiments/tts/

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

```env
# Storage Configuration
STORAGE_TYPE=local          # 'local' or 's3'
FILE_MAX_AGE_SECONDS=3600   # Auto-delete after 1 hour

# For S3 storage (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket
S3_REGION=us-east-1
```

## 📁 Adding New Experiments

1. Create a new folder under `experiments/`:
   ```
   experiments/
   └── your_experiment/
       ├── __init__.py
       ├── routes.py
       └── templates/
           └── app.html
   ```

2. Define a Blueprint in `routes.py`:
   ```python
   from flask import Blueprint
   your_bp = Blueprint('your_exp', __name__, template_folder='templates')
   
   @your_bp.route('/')
   def index():
       return render_template('app.html')
   ```

3. Register it in `run.py`:
   ```python
   from experiments.your_experiment.routes import your_bp
   app.register_blueprint(your_bp, url_prefix='/experiments/your-experiment')
   ```

4. Add it to the `EXPERIMENTS` list in `core/routes.py`.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

*Not built with Lovable - 2026*
