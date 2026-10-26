<?php
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$db = new mysqli(getenv('DB_HOST'), getenv('DB_USER'), getenv('DB_PASSWORD'), getenv('DB_NAME'));
$tables = $db->query('SHOW TABLES');
if ($tables->num_rows === 0) {
    echo 'empty';
    exit;
}
try {
    $version = $db->query("SELECT value FROM mdl_config WHERE name='version'")->fetch_row();
    $admin = $db->query("SELECT id FROM mdl_user WHERE username='admin' AND password <> 'adminsetuppending'")->fetch_row();
    echo ($version && $admin) ? 'installed' : 'partial';
} catch (Throwable $e) {
    echo 'partial';
}
