# PramaanX P4 frontend

React/Vite operator console for the P4 biometric service.

## Development

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to the Flask
service at `http://127.0.0.1:5001` by default. Override it with
`VITE_BACKEND_URL`.

## Production build

```powershell
npm run build
```

The Flask service serves `frontend/dist` at `/` when the build exists. The
frontend can also be hosted separately by setting `VITE_API_BASE_URL`.
