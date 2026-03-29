import os

#  SMELL: Variable con nombre no descriptivo y global
db = []

def process_user_data(user_input_id):
    """
    Simula la obtención de un usuario.
    """
    #  VULNERABILIDAD: Concatenación directa de SQL (SQL Injection)
    # SonarCloud lo detectará como un "Security Hotspot" crítico.
    query = "SELECT * FROM users WHERE id = " + user_input_id
    print(f"Ejecutando: {query}") 
    
    #  SMELL: Código muerto (Variable declarada y no usada)
    temp_session_token = "ABC123XYZ" 

    return query

def calculate_discount(price, age):
    #  SMELL: Complejidad Ciclomática alta (Demasiados IFs anidados)
    # Esto baja la métrica de "Maintainability"
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

#  BUG: Bloque try-except demasiado genérico que silencia errores
def save_to_file(data):
    try:
        with open("log.txt", "a") as f:
            f.write(data)
    except Exception:
        pass #  Esto es una mala práctica grave

if __name__ == "__main__":
    process_user_data("101")