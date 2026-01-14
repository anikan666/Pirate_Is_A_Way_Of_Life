# Why Should I Pay For ElevenLabs - Project Documentation

## Overview
A free, open-source text-to-speech web application that provides 300+ neural voices using Microsoft Edge TTS. Built as an alternative to paid services like ElevenLabs.

## Tech Stack
- **Backend**: Python Flask
- **TTS Engines**: 
  - Edge TTS (online, 300+ neural voices) - PRIMARY
  - pyttsx3 (offline, Windows SAPI) - LOCAL ONLY
- **Frontend**: Vanilla HTML/CSS/JS with modern UI

## Project Structure
```
c:\Projects\Text to speech\
├── app.py              # Flask backend (API endpoints)
├── requirements.txt    # Python dependencies
├── CLAUDE.md          # This file
├── templates/
│   └── index.html     # Frontend (single-page app)
└── audio_output/      # Generated audio files
```

## Running Locally
```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

## Key Features
1. **Split-screen Studio Layout** - 60/40 editor/controls design
2. **Voice Selection** - Rich cards with flags, gender icons, preview buttons
3. **Tabbed Panels** - "Create" tab for generation, "Files" tab for history
4. **Click-to-rename** - Click file titles to rename saved audio
5. **Speed/Volume Controls** - With clickable snap points

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page |
| `/api/voices` | GET | Get all available voices |
| `/api/speak` | POST | Generate speech (returns audio URL) |
| `/api/save` | POST | Save speech to file |
| `/api/play/<filename>` | GET | Stream audio file |
| `/api/download/<filename>` | GET | Download audio file |
| `/api/delete/<filename>` | DELETE | Delete audio file |
| `/api/rename/<filename>` | POST | Rename audio file |
| `/api/history` | GET | List saved files |

## Design Notes
- **UI Inspiration**: urfd.net - off-white background with blue ambient glow
- **No frameworks**: Pure vanilla CSS for maximum control
- **Responsive**: Collapses to single column on mobile

## Known Limitations
1. **Offline voices** (pyttsx3) only work on Windows
2. **For web hosting**: Must disable offline voices (Linux servers don't have Windows SAPI)
3. **Temp files**: Auto-cleaned on startup, but accumulate during session

## Deployment Considerations
If deploying to web (Render, Railway, etc.):
1. Remove/hide offline voice option
2. Add `gunicorn` to requirements
3. Create `Procfile`: `web: gunicorn app:app`
4. Use cloud storage for persistent file storage

## Session History (2026-01-13)
- Built complete TTS application
- Implemented urfd.net-inspired UI with ambient glow
- Added split-screen studio layout
- Created tabbed panel system (Create/Files)
- Added inline file renaming
- Fixed volume slider (was sending 0-1 instead of 0-100)
- Cleaned up temp files and redundant API endpoints

## Next Steps (if continuing)
- [ ] Prepare for web deployment (remove offline voices)
- [ ] Add Procfile and gunicorn for production
- [ ] Consider cloud storage for saved files
- [ ] Add user authentication if making public
