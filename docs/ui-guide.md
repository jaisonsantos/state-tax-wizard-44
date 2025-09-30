# UI Guide

## Dashboard & Analytics
- The **Dashboard** now renders KPI cards from `/v1/analytics/overview`. Each card surfaces live counts, trend indicators, and jurisdiction badges when scoped (for example, CO fee totals). Loading skeletons appear while the API request is in flight so operators never see stale placeholder data.
- Clicking **Refresh analytics snapshot** reissues the overview query to capture the latest counters without reloading the page. Use this after generating reports to see the applied/absorbed mix update.
- The **Recent Fee Decisions** feed hydrates directly from audit logs using cursor-based pagination. The **Load more activity** button requests additional pages without re-fetching the first set, and disables itself while the API call is in progress to prevent duplicate clicks.
- A Prometheus snapshot card shows the aggregated counters returned by the backend dependency injection. Link buttons reference `docs/observability.md` and `docs/api/analytics.md` so operators know where the contract and metrics live.

## Reports
- The **Reports** page disables download buttons until a store is selected and shows inline helper text describing CSV vs JSON behavior.
- CO exports are limited to CSV. MN exports offer CSV and JSON; helper text clarifies when to use each.
- Skeleton rows render while export history loads, and inline destructive alerts surface failures alongside toast notifications.
- The export history table hydrates from `/v1/audit?action=report_export`, refreshing automatically after a download to display the latest outcome, format, and date range. Use the **Load more history** button to traverse additional pages via the new cursor support without re-querying from the beginning.
- Re-run buttons allow operators to trigger the same export filters again and reuse the new inline spinner states for feedback.
- Downloads honor the backend-provided filenames (via `Content-Disposition`) so browsers save CSV/JSON artifacts with the requested date range. Fallback names still mirror the selected filters if headers are missing.

## Account menu & logout
- The global header now renders the authenticated user's email next to the store selector. It collapses into initials on narrow viewports to stay within the 14px toolbar height.
- Selecting **Sign out** sends a `POST /api/auth/logout` request, clears local storage, and redirects to the login screen. While the request is in flight the menu item is disabled and the store selector is temporarily locked.
- Session metadata (active session ID, issued/expires timestamps, and last activity) is displayed above the logout action when `GET /api/me` returns an active `session` object. This gives operators immediate visibility into which token is active and which stores it spans.
- Use the account menu to confirm which environment you are browsing; the email label mirrors the `GET /api/me` payload returned by the backend.

## Accessibility
- All buttons and interactive controls expose accessible labels via `<Label>` components or descriptive text.
- Status badges use semantic colors that meet contrast guidelines (`bg-success` for success, `bg-destructive` for failures) and also present textual state for screen readers.
- Loading indicators use `aria-busy` friendly spinners (via animated icons) to communicate activity without relying solely on color.
