<?php
define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
$result = [];
foreach ($DB->get_records_select('course', "shortname LIKE 'TUARI-%'", [], 'shortname', 'id,shortname') as $course) {
    $result[] = ['id' => (int)$course->id, 'institution' => (((int)substr($course->shortname, 6)) - 1) % 3];
}
echo json_encode($result) . "\n";
