<?php
if (!defined('ABSPATH')) {
    exit;
}

class STW_Fee_Calculator {
    private STW_Settings $settings;
    private STW_Logger $logger;

    public function __construct(STW_Settings $settings) {
        $this->settings = $settings;
        $this->logger = new STW_Logger();
    }

    public function request_quote(): ?array {
        if (!WC()->cart) {
            return null;
        }

        $config = $this->settings->get();
        $body = $this->build_cart_payload($config);

        return $this->post('/api/v1/fees/quote', $body);
    }

    public function apply_order(\WC_Order $order): void {
        $config = $this->settings->get();
        $body = $this->build_order_payload($config, $order);
        $response = $this->post('/api/v1/fees/apply', $body);
        if (!$response) {
            throw new Exception('Failed to apply fee');
        }
    }

    private function build_cart_payload(array $config): array {
        $items = [];
        foreach (WC()->cart->get_cart() as $item) {
            $product = $item['data'];
            $items[] = [
                'sku' => $product->get_sku() ?: $product->get_id(),
                'qty' => (int) $item['quantity'],
                'unit_price_cents' => (int) round($product->get_price() * 100),
                'taxability' => $product->is_taxable() ? 'taxable' : 'nontaxable',
            ];
        }

        $destination = [
            'state' => WC()->customer->get_shipping_state() ?: WC()->customer->get_billing_state(),
            'postal_code' => WC()->customer->get_shipping_postcode(),
        ];

        return [
            'store_id' => $config['store_id'],
            'order_id' => 'woo-cart-' . wp_generate_uuid4(),
            'destination' => array_filter($destination),
            'delivery_method' => 'ship',
            'items' => $items,
            'shipping_amount_cents' => (int) round(WC()->cart->get_shipping_total() * 100),
        ];
    }

    private function build_order_payload(array $config, \WC_Order $order): array {
        $items = [];
        foreach ($order->get_items() as $item) {
            $product = $item->get_product();
            $items[] = [
                'sku' => $product ? ($product->get_sku() ?: $product->get_id()) : $item->get_name(),
                'qty' => (int) $item->get_quantity(),
                'unit_price_cents' => (int) round($item->get_total() / max($item->get_quantity(), 1) * 100),
                'taxability' => $product && $product->is_taxable() ? 'taxable' : 'nontaxable',
            ];
        }

        $destination = [
            'state' => $order->get_shipping_state() ?: $order->get_billing_state(),
            'postal_code' => $order->get_shipping_postcode(),
        ];

        return [
            'store_id' => $config['store_id'],
            'order_id' => $order->get_id(),
            'destination' => array_filter($destination),
            'delivery_method' => $order->has_shipping_address() ? 'ship' : 'pickup',
            'items' => $items,
            'shipping_amount_cents' => (int) round($order->get_shipping_total() * 100),
            'metadata' => [
                'woo_order_key' => $order->get_order_key(),
            ],
        ];
    }

    private function post(string $path, array $payload): ?array {
        $config = $this->settings->get();
        $url = trailingslashit($config['api_base_url']) . ltrim($path, '/');
        $body = wp_json_encode($payload, JSON_UNESCAPED_SLASHES);
        $headers = $this->signed_headers($config, $body);

        $response = wp_remote_post($url, [
            'headers' => $headers,
            'body' => $body,
            'timeout' => 10,
        ]);

        if (is_wp_error($response)) {
            $this->logger->error('Integration request failed', [
                'url' => $url,
                'error' => $response->get_error_message(),
            ]);
            return null;
        }

        $status = wp_remote_retrieve_response_code($response);
        $decoded = json_decode(wp_remote_retrieve_body($response), true);
        if ($status >= 400) {
            $this->logger->warn('Integration request returned error', [
                'url' => $url,
                'status' => $status,
                'response' => $decoded,
            ]);
            return null;
        }

        $this->logger->info('Integration request succeeded', [
            'url' => $url,
            'status' => $status,
        ]);

        return is_array($decoded) ? $decoded : null;
    }

    private function signed_headers(array $config, string $body): array {
        $timestamp = gmdate('c');
        $nonce = bin2hex(random_bytes(8));
        $canonical = sprintf("%s\n%s\n%s", $timestamp, $nonce, $body);
        $signature = hash_hmac('sha256', $canonical, $config['hmac_secret']);

        return [
            'Content-Type' => 'application/json',
            'X-RDF-Timestamp' => $timestamp,
            'X-RDF-Nonce' => $nonce,
            'X-RDF-Signature' => $signature,
        ];
    }
}
