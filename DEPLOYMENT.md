# Deploying Vision64

Two services: the **backend** (FastAPI + Stockfish + Postgres) on Render, and the
**frontend** (Vite/React) on Vercel. Deploy the backend first — you need its URL
to configure the frontend.

Everything in this repo is already configured for it: `render.yaml` (blueprint),
`backend/Dockerfile` (bundles Stockfish), and `frontend/vercel.json` (SPA
rewrites).

> **You have to do these steps yourself.** They require signing into your Render,
> Vercel, Anthropic, and Clerk accounts and pasting secret keys — credentials
> that should only ever be typed by you, into the providers' own dashboards.

---

## 1. Backend → Render

1. Go to **[dashboard.render.com](https://dashboard.render.com)** → **New** → **Blueprint**.
2. Connect the GitHub repo `dhruvmehrish1527/vision64`. Render reads `render.yaml`
   from the repo root, creates the web service, and provisions a free Postgres
   database, injecting `DATABASE_URL` automatically.
3. Before the first deploy finishes, open the service's **Environment** tab and
   add the secrets (these are deliberately *not* in the repo):

   | Key | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | your key from [console.anthropic.com](https://console.anthropic.com) |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://vision64.vercel.app` (fill in after step 2) |
   | `CLERK_JWKS_URL` | `https://<your-app>.clerk.accounts.dev/.well-known/jwks.json` |
   | `CLERK_ISSUER` | `https://<your-app>.clerk.accounts.dev` |

   `ENVIRONMENT=production`, `AUTH_DEV_BYPASS=false`, and `STOCKFISH_PATH` are
   already set by the blueprint.

4. Deploy. The container runs `alembic upgrade head` before starting, so the
   schema is created automatically.
5. Verify: open `https://<your-service>.onrender.com/api/health`. You want

   ```json
   { "status": "ok", "stockfish_configured": true, "coach_configured": true }
   ```

> **Free-tier note:** Render spins free services down after inactivity, so the
> first request after a quiet period takes ~30s. Engine analysis is CPU-bound —
> if reviews feel slow, lower `ENGINE_POOL_SIZE` to `1` and review depth to
> `10–12`, or move to a paid instance.

---

## 2. Frontend → Vercel

1. Go to **[vercel.com/new](https://vercel.com/new)** and import the same repo.
2. Set **Root Directory** to `frontend`. Vercel auto-detects Vite; `vercel.json`
   handles the SPA rewrites so deep links like `/shared/<token>` work.
3. Add environment variables:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://<your-service>.onrender.com/api` |
   | `VITE_CLERK_PUBLISHABLE_KEY` | your Clerk publishable key (`pk_live_…`) |
   | `VITE_AUTH_DEV_BYPASS` | `false` |

4. Deploy, then go back to Render and set `CORS_ORIGINS` to the Vercel URL you
   were assigned. Redeploy the backend so it picks the value up.

---

## 3. Clerk

1. Create an application at **[clerk.com](https://clerk.com)**.
2. Add your Vercel domain to the allowed origins.
3. Copy the publishable key into Vercel and the JWKS URL / issuer into Render
   (both shown in the Clerk dashboard under **API Keys**).

---

## Post-deploy checklist

- [ ] `/api/health` reports `stockfish_configured: true`
- [ ] `/api/docs` loads the OpenAPI page
- [ ] The board analyses a position (engine reachable)
- [ ] The coach panel streams text (Anthropic key valid)
- [ ] Sign-in works and `AUTH_DEV_BYPASS` is `false` in production
- [ ] A shared game link opens in a private window (public route works)

---

## Rolling back

Both platforms keep previous deploys: Render → **Events** → *Rollback*; Vercel →
**Deployments** → *Promote to Production* on the last good build.
