# sonarcloud-pipeline

# Windows
python -m venv uniagustiniana
.\uniagustiniana\Scripts\activate

# Linux/macOS
python3 -m venv uniagustiniana
source uniagustiniana/bin/activate

pip install --upgrade pip
pip install -r requirements.txt 

# Ejecutar pruebas unitarias
pytest

# Ejecutar pruebas con reporte de cobertura para SonarCloud
pytest --cov=. --cov-report=xmlx

# Informe Técnico — Pipeline CI/CD con Análisis de Calidad en SonarCloud

**Proyecto:** sonarcloud-pipeline | **Organización:** gutti666  
**Estudiante:** Luis Angel Gutiérrez Garzón  
**Docente:** Ing. José Danilo Sánchez Torres  
**Asignatura:** Mantenimiento de Sistemas de SW — Sesión 8  
**Fecha:** Marzo 2026

---

## 1. Diagrama de Arquitectura del Pipeline

Cuando el desarrollador hace un `git push` a la rama `main`, GitHub detecta el cambio y activa automáticamente el workflow definido en `ci-quality.yml`. A partir de ese momento, el proceso ocurre en tres etapas principales:

```
  DESARROLLADOR         GITHUB ACTIONS           SONARCLOUD
  ──────────────────────────────────────────────────────────
  git push  ──────►  Runner (ubuntu-latest)  ──►  Dashboard
  (rama main)         1. Checkout del código      Quality
                      2. Ejecuta SonarScanner      Gate
                      3. Envía resultados  ──────► (A/B/C/D/E)
                      VM se destruye al finalizar
```

El pipeline funciona de la siguiente manera: primero se crea una máquina virtual temporal (Runner), luego se descarga el código del repositorio, después el SonarScanner analiza el código y envía los resultados a SonarCloud, y finalmente la VM se elimina completamente.

| Archivo / Componente | ¿Para qué sirve? |
|---|---|
| `ci-quality.yml` | Define cuándo se activa el pipeline, en qué máquina corre y qué pasos ejecuta. |
| `sonar-project.properties` | Indica a SonarCloud el nombre del proyecto, la organización y qué archivos analizar. |
| `SONAR_TOKEN` | Clave secreta almacenada en GitHub para que el pipeline se autentique con SonarCloud. |
| Quality Gate | Conjunto de umbrales de calidad que determinan si el código es apto para producción. |

---

## 2. Marco Teórico

### 2.1 Entornos Efímeros en los Runners

Un Runner es una máquina virtual que GitHub crea exclusivamente para ejecutar un Job. Se llama "efímero" porque su vida útil es muy corta: nace cuando comienza el Job y se destruye en cuanto termina, sin importar si el resultado fue exitoso o fallido.

Esto significa que cada ejecución del pipeline empieza desde cero: sin archivos previos, sin dependencias instaladas y sin ningún rastro de ejecuciones anteriores. Por esa razón, el primer paso del workflow siempre debe ser `actions/checkout`, que descarga el código del repositorio en la VM recién creada.

En términos prácticos, si el pipeline genera un reporte (por ejemplo, `coverage.xml`) y no se guarda explícitamente, ese archivo desaparece para siempre cuando termina el Job.

### 2.2 Persistencia de Archivos con actions/upload-artifact

Dado que cada Job corre en una VM diferente que se destruye al finalizar, los archivos generados en un Job no están disponibles para el siguiente. Para solucionar esto existe `actions/upload-artifact`, que sube archivos al almacenamiento de GitHub antes de que la VM se destruya.

Esos archivos quedan disponibles para otros Jobs (usando `actions/download-artifact`), para el usuario como descarga manual desde la pestaña Actions, y por un período de hasta 90 días por defecto.

Ejemplo de uso en este proyecto:

```yaml
- name: Subir reporte de cobertura
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
    retention-days: 7
```

### 2.3 Protección del SONAR_TOKEN

El `SONAR_TOKEN` es una clave que permite al pipeline autenticarse con SonarCloud. Se guarda en GitHub como "secreto" cifrado y nunca aparece en texto claro en el código ni en los logs.

Cuando el pipeline se ejecuta, GitHub inyecta el valor del secreto directamente en la memoria del Runner como variable de entorno. Si por alguna razón ese valor apareciera en los logs, GitHub lo reemplaza automáticamente con `***`.

