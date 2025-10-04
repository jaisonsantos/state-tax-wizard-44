import crypto from 'crypto';
import { signPayload, verifyShopifyWebhook } from '../src/lib/hmac.js';

describe('signPayload', () => {
  it('generates canonical signature with timestamp and nonce', () => {
    const now = new Date('2024-01-01T00:00:00.000Z');
    const result = signPayload('secret', { foo: 'bar' }, now);

    expect(result.headers['X-RDF-Timestamp']).toBe(now.toISOString());
    expect(result.headers['X-RDF-Nonce']).toHaveLength(32);
    expect(result.headers['X-RDF-Signature']).toHaveLength(64);
  });
});

describe('verifyShopifyWebhook', () => {
  it('returns true for matching HMAC signatures', () => {
    const payload = '{"foo":"bar"}';
    const secret = 'webhook';
    const hmac = crypto.createHmac('sha256', secret).update(payload).digest('base64');

    expect(verifyShopifyWebhook(payload, hmac, secret)).toBe(true);
  });

  it('returns false for mismatched signatures', () => {
    expect(verifyShopifyWebhook('{}', 'invalid', 'secret')).toBe(false);
  });
});
