# TigerLine – 16th Ave Belmar Surf Forecast

TigerLine is a physics-driven surf forecasting app for **16th Ave, Belmar, NJ**, built as:

- A **Flask** backend that ingests live buoy, wind and tide data, runs wave physics, and returns a surf score.
- A **Next.js (TypeScript + React)** frontend that presents a clean, surf-centric dashboard.

The model is based on linear wave theory, shoaling, refraction, depth-limited breaking, and a transparent scoring system tuned for 16th Ave beach-break conditions.

---

## Features

- **Spot-specific forecast** for 16th Ave, Belmar (fixed beach profile and orientation).
- **Breaking wave height at the beach**, not just buoy Hs.
- **Physics-based transformation**:
  - Deep-water dispersion and group speed
  - Shoaling and refraction over a 1D bathymetric profile
  - Depth-limited breaking using a breaker index
- **Live data inputs**:
  - Wave data from NDBC buoy 44025
  - Wind data from OpenWeatherMap (or configured provider)
  - Tide predictions from NOAA CO-OPS (or configured provider)
- **Surf score (0–10)** based on:
  - Breaking height
  - Period
  - Direction vs coastline
  - Wind speed and direction
  - Tide state
  - Breaker type (plunging / spilling / surging)
- **Board and conditions recommendations**:
  - Board type and size by size/quality band
  - Short, human-readable conditions blurbs
- **Physics view (“nerd mode”)**:
  - Step-by-step propagation, shoaling and breaking output
  - Sub-scores and internal model diagnostics

---

## Tech Stack

**Backend**

- Python 3.x
- Flask (API layer)
- WSGI (via `wsgi.py` for production servers)
- Numerical stack: `numpy`, etc. (as listed in `requirements.txt`)

**Frontend**

- Next.js (React + TypeScript)
- CSS modules and global styles
- Simple theme + unit toggles (dark/light, metric/imperial)

---

## Project Structure

```text
TigerLine/
├─ backend/
│  ├─ api/
│  │  ├─ __init__.py
│  │  └─ server.py              # Flask app / API endpoints
│  │
│  ├─ data_sources/
│  │  ├─ __init__.py
│  │  ├─ buoy.py                # NDBC buoy data ingestion
│  │  ├─ sync.py                # Data sync / orchestration helpers
│  │  ├─ tides.py               # Tide data ingestion
│  │  └─ wind.py                # Wind data ingestion
│  │
│  ├─ surf_model/
│  │  ├─ __init__.py
│  │  ├─ board_recommendations.py
│  │  ├─ calibration.py         # K_site and local tuning
│  │  ├─ climatology.py         # Historical stats / seasonality
│  │  ├─ config.py              # Site & model config hooks
│  │  ├─ quality.py             # Surf score + sub-score logic
│  │  ├─ recommendations.py     # Text blurbs, conditions, etc.
│  │  ├─ storage.py             # Persistence for calibration/trends
│  │  └─ trends.py              # Rising/falling swell, recent history
│  │
│  ├─ waves/
│  │  ├─ __init__.py
│  │  ├─ dispersion.py          # Linear dispersion, phase/group speed
│  │  ├─ propagation.py         # Buoy → nearshore propagation
│  │  ├─ spectra.py             # Spectral moments, Hs, periods
│  │  ├─ stats.py               # Generic statistics helpers
│  │  └─ transform.py           # Shoaling, refraction, breaking search
│  │
│  ├─ config/
│  │  ├─ belmar_profile.json    # 1D bathymetry profile for 16th Ave
│  │  └─ production.py          # Production settings / environment
│  │
│  ├─ __init__.py
│  ├─ requirements.txt          # Backend Python dependencies
│  └─ wsgi.py                   # WSGI entrypoint (e.g. gunicorn)
│
└─ frontend/
   ├─ src/
   │  ├─ components/
   │  │  ├─ ErrorBoundary.tsx
   │  │  ├─ ForecastDashboard.tsx
   │  │  ├─ HeroSection.tsx
   │  │  ├─ PhysicsView.tsx
   │  │  ├─ PhysicsView_SIMPLE_TEST.tsx
   │  │  ├─ ThemeToggle.tsx
   │  │  └─ UnitToggle.tsx
   │  │
   │  ├─ contexts/
   │  │  ├─ ThemeContext.tsx
   │  │  └─ UnitContext.tsx
   │  │
   │  ├─ pages/
   │  │  ├─ _app.tsx
   │  │  └─ index.tsx
   │  │
   │  └─ styles/
   │     ├─ example-globals.css
   │     ├─ globals.css
   │     └─ surf.module.css
   │
   ├─ next-env.d.ts
   ├─ next.config.js
   ├─ package.json
   ├─ package-lock.json
   └─ tsconfig.json
