# Store Settings API

The store settings endpoints manage delivery fee configuration flags for each
merchant store. They back the React settings page and the fee engine, enabling
merchants to toggle state-specific fees, absorb delivery charges, and customize
checkout labels. When a custom label is omitted the engine now falls back to the
jurisdiction defaults – **Road Improvement and Food Delivery Fee (MN)** and
**Retail Delivery Fee (CO)** – ensuring quotes and persisted order fees stay in
sync with the latest regulatory copy.

## Authentication

All routes require a valid bearer token created via `POST /api/auth/login`. The
authenticated user must have access to the target store. Requests without the
`Authorization: Bearer {{token}}` header receive a `401`, while users lacking
store access receive a `403`.

## Endpoints

### `GET /api/v1/stores/{store_id}/settings`

Returns the persisted configuration for the selected store. A settings row is
created on first access if it does not exist.

**Response**

```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "enable_mn": true,
  "enable_co": true,
  "absorb_fee": false,
  "label_override": "Delivery Fee",
  "plan": "starter",
  "hmac_last_rotated_at": "2025-01-12T19:44:21+00:00"
}
```

### `PUT /api/v1/stores/{store_id}/settings`

Persists the configuration flags for the store and writes an audit log entry
(`store_settings.update`). The request body must include all fields; the API
trims surrounding whitespace on `label_override`.

**Request body**

```json
{
  "enable_mn": false,
  "enable_co": true,
  "absorb_fee": true,
  "label_override": "Handling Surcharge"
}
```

**Response**

```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "enable_mn": false,
  "enable_co": true,
  "absorb_fee": true,
  "label_override": "Handling Surcharge",
  "plan": "starter",
  "hmac_last_rotated_at": "2025-01-12T19:44:21+00:00"
}
```

### `POST /api/v1/stores/{store_id}/hmac/rotate`

Generates a new per-store HMAC secret, persists the timestamp, emits a `store_secret.rotated` audit log, and returns the secret **once** so operators can copy it into their integration tooling.

**Response**

```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "hmac_secret": "<new-secret-value>",
  "rotated_at": "2025-01-12T19:45:02+00:00",
  "previous_rotated_at": "2024-12-01T17:12:44+00:00"
}
```

> Copy the secret immediately—neither the API nor audit log payloads will display it again.

## Audit trail

Updates emit an `audit_logs` record capturing the actor email, store ID, and the
submitted payload. This keeps compliance teams informed about who changed fee
rules and when.

## Related resources

- Frontend integration lives in `src/pages/Settings.tsx`.
- Postman collection requests (including rotation) live under the **Store Settings** and **Fees** folders in `docs/postman/state-tax-wizard.postman_collection.json`.
- Fee calculation honors these toggles via `backend/app/services/fee_service.py` and
  propagates `absorb_fee` to `FeeLine.absorbed` / `order_fees.absorbed` for audit and
  reporting.
