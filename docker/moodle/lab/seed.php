<?php

define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/mod/forum/lib.php');
require_once($CFG->dirroot . '/mod/assign/locallib.php');
require_once(__DIR__ . '/session.php');

function number_setting(string $name, int $default, int $min, int $max): int {
    $raw = getenv($name);
    $value = $raw === false || $raw === '' ? $default : filter_var($raw, FILTER_VALIDATE_INT);
    if ($value === false || $value < $min || $value > $max) {
        throw new InvalidArgumentException("$name fuera de rango ($min-$max)");
    }
    return $value;
}

$students = number_setting('STUDENT_COUNT', 120, 6, 2000);
$teachers = number_setting('TEACHER_COUNT', 6, 3, 100);
$courses = number_setting('COURSE_COUNT', 12, 3, 100);
$password = getenv('PARTICIPANT_PASSWORD');
if (!$password) {
    throw new RuntimeException('PARTICIPANT_PASSWORD requerido');
}
$signature = hash('sha256', json_encode([$students, $teachers, $courses, 'seed-v1']));
if (get_config('local_tuari', 'seed_version')) {
    if (get_config('local_tuari', 'seed_signature') !== $signature) {
        throw new RuntimeException('El volumen tiene otra escala de datos. Restaurar o reiniciar explícitamente.');
    }
    echo "Dataset v1 ya instalado; no se modifican usuarios ni actividades.\n";
    exit(0);
}

$admin = get_admin();
lab_set_user($admin);
set_config('timezone', 'America/Argentina/Buenos_Aires');
set_config('forcelogin', 1);
set_config('enablecompletion', 1);
set_config('enableblogs', 0);
set_config('passwordpolicy', 1);
set_config('allowthemechangeonurl', 0);
set_config('sitepolicy', '');

$institutions = ['Instituto Horizonte', 'Fundación Aprender', 'Centro de Formación del Sur'];
$categories = [];
foreach ($institutions as $i => $name) {
    $idnumber = 'TUARI-INST-' . ($i + 1);
    $category = $DB->get_record('course_categories', ['idnumber' => $idnumber]);
    $categories[$i] = $category ?: \core_course_category::create([
        'name' => $name, 'idnumber' => $idnumber,
        'description' => 'Institución ficticia del caso TUARI.', 'descriptionformat' => FORMAT_HTML,
    ]);
}

function lab_user(string $username, string $firstname, string $lastname, string $institution): stdClass {
    global $DB, $CFG, $password;
    $user = $DB->get_record('user', ['username' => $username, 'mnethostid' => $CFG->mnet_localhost_id]);
    if ($user) {
        return $user;
    }
    $id = user_create_user((object)[
        'username' => $username, 'password' => $password, 'auth' => 'manual', 'confirmed' => 1,
        'mnethostid' => $CFG->mnet_localhost_id, 'firstname' => $firstname, 'lastname' => $lastname,
        'email' => "$username@campus.example.test", 'institution' => $institution,
        'city' => 'Tandil', 'country' => 'AR', 'lang' => 'en',
        'timezone' => 'America/Argentina/Buenos_Aires', 'maildisplay' => 0,
    ]);
    return $DB->get_record('user', ['id' => $id], '*', MUST_EXIST);
}

$studentusers = [];
for ($i = 1; $i <= $students; $i++) {
    $studentusers[$i] = lab_user(sprintf('estudiante%03d', $i), 'Estudiante', sprintf('Simulado %03d', $i), $institutions[($i - 1) % 3]);
}
$teacherusers = [];
for ($i = 1; $i <= $teachers; $i++) {
    $teacherusers[$i] = lab_user(sprintf('docente%02d', $i), 'Docente', sprintf('Simulado %02d', $i), $institutions[($i - 1) % 3]);
}
$observer = lab_user('relevador', 'Equipo', 'Relevamiento', 'Consultora ficticia');

$roleid = $DB->get_field('role', 'id', ['shortname' => 'tuari_observer']);
if (!$roleid) {
    $roleid = create_role('Relevador TUARI', 'tuari_observer', 'Consulta de cursos e informes para el laboratorio.');
}
foreach (['moodle/category:viewcourselist', 'moodle/course:view', 'moodle/course:viewparticipants',
    'moodle/site:viewreports', 'report/log:view', 'report/log:viewtoday', 'report/stats:view',
    'report/outline:view', 'moodle/user:viewdetails', 'mod/page:view', 'mod/forum:viewdiscussion'] as $cap) {
    if (get_capability_info($cap)) {
        assign_capability($cap, CAP_ALLOW, $roleid, context_system::instance()->id, true);
    }
}
role_assign($roleid, $observer->id, context_system::instance()->id);

