# Phase 4 — CORS Configuration Report

## 1. Overview and Objectives

To support the separation of the frontend into two independent deployments (Customer App and Partner App), the backend CORS configuration was upgraded to handle **multi-origin production environments** without sacrificing security or exposing the API to arbitrary origins.

Key requirements fulfilled:
1. Support distinct `CUSTOMER_APP_ORIGIN` and `PARTNER_APP_ORIGIN` environment variables.
2. Maintain backward compatibility with existing `ALLOWED_ORIGINS` and `CORS_ORIGINS`.
3. Reject wildcard origins (`*`) in production.
4. Disable permissive regular expressions (such as generic `r"https://.*\.vercel\.app"`) in production environments so unauthorized third-party Vercel apps cannot execute cross-origin requests.
5. Provide automatic preflight `OPTIONS` handling with full support for `Authorization`, `Content-Type`, and credentialed cookies/headers.

---

## 2. Configuration Schema & Implementation

In `core/config.py`:
```python
class Settings(BaseSettings):
    ...
    # CORS Configuration
    ALLOWED_ORIGINS: Optional[Union[str, List[str]]] = None
    CORS_ORIGINS: Optional[Union[str, List[str]]] = None
    CUSTOMER_APP_ORIGIN: Optional[Union[str, List[str]]] = None
    PARTNER_APP_ORIGIN: Optional[Union[str, List[str]]] = None
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"
```

### Dynamic Assembly Logic
During settings initialization and post-validation:
- Origins are aggregated from `ALLOWED_ORIGINS`, `CORS_ORIGINS`, `CUSTOMER_APP_ORIGIN`, and `PARTNER_APP_ORIGIN`.
- Any wildcard `*` origin is stripped and rejected.
- In **development** (`ENV=development`):
  - Localhost defaults (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`) are provided if no explicit origins are set.
  - Preview deployments matching `CORS_ORIGIN_REGEX` are permitted for rapid prototyping.
- In **production** (`ENV=production` or `ENV=staging`):
  - Localhost origins are **not injected**.
  - Permissive default regex matching (`r"https://.*\.vercel\.app"`) is automatically set to `None`, ensuring **only explicitly whitelisted origins** receive `Access-Control-Allow-Origin`.

---

## 3. Allowed Methods and Headers

As mounted via Starlette's `CORSMiddleware` in `main.py`:
- **Allowed Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- **Allowed Headers**: All standard request headers, including `Authorization`, `Content-Type`, `Accept`, `Origin`, `X-Requested-With`
- **Allow Credentials**: `True` (enables cookies and Authorization headers across origins)

---

## 4. Test Verification Evidence

Tests in `tests/test_phase4_app_separation.py` and `tests/test_health_cors.py` validate:
1. **Dual Origin Resolution**:
   - `Settings(ENV="production", CUSTOMER_APP_ORIGIN="https://customer.app", PARTNER_APP_ORIGIN="https://partner.app", ALLOWED_ORIGINS="*")` strips `*` and yields `ALLOWED_ORIGINS=["https://customer.app", "https://partner.app"]` with `CORS_ORIGIN_REGEX=None`.
2. **Preflight OPTIONS Request**:
   - `Origin: http://localhost:5173` -> returns `HTTP 200` with `access-control-allow-origin: http://localhost:5173`.
   - `Origin: http://localhost:3000` -> returns `HTTP 200` with `access-control-allow-origin: http://localhost:3000`.
   - `Origin: http://malicious-phishing-site.com` -> returns `HTTP 200` without any `access-control-allow-origin` header (browser blocks request).

