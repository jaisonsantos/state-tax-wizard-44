<?php
if (!defined('ABSPATH')) {
    exit;
}
?>
<div class="wrap">
    <h1><?php echo esc_html__('State Tax Wizard Logs', 'state-tax-wizard'); ?></h1>
    <p><?php echo esc_html__('Last 50 synchronization events.', 'state-tax-wizard'); ?></p>
    <table class="wp-list-table widefat fixed striped">
        <thead>
            <tr>
                <th><?php esc_html_e('Timestamp', 'state-tax-wizard'); ?></th>
                <th><?php esc_html_e('Level', 'state-tax-wizard'); ?></th>
                <th><?php esc_html_e('Message', 'state-tax-wizard'); ?></th>
                <th><?php esc_html_e('Context', 'state-tax-wizard'); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php if (empty($entries)) : ?>
                <tr>
                    <td colspan="4"><?php esc_html_e('No entries recorded yet.', 'state-tax-wizard'); ?></td>
                </tr>
            <?php else : ?>
                <?php foreach ($entries as $entry) : ?>
                    <tr>
                        <td><?php echo esc_html($entry['timestamp']); ?></td>
                        <td><?php echo esc_html(strtoupper($entry['level'])); ?></td>
                        <td><?php echo esc_html($entry['message']); ?></td>
                        <td><code><?php echo esc_html($entry['context']); ?></code></td>
                    </tr>
                <?php endforeach; ?>
            <?php endif; ?>
        </tbody>
    </table>
</div>
