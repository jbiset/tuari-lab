# Operación

## Arranque y diagnóstico

```sh
./lab setup
./lab up
./lab status
docker compose logs --tail=100 init
./lab smoke
```

La secuencia es MariaDB saludable → instalación y seed terminados → Moodle saludable → proxy y cron. El healthcheck HTTP verifica base y marcador del seed; `smoke` agrega controles funcionales y login con sesión. Un healthcheck correcto no demuestra que todos los módulos funcionen.

Si falla la descarga durante el build, verificar la conectividad de Docker a GitHub, Docker Hub y repositorios Debian/Alpine. El build valida la revisión Moodle descargada contra el commit esperado.

Si aparece `permission denied` sobre `docker.sock`, la terminal o sesión necesita acceso al motor Docker. Los chequeos estáticos y el historial offline siguen disponibles. Si el motor no está iniciado, iniciar Docker Desktop.

Si el puerto 8080 está ocupado, editar juntos `MOODLE_PORT` y `MOODLE_URL` en `.env`, por ejemplo `8081` y `http://localhost:8081`, y ejecutar `./lab up`. Si ya se cargó contenido con URLs absolutas antiguas, revisar también esas referencias. Para el correo, cambiar `MAIL_PORT`.

Para consultar el correo capturado, abrir `http://127.0.0.1:8025` o el puerto configurado en `MAIL_PORT`. `docker compose ps mail` debe mostrar una publicación como `127.0.0.1:8025->8025/tcp`; mostrar únicamente `8025/tcp` no indica que el puerto esté publicado en el equipo. Si el contenedor conserva una configuración anterior, ejecutar `docker compose up -d --no-deps --force-recreate mail`. La recreación elimina los mensajes de la bandeja temporal.

Si la instalación del esquema quedó parcial, conservar los logs de `init`. Corregir la causa y, si se trata de una copia descartable sin trabajo a conservar, ejecutar el reinicio explícito al final de este documento. No borrar tablas individuales para intentar continuar.

## Respaldo consistente

```sh
./lab backup
```

Detiene el simulador administrado por Compose, proxy, Moodle y cron; conserva MariaDB y Mailpit. Exporta la base y archiva el volumen completo `moodledata`, sin escritores concurrentes del laboratorio. Al terminar vuelve a iniciar los servicios web y cron. No ejecutar otros contenedores manuales que escriban durante la copia. El simulador no se reinicia automáticamente.

El resultado contiene `database.sql`, `moodledata.tar.gz` y `manifest.json` con checksums, escala e imágenes observadas. El archivo `.env` debe conservarse aparte. La imagen y el código de esta revisión también son necesarios para restaurar: el backup no los incluye.

La operación no conserva el estado previo del escenario: al finalizar deja cron activo. No usar `backup` como parte del escenario de cron detenido si se pretende mantenerlo detenido.

## Restauración

La siguiente operación reemplaza la base y los archivos del proyecto local:

```sh
./lab restore backups/<identificador> --confirm
./lab smoke
```

Requiere que la base y los contenedores ya estén creados (`./lab up`) y usar la misma revisión del laboratorio y escala de `.env`. Verifica checksums y entradas del tar antes de detener servicios. Si falla después de comenzar a reemplazar datos, deja la aplicación detenida para investigar o repetir la restauración.

La verificación técnica se ejecuta al terminar. Completar una prueba de recuperación significa además entrar con docente y estudiante, abrir una guía, descargar el archivo y comprobar una entrega y una nota existentes. Registrar tiempos, resultado y responsable. Hasta realizarlo, un archivo de backup no equivale a una recuperación validada.

Mailpit guarda sus mensajes de forma efímera; los correos capturados, logs Docker e historial externo no forman parte del respaldo del campus. Exportarlos como evidencia cuando sean necesarios.

## Recuperar el estado normal

```sh
./lab scenario normal
./lab status
./lab logs cron
```

## Reinicialización completa

Solo para descartar la base y los archivos de la copia actual:

```sh
./lab reset --confirm
./lab up
./lab smoke
```

Elimina exclusivamente los volúmenes administrados por este proyecto Compose. No elimina respaldos ni evidencias del directorio local. Usa un `COMPOSE_PROJECT_NAME` diferente para mantener copias independientes; cada copia necesita puertos libres.

## Consulta SQL

`./lab query` ejecuta `sql/relevamiento.sql` como `relevador`, con SELECT sobre `moodle.*`. La contraseña fija y ficticia es `TuariLectura-2026!`; el acceso se realiza dentro de la red Docker y no hay puerto MariaDB publicado. El permiso de lectura abarca también tablas de usuarios, por lo que no representa un perfil de acceso adecuado para una base con datos personales reales.

El permiso se crea al inicializar el volumen MariaDB. `./lab verify` comprueba que una operación DELETE sin filas afectadas sea rechazada con el error de privilegios 1142.

Las fechas SQL de los informes se convierten explícitamente a UTC. Moodle muestra fechas según su zona horaria configurada. Los tamaños SQL de archivos distinguen referencias lógicas de contenido único; no equivalen al espacio total de un volumen Docker.
