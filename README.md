# Kampala Needs

Find trusted service providers in Kampala — mechanics, brokers, shops, offices, and more.

**Served by Mabero Evarist** · 0772228112 · WhatsApp 0781431799 · Evazomabs697@gmail.com

Public GitHub: https://github.com/maberoevarist/kampala-needs

## Admin password (your own)

There is **no default password**.

1. After the site is live, open `/admin` yourself first.
2. Create a password (at least 8 characters). Only you will know it.
3. You can change it later under **Change password**.

Do this immediately so nobody else can claim the first password.

## Go live on Render (free)

1. Open [https://dashboard.render.com](https://dashboard.render.com) and sign in (GitHub login is easiest).
2. **New +** → **Web Service** → connect `maberoevarist/kampala-needs`.
3. Settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance type:** Free
4. Create the service. After 2–5 minutes you get a public link such as `https://kampala-needs.onrender.com`.
5. Open `/admin` and set your password.

Free Render apps sleep after ~15 minutes of no traffic. The first visit after sleep can take up to a minute.

SQLite storage on the free plan can reset when the service restarts. Re-add featured listings after a reset if needed.

## Features

- Search and category browse
- Kampala district / area filter
- GPS nearest providers + boda / Maps links
- User suggestions (admin review)
- Featured paid listings and Verified badge
- Admin: search, edit, delete, featured dates, change password
