import { createHmac } from 'crypto';
import { describe, expect, it } from 'vitest';
import { signFeeRequest, noncePreview } from '../src/index.js';

describe('signFeeRequest', () => {
  it('produces deterministic signature when nonce and timestamp are supplied', () => {
    const payload = {
      store_id: 'store-demo',
      order_id: 'order-1',
      destination: { state: 'MN' },
      delivery_method: 'ship',
      items: [],
      shipping_amount_cents: 0,
    };

    const secret = 'secret';
    const timestamp = new Date('2024-01-01T00:00:00.000Z');
    const nonce = 'abcd1234abcd1234';

    const signed = signFeeRequest(secret, payload, {
      timestamp: new Date('2024-01-01T00:00:00.000Z'),
      nonce
    });

    const canonical = `${timestamp.toISOString()}\n${nonce}\n${signed.body}`;
    const expectedSignature = createHmac('sha256', secret).update(canonical).digest('hex');

    expect(signed.body).toContain('"store_id":"store-demo"');
    expect(signed.headers['X-Taxo-Timestamp']).toBe(timestamp.toISOString());
    expect(signed.headers['X-Taxo-Nonce']).toBe(nonce);
    expect(signed.headers['X-Taxo-Signature']).toBe(expectedSignature);
    expect(canonical).toBeTruthy();
  });
});

describe('noncePreview', () => {
  it('returns first characters of nonce', () => {
    expect(noncePreview('1234567890abcdef')).toBe('12345678');
  });
});
