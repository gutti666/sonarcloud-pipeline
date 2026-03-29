import pytest
from main import calculate_discount, process_user_data

def test_calculate_discount_senior():
    # Prueba el descuento para mayores de 60 años
    assert calculate_discount(100, 65) == 50.0

def test_calculate_discount_adult():
    # Prueba el descuento para adultos (10%)
    assert calculate_discount(100, 30) == 10.0

def test_calculate_discount_minor():
    # Prueba que los menores de 18 no tengan descuento (0)
    assert calculate_discount(100, 15) == 0

def test_process_user_data_format():
    # Verifica que el retorno sea un string (aunque el SQL esté mal construido)
    result = process_user_data("105")
    assert isinstance(result, str)
    assert "105" in result

#  TEST FALLIDO (Reto para el alumno):
# Si el alumno refactoriza calculate_discount para manejar precios negativos,
# este test debería pasar. Actualmente, si el código original no lo maneja, 
# el estudiante debe decidir qué debe retornar.
def test_calculate_discount_negative_price():
    assert calculate_discount(-100, 25) == 1