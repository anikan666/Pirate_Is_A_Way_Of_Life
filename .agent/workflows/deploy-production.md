---
description: Deploy TTS app to production as a website tab
---

# Production Deployment Tasks

## Task 1: Production Dependencies ✅ COMPLETE
1. ✅ Add gunicorn to requirements.txt
2. ✅ Create Procfile
3. ✅ Add .env.example

## Task 2: Remove Offline TTS
1. Disable pyttsx3 code in app.py (wrap with env check)
2. Update /api/voices to filter offline voices in production
3. Update frontend to hide Local voice option when unavailable

## Task 3: Security Hardening
1. Add rate limiting (flask-limiter)
2. Add CORS config for website domain
3. Add input validation (max 5000 chars)

## Task 4: Cloud Storage
1. Add S3/cloud storage support for audio files
2. Update file APIs to use cloud storage
3. Add storage config to .env.example

## Task 5: Website Integration
1. Extract frontend as embeddable component
2. Configure API base URL as environment variable
3. Test iframe/tab embedding
