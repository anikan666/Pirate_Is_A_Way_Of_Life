# Daily Planner Experiment — Code Review & Progress

## Overall Assessment
**Status:** Functional Prototype  
**Production Readiness:** Needs Refactoring  

This is a working experiment with Gmail integration, AI task extraction, and calendar sync. However, it has significant technical debt and architectural issues that need to be addressed before production use.

---

## Summary Scores

| Category | Score | Notes |
|----------|-------|-------|
| Functionality | 7/10 | Works, but fragile |
| Code Quality | 4/10 | Monolithic, debug code, inline imports |
| Security | 5/10 | Insecure transport, bypassed scope check |
| Maintainability | 3/10 | Hard to extend or test |
| Frontend | 7/10 | Good UX, relies on CDN |

---

## ✅ Strengths

- OAuth flow works correctly using `google-auth-oauthlib`
- Multi-LLM support — Anthropic, Gemini, and Ollama fallback
- Deep linking feature — Email source linking via `source_email_id`
- Graceful AI fallback — If AI fails, emails become tasks automatically
- Polished UI — Visually appealing with good UX patterns

---

## 🔴 Critical Issues

### 1. Monolithic Route File
**File:** `routes.py` (567 lines)  
**Problem:** The `dashboard()` function is 338 lines and handles OAuth, email fetching, AI processing, response formatting, and calendar sync.

### 2. Inline Imports
**Location:** Lines 126, 134  
**Problem:** `import base64` appears inside loops, hurting performance and readability.

### 3. Debug Code in Production Path
**Location:** Lines 144-151, 234, 288, 472-476  
**Problem:** Heavy `print()` statements throughout instead of proper logging.

### 4. Hardcoded Constants
**Location:** Lines 525-530  
**Problem:** Timezone `'Asia/Kolkata'` and other config values hardcoded.

### 5. Insecure OAuth Transport
**Location:** Line 32  
**Problem:** `OAUTHLIB_INSECURE_TRANSPORT = '1'` is dangerous for production.

---

## 🟠 Moderate Issues

### 6. Unused Prompt File
**Files:** `ai_prompt.txt` exists but prompt is hardcoded in `routes.py` (lines 171-231)

### 7. Weak Frontend Error Handling
**Location:** `planner_dashboard.html` lines 742-744  
**Problem:** Catch blocks show generic "Network error" with no context.

### 8. Magic Numbers
**Locations:** Lines 170, 106, 350  
**Problem:** Values like `2000`, `20`, `80` with no explanation.

### 9. Bypassed Scope Check
**Location:** Lines 453-464  
**Problem:** Calendar scope check is bypassed with `has_calendar_scope = True`.

---

## 🟡 Minor Issues

### 10. CDN TailwindCSS
**Location:** `planner_dashboard.html` line 8  
**Problem:** `cdn.tailwindcss.com` is not recommended for production.

### 11. Nested Function Definition
**Location:** Lines 340-344  
**Problem:** `extract_sender_name()` defined inside `dashboard()`.

### 12. Missing Type Hints
**Problem:** No type annotations anywhere in Python code.

---

## 📋 Task Checklist

### Critical Priority
- [x] Create `auth.py` module and move OAuth routes (`login`, `callback`, `logout`, `check_auth`)
- [x] Create `gmail_service.py` module with email fetching logic
- [x] Create `ai_service.py` module with LLM integration (Anthropic, Gemini, Ollama)
- [x] Create `calendar_service.py` module with Google Calendar sync logic
- [x] Move all `import base64` statements to top of file
- [x] Replace all `print()` statements with `logging` module
- [x] Create `config.py` for constants (timezone, max results, etc.)
- [x] Add environment variable for timezone configuration
- [x] Remove or conditionally set `OAUTHLIB_INSECURE_TRANSPORT` based on environment

### Moderate Priority
- [x] Delete unused `ai_prompt.txt` or load prompt from it
- [ ] Add detailed error messages to frontend catch blocks
- [ ] Define named constants for magic numbers (EMAIL_BODY_MAX_LENGTH, MAX_RESULTS, etc.)
- [ ] Restore calendar scope check and remove bypass comment
- [ ] Move `extract_sender_name()` to a utilities module

### Low Priority
- [ ] Replace CDN Tailwind with local build or production CDN
- [ ] Add type hints to all Python functions
- [ ] Add docstrings to all public functions
- [ ] Create unit tests for email parsing logic
- [ ] Create unit tests for AI response parsing logic

---

## Next Steps

1. Start with module extraction (auth, gmail, ai, calendar)
2. Fix security issues (OAuth transport, scope check)
3. Add configuration management
4. Improve error handling and logging
5. Add tests before refactoring complex logic
