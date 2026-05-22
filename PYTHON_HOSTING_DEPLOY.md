# Deploy The 3 Python Tools

Use this version for the full website with:

- Instagram Date Finder
- Instagram Words Finder
- TikTok Extract / Downloader

This version needs a Python-capable host. It will not run on a Bluehost shared plan unless Bluehost enables **Setup Python App / Passenger Python**.

## Recommended Fast Deployment: Render With Docker

1. Create a GitHub repository.
2. Upload this project to the repository.
3. Go to Render and create a new **Web Service**.
4. Choose your GitHub repository.
5. Choose **Docker** runtime.
6. Render will use the included `Dockerfile`.
7. Set the service port automatically through Render's `PORT` variable.
8. Deploy.

The app start command is already inside the Dockerfile:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Local Test

```bash
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Connect Your Domain

For the Python version, use a subdomain so it does not replace the PHP Date Finder currently on Bluehost:

```text
app.socialtools.cyou
```

In Namecheap or Bluehost DNS, create the DNS record that Render gives you. Render usually asks for a `CNAME` record for subdomains.

Example:

```text
Type: CNAME
Host: app
Value: your-render-service.onrender.com
```

Then in Render, add:

```text
app.socialtools.cyou
```

as a custom domain.

## Important Notes

- Instagram often blocks public/shared server IPs. Use session/cookies inside Instagram Words Finder if needed.
- TikTok downloads depend on `yt-dlp`, `curl_cffi`, and `ffmpeg`; the Dockerfile installs `ffmpeg`.
- Downloaded TikTok files are temporary and may disappear when the service restarts.
- For production with many users, a VPS is stronger than free/shared hosting.

