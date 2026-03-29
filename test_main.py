import pytest
from unittest.mock import patch, mock_open
from main import calculate_discount, process_user_data, save_to_file


def test_calculate_discount_senior():
    # Prueba el descuento para mayores de 60 años
    assert calculate_discount(100, 65) == 50.0


def test_calculate_discount_adult():
    # Prueba el descuento para adultos (10%)
    assert calculate_discount(100, 30) == 10.0


def test_calculate_discount_minor():
    # Prueba que los menores de 18 no tengan descuento (0)
    assert calculate_discount(100, 15) == 0


def test_calculate_discount_negative_price():
    # Precio negativo retorna 0 tras la refactorización (cláusula de guarda)
    assert calculate_discount(-100, 25) == 0


def test_process_user_data_format():
    # Verifica que el retorno sea un string con el id incluido
    result = process_user_data("105")
    assert isinstance(result, str)
    assert "105" in result


def test_process_user_data_invalid_input():
    # Verifica que entrada no numérica lanza ValueError
    with pytest.raises(ValueError):
        process_user_data("not_a_number")


def test_save_to_file_success():
    # Verifica escritura exitosa usando mock de open
    m = mock_open()
    with patch("builtins.open", m):
        result = save_to_file("test data")
    assert result is True


def test_save_to_file_invalid_type():
    # Verifica que un tipo incorrecto lanza TypeError
    with pytest.raises(TypeError):
        save_to_file(12345)


def test_save_to_file_os_error():
    # Verifica que un error de I/O retorna False en lugar de propagar excepción
    with patch("builtins.open", side_effect=OSError("Disk full")):
        result = save_to_file("test data")
    assert result is False
