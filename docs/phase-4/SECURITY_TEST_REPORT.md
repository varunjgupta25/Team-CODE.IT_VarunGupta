# Phase 4 — Security Test Report

## 1. Security Verification Matrix

The 10 security scenarios specified for Phase 4 were tested and validated against the shared backend service.

| # | Security Requirement | Test Name / Location | Result |
|---|---|---|---|
| 1 | Customer cannot access Worker-only operations | `test_origin_header_does_not_confer_role` (`tests/test_phase4_app_separation.py`) | **PASSED** (`403 Forbidden`) |
| 2 | Customer cannot access Admin-only operations | `test_origin_header_does_not_confer_role` (`tests/test_phase4_app_separation.py`) | **PASSED** (`403 Forbidden`) |
| 3 | Worker cannot access Admin-only operations | `test_admin_endpoints_require_admin_role` (`tests/test_auth_roles.py`) | **PASSED** (`403 Forbidden`) |
| 4 | Worker cannot modify another worker's profile | `test_cross_entity_data_isolation` (`tests/test_phase4_app_separation.py`) | **PASSED** (`403 Forbidden`) |
| 5 | Customer cannot modify another customer's job | `test_cross_entity_data_isolation` (`tests/test_phase4_app_separation.py`) | **PASSED** (`403 Forbidden`) |
| 6 | Admin endpoints reject unauthorized users | `test_admin_verifications_unauthorized` (`tests/test_auth_roles.py`) | **PASSED** (`401 / 403`) |
| 7 | Invalid Firebase tokens are rejected | `test_invalid_token_fails_fast` (`tests/test_auth_roles.py`) | **PASSED** (`401 Unauthorized`) |
| 8 | Expired / malformed tokens are rejected | `test_get_current_user_no_token` (`tests/test_auth_roles.py`) | **PASSED** (`401 Unauthorized`) |
| 9 | Unauthorized frontend origins rejected by CORS | `test_customer_and_partner_cors_preflight` (`tests/test_phase4_app_separation.py`) | **PASSED** (No allow header) |
| 10 | Allowed frontend origins can make authorized requests | `test_customer_and_partner_cors_preflight` (`tests/test_phase4_app_separation.py`) | **PASSED** (`200 OK` + allow origin) |

---

## 2. CORS vs Backend Security Distinction

> [!IMPORTANT]
> CORS is a browser mechanism that instructs user agents whether web scripts running on Origin A may read responses from Origin B.
> CORS does **not** protect against non-browser clients (cURL, Postman, scripts).
> 
> Therefore, **the backend never relies on CORS as an authentication or authorization boundary**. Every request is cryptographically validated using the `Authorization: Bearer <token>` header regardless of origin.

---

## 3. Data Protection & Phone Masking Verification

To protect customer and worker privacy across shared endpoints:
- In `GET /customers/{id}`: If the requesting user is neither the customer themselves nor an admin, the phone number is masked (`+91 98*** ***22`).
- In `GET /workers/{id}`: Phone number and exact street address are hidden from customers until a booking/offer is formally accepted.
- In `GET /jobs/{id}`: Exact customer street address is hidden from workers in the nearby feed until the customer accepts their specific offer.