$manual = enrol_get_plugin('manual');
$studentrole = $DB->get_field('role', 'id', ['shortname' => 'student'], MUST_EXIST);
$teacherrole = $DB->get_field('role', 'id', ['shortname' => 'editingteacher'], MUST_EXIST);
$subjects = ['Administración de redes', 'Seguridad informática', 'Servicios web', 'Herramientas de oficina'];

function lab_module(stdClass $course, string $type, string $code, string $name, array $extra = []): stdClass {
    global $DB;
    $existing = $DB->get_record('course_modules', ['course' => $course->id, 'idnumber' => $code]);
    if ($existing) {
        return (object)['coursemodule' => $existing->id, 'instance' => $existing->instance];
    }
    return create_module((object)array_merge([
        'course' => $course->id, 'modulename' => $type, 'section' => 1, 'visible' => 1,
        'name' => $name, 'cmidnumber' => $code,
        'introeditor' => ['text' => '<p>Actividad ficticia para el laboratorio TUARI.</p>', 'format' => FORMAT_HTML, 'itemid' => 0],
        'showdescription' => 1, 'completion' => 0, 'groupmode' => 0,
    ], $extra));
}

for ($i = 1; $i <= $courses; $i++) {
    $shortname = sprintf('TUARI-%02d', $i);
    $course = $DB->get_record('course', ['shortname' => $shortname]);
    if (!$course) {
        $course = create_course((object)[
            'fullname' => $subjects[($i - 1) % 4] . " - Comisión $i", 'shortname' => $shortname,
            'idnumber' => $shortname, 'category' => $categories[($i - 1) % 3]->id,
            'summary' => '<p>Curso de una organización ficticia de capacitación a distancia.</p>',
            'summaryformat' => FORMAT_HTML, 'format' => 'topics', 'numsections' => 3,
            'startdate' => strtotime('-8 weeks midnight'), 'enddate' => strtotime('+8 weeks midnight'),
            'enablecompletion' => 1, 'newsitems' => 0,
        ]);
    }
    $instance = null;
    foreach (enrol_get_instances($course->id, false) as $enrolment) {
        if ($enrolment->enrol === 'manual') {
            $instance = $enrolment;
            break;
        }
    }
    if (!$instance) {
        $instanceid = $manual->add_instance($course);
        $instance = $DB->get_record('enrol', ['id' => $instanceid], '*', MUST_EXIST);
    }
    $teacher = $teacherusers[(($i - 1) % $teachers) + 1];
    $manual->enrol_user($instance, $teacher->id, $teacherrole);
    $members = [];
    foreach ($studentusers as $n => $student) {
        if (($n - 1) % 3 === ($i - 1) % 3) {
            $manual->enrol_user($instance, $student->id, $studentrole);
            $members[] = $student;
        }
    }
    $page = lab_module($course, 'page', "$shortname-GUIA", 'Guía de estudio', [
        'content' => '<h3>Material de trabajo</h3><p>Leer el material y resolver la actividad.</p><p><a href="@@PLUGINFILE@@/guia.txt">Descargar guía de práctica</a></p>',
        'contentformat' => FORMAT_HTML, 'display' => 5, 'printintro' => 0,
        'printlastmodified' => 1, 'displayoptions' => serialize([]),
    ]);
    $fileinfo = [
        'contextid' => context_module::instance($page->coursemodule)->id,
        'component' => 'mod_page', 'filearea' => 'content', 'itemid' => 0,
        'filepath' => '/', 'filename' => 'guia.txt', 'userid' => $teacher->id,
    ];
    $fs = get_file_storage();
    if (!$fs->file_exists($fileinfo['contextid'], 'mod_page', 'content', 0, '/', 'guia.txt')) {
        $fs->create_file_from_string($fileinfo, str_repeat("Material ficticio de $shortname. Práctica de redes y servicios.\n", 800));
    }
    $forum = lab_module($course, 'forum', "$shortname-FORO", 'Consultas del curso', [
        'type' => 'general', 'forcesubscribe' => 0, 'trackingtype' => 1, 'maxbytes' => 0,
        'maxattachments' => 1, 'assessed' => 0, 'scale' => 0, 'grade_forum' => 0,
        'blockafter' => 0, 'blockperiod' => 0, 'warnafter' => 0,
        'completiondiscussions' => 0, 'completionreplies' => 0, 'completionposts' => 0,
    ]);
    if (!$DB->record_exists('forum_discussions', ['forum' => $forum->instance, 'name' => 'Bienvenida y fechas de entrega'])) {
        forum_add_discussion((object)[
            'course' => $course->id, 'forum' => $forum->instance,
            'name' => 'Bienvenida y fechas de entrega',
            'message' => '<p>Las entregas se concentran los viernes. Avisar si encuentran inconvenientes al acceder al campus.</p>',
            'messageformat' => FORMAT_HTML, 'messagetrust' => 0, 'mailnow' => 0,
            'groupid' => -1, 'timestart' => 0, 'timeend' => 0,
        ], null, null, $teacher->id);
    }
    $assignment = lab_module($course, 'assign', "$shortname-TP", 'Trabajo práctico integrador', [
        'alwaysshowdescription' => 1, 'submissiondrafts' => 0, 'requiresubmissionstatement' => 0,
        'sendnotifications' => 0, 'sendstudentnotifications' => 0, 'sendlatenotifications' => 0,
        'duedate' => strtotime('next Friday 23:59'), 'allowsubmissionsfromdate' => 0,
        'grade' => 100, 'cutoffdate' => 0, 'gradingduedate' => 0, 'teamsubmission' => 0,
        'requireallteammemberssubmit' => 0, 'teamsubmissiongroupingid' => 0,
        'blindmarking' => 0, 'attemptreopenmethod' => 'none', 'maxattempts' => 1,
        'markingworkflow' => 0, 'markingallocation' => 0,
        'assignsubmission_onlinetext_enabled' => 1, 'assignsubmission_file_enabled' => 1,
        'assignsubmission_file_maxfiles' => 2, 'assignsubmission_file_maxsizebytes' => 8388608,
        'assignfeedback_comments_enabled' => 1,
    ]);
    $cm = get_coursemodule_from_id('assign', $assignment->coursemodule, 0, false, MUST_EXIST);
    foreach (array_slice($members, 0, 6) as $n => $student) {
        if (!$DB->record_exists('assign_submission', ['assignment' => $assignment->instance, 'userid' => $student->id, 'status' => 'submitted'])) {
            lab_set_user($student);
            $context = context_module::instance($cm->id);
            if (!has_capability('mod/assign:submit', $context)) {
                throw new RuntimeException("Sin permiso de entrega: {$student->username} en $shortname (actividad {$cm->id}).");
            }
            $assign = new assign($context, $cm, $course);
            $notices = [];
            $ok = $assign->save_submission((object)[
                'onlinetext_editor' => ['text' => '<p>Entrega ficticia: inventario, diagnóstico inicial y preguntas pendientes.</p>', 'format' => FORMAT_HTML, 'itemid' => 0],
            ], $notices);
            if (!$ok) {
                throw new RuntimeException('Entrega fallida: ' . implode('; ', $notices));
            }
        }
        lab_set_user($admin);
        if ($n < 3 && !$DB->record_exists_select('assign_grades', 'assignment = ? AND userid = ? AND grade >= 0', [$assignment->instance, $student->id])) {
            $assign = new assign(context_module::instance($cm->id), $cm, $course);
            $assign->save_grade($student->id, (object)[
                'grade' => 65 + $n * 10, 'attemptnumber' => -1, 'addattempt' => 0,
                'applytoall' => 0, 'sendstudentnotifications' => 0,
                'assignfeedbackcomments_editor' => ['text' => 'Devolución ficticia: ampliar las evidencias del diagnóstico.', 'format' => FORMAT_HTML],
            ]);
        }
    }
    echo "$shortname: curso, matrículas, guía, foro, entregas y calificaciones.\n";
}
lab_set_user($admin);
set_config('seed_signature', $signature, 'local_tuari');
set_config('seed_version', '1', 'local_tuari');
echo "Dataset v1 listo: $students estudiantes, $teachers docentes, $courses cursos y relevador.\n";
