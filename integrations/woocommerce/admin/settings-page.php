<?php
if (!defined('ABSPATH')) {
    exit;
}

$settings = $this->settings->get();
?>
<div class="wrap">
    <h1><?php echo esc_html__('State Tax Wizard Integration', 'state-tax-wizard'); ?></h1>
    <p><?php echo esc_html__('Configure the connection between WooCommerce and the State Tax Wizard API.', 'state-tax-wizard'); ?></p>
    <table class="form-table">
        <tr>
            <th scope="row"><?php esc_html_e('API Base URL', 'state-tax-wizard'); ?></th>
            <td>
                <input type="text" name="stw_api_base_url" value="<?php echo esc_attr($settings['api_base_url'] ?? ''); ?>" class="regular-text" />
                <p class="description"><?php esc_html_e('Example: https://api.statetaxwizard.com', 'state-tax-wizard'); ?></p>
            </td>
        </tr>
        <tr>
            <th scope="row"><?php esc_html_e('Store ID', 'state-tax-wizard'); ?></th>
            <td>
                <input type="text" name="stw_store_id" value="<?php echo esc_attr($settings['store_id'] ?? ''); ?>" class="regular-text" />
            </td>
        </tr>
        <tr>
            <th scope="row"><?php esc_html_e('HMAC Secret', 'state-tax-wizard'); ?></th>
            <td>
                <input type="password" name="stw_hmac_secret" value="<?php echo esc_attr($settings['hmac_secret'] ?? ''); ?>" class="regular-text" autocomplete="off" />
                <p class="description"><?php esc_html_e('Rotate the secret from the State Tax Wizard admin after installation.', 'state-tax-wizard'); ?></p>
            </td>
        </tr>
        <tr>
            <th scope="row"><?php esc_html_e('Label override', 'state-tax-wizard'); ?></th>
            <td>
                <input type="text" name="stw_label_override" value="<?php echo esc_attr($settings['label_override'] ?? 'Retail Delivery Fee'); ?>" class="regular-text" />
            </td>
        </tr>
        <tr>
            <th scope="row"><?php esc_html_e('Jurisdictions', 'state-tax-wizard'); ?></th>
            <td>
                <label>
                    <input type="checkbox" name="stw_enable_mn" <?php checked(!empty($settings['enable_mn'])); ?> />
                    <?php esc_html_e('Enable Minnesota (MN)', 'state-tax-wizard'); ?>
                </label>
                <br />
                <label>
                    <input type="checkbox" name="stw_enable_co" <?php checked(!empty($settings['enable_co'])); ?> />
                    <?php esc_html_e('Enable Colorado (CO)', 'state-tax-wizard'); ?>
                </label>
            </td>
        </tr>
    </table>
    <p class="submit">
        <button type="submit" class="button-primary"><?php esc_html_e('Save Changes', 'state-tax-wizard'); ?></button>
    </p>
</div>