Imprimir un secreto en la consola (por ejemplo con `echo $SONAR_TOKEN`) es una vulnerabilidad porque: en repositorios públicos los logs son visibles para cualquier persona, el historial de logs se conserva hasta 400 días, y el sistema de enmascaramiento puede ser evadido mediante codificación en Base64.

### 2.4 Optimización con Caché (actions/cache)

Como cada VM empieza desde cero, sin caché el pipeline descarga e instala todas las dependencias desde internet en cada ejecución, lo que puede tomar entre 60 y 120 segundos solo en esa etapa.

`actions/cache` guarda el directorio de dependencias entre ejecuciones. Si el archivo `requirements.txt` no cambió desde la última vez, el pipeline reutiliza el caché en lugar de descargar todo de nuevo, reduciendo ese tiempo a unos 15 segundos.

| Etapa | Sin caché | Con caché |
|---|---|---|
| Instalación de dependencias | ~90 segundos | ~15 segundos |
| Tiempo total del pipeline | ~150 segundos | ~75 segundos |

### 2.5 Quality Gates: Calidad vs. Ejecución Técnica

Que un pipeline termine en verde no significa que el código sea bueno. Existen dos situaciones distintas:

El pipeline tiene **éxito técnico** cuando todos los pasos se ejecutaron sin errores de sistema (descarga de código, instalación de dependencias, ejecución del análisis). El pipeline **falla por políticas de calidad** cuando el análisis se completó correctamente, pero el código no cumple los umbrales definidos en SonarCloud (por ejemplo, cobertura menor al 80% o bugs nuevos).

Un Quality Gate funciona como una compuerta AND: el código solo pasa si cumple todas las condiciones al mismo tiempo. Esto aplica el principio "Fail Fast" de DevOps: detectar problemas cuanto antes, cuando son más baratos de corregir.

| Tipo de resultado | Causa | Ícono en GitHub |
|---|---|---|
| Éxito técnico | Todos los pasos del pipeline corrieron sin errores | ✅ verde |
| Fallo por calidad | El código no cumple los umbrales de SonarCloud | ❌ rojo |
| Fallo técnico | Error de sistema: token inválido, error de red, sintaxis YAML | ❌ rojo |

---

## 3. Evidencia de Ejecución

### 3.1 GitHub Actions — Pipeline ejecutado exitosamente

