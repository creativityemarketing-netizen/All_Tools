# Bluehost Deployment

This project is a FastAPI app prepared for Bluehost/cPanel Python hosting through Passenger.

## 1. Upload Files

Upload the full contents of this folder to your Bluehost app directory, for example:

```text
/home/YOUR_CPANEL_USER/socialtools
```

Do not upload the original zip files. Upload this unified project folder.

## 2. Create The Python App In cPanel

In Bluehost/cPanel:

1. Open **Setup Python App**.
2. Click **Create Application**.
3. Choose Python **3.10+** if available.
4. Set **Application root** to the folder where you uploaded the project, for example:

```text
socialtools
```

5. Set **Application URL** to the domain/subdomain path you want, for example:

```text
tools.yourdomain.com
```

or:

```text
yourdomain.com/socialtools
```

6. Set **Application startup file**:

```text
passenger_wsgi.py
```

7. Set **Application entry point**:

```text
application
```

8. Save/create the app.

## 3. Install Requirements

In the cPanel Python app screen, open the app terminal or run the package installer for:

```bash
pip install -r requirements.txt
```

If Bluehost gives you a virtualenv command, activate it first, then run the command above.

## 4. Restart

In cPanel **Setup Python App**, click **Restart** for the app.

Then open:

```text
https://your-domain-or-subdomain/
```

## Important Hosting Notes

- Instagram and TikTok may block shared hosting IPs. If Instagram Words Finder fails with `429 Too Many Requests`, use a valid session or `cookies.txt`.
- TikTok downloading may require `ffmpeg` on the server. Metadata/export can still work even if video merging is limited by Bluehost.
- Uploaded databases, sessions, and downloads should be on persistent storage. On Bluehost shared hosting this is usually the app folder itself.
- If the app shows **503 Service Unavailable**, check cPanel's Passenger error log first. Most issues are missing packages, wrong startup file, or wrong entry point.

## Local Test Command

For local testing only:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

