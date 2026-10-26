# Laboratorio TUARI

Entorno Moodle de una organización ficticia de capacitación a distancia para trabajar en Relevamiento, Evaluación e Implementación de Proyectos de la Tecnicatura Universitaria en Administración de Redes Informáticas.

El objetivo es explorar los servicios, reunir evidencias y fundamentar un diagnóstico. La [guía de relevamiento](docs/estudiante.md) propone preguntas y entregables para el trabajo.

## Requisitos

- Docker Engine con Compose v2 o superior, o Docker Desktop con contenedores Linux.
- Python 3.10 o superior.
- Conexión a Internet para descargar las imágenes y construir el entorno por primera vez.

Como referencia inicial, disponer de cuatro CPU, 6 GiB de RAM para Docker y 10 GiB de disco libre. El consumo dependerá de la escala configurada y de la actividad generada. No se necesita PHP instalado en el equipo para ejecutar el laboratorio.

## Puesta en marcha

Descargar el repositorio, abrir una terminal en su carpeta y ejecutar:

```sh
./lab setup
./lab up
./lab smoke
```

`setup` crea `.env` y genera el historial sintético. Revisar `.env` antes de ejecutar `up`, que construye la imagen e instala Moodle y sus datos iniciales. La primera ejecución puede tardar varios minutos. `smoke` comprueba los datos, permisos y sesiones de estudiantes.

En Windows, ejecutar los comandos desde una terminal WSL con Python y la integración de Docker Desktop habilitada.

## Accesos

- Campus: http://localhost:8080
- Correo capturado: http://localhost:8025

| Usuario | Contraseña inicial | Perfil |
| --- | --- | --- |
| `admin` | `TuariAdmin-2026!` | Administración del campus |
| `relevador` | `TuariClase-2026!` | Consulta de cursos e informes |
| `docente01` a `docente06` | `TuariClase-2026!` | Docencia en cursos asignados |
| `estudiante001` a `estudiante120` | `TuariClase-2026!` | Cursada y entregas |

Los valores efectivos se definen en `.env`. Las cuentas y contraseñas son ficticias y exclusivas del laboratorio local. Los servicios publicados solo aceptan conexiones desde el equipo que ejecuta Docker. Cada grupo puede levantar su propia copia.

## Datos del laboratorio

La configuración predeterminada crea tres instituciones, 120 estudiantes, seis docentes y 12 cursos, con guías descargables, foros, tareas, entregas y calificaciones. La interfaz de Moodle usa inglés y los contenidos de práctica están en español.

El historial externo se encuentra en `evidence/history/` y puede analizarse sin iniciar Docker. Incluye peticiones HTTP, métricas y tickets ficticios. El manifiesto registra semilla, período y checksums. Cada registro indica su origen sintético.

El período predeterminado termina el 20 de octubre de 2026 a las 00:00 UTC, límite exclusivo. Los registros históricos externos y los eventos actuales de Moodle son fuentes distintas: indicar su procedencia al utilizarlos como evidencia.

## Comandos de trabajo

| Comando | Acción |
| --- | --- |
| `./lab status` | Consultar el estado de los servicios |
| `./lab logs proxy` | Observar peticiones web |
| `./lab logs cron` | Observar tareas programadas |
| `./lab query` | Consultar la base con una identidad de lectura |
| `./lab simulate --users 4 --rounds 20 --delay 1` | Generar actividad HTTP con estudiantes |
| `./lab evidence` | Exportar evidencias del entorno actual |
| `./lab history` | Regenerar el historial sintético |
| `./lab verify` | Comprobar datos y permisos |
| `./lab down` | Detener el entorno conservando sus datos |

El simulador inicia sesiones y visita cursos y actividades. No reproduce todas las acciones de un navegador ni resuelve cuestionarios o genera entregas automáticamente. Sus tiempos no equivalen al tiempo de renderizado de una página.

Para experimentar con las tareas programadas, registrar primero el estado del servicio y ejecutar:

```sh
./lab scenario cron-stopped
```

Observar los efectos sobre las actividades elegidas y restaurar el procesamiento con:

```sh
./lab scenario normal
```

## Configuración y persistencia

Editar `.env` antes de la primera carga para ajustar la escala: entre 6 y 2000 estudiantes, entre 3 y 100 docentes y entre 3 y 100 cursos. Los límites admitidos no representan capacidad de rendimiento comprobada. El simulador admite hasta 50 usuarios HTTP y 1000 rondas.

Los datos se conservan en volúmenes Docker. La inicialización no vuelve a cargar un conjunto de datos completado. Cambiar la escala requiere una reinicialización explícita. Cambiar contraseñas en `.env` no actualiza las cuentas ya creadas en Moodle o MariaDB.

Consultar la [guía de operación](docs/operacion.md) para respaldos, restauración, cambios de puertos y resolución de problemas.

`.env`, respaldos, evidencias y archivos generados quedan excluidos de Git. Para ejecutar los chequeos locales de scripts y configuración se requiere además PHP CLI:

```sh
./lab check
```

Moodle se obtiene de su repositorio oficial durante la construcción y conserva su licencia GPL.
