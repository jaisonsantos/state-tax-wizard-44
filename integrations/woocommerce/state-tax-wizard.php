<?php
/**
 * Plugin Name:       State Tax Wizard
 * Description:       Sync WooCommerce carts and orders with the State Tax Wizard API using HMAC signed requests.
 * Version:           0.1.0
 * Author:            State Tax Wizard
 * Requires at least: 6.0
 * Requires PHP:      8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

define('STW_PLUGIN_VERSION', '0.1.0');

define('STW_PLUGIN_PATH', plugin_dir_path(__FILE__));

define('STW_PLUGIN_URL', plugin_dir_url(__FILE__));

require_once STW_PLUGIN_PATH . 'includes/class-fee-calculator.php';
require_once STW_PLUGIN_PATH . 'includes/class-settings.php';
require_once STW_PLUGIN_PATH . 'includes/class-logger.php';

class STW_Plugin {
    private STW_Fee_Calculator $calculator;
    private STW_Settings $settings;
    private STW_Logger $logger;

    public function __construct() {
        $this->settings = new STW_Settings();
        $this->calculator = new STW_Fee_Calculator($this->settings);
        $this->logger = new STW_Logger();

        add_action('admin_menu', [$this, 'register_admin_pages']);
        add_action('woocommerce_cart_calculate_fees', [$this, 'inject_fee']);
        add_action('woocommerce_checkout_order_processed', [$this, 'persist_order'], 10, 3);
        add_filter('woocommerce_settings_tabs_array', [$this, 'register_settings_tab'], 50);
        add_action('woocommerce_settings_tabs_state_tax_wizard', [$this, 'render_settings']);
        add_action('woocommerce_update_options_state_tax_wizard', [$this->settings, 'save']);
    }

    public function register_admin_pages(): void {
        add_submenu_page(
            'woocommerce',
            __('State Tax Wizard', 'state-tax-wizard'),
            __('State Tax Wizard', 'state-tax-wizard'),
            'manage_woocommerce',
            'state-tax-wizard-logs',
            [$this, 'render_logs_page']
        );
    }

    public function register_settings_tab(array $tabs): array {
        $tabs['state_tax_wizard'] = __('State Tax Wizard', 'state-tax-wizard');
        return $tabs;
    }

    public function render_settings(): void {
        include STW_PLUGIN_PATH . 'admin/settings-page.php';
    }

    public function render_logs_page(): void {
        $entries = $this->logger->recent(50);
        include STW_PLUGIN_PATH . 'admin/logs-page.php';
    }

    public function inject_fee(): void {
        if (!is_admin() && defined('WC_DOING_AJAX') && !WC_DOING_AJAX) {
            return;
        }

        $config = $this->settings->get();
        if (empty($config['api_base_url']) || empty($config['store_id']) || empty($config['hmac_secret'])) {
            $this->logger->warn('Missing configuration, skipping fee injection');
            return;
        }

        $quote = $this->calculator->request_quote();
        if (!$quote || empty($quote['total_fee_cents'])) {
            return;
        }

        $amount = $quote['total_fee_cents'] / 100;
        $label = !empty($config['label_override']) ? $config['label_override'] : __('Retail Delivery Fee', 'state-tax-wizard');
        WC()->cart->add_fee($label, $amount, true);
    }

    public function persist_order(int $order_id, array $posted_data, \WC_Order $order): void {
        $config = $this->settings->get();
        if (empty($config['api_base_url']) || empty($config['store_id']) || empty($config['hmac_secret'])) {
            return;
        }

        try {
            $this->calculator->apply_order($order);
        } catch (Exception $exception) {
            $this->logger->error('Failed to sync order', [
                'order_id' => $order_id,
                'message' => $exception->getMessage(),
            ]);
        }
    }
}

new STW_Plugin();
