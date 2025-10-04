import type { Request, Response, Router } from 'express';
import axios from 'axios';
import { signPayload } from '../lib/hmac.js';

export interface ProxyConfig {
  apiBaseUrl: string;
  storeId: string;
  hmacSecret: string;
}

export function registerProxyRoute(router: Router, config: ProxyConfig): void {
  router.get('/apps/state-tax-wizard/quote', async (req: Request, res: Response) => {
    const timestamp = new Date();
    const payload = {
      store_id: config.storeId,
      order_id: `shopify-proxy-${timestamp.getTime()}`,
      destination: { province: req.query.province, country: req.query.country },
      delivery_method: 'ship',
      items: JSON.parse((req.query.items as string) ?? '[]'),
      shipping_amount_cents: Number(req.query.shipping_amount_cents ?? 0),
    };

    const signed = signPayload(config.hmacSecret, payload, timestamp);

    try {
      const response = await axios.post(
        `${config.apiBaseUrl}/api/v1/fees/quote`,
        signed.body,
        { headers: signed.headers, validateStatus: () => true }
      );

      return res.status(response.status).json(response.data);
    } catch (error) {
      return res.status(502).json({ message: 'Failed to fetch quote', error: String(error) });
    }
  });
}
