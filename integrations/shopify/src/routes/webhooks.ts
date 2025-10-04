import type { Request, Response, Router } from 'express';
import axios from 'axios';
import { verifyShopifyWebhook, signPayload } from '../lib/hmac.js';

export interface WebhookConfig {
  apiBaseUrl: string;
  storeId: string;
  hmacSecret: string;
  webhookSecret: string;
}

export function registerWebhookRoute(router: Router, config: WebhookConfig): void {
  router.post('/webhooks/orders/create', async (req: Request, res: Response) => {
    const rawBody = JSON.stringify(req.body);
    const signature = req.headers['x-shopify-hmac-sha256'];

    if (!verifyShopifyWebhook(rawBody, typeof signature === 'string' ? signature : undefined, config.webhookSecret)) {
      return res.status(401).json({ message: 'Invalid Shopify webhook signature' });
    }

    const payload = {
      store_id: config.storeId,
      order_id: req.body.id,
      destination: {
        state: req.body.shipping_address?.province_code,
        postal_code: req.body.shipping_address?.zip,
      },
      delivery_method: 'ship',
      items: (req.body.line_items ?? []).map((line: any) => ({
        sku: line.sku ?? line.variant_id,
        qty: line.quantity,
        unit_price_cents: Math.round(Number(line.price ?? 0) * 100),
        taxability: line.taxable ? 'taxable' : 'nontaxable',
      })),
      shipping_amount_cents: Math.round(Number(req.body.total_shipping_price_set?.shop_money?.amount ?? 0) * 100),
    };

    const signed = signPayload(config.hmacSecret, payload);

    try {
      await axios.post(`${config.apiBaseUrl}/api/v1/fees/apply`, signed.body, { headers: signed.headers });
      return res.status(200).json({ status: 'processed' });
    } catch (error) {
      return res.status(502).json({ message: 'Failed to sync order', error: String(error) });
    }
  });
}
