

# AsyncTasQ

[![Tests](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/tests.svg)](https://github.com/adamrefaey/asynctasq/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)
[![Python Version](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/python-version.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/asynctasq)](https://pypi.org/project/asynctasq/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Una cola de tareas moderna, asincrónica por diseño y segura en tipos para Python. Construida con asyncio, cuenta con 5 backends de cola (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS), serialización automática de ORM y fiabilidad de nivel empresarial.

## Índice

- [AsyncTasQ](#asynctasq)
  - [Índice](#table-of-contents)
  - [Inicio Rápido](#quick-start)
  - [Documentación](#documentation)
  - [¿Por qué AsyncTasQ?](#why-asynctasq)
  - [Características Principales](#key-features)
  - [Comparación con Alternativas](#comparison-with-alternatives)
  - [Contribuir](#contributing)
  - [Hoja de Ruta](#roadmap)
  - [Licencia y Soporte](#license--support)

## Inicio Rápido

```bash
# Install with your preferred driver
uv add "asynctasq[redis]"

# Configure environment
asynctasq publish  # Generate .env.example template
cp .env.example .env  # Edit with your settings
```

**Definir y enviar tareas:**

```python
from asynctasq import init, run, task

init()  # Loads from .env

@task
async def send_email(to: str, subject: str):
    print(f"Sending to {to}: {subject}")
    return f"Email sent to {to}"

# Dispatch tasks
async def main():
    task_id = await send_email(to="user@example.com", subject="Welcome!").dispatch()
    print(f"Task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

**Ejecutar trabajadores:**

```bash
uv run asynctasq worker --queues default
```

Consulta la [guía completa de inicio rápido](docs/examples/function-based-tasks.md) para ver ejemplos completos con configuración de Redis, tareas basadas en clases y encadenamiento de configuraciones.

## Documentación

- **[Instalación](docs/installation.md)** – Instrucciones de instalación
- **[Configuración](docs/configuration.md)** – Guía completa de configuración
- **[Variables de Entorno](docs/environment-variables.md)** – Soporte y configuración del archivo .env
- **[Definición de Tareas](docs/task-definitions.md)** – Tareas basadas en funciones y clases
- **[Conductores de Cola](docs/queue-drivers.md)** – Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS
- **[Ejecución de Trabajadores](docs/running-workers.md)** – Trabajadores por CLI y programación
- **[Monitoreo](docs/monitoring.md)** – Transmisión de eventos y estadísticas de cola
- **[Integraciones con ORM](docs/orm-integrations.md)** – SQLAlchemy, Django, Tortoise
- **[Integraciones con Frameworks](docs/framework-integrations.md)** – Integración con FastAPI
- **[Referencia de CLI](docs/cli-reference.md)** – Referencia de comandos
- **[Mejores Prácticas](docs/best-practices.md)** – Directrices para producción

**Ejemplos:**
- [Tareas Basadas en Funciones](docs/examples/function-based-tasks.md)
- [Tareas Basadas en Clases](docs/examples/class-based-tasks.md)

## ¿Por qué AsyncTasQ?

**Arquitectura verdaderamente asincrónica** – Construida con asyncio desde cero, no adaptada sobre bases sincrónicas como Celery/RQ. Cuatro modos de ejecución (E/S asíncrona, E/S sincrónica, CPU asíncrona, CPU sincrónica) para un rendimiento óptimo.

**Serialización inteligente** – Manejo automático de modelos ORM (SQLAlchemy, Django, Tortoise) con codificación msgpack que reduce las cargas de datos en más del 90%. Pasa los modelos directamente como argumentos de la tarea.

**Fiabilidad empresarial** – Garantías ACID (PostgreSQL/MySQL), colas de mensajes muertos, recuperación tras fallos mediante timeouts de visibilidad, cierre ordenado y transmisión de eventos en tiempo real.

**Cero dependencia del proveedor** – 5 backends de producción (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS) con API idéntica. Cambia de conductor con una sola línea de configuración.

**Experiencia de desarrollo** – Segura en tipos con soporte para IDE, API elegante inspirada en Laravel, encadenamiento de métodos, salida de consola atractiva con formato Rich e integración de primer nivel con FastAPI.

## Características Principales

- ✅ **Asincrónico por diseño** con asyncio nativo en todo el stack
- ✅ **5 backends de cola**: Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS
- ✅ **Seguro en tipos** con indicadores de tipo completos y soporte para IDE
- ✅ **4 modos de ejecución**: E/S asíncrona, E/S sincrónica (hilos), vinculada a CPU (procesos)
- ✅ **Integración con ORM**: Serialización automática para SQLAlchemy, Django, Tortoise
- ✅ **Serialización msgpack**: 2-3 veces más rápida que JSON
- ✅ **Garantías ACID** (PostgreSQL/MySQL)
- ✅ **Colas de mensajes muertos** para inspeccionar tareas fallidas
- ✅ **Soporte para variables de entorno y archivos .env**
- ✅ **Integración con FastAPI** con gestión del ciclo de vida
- ✅ **Transmisión de eventos en tiempo real** mediante Redis Pub/Sub
- ✅ **Salida de consola atractiva** con formato Rich
- ✅ **Cierre ordenado** con manejadores de señales
- ✅ **Reintentos configurables** con hooks de lógica personalizada

## Comparación con Alternativas

AsyncTasQ se diferencia por su **arquitectura verdaderamente asincrónica**, **serialización automática de ORM**, **5 backends de producción** (Redis, PostgreSQL, MySQL, RabbitMQ, SQS), **garantías ACID** y **colas de mensajes muertos**.

| Característica                 | AsyncTasQ                         | Celery     | ARQ      | Dramatiq  | RQ       | Huey      |
| ------------------------------ | --------------------------------- | ---------- | -------- | --------- | -------- | --------- |
| **Asincrónico**                | ✅ Nativo                          | ❌ No       | ✅ Sí    | ⚠️ Limitado | ❌ No     | ⚠️ Limitado |
| **Seguridad de Tipos**         | ✅ Indicadores completos y soporte IDE | ⚠️ Externo | ✅ Sí    | ✅ Sí     | ✅ Sí    | ⚠️ Limitado |
| **Backends**                   | 5                                 | 3          | 1        | 2         | 1        | 4         |
| **Serialización automática ORM** | ✅ Sí                             | ❌ No       | ❌ No     | ❌ No      | ❌ No     | ❌ No      |
| **ACID**                       | ✅ Sí                             | ❌ No       | ❌ No     | ❌ No      | ❌ No     | ❌ No      |
| **DLQ**                        | ✅ Integrado                       | ⚠️ Manual   | ❌ No     | ✅ Sí     | ❌ No     | ❌ No      |
| **FastAPI**                    | ✅ Nativo                          | ⚠️ Manual   | ⚠️ Manual | ⚠️ Manual  | ⚠️ Manual | ⚠️ Manual  |

**Elija AsyncTasQ para:** Aplicaciones asincrónicas modernas (FastAPI, aiohttp), bases de código seguras en tipos, manejo automático de ORM, requisitos ACID empresariales y flexibilidad multi-backend.

**Elija alternativas para:** Ecosistemas maduros con muchos plugins (Celery), programación tipo cron (Huey, ARQ), aplicaciones sincrónicas simples (RQ) o bases de código grandes existentes.

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para la configuración y el flujo de trabajo de desarrollo:

```bash
just init        # One-line setup with deps and hooks
just docker-up   # Start Redis, PostgreSQL, MySQL, RabbitMQ, LocalStack
just test        # Run all tests (or just test-unit / just test-integration)
just ci          # Full CI suite locally
```

## Hoja de Ruta

- [ ] Controladores para SQLite y Oracle
- [ ] Encadenamiento de tareas y flujos de trabajo
- [ ] Limitación de velocidad y prioridad de tareas
- [ ] Tareas programadas/cron

## Licencia y Soporte

Licencia MIT – consulta [LICENSE](LICENSE).

**Enlaces:** [Repositorio](https://github.com/adamrefaey/asynctasq) • [Incidentes](https://github.com/adamrefaey/asynctasq/issues) • [Discusiones](https://github.com/adamrefaey/asynctasq/discussions)

Construido con ❤️ por [Adam Refaey](https://github.com/adamrefaey)
