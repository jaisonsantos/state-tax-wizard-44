# Store Settings API

The store settings endpoints manage delivery fee configuration flags for each
merchant store. They back the React settings page and the fee engine, enabling
merchants to toggle state-specific fees, absorb delivery charges, and customize
checkout labels.

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
  "plan": "starter"
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
  "plan": "starter"
}
```

## Audit trail

Updates emit an `audit_logs` record capturing the actor email, store ID, and the
submitted payload. This keeps compliance teams informed about who changed fee
rules and when.

## Related resources

- Frontend integration lives in `src/pages/Settings.tsx`.
- Postman collection requests are stored under the **Store Settings** folder in
  `docs/postman/state-tax-wizard.postman_collection.json`.
- Fee calculation honors these toggles via `backend/app/services/fee_service.py`.
