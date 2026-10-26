SELECT 'Usuarios por institución' AS informe;
SELECT institution, COUNT(*) AS usuarios FROM mdl_user
WHERE deleted = 0 AND username NOT IN ('guest', 'admin', 'relevador') GROUP BY institution;

SELECT 'Cursos y matrículas activas' AS informe;
SELECT c.shortname, c.fullname, COUNT(DISTINCT ue.userid) AS matriculados
FROM mdl_course c LEFT JOIN mdl_enrol e ON e.courseid = c.id
LEFT JOIN mdl_user_enrolments ue ON ue.enrolid = e.id AND ue.status = 0
WHERE c.id <> 1 GROUP BY c.id, c.shortname, c.fullname ORDER BY c.shortname;

SELECT 'Archivos: referencias lógicas y contenido único (sin directorios)' AS informe;
SELECT COUNT(*) AS referencias, SUM(filesize) AS bytes_logicos FROM mdl_files WHERE filename <> '.';
SELECT SUM(t.bytes) AS bytes_contenido_unico FROM
(SELECT contenthash, MAX(filesize) AS bytes FROM mdl_files WHERE filename <> '.' GROUP BY contenthash) t;

SELECT 'Entregas por estado' AS informe;
SELECT status, COUNT(*) AS cantidad FROM mdl_assign_submission GROUP BY status;

SELECT 'Eventos reales por hora UTC (incluye inicialización y simulador)' AS informe;
SET time_zone = '+00:00';
SELECT DATE_FORMAT(FROM_UNIXTIME(timecreated), '%Y-%m-%d %H:00') AS hora_utc,
       action, COUNT(*) AS eventos FROM mdl_logstore_standard_log
GROUP BY hora_utc, action ORDER BY hora_utc DESC, action LIMIT 48;

SELECT 'Última ejecución de tareas programadas (epoch; 0 = nunca)' AS informe;
SELECT classname, lastruntime, nextruntime, faildelay FROM mdl_task_scheduled
ORDER BY lastruntime DESC LIMIT 15;
