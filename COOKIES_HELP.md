# How to fix "Sign in to confirm you're not a bot" Error

YouTube often blocks automated requests (like `yt-dlp` or `youtube-transcript-api`) with a "Sign in" prompt. To fix this, you need to provide your browser cookies so the application can "act" as you.

## Steps:

1.  **Install a Cookie Exporter Extension**:
    *   **Chrome**: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
    *   **Firefox**: [Get cookies.txt LOCALLY](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/)

2.  **Go to YouTube**:
    *   Open [YouTube.com](https://www.youtube.com).
    *   Ensure you are logged in (or not, but logged in is usually better for bypassing age-gating).

3.  **Export Cookies**:
    *   Click the extension icon.
    *   Click "Export".
    *   Wait for the file to download.

4.  **Save the File**:
    *   Rename the downloaded file to **`cookies.txt`**.
    *   Place it in this directory: **`c:\Projects\Text to speech\`** (The root of your project).

5.  **Restart the Application**:
    *   Stop the running `python run.py`.
    *   Start it again.

The application `youtube_service.py` is now configured to automatically look for this file and use it to authenticate requests.
