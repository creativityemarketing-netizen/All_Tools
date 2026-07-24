# YouTube Channel Excel Exporter

A local web app that accepts a YouTube channel link and exports an Excel workbook with:

- Channel profile and statistics
- Total uploaded content fetched from the uploads playlist
- Video/short classification
- Content links
- Publication dates
- Views, likes, comments
- Durations and descriptions

## Requirements

- Python 3.10 or newer
- `yt-dlp` and `openpyxl` installed in Python

This workspace already has `yt-dlp` available. No YouTube API key is required for normal use.

## Run

```powershell
python server.py
```

Then open:

```text
http://127.0.0.1:8000
```

Paste a YouTube channel URL such as:

- `https://www.youtube.com/@mkbhd`
- `https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ`
- `https://www.youtube.com/user/GoogleDevelopers`
- `https://www.youtube.com/c/GoogleDevelopers`

## Notes

No-API mode uses public YouTube pages through `yt-dlp`. It fetches the channel `/videos` and `/shorts` tabs, then merges them into one Excel workbook. Leaving the limit empty fetches all available videos and shorts. Add a limit only when you want a faster smaller export. Some channel-level totals, such as subscriber count, may be unavailable without the official API.

