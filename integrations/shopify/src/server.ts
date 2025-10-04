import express from 'express';
import bodyParser from 'body-parser';
import { registerProxyRoute } from './routes/proxy.js';
import { registerWebhookRoute } from './routes/webhooks.js';

const app = express();
app.use(bodyParser.json({ verify: (req: any, res, buf) => (req.rawBody = buf.toString()) }));

const config = {
  apiBaseUrl: process.env.STW_API_BASE_URL ?? 'http://localhost:8000',
  storeId: process.env.STW_STORE_ID ?? 'store_demo_1',
  hmacSecret: process.env.STW_HMAC_SECRET ?? 'demo-hmac-secret',
  webhookSecret: process.env.SHOPIFY_WEBHOOK_SECRET ?? 'demo-webhook-secret',
};

registerProxyRoute(app, config);
registerWebhookRoute(app, config);

const port = Number(process.env.PORT ?? 4000);
app.listen(port, () => {
  console.log(`State Tax Wizard Shopify app listening on port ${port}`);
});
