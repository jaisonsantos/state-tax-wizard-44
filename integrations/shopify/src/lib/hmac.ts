import crypto from 'crypto';

export interface SignedRequest {
  headers: Record<string, string>;
  body: string;
}

export function signPayload(secret: string, payload: unknown, timestamp: Date = new Date()): SignedRequest {
  const body = JSON.stringify(payload);
  const nonce = crypto.randomBytes(16).toString('hex');
  const canonical = `${timestamp.toISOString()}\n${nonce}\n${body}`;
  const signature = crypto.createHmac('sha256', secret).update(canonical).digest('hex');

  return {
    headers: {
      'Content-Type': 'application/json',
      'X-Taxo-Timestamp': timestamp.toISOString(),
      'X-Taxo-Nonce': nonce,
      'X-Taxo-Signature': signature,
    },
    body,
  };
}

export function verifyShopifyWebhook(payload: string, header: string | undefined, secret: string): boolean {
  if (!header) {
    return false;
  }

  const hmac = crypto.createHmac('sha256', secret).update(payload, 'utf8').digest('base64');
  return crypto.timingSafeEqual(Buffer.from(hmac), Buffer.from(header));
}
