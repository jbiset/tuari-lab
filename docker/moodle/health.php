<?php

try {
    $db = new mysqli(getenv('DB_HOST'), getenv('DB_USER'), getenv('DB_PASSWORD'), getenv('DB_NAME'));
    $result = $db->query("SELECT value FROM mdl_config_plugins WHERE plugin='local_tuari' AND name='seed_version'");
    if (!$result || $result->fetch_row()[0] !== '1') {
        throw new RuntimeException('Seed incomplete');
    }
    header('Content-Type: text/plain');
    echo "ready\n";
} catch (Throwable $e) {
    http_response_code(503);
    echo "not ready\n";
}
