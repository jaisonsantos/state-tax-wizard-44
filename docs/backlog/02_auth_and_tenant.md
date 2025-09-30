# Epic 02 — Authentication & Tenant Isolation

## Context
Multi-tenant SaaS requires reliable authentication and authorization for each
store. The MVP currently seeds a demo store and issues JWTs without checking
store-level claims, leaving critical security gaps.

## Current Status
- ✅ `POST /api/auth/login` creates/retrieves a user and returns JWT + stores.
- ✅ `GET /api/me` returns the authenticated user and linked stores.
- ✅ All `/api/v1/**` endpoints require bearer tokens and verify store access
  against both JWT claims and persisted relationships.
- ✅ JWT payload encodes `sub`, `exp`, and `stores` scopes with configurable TTL.
- ✅ Session tokens are persisted in `session_tokens`, `/api/auth/logout` revokes
  active sessions, and the frontend header exposes a logout affordance tied to
  the new endpoint.

## Acceptance Criteria
1. **Secure JWTs**: Tokens include `sub`, `exp`, and `stores` claim (array of
   UUIDs). Tokens expire within configurable TTL (default 24h).
2. **Authorization Dependency**: FastAPI dependency that validates the bearer
   token and ensures the requested `store_id` belongs to the user. Every
   `/api/v1/**` endpoint must use it.
3. **Store Selection Workflow**: Frontend stores the selected store in state and
   sends it in requests. Users with access to multiple stores can switch safely.
4. **Audit Trail**: Audit logs include the authenticated user identifier (or
   token subject) when actions are taken.
5. **Documentation**: `docs/backlog/02_auth_and_tenant.md` (this file) links to
   a sequence diagram showing login → token issuance → authorized request.

## Deliverables
- Updated `core/security.py` and router dependencies enforcing authorization.
- Frontend state management for selected store (context or Zustand store).
- Session token persistence with explicit logout endpoint and metrics/logs.
- Tests ensuring unauthorized access is rejected (pytest) and token expiry is
  respected.
- Updated documentation with diagrams (`docs/diagrams/auth_flow.mermaid`).
  - Sequence: [Auth Flow](../diagrams/auth_flow.mermaid)

## Validation
- Backend pytest suite passes with new authorization tests.
- Manual smoke tests fail when omitting `Authorization` or using a store not in
  the token claims.

## Definition of Done
- All production routers import and use the shared authorization dependency;
  automated lint/test checks fail if the dependency is absent.
- JWT configuration, rotation process, and environment variables documented in
  `docs/environment.md` with references from this epic.
- Frontend default store selection persisted and exercised in `make smoke` or
  equivalent automated scenario.
- Audit logs verified to include authenticated subject identifiers, and
  observability catalog updated with the new field.
- Epic status updated with links to PRs/tests demonstrating blocked access when
  claims do not match the target store.

## Dependencies
- Relies on Epic 01 documentation for environment variables (JWT secret, TTL).
