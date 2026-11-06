# Phase 4.1 — CORS & Domain Security Report

**Project:** RepairBuddy  
**Branch:** `phase-4.1-stabilization`  
**Date:** 2026-11-06  

---

## 1. Vulnerability Analysis

In earlier revisions of the backend configuration (`core/config.py`):
```python
# Previous vulnerable configuration
CORS_ORIGIN_REGEX: str | None = r"https://.*\.vercel\.app"
```
### Security Threat:
The regular expression `https://.*\.vercel\.app` matched **every** website deployed on Vercel anywhere in the world. An attacker could deploy a malicious client at `https://evil-attacker.vercel.app`, and if an authenticated RepairBuddy customer or partner visited that site, the attacker's script could make cross-origin requests to `https://repair-buddy.onrender.com/api` with full credentials and session headers (`allow_credentials=True`).

---

## 2. Hardened CORS Architecture

Phase 4.1 completely eliminates permissive wildcard regex and implements strict domain allowlisting.

### 2.1 Explicit Domain Separation
Backend CORS configuration now isolates the two production frontends:
- **Customer App Origin**: `https://repair-buddy-customer.vercel.app`
- **Partner App Origin**: `https://repair-buddy-partner.vercel.app`

### 2.2 Removal of Global Wildcards in Production (`core/config.py`)
In development and CI, `CORS_ORIGIN_REGEX` defaults to `r"https://.*\.vercel\.app"` to accommodate dynamic preview branches. However, in production and staging environments (`ENV in ["production", "staging"]`), `core/config.py` enforces:
```python
if self.CORS_ORIGIN_REGEX == r"https://.*\.vercel\.app":
    self.CORS_ORIGIN_REGEX = None
```
Wildcard matching is strictly dismantled in production, requiring requests to originate from explicit entries:
```python
CUSTOMER_APP_ORIGIN: str = "https://repair-buddy-customer.vercel.app"
PARTNER_APP_ORIGIN: str = "https://repair-buddy-partner.vercel.app"
```

### 2.3 Automatic Localhost Stripping in Production
To avoid accidental local origins leaking into production through `.env` files or misconfigured environment blocks, `Settings.clean_origins` filters out local domains:
```python
raw_list = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# Strip any localhost or 127.0.0.1 origins when running in production or staging
if self.ENV in ["production", "staging"]:
    raw_list = [o for o in raw_list if not ("localhost" in o or "127.0.0.1" in o)]

return raw_list
```

### 2.4 Middleware Setup (`main.py`)
FastAPI CORS middleware is attached using the sanitized explicit origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.clean_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "X-Total-Count"],
    max_age=600,
)
```

---

## 3. Preflight & Request Handling Verification

| Request Origin | Request Type | Expected Status | CORS Headers Returned |
|---|---|---|---|
| `https://repair-buddy-customer.vercel.app` | `OPTIONS /api/jobs` | `200 OK` | `Access-Control-Allow-Origin: https://repair-buddy-customer.vercel.app` |
| `https://repair-buddy-partner.vercel.app` | `GET /api/workers` | `200 OK` | `Access-Control-Allow-Origin: https://repair-buddy-partner.vercel.app` |
| `https://unauthorized-site.vercel.app` | `OPTIONS /api/jobs` | `400 / Rejected` | Origin rejected, headers absent |
| `http://localhost:5173` (in Production) | `GET /api/jobs` | `Rejected` | Origin stripped, cross-origin denied |
| `http://localhost:5173` (in Development) | `GET /api/jobs` | `200 OK` | `Access-Control-Allow-Origin: http://localhost:5173` |

---

## 4. Test Verification

Automated test cases in `tests/test_phase4_1_stabilization.py`:
- `test_cors_wildcard_regex_disabled_by_default`: Confirms `CORS_ORIGIN_REGEX` is `None` by default.
- `test_cors_strips_localhost_in_production`: Instantiates settings with `ENV="production"` and confirms that `localhost` is completely purged from `clean_origins`.

All tests passed.

