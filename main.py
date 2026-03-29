import logging

# Logger del módulo (reemplaza print directo)
logger = logging.getLogger(__name__)

# Lista de sesiones activas (nombre descriptivo)
active_sessions = []

# Constantes de descuento (elimina magic numbers)
DISCOUNT_SENIOR = 0.50
DISCOUNT_ADULT = 0.10
AGE_ADULT = 18
AGE_SENIOR = 60


def process_user_data(user_input_id):
    """
    Simula la obtención de un usuario con consulta parametrizada.
    """
    # Validación en la frontera del sistema
    if not isinstance(user_input_id, str) or not user_input_id.isdigit():
        raise ValueError("user_input_id debe ser un string numérico")

    # Parámetro posicional en lugar de concatenación directa (evita SQL Injection)
    query = "SELECT * FROM users WHERE id = %s"
    logger.info("Consultando usuario con id: %s", user_input_id)
    return query % user_input_id


def calculate_discount(price: float, age: int) -> float:
    """
    Calcula el descuento aplicable según precio y edad del usuario.

    Args:
        price: Precio base del producto. Debe ser positivo.
        age: Edad del usuario en años.

    Returns:
        Precio con descuento aplicado. Retorna 0 si el precio no es
        positivo o si el usuario es menor de edad.
    """
    # Cláusula de guarda: precio inválido
    if price <= 0:
        return 0

    # Cláusula de guarda: usuario menor de edad
    if age <= AGE_ADULT:
        return 0

    # Descuento para adultos mayores
    if age > AGE_SENIOR:
        return price * DISCOUNT_SENIOR

    # Descuento estándar para adultos
    return price * DISCOUNT_ADULT


def save_to_file(data: str) -> bool:
    """
    Persiste datos en el archivo de log 'log.txt'.

    Args:
        data: Cadena de texto a escribir en el archivo.

    Returns:
        True si la escritura fue exitosa, False en caso de error de I/O.

    Raises:
        TypeError: Si data no es una cadena de texto.
    """
    if not isinstance(data, str):
        raise TypeError(f"Se esperaba str, se recibió {type(data).__name__}")

    try:
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(data)
        return True
    except OSError as e:
        logger.error("No se pudo escribir en log.txt: %s", e)
        return False


if __name__ == "__main__":
    process_user_data("101")
