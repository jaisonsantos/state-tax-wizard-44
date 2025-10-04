<?php
if (!defined('ABSPATH')) {
    exit;
}

class STW_Logger {
    private const TRANSIENT_KEY = 'stw_logs';
    private const MAX_ENTRIES = 200;

    public function recent(int $limit = 50): array {
        $entries = get_option(self::TRANSIENT_KEY, []);
        if (!is_array($entries)) {
            return [];
        }
        return array_slice(array_reverse($entries), 0, $limit);
    }

    public function info(string $message, array $context = []): void {
        $this->append('info', $message, $context);
    }

    public function warn(string $message, array $context = []): void {
        $this->append('warning', $message, $context);
    }

    public function error(string $message, array $context = []): void {
        $this->append('error', $message, $context);
    }

    private function append(string $level, string $message, array $context): void {
        $entries = get_option(self::TRANSIENT_KEY, []);
        if (!is_array($entries)) {
            $entries = [];
        }

        $entries[] = [
            'timestamp' => gmdate('c'),
            'level' => $level,
            'message' => $message,
            'context' => wp_json_encode($context, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
        ];

        if (count($entries) > self::MAX_ENTRIES) {
            $entries = array_slice($entries, -self::MAX_ENTRIES);
        }

        update_option(self::TRANSIENT_KEY, $entries, false);
    }
}
