# Lahore Pulse AI — Frontend

React 19 + Vite 8 frontend for the Lahore Pulse AI air quality intelligence platform.

## Quick Start

```bash
npm install
npm run dev    # starts on http://localhost:5173
npm run build  # production build to dist/
npx vitest run # run 756 tests
```

## Architecture

- **React 19** with React Router v7
- **Vite 8** dev server with `/api` proxy to backend on port 8002
- **Recharts** for data visualization, **Leaflet** for maps
- **Vitest 4** + React Testing Library for 756 unit tests
- **Lucide React** for icons

## Key Directories

| Path | Purpose |
|------|---------|
| `src/pages/` | 21 page components (public + government) |
| `src/components/` | Shared UI components |
| `src/hooks/` | Custom React hooks (scroll reveal, 3D tilt, data fetching) |
| `src/contexts/` | Auth and demo mode providers |
| `src/services/api.js` | Centralized API client |
| `src/styles/` | CSS (global styles, animations, 3D effects) |

## Pages

**Public:** Landing, Citizen Dashboard, Air Quality, City Map, Alerts, Insights, Reports, My Lahore, Data Trust, Login

**Government:** Command Center, Incidents, Forecasts, Analytics, Investigations, Reports, Replay, System

**Demo Mode:** Append `?demo=true` to any government URL for a self-contained 7-step demo walkthrough.

## Environment

The frontend connects to the backend at `http://localhost:8002` via Vite proxy. No `.env` file required for development.
