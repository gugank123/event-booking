# Deploying EventFlow online (Render + Railway MySQL + Vercel)

The code is deploy-ready. You (the human) need to click through three free
accounts; each step is below. Nothing else to install.

Architecture:

```
Browser → Vercel (React site) → Render (Django API) → Railway (MySQL)
```

Expected cost: **~$5/month** (Railway MySQL; Render web + Vercel are free).
Without a paid DB host there is no reliable free MySQL — that $5 is the only
required spend. Everything else has a free tier.

---

## 0. Push the code to GitHub

Render and Vercel both deploy from a Git repo.

1. Create a GitHub account (if needed) and a **new private repo**, e.g. `eventflow`.
2. In a terminal at the `eventflow-django-app` folder:
   ```
   git init
   git add .
   git commit -m "EventFlow ready to deploy"
   git branch -M main
   git remote add origin https://github.com/YOURNAME/eventflow.git
   git push -u origin main
   ```
   (`.env` files, `venv/`, `node_modules/`, `dist/` and `staticfiles/` are
   git-ignored and will NOT be uploaded — that is correct.)

## 1. MySQL on Railway (~$5/mo)

1. Sign up at https://railway.app (GitHub login works).
2. **New Project → Provision MySQL** (or Add Service → Database → MySQL).
3. Click the MySQL service → **Variables** tab → copy **`MYSQL_URL`**
   (looks like `mysql://root:xxxx@host:port/railway`).
4. Keep that tab open — you paste this into Render next.

## 2. Backend API on Render (free)

1. Sign up at https://render.com (GitHub login works).
2. **New → Web Service → connect your `eventflow` repo.**
   - Render detects `render.yaml` and pre-fills everything.
   - **Root Directory:** `backend` (important — the blueprint sets this).
   - Plan: **Free**.
3. Before hitting Deploy, fill the `sync: false` environment variables:
   - `MYSQL_URL` → paste from Railway.
   - `CORS_ALLOWED_ORIGINS` → your Vercel URL (you get this in step 3;
     come back and add it, e.g. `https://eventflow.vercel.app`).
   - `FRONTEND_URL` → same Vercel URL.
   - `GOOGLE_OAUTH_CLIENT_ID` → your Google OAuth Web client ID (see step 4;
     can be added later — Google login just stays hidden until then).
   - `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` → Gmail address + App Password
     (see below; can be added later — mail prints to Render logs until then).
4. **Deploy.** The build installs deps, collects static files and runs
   migrations automatically (`backend/build.sh`).
5. Note your API URL: `https://eventflow-api.onrender.com` (name may differ).

### Gmail sending (optional, later)

1. Google Account → Security → 2-Step Verification ON → **App passwords** →
   create one for "Mail".
2. Put the Gmail address in `EMAIL_HOST_USER` and the 16-letter app password
   in `EMAIL_HOST_PASSWORD` on Render → **Save** (auto-redeploys).

### Create your admin user online

Render dashboard → your service → **Shell** tab:

```
python manage.py createsuperuser
```

(Do NOT run `seed_demo` online — it is for local demo data only.)

Admin panel: `https://YOUR-API.onrender.com/admin/`

## 3. Frontend on Vercel (free)

1. Sign up at https://vercel.com (GitHub login works).
2. **Add New → Project → import your `eventflow` repo.**
   - **Root Directory:** `frontend`.
   - Framework preset: **Vite**. Build command `npm run build`, output `dist/`
     (pre-filled from `frontend/vercel.json`, which also handles page refreshes).
3. **Environment Variables** (add before deploying):
   - `VITE_API_URL` → `https://YOUR-API.onrender.com/api`
   - `VITE_GOOGLE_CLIENT_ID` → same Google client ID (or leave empty for now).
4. **Deploy.** You get `https://YOUR-SITE.vercel.app`.
5. Go back to Render and set `CORS_ALLOWED_ORIGINS` + `FRONTEND_URL` to that
   URL (step 2.3) — otherwise the site can't talk to the API.

## 4. Google sign-in online (optional, later)

Google Cloud Console → your OAuth client → **Authorized JavaScript origins**,
add `https://YOUR-SITE.vercel.app` (keep `http://localhost:5173` too for
local work). Put the client ID in both Render (`GOOGLE_OAUTH_CLIENT_ID`) and
Vercel (`VITE_GOOGLE_CLIENT_ID`) env vars and redeploy both.

## 5. Check it works

- Open the Vercel URL → events load (proves site → API → MySQL chain).
- Register an account, book a ticket, open `/notifications`.
- Render logs show request logs; Railway shows DB size/queries.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Site loads but "no events" / network error | `CORS_ALLOWED_ORIGINS` on Render must exactly match the Vercel URL (https, no trailing slash). `VITE_API_URL` must end with `/api`. |
| Render build fails on `collectstatic` | Check build logs; usually a missing env var. `DJANGO_DEBUG` must be `false`. |
| API 500s, "can't connect to MySQL" | `MYSQL_URL` wrong/outdated — re-copy from Railway Variables. Railway DB must be running (not paused). |
| Google button missing online | `VITE_GOOGLE_CLIENT_ID` empty on Vercel, or origin not added in Google console. |
| Free Render sleeps | Free web services sleep after 15 min idle; first visit takes ~30s to wake. Paid ($7/mo) avoids this. |

## Local development (unchanged)

Double-click `start_app.bat`. Local `.env` files are untouched by all of this.
