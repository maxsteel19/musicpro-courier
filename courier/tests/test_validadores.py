from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from courier.validators import calcular_digito_verificador, normalizar_patente, normalizar_rut


class ValidadoresTests(SimpleTestCase):
    def test_digito_verificador(self):
        self.assertEqual(calcular_digito_verificador('12345678'), '5')
        self.assertEqual(calcular_digito_verificador('11111111'), '1')
        self.assertEqual(calcular_digito_verificador('10000013'), 'K')

    def test_normalizar_rut(self):
        self.assertEqual(normalizar_rut('123456785'), '12.345.678-5')
        self.assertEqual(normalizar_rut('10.000.013-k'), '10.000.013-K')
        with self.assertRaises(ValidationError):
            normalizar_rut('12.345.678-9')
        with self.assertRaises(ValidationError):
            normalizar_rut('abc')

    def test_normalizar_patente(self):
        self.assertEqual(normalizar_patente('bcdf12'), 'BCDF-12')
        self.assertEqual(normalizar_patente('AB 1234'), 'AB-1234')
        with self.assertRaises(ValidationError):
            normalizar_patente('123')
