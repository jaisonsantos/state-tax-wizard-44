<?php

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../includes/class-settings.php';
require_once __DIR__ . '/../includes/class-logger.php';
require_once __DIR__ . '/../includes/class-fee-calculator.php';

if (!function_exists('trailingslashit')) {
    function trailingslashit(string $path): string {
        return rtrim($path, '/') . '/';
    }
}

if (!function_exists('wp_json_encode')) {
    function wp_json_encode($data, $options = 0) {
        return json_encode($data, $options);
    }
}

class Stub_Settings extends STW_Settings {
    private array $data;

    public function __construct(array $data) {
        $this->data = $data;
    }

    public function get(): array {
        return $this->data;
    }
}

class STW_Fee_Calculator_Test extends TestCase {
    public function test_signed_headers_include_valid_hmac(): void {
        $settings = new Stub_Settings([
            'api_base_url' => 'https://api.example.com',
            'store_id' => 'store-demo',
            'hmac_secret' => 'secret-key',
        ]);
        $calculator = new STW_Fee_Calculator($settings);

        $reflection = new ReflectionClass($calculator);
        $method = $reflection->getMethod('signed_headers');
        $method->setAccessible(true);

        $headers = $method->invoke($calculator, $settings->get(), json_encode(['foo' => 'bar']));

        $this->assertArrayHasKey('X-RDF-Timestamp', $headers);
        $this->assertArrayHasKey('X-RDF-Nonce', $headers);
        $this->assertArrayHasKey('X-RDF-Signature', $headers);

        $timestamp = $headers['X-RDF-Timestamp'];
        $nonce = $headers['X-RDF-Nonce'];
        $expected = hash_hmac('sha256', $timestamp . "\n" . $nonce . "\n" . json_encode(['foo' => 'bar']), 'secret-key');
        $this->assertSame($expected, $headers['X-RDF-Signature']);
    }
}
