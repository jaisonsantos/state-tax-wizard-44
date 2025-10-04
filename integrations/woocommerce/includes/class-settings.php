<?php
if (!defined('ABSPATH')) {
    exit;
}

class STW_Settings {
    private const OPTION_KEY = 'stw_settings';

    public function get(): array {
        $defaults = [
            'api_base_url' => '',
            'store_id' => '',
            'hmac_secret' => '',
            'label_override' => 'Retail Delivery Fee',
            'enable_mn' => true,
            'enable_co' => true,
        ];

        $stored = get_option(self::OPTION_KEY, []);
        if (!is_array($stored)) {
            $stored = [];
        }

        return wp_parse_args($stored, $defaults);
    }

    public function save(): void {
        if (!current_user_can('manage_woocommerce')) {
            return;
        }

        $data = [
            'api_base_url' => sanitize_text_field(wp_unslash($_POST['stw_api_base_url'] ?? '')),
            'store_id' => sanitize_text_field(wp_unslash($_POST['stw_store_id'] ?? '')),
            'hmac_secret' => sanitize_text_field(wp_unslash($_POST['stw_hmac_secret'] ?? '')),
            'label_override' => sanitize_text_field(wp_unslash($_POST['stw_label_override'] ?? 'Retail Delivery Fee')),
            'enable_mn' => !empty($_POST['stw_enable_mn']),
            'enable_co' => !empty($_POST['stw_enable_co']),
        ];

        update_option(self::OPTION_KEY, $data, false);
        add_settings_error(
            'state-tax-wizard',
            'state-tax-wizard-saved',
            __('State Tax Wizard settings saved.', 'state-tax-wizard'),
            'updated'
        );
    }
}
