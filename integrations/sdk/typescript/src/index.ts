import { createHmac, randomBytes } from 'crypto';

export interface FeeRequestPayload {
  store_id: string;
  order_id: string;
  destination: Record<string, unknown>;
  delivery_method: string;
  items: Array<Record<string, unknown>>;
  shipping_amount_cents: number;
  metadata?: Record<string, unknown>;
}

export interface SignedPayload {
  body: string;
  headers: Record<string, string>;
}

export interface SignOptions {
  timestamp?: Date;
  nonce?: string;
}

export function signFeeRequest(secret: string, payload: FeeRequestPayload, options: SignOptions = {}): SignedPayload {
  if (!secret) {
    throw new Error('Secret is required');
  }

  const timestamp = (options.timestamp ?? new Date()).toISOString();
  const nonce = options.nonce ?? randomBytes(16).toString('hex');
  const body = JSON.stringify(payload);
  const canonical = `${timestamp}\n${nonce}\n${body}`;
  const signature = createHmac('sha256', secret).update(canonical).digest('hex');

  return {
    body,
    headers: {
      'Content-Type': 'application/json',
      'X-Taxo-Timestamp': timestamp,
      'X-Taxo-Nonce': nonce,
      'X-Taxo-Signature': signature,
    },
  };
}

export function noncePreview(value: string, length = 8): string {
  if (value.length <= length) {
    return value;
  }
  return value.slice(0, length);
}

