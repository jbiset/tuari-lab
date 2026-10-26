# Guía de relevamiento

Una organización que ofrece capacitación a varias instituciones reporta lentitud en fechas de entrega, crecimiento de información y dificultades para administrar su infraestructura. La propuesta original es la fuente de necesidades; el laboratorio aporta un caso ficticio para investigarlas.

## Acceso y fuentes

El docente entrega las credenciales y el alcance de acceso. Empezar con un estudiante, un docente y la cuenta `relevador`. La administración global queda disponible para inspecciones acompañadas cuando haga falta.

Fuentes disponibles:

- Campus operativo: cursos, matrículas, actividades, archivos y registros Moodle.
- `./lab query`: consultas de lectura sobre el estado actual.
- `./lab evidence`: evidencia del despliegue y actividad reciente.
- `evidence/history/`: historial sintético con su manifiesto de procedencia.
- Entrevistas con integrantes de la organización representados por el docente.

Los eventos de Moodle incluyen la inicialización del laboratorio. Los datos históricos externos no se presentan como registros recuperados del campus real. Identificar siempre fuente, período, zona horaria y limitaciones de cada evidencia.

## Preguntas iniciales

1. ¿Qué servicios existen, de qué dependen y quiénes los usan?
2. ¿Cuántos usuarios están registrados, cuántos participan y qué podemos afirmar sobre concurrencia?
3. ¿Qué ocurre alrededor de los reclamos? ¿Los registros sostienen lo declarado?
4. ¿Qué información crece y cómo se conserva? ¿Qué diferencia hay entre tamaño lógico y almacenamiento utilizado?
5. ¿Cómo se detectan incidentes y cuánto tiempo pasa hasta el primer reporte?
6. ¿Qué tareas se ejecutan sin intervención humana? ¿Cómo se comprueba su funcionamiento?
7. ¿Qué se respalda y qué evidencia demuestra que puede recuperarse?
8. ¿Qué información necesitamos solicitar para estimar capacidad y continuidad?
9. ¿Quién tiene permisos para administrar y cómo se realizan los cambios?
10. ¿Qué no puede medirse con esta copia local?

## Prueba breve

Registrar el estado inicial y una hipótesis. Con autorización del docente, generar actividad controlada:

```sh
./lab simulate --users 4 --rounds 20 --delay 1
./lab evidence
```

Comparar eventos del campus y peticiones del proxy. El tiempo informado por el simulador incluye redirecciones y descarga del HTML. No equivale al tiempo de renderizado de un navegador ni a la latencia aislada de la red. Un usuario HTTP no reproduce todos los recursos y acciones de una persona en un navegador.

## Entrega sugerida

- Inventario y mapa de dependencias de la situación observada.
- Registro de entrevistas y preguntas pendientes.
- Evidencias con fecha, fuente y condiciones de obtención.
- Hallazgos que separen hechos, declaraciones, hipótesis y limitaciones.
- Necesidades y problemas priorizados por impacto, con fundamento.
- Restricciones conocidas y supuestos que requieren validación.
- Pruebas acotadas y criterios que permitirían evaluar una mejora posteriormente.

No se evalúa la cantidad de herramientas propuestas. Se evalúa si cada recomendación se vincula con una necesidad comprobada. Una correlación entre CPU y lentitud no demuestra por sí sola la causa de un incidente.
