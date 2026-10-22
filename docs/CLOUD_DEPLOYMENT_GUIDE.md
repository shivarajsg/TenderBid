# Cloud Deployment Guide — TenderBid AI

This guide provides step-by-step instructions for deploying TenderBid AI to production cloud platforms.

---

## Deployment Architecture Options

| Method | Frontend Host | Backend Host | Database Host | Ease | Cost Tier |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Option A (Recommended)** | Render (Static Site) | Render (Web Service) | Render (Managed Postgres) | ⭐️⭐️⭐️⭐️⭐️ (1-Click) | Free Tier Available |
| **Option B (High Performance)** | Vercel (Edge CDN) | Render / Railway (Web Service) | Neon (Serverless Postgres) | ⭐️⭐️⭐️⭐️ | Free Tier Available |
| **Option C (Unified Container)** | Railway | Railway | Railway (Postgres Plugin) | ⭐️⭐️⭐️⭐️ | Hobby / Pay-as-you-go |

---

## Option A: 1-Click Blueprint Deployment on Render (Easiest)

Render natively reads the included [`render.yaml`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/render.yaml) file to automatically provision the PostgreSQL database, the FastAPI backend, and the React static site in a single click.

### Step 1: Connect Your GitHub Repository
1. Log in or create a free account at [render.com](https://render.com).
2. On your Render Dashboard, click the **New +** button in the top right.
3. Select **Blueprint** from the dropdown.
4. Connect your GitHub account and select the repository: `shivarajsg/TenderBid` (or your fork).
5. Branch: `main`.

### Step 2: Review Blueprint Resources
Render will automatically detect `render.yaml` and display 3 resources to create:
- **`tenderbid-db`**: Managed PostgreSQL Database.
- **`tenderbid-backend`**: FastAPI Python Web Service (Runs migrations + Uvicorn server).
- **`tenderbid-frontend`**: React + Vite Static Site (Pre-configured with SPA route rewrites).

### Step 3: Configure Environment Variables
Render will prompt you for any unpopulated environment variables:
- **`GEMINI_API_KEY`**: *(Optional)* Enter your Google Gemini API key from [Google AI Studio](https://aistudio.google.com/). If left empty, the engine operates using deterministic rules and local RRF retrieval.
- **`JWT_SECRET_KEY`**: Render automatically generates a cryptographically secure 64-character secret.
- **`DATABASE_URL`**: Render automatically links this directly to `tenderbid-db`.

### Step 4: Click "Apply"
Click **Apply**. Render will automatically:
1. Provision the PostgreSQL database.
2. Install Python dependencies and run `alembic upgrade head` to build all tables.
3. Start the FastAPI backend and verify health at `/api/v1/health`.
4. Build the React frontend with Vite and link `VITE_API_BASE_URL` to the backend.

Your live platform will be accessible at:
`https://tenderbid-frontend.onrender.com`

---

## Option B: Vercel (Frontend) + Render / Railway (Backend) + Neon (Database)

This architecture provides the fastest global CDN performance for the React UI while utilizing a serverless PostgreSQL database.

### Part 1: Provision Cloud PostgreSQL (Neon)
1. Go to [neon.tech](https://neon.tech) and create a free account.
2. Click **Create Project** (Name: `tenderbid-db`, Region: choose closest to your users).
3. Copy the generated PostgreSQL Connection String. It will look like:
   ```
   postgresql://tender_user:your_password@ep-cool-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Note: The platform's configuration automatically normalizes `postgresql://` and `postgres://` to `postgresql+asyncpg://` at runtime).*

### Part 2: Deploy Backend on Render or Railway

#### On Render:
1. Click **New +** -> **Web Service**.
2. Select your repository: `shivarajsg/TenderBid`.
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python -m alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `DATABASE_URL`: *(Paste your Neon connection string)*
   - `JWT_SECRET_KEY`: *(Generate a 32+ character random secret)*
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
   - `FRONTEND_ORIGINS`: `*` (or your Vercel domain once deployed)
   - `GEMINI_API_KEY`: *(Your Google AI Studio key)*
5. Click **Create Web Service**.
6. Once deployed, note down your backend URL (e.g., `https://tenderbid-backend.onrender.com`).

### Part 3: Deploy Frontend on Vercel
1. Go to [vercel.com](https://vercel.com) and log in with GitHub.
2. Click **Add New...** -> **Project**.
3. Select `shivarajsg/TenderBid`.
4. In the project configuration:
   - **Root Directory**: Click edit and select `frontend`.
   - **Framework Preset**: `Vite` (automatically detected).
5. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://tenderbid-backend.onrender.com/api/v1`
6. Click **Deploy**.
7. Vercel automatically deploys the frontend with global edge caching and SPA client routing (via [`frontend/vercel.json`](file:///c:/Users/KumarShiva/Downloads/Tender_Bid/frontend/vercel.json)).

---

## Option C: Deploy on Railway

1. Go to [railway.app](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select `shivarajsg/TenderBid`.
4. Add a PostgreSQL plugin to the project:
   - Click **+ New** -> **Database** -> **Add PostgreSQL**.
5. In the backend service settings:
   - Set **Root Directory** to `/backend`.
   - Set **Build Command** to `pip install -r requirements.txt && python -m alembic upgrade head`.
   - Add environment variable `DATABASE_URL` set to `${{Postgres.DATABASE_URL}}`.
   - Add environment variable `JWT_SECRET_KEY` set to a secure string.
6. In the frontend service settings:
   - Set **Root Directory** to `/frontend`.
   - Set `VITE_API_BASE_URL` to your backend's public domain + `/api/v1`.

---

## Post-Deployment Verification & Admin Setup

### 1. Verify Backend Health
Open your backend URL in the browser:
```
https://<YOUR-BACKEND-DOMAIN>/api/v1/health
```
Expected response:
```json
{
  "status": "healthy",
  "app_name": "TenderBid AI API",
  "environment": "production"
}
```

### 2. Provision Initial Platform Administrator
To create the first `ADMIN` user on your cloud instance:

#### On Render:
1. Go to your backend service dashboard on Render.
2. Click the **Shell** tab on the left.
3. Run:
   ```bash
   python -m app.cli create-admin --email admin@tenderbid.com --full-name "Admin User" --password "YourStrongPassword2026!"
   ```

#### On Railway:
1. Open the backend service -> **CLI**.
2. Run the same command as above.

### 3. Log In from Frontend
1. Open your frontend URL (e.g., `https://tenderbid.vercel.app` or `https://tenderbid-frontend.onrender.com`).
2. Log in with your admin credentials or click **Register** to create an MSME account.
3. Navigate to:
   - **Dashboard**: View active opportunities and analytics.
   - **Find Tenders**: Search and discover live government notices.
   - **Company Profile**: Setup MSME credentials and check your Readiness Score.
   - **Evaluate Tender**: Run compliance evaluations with deterministic rule guarantees.
