# Pirate Lab - AI Experiments Laboratory

## Overview
A personal AI experiments playground that hosts various interactive experiments as embeddable modal experiences. The main landing page showcases experiment cards, and each experiment runs in its own iframe modal.

Currently hosting:
- **TTS Pirate** - Free text-to-speech with 300+ neural voices (ElevenLabs alternative)

## Tech Stack
- **Backend**: Python Flask (modular Blueprint architecture)
- **Frontend**: Vanilla HTML/CSS/JS with modern glassmorphism UI
- **Deployment**: Render.com with Gunicorn

## Project Structure
```
c:\Projects\Text to speech\
├── run.py                  # Main entry point
├── app.py                  # Flask app factory with Blueprint registration
├── requirements.txt        # Python dependencies
├── Procfile               # Production server config
├── CLAUDE.md              # This file
├── templates/
│   └── index.html         # Main landing page (experiment cards)
└── experiments/
    └── tts_pirate/        # TTS experiment module
        ├── __init__.py    # Blueprint initialization
        ├── routes.py      # API endpoints
        └── templates/
            └── app.html   # TTS app UI (embedded in modal)
```

## Running Locally
```bash
pip install -r requirements.txt
python run.py
# Open http://localhost:5000
```

## Architecture

### 1. Main Landing Page (`/`)
- Displays experiment cards with glassmorphism design
- Clicking a card opens the experiment in a modal iframe
- URL hash updates to `#experiment-id` for deep linking

### 2. Experiment Blueprints
Each experiment is a Flask Blueprint registered under `/experiments/<name>/`:
- Has its own `routes.py` for API endpoints
- Has its own `templates/` folder for UI
- Supports `?embed=1` query param for iframe mode (hides navigation)

### 3. Embed Mode
Experiments detect `embed=1` and adjust:
- Hide back navigation
- Use relative API URLs via `base_url` template variable
- Compact layout optimized for modal viewport

## Adding a New Experiment

### Step 1: Create the experiment folder
```
experiments/
└── my_experiment/
    ├── __init__.py
    ├── routes.py
    └── templates/
        └── app.html
```

### Step 2: Define the Blueprint (`__init__.py`)
```python
from flask import Blueprint

my_experiment_bp = Blueprint(
    'my_experiment',
    __name__,
    template_folder='templates',
    static_folder='static',  # if needed
    url_prefix='/experiments/my-experiment'
)

from . import routes
```

### Step 3: Create routes (`routes.py`)
```python
from flask import render_template, request, jsonify
from . import my_experiment_bp

@my_experiment_bp.route('/')
def index():
    embed_mode = request.args.get('embed') == '1'
    base_url = '/experiments/my-experiment' if embed_mode else ''
    return render_template('app.html', 
                         embed_mode=embed_mode, 
                         base_url=base_url)

@my_experiment_bp.route('/api/action', methods=['POST'])
def action():
    # Your API logic
    return jsonify({'status': 'ok'})
```

### Step 4: Register in `app.py`
```python
from experiments.my_experiment import my_experiment_bp
app.register_blueprint(my_experiment_bp)
```

### Step 5: Add card to landing page (`templates/index.html`)
Add a new experiment card in the `.experiments-container`:
```html
<div class="experiment-card" data-experiment="my-experiment" data-url="/experiments/my-experiment/?embed=1">
    <div class="experiment-icon">🎯</div>
    <div class="experiment-content">
        <h3>My Experiment</h3>
        <p>Description of what this experiment does</p>
    </div>
</div>
```

## TTS Pirate Experiment

### Features
1. **300+ Neural Voices** - Via Microsoft Edge TTS (free!)
2. **Split-screen Layout** - Text editor + controls panel
3. **Voice Preview** - Play samples before generating
4. **File Management** - Save, rename, download, delete audio
5. **Speed/Volume Controls** - With clickable snap points

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/experiments/tts/` | GET | TTS app page |
| `/experiments/tts/api/voices` | GET | Get all voices |
| `/experiments/tts/api/speak` | POST | Generate speech |
| `/experiments/tts/api/save` | POST | Save to file |
| `/experiments/tts/api/play/<file>` | GET | Stream audio |
| `/experiments/tts/api/download/<file>` | GET | Download audio |
| `/experiments/tts/api/delete/<file>` | DELETE | Delete file |
| `/experiments/tts/api/rename/<file>` | POST | Rename file |
| `/experiments/tts/api/history` | GET | List saved files |

## Design Guidelines

### Visual Style
- **Theme**: Dark glassmorphism with blue accent (#3b82f6)
- **Background**: Gradient with ambient glow effects
- **Cards**: Semi-transparent with blur backdrop
- **Typography**: Inter font family

### Embed Mode Layout
When designing experiment UIs for embed mode:
- Target viewport: ~550px x 500px (modal size)
- Keep controls compact (smaller padding, tighter spacing)
- Ensure all primary actions visible without scrolling
- Use scrollable lists for long content (e.g., voice lists)

## Deployment

### Render.com Setup
1. Connect GitHub repo
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Environment: Python 3.11+

### Environment Variables
- `FLASK_ENV`: production/development
- (Add more as experiments require)

## Session History

### 2026-01-14
- Restructured as "Pirate Lab" experiments platform
- Created modular Blueprint architecture
- Built landing page with experiment cards
- Implemented modal iframe embedding system
- Optimized TTS layout for embed mode (compact, no-scroll)
- Added file renaming, history management
- Prepared for production deployment

### 2026-01-13
- Built initial TTS application
- Implemented urfd.net-inspired UI
- Created split-screen studio layout

## Future Experiment Ideas
- [ ] AI Image Generator
- [ ] Voice Cloning Demo
- [ ] Audio Transcription
- [ ] Document Summarizer

