<?php
define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
require_once(__DIR__ . '/session.php');
$expected = ['students' => (int)getenv('STUDENT_COUNT'), 'teachers' => (int)getenv('TEACHER_COUNT'), 'courses' => (int)getenv('COURSE_COUNT')];
$actual = [
    'students' => $DB->count_records_select('user', "username LIKE 'estudiante%' AND deleted=0"),
    'teachers' => $DB->count_records_select('user', "username LIKE 'docente%' AND deleted=0"),
    'courses' => $DB->count_records_select('course', "shortname LIKE 'TUARI-%'"),
];
$observerid = $DB->get_field('user', 'id', ['username' => 'relevador'], MUST_EXIST);
$observer = $DB->get_record('user', ['id' => $observerid], '*', MUST_EXIST);
$checks = [
    'seed_complete' => get_config('local_tuari', 'seed_version') === '1',
    'counts' => $actual === $expected,
    'submissions' => $DB->count_records('assign_submission', ['status' => 'submitted']) >= $expected['courses'] * min(6, intdiv($expected['students'], 3)),
    'grades' => $DB->count_records_select('assign_grades', 'grade >= 0') >= $expected['courses'] * min(3, intdiv($expected['students'], 3)),
    'observer_cannot_configure' => !has_capability('moodle/site:config', context_system::instance(), $observer),
    'files_exist' => true,
];
$files = $DB->get_records('files', ['component' => 'mod_page', 'filearea' => 'content', 'filename' => 'guia.txt']);
$checks['files_exist'] = count($files) === $expected['courses'];
foreach ($files as $file) {
    $stored = get_file_storage()->get_file_by_id($file->id);
    $checks['files_exist'] = $checks['files_exist'] && $stored && $stored->get_filesize() > 0 && strlen($stored->get_content()) > 0;
}
$checks['student_submission_permissions'] = true;
$permissionfailures = [];

$sampleusers = [];
for ($i = 1; $i <= min(6, $expected['students']); $i++) {
    $sampleusers[$i] = $DB->get_record('user', ['username' => sprintf('estudiante%03d', $i)], '*', MUST_EXIST);
}
foreach ($DB->get_records_select('course', "shortname LIKE 'TUARI-%'", [], 'shortname') as $course) {
    $institution = ((int)substr($course->shortname, 6) - 1) % 3;
    $cm = $DB->get_record('course_modules', ['course' => $course->id, 'idnumber' => $course->shortname . '-TP']);
    foreach ($sampleusers as $i => $student) {
        if (($i - 1) % 3 !== $institution) {
            continue;
        }
        lab_set_user($student);
        if (!$cm || !has_capability('mod/assign:submit', context_module::instance($cm->id))) {
            $checks['student_submission_permissions'] = false;
            $permissionfailures[] = $student->username . ':' . $course->shortname;
        }
    }
}
echo json_encode(['permission_failures' => $permissionfailures], JSON_UNESCAPED_UNICODE) . "\n";
echo json_encode(['checks' => $checks, 'actual' => $actual, 'expected' => $expected], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
exit(in_array(false, $checks, true) ? 1 : 0);
