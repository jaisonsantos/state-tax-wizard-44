# Epic 05 — Frontend Experience & Admin Console

## Context
Merchants interact primarily through the React dashboard. The MVP ships with
placeholder data and manual flows that must be tied to real backend behavior
and polished for GA.

## Current Status
- ✅ Pages scaffolded: Dashboard, Onboarding, Settings/Playground, Reports,
  Logs, Billing, Help.
- ✅ Settings page can trigger quote/apply demos using seeded store.
- ✅ Settings toggles and labels persist via `/v1/stores/{id}/settings` API.
- ✅ Dashboard metrics hydrate from `/v1/analytics/overview` using React Query in
  [`src/pages/Dashboard.tsx`](../../src/pages/Dashboard.tsx). KPI cards, trends,
  and Prometheus snapshots now reflect real data.
- ✅ Global store selector persists across sessions via AuthContext/localStorage
  and wires the dropdown + logout flow in [`src/components/layout/AppLayout.tsx`](../../src/components/layout/AppLayout.tsx).
- ✅ Reports and Logs surfaces now hydrate from live `/v1/audit` data with
  loading skeletons, empty-state copy, toast notifications, and export
  re-run actions (see [`src/pages/Reports.tsx`](../../src/pages/Reports.tsx) and
  [`src/pages/Logs.tsx`](../../src/pages/Logs.tsx)).
- ✅ Account menu surfaces session metadata (active session ID, issued/expiry,
  last activity, store scope) returned by the enriched `GET /api/me` endpoint.

## Acceptance Criteria
1. **Store Context**: Implement global store selector (header or modal) that
   reads from `/api/me` and drives API requests.
2. **Settings Persistence**: Integrate with backend endpoints to read/update
   `store_settings`, including absorb fee, label override, and enable flags.
3. **Dashboard Live Metrics**: Fetch aggregated KPIs from a new backend endpoint
   (e.g., `/api/v1/analytics/overview`) showing applies, absorbed count, last fee
   timestamp.
4. **UX Polish**: Loading spinners, empty states, and toast notifications across
   Reports, Logs, and Billing pages.
5. **Design System Consistency**: Document component usage (shadcn variants,
   Tailwind classes) in `docs/ui-guide.md`.

## Deliverables
- Frontend state management updates (React Query/Zustand contexts).
- API client additions in `src/lib/api.ts` for new endpoints.
- UI/UX guidelines doc.
- Optional: Storybook or Chromatic setup for critical components.

## Validation
- Cypress or Playwright smoke covering login → settings toggle → quote apply →
  logs view.
- Manual acceptance using QA scenarios (MN/CO) via the playground.

## Definition of Done
- Global store selector UX validated with multiple seeded stores and reflected
  in automated UI tests.
- Settings persistence confirmed via API assertions and visual regression
  capture (screenshot or Storybook snapshot) stored with the iteration output.
- Dashboard metrics sourced from live API, with fallback states documented and
  covered by unit/component tests.
- Error/loading states demonstrated in Playwright recordings and referenced in
  `docs/ui-guide.md`.
- Epic status updated to link to design artifacts and QA evidence.

## Dependencies
- Epic 02 for multi-store awareness.
- Epic 03 for settings persistence and analytics data sources.