La siguiente imagen muestra el workflow Build ejecutado con éxito (Build #3, commit `90d3013`, rama `main`). El pipeline tardó 40 segundos y fue activado por el usuario `gutti666`.

> 📸 *Figura 1. Pestaña Actions de GitHub — workflow completado en verde (✅)*

### 3.2 SonarCloud — Dashboard de métricas

La siguiente imagen muestra el dashboard del proyecto `sonarcloud-pipeline` en SonarCloud con los resultados del análisis de código.

> 📸 *Figura 2. Dashboard de SonarCloud — resultado del análisis estático*

---

## 4. Mapeo de Calidad — ISO/IEC 25010

La norma ISO/IEC 25010 define un modelo de calidad para productos de software. A continuación se relacionan los resultados obtenidos en SonarCloud con las características de esa norma.

### 4.1 Mantenibilidad

SonarCloud otorgó **Rating A** en Mantenibilidad con 1 issue abierto. Esto significa que el código es fácil de modificar y tiene una deuda técnica baja. Los code smells encontrados suman aproximadamente 32 minutos de trabajo para corregirlos.

| # | Archivo | Problema detectado | Tiempo estimado |
|---|---|---|---|
| 1 | `main.py`, línea 4 | Nombre de variable poco descriptivo (`db`) | 5 min |
| 2 | `main.py`, línea 16 | Variable declarada pero nunca usada (código muerto) | 2 min |
| 3 | `main.py`, línea 21 | Función con demasiados niveles de anidamiento (4 niveles) | 15 min |
| 4 | `main.py`, línea 35 | Bloque `except` que ignora errores completamente (`pass`) | 10 min |

### 4.2 Fiabilidad

SonarCloud otorgó **Rating C** en Fiabilidad con 2 issues abiertos. Este rating indica la presencia de al menos un bug de tipo Major, lo que puede causar comportamientos inesperados en producción.

El bug principal está en la función `save_to_file()`: el bloque `except Exception: pass` captura todos los errores posibles y los ignora sin registrarlos. Si el archivo `log.txt` no se puede escribir por falta de permisos o disco lleno, el sistema fallará en silencio.

### 4.3 Seguridad

SonarCloud otorgó **Rating A** en Seguridad con 0 issues abiertos. Aunque el rating es bueno, se identificaron Security Hotspots que requieren revisión manual.

| Riesgo (OWASP) | Archivo | Descripción |
|---|---|---|
| A03 - Injection | `main.py`, línea 11 | Consulta SQL construida con concatenación directa. Puede ser explotada con SQL Injection. |
| A06 - Componentes vulnerables | `requirements.txt` | `django==1.11.29` tiene fin de vida útil y múltiples CVEs conocidas. |
| A09 - Logging | `main.py`, línea 13 | Se imprime la consulta SQL completa con `print()`, lo que puede exponer datos sensibles. |

---

## 5. Plan de Refactorización

A continuación se presentan dos code smells detectados por SonarCloud con su código original y la corrección propuesta.

### Code Smell #1 — Función con demasiados niveles de anidamiento

**Regla SonarCloud:** `python:S3776` — La complejidad cognitiva no debe ser demasiado alta.

El problema es que la función `calculate_discount` tiene tres `if` anidados uno dentro del otro, lo que la hace difícil de leer y probar. Además usa números directamente en el código (`0.5`, `0.1`) sin explicar qué significan.

**Código original (con el problema):**

```python
def calculate_discount(price, age):
    if price > 0:
        if age > 18:
            if age > 60:
                return price * 0.5   # magic number
            else:
                return price * 0.1   # magic number
        else:
            return 0
    else:
        return 0
```

**Código corregido:**

```python
DESCUENTO_MAYOR  = 0.50   # Constantes con nombre claro
DESCUENTO_ADULTO = 0.10
EDAD_ADULTO = 18
EDAD_MAYOR  = 60

def calculate_discount(price: float, age: int) -> float:
    if price <= 0:            # Validación al inicio (cláusula de guarda)
        return 0
    if age <= EDAD_ADULTO:    # Sin descuento para menores
        return 0
    if age > EDAD_MAYOR:      # Descuento adulto mayor
        return price * DESCUENTO_MAYOR
    return price * DESCUENTO_ADULTO
```

La corrección usa cláusulas de guarda al inicio de la función para manejar los casos especiales primero y salir rápido, eliminando los niveles de anidamiento. Los números mágicos se reemplazaron por constantes con nombres descriptivos.

---

### Code Smell #2 — Bloque except que silencia errores

**Regla SonarCloud:** `python:S1166` — Los manejadores de excepciones deben preservar el error original.

El problema es que el bloque `except Exception: pass` captura cualquier tipo de error y simplemente lo ignora. Si el archivo no se puede abrir o escribir, el programa continúa como si nada hubiera pasado, haciendo imposible detectar fallos en producción.

**Código original (con el problema):**

```python
def save_to_file(data):
    try:
        with open('log.txt', 'a') as f:
            f.write(data)
    except Exception:   # Captura todo
        pass            # Y no hace nada
```

**Código corregido:**

```python
import logging
logger = logging.getLogger(__name__)

def save_to_file(data: str) -> bool:
    try:
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(data)
        return True
    except OSError as e:           # Solo errores de escritura
        logger.error('Error al escribir log.txt: %s', e)
        return False               # Informa al llamador que falló
```

La corrección captura únicamente `OSError` (el tipo específico de error de escritura en disco), registra el problema con el módulo `logging` estándar de Python, y retorna un booleano para que el código que llama a la función sepa si la operación fue exitosa o no.

---

## 6. Bibliografía

1. Eniun. (s.f.). Resumen de comandos Git y GitHub. https://www.eniun.com/resumen-comandos-git-github/
2. En Mi Local Funciona. Cómo montar un SonarQube en Cloud – Parte 1. https://www.enmilocalfunciona.io/
3. FreeCodeCamp. (s.f.). 10 comandos de Git que todo desarrollador debería saber. https://www.freecodecamp.org/espanol/
4. GeeksforGeeks. (s.f.). Naming Conventions for Git Branches. https://www.geeksforgeeks.org/
5. Okken, B. (2022). *Python testing with pytest*. Pragmatic Programmers, LLC.
6. Peres, H. (2018). *Automating software tests using selenium*. Scribl.
7. Pixolo, A. (s.f.). Naming Conventions for Git Branches: A Cheatsheet. Medium.
8. Verona, J. (2018). *Practical DevOps, second edition*. Packt Publishing, Limited.