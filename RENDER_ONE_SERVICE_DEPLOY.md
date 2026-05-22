# Deploy Social Tools on Render as One Web Service

This guide deploys the full unified website with all 3 tools in one Render web service:

- Instagram Date Finder: `/tools/instagram-date/`
- Instagram Words Finder: `/tools/instagram-words/`
- TikTok Extract / Downloader: `/tools/tiktok/`

The homepage is available at `/` and shows one card per tool.

## Recommended Cost

Start with:

- Render workspace: `Hobby`
- Web Service instance: `Starter`
- Persistent disk: `2 GB`

Expected starting cost:

- Web service: about `$7/month`
- Persistent disk: about `$0.50/month`

Estimated total: about `$7.50-$8/month`.

## Why One Web Service

The 3 tools are already mounted inside one FastAPI app in `main.py`.

This means:

- One deploy
- One domain
- One server bill
- One shared runtime folder for cache/sessions/downloads

If traffic becomes heavy later, TikTok or Instagram Words can be split into a worker/service, but one web service is the best starting setup.

## Project Files Render Uses

Render will use these files:

- `Dockerfile`: builds the Python app image
- `render.yaml`: optional Render Blueprint config
- `requirements.txt`: Python dependencies
- `main.py`: unified FastAPI entrypoint
- `templates/home.html`: homepage with tool cards
- `tools/`: all tool code

Runtime files are stored under:

```text
SOCIAL_TOOLS_DATA_DIR=/var/data/social-tools
```

On Render, `/var/data` is the persistent disk mount.

## Step 1: Prepare GitHub

1. Create a new GitHub repository, for example:

```text
social-tools
```

2. Upload the project files to that repo.

Make sure these are included:

```text
main.py
Dockerfile
render.yaml
requirements.txt
templates/
static/
tools/
```

Do not upload old zips like:

```text
find date insta.zip
recherche par mots in instagram.zip
tiktok extract.zip
date-finder-bluehost-php.zip
```

## Step 2: Create the Render Service

1. Go to Render.
2. Choose `Hobby` workspace.
3. Click `New`.
4. Choose `Web Service`.
5. Connect your GitHub repo.
6. For runtime/environment, choose `Docker`.
7. Choose instance type:

```text
Starter
```

8. Set the health check path:

```text
/health
```

If Render detects `render.yaml`, it may prefill most settings automatically.

## Step 3: Add Persistent Disk

Add one persistent disk:

```text
Name: social-tools-data
Mount path: /var/data
Size: 2 GB
```

This keeps:

- Instagram Words cache
- Instagram sessions/cookies if used
- TikTok metadata cache
- temporary TikTok download files
- uploaded Date Finder databases if you upload one from the Python app

Without a persistent disk, cache can disappear after restart/redeploy.

## Step 4: Environment Variables

Add these environment variables in Render:

```text
SOCIAL_TOOLS_DATA_DIR=/var/data/social-tools
INSTAGRAM_REQUEST_TIMEOUT=18
INSTAGRAM_CACHE_TTL=86400
TIKTOK_CACHE_TTL=86400
```

Meaning:

- `SOCIAL_TOOLS_DATA_DIR`: where runtime files are saved
- `INSTAGRAM_REQUEST_TIMEOUT`: Instagram request timeout in seconds
- `INSTAGRAM_CACHE_TTL`: Instagram cache lifetime, `86400` = 24 hours
- `TIKTOK_CACHE_TTL`: TikTok cache lifetime, `86400` = 24 hours

## Step 5: Deploy

Click `Deploy`.

After the deploy finishes, open the Render URL.

Test these routes:

```text
/
/health
/tools/instagram-date/
/tools/instagram-words/
/tools/tiktok/
```

Expected `/health` response:

```json
{"ok":true,"tools":3}
```

## Step 6: Connect Your Domain

In Render:

1. Open the web service.
2. Go to `Settings`.
3. Find `Custom Domains`.
4. Add:

```text
socialtools.cyou
www.socialtools.cyou
```

Render will show DNS records.

In Namecheap:

1. Open your domain DNS settings.
2. Add the records Render gives you.
3. Wait for DNS propagation.

Use `www.socialtools.cyou` first if the root domain is slow to propagate.

## Step 7: Test The Tools

Instagram Date Finder:

- Open `/tools/instagram-date/`
- Search by Instagram link, shortcode, or post ID
- Exact results show exact date
- Estimated results show an estimated range

Instagram Words Finder:

- Open `/tools/instagram-words/`
- Load a profile
- Use `Full` once for a profile if you want to cache many posts
- Later searches on the same profile reuse cache

TikTok Extract:

- Open `/tools/tiktok/`
- Fetch single video info
- Fetch account videos
- Export CSV/JSON
- Download selected videos if TikTok allows it

## If Render Shows Internal Server Error

First test the health endpoint:

```text
https://YOUR-RENDER-URL.onrender.com/health
```

If `/health` does not return:

```json
{"ok":true,"tools":3}
```

then the app is failing during startup.

Open Render:

1. Go to your web service.
2. Open `Logs`.
3. Click `Live tail`.
4. Refresh the failing page.
5. Copy the first Python traceback/error shown in the logs.

Common causes:

- `tools/storage.py` was not uploaded to GitHub.
- The repo is missing one of these folders: `tools/`, `templates/`, `static/`.
- The service is not using Docker.
- The start command was changed manually.
- The persistent disk/env variable was not configured correctly.

Expected Render settings:

```text
Environment: Docker
Health Check Path: /health
Dockerfile Path: ./Dockerfile
```

Expected environment variables:

```text
SOCIAL_TOOLS_DATA_DIR=/var/data/social-tools
INSTAGRAM_REQUEST_TIMEOUT=18
INSTAGRAM_CACHE_TTL=86400
TIKTOK_CACHE_TTL=86400
```

If only one tool fails, test each route:

```text
/tools/instagram-date/
/tools/instagram-date/api/stats
/tools/instagram-words/
/tools/tiktok/
```

The exact route that returns `500` tells us which tool is causing the issue.

## Important Limits

Render solves the Python hosting problem, but Instagram/TikTok can still limit scraping.

To reduce blocking:

- Use cache instead of rescanning profiles every time.
- Avoid many full scans at the same time.
- Use Instagram sessions/cookies only if needed.
- Upgrade later if the service becomes slow.
- Consider proxies or external APIs only if blocking becomes frequent.

## Adding More Tools Later

Recommended structure:

```text
tools/
  new_tool/
    __init__.py
    app.py
    templates/
    static/
```

Then update `main.py`:

1. Import the tool app.
2. Mount it under `/tools/new-tool`.
3. Add one entry to the `TOOLS` list so it appears on the homepage.

Example:

```python
from tools.new_tool.app import app as new_tool_app

app.mount("/tools/new-tool", new_tool_app, name="new_tool")

TOOLS.append({
    "path": "/tools/new-tool/",
    "platform": "Platform",
    "title": "New Tool",
    "description": "Short description for the homepage card.",
    "icon": "N",
    "class": "newtool",
})
```

If the new tool needs runtime files, use:

```python
from tools.storage import tool_data_dir

RUNTIME_DIR = tool_data_dir("new_tool")
```

That keeps all runtime files organized under the Render persistent disk.

## Current Unified Routes

```text
/                         Homepage
/health                   Health check
/tools/instagram-date/    Instagram Date Finder
/tools/instagram-words/   Instagram Words Finder
/tools/tiktok/            TikTok Extract / Downloader
```

## Local Test Command

Before deploying, you can test locally:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```
