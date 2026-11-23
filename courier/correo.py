"""Backend de correo para desarrollo.

El backend de consola de Django imprime el mensaje codificado (quoted-printable):
las tildes salen como =C3=B3 y los enlaces largos quedan cortados con "=".
Este backend imprime el texto tal cual, para poder copiar el enlace de
recuperación de contraseña durante una demostración.
"""
from django.core.mail.backends.console import EmailBackend


class ConsolaLegibleEmailBackend(EmailBackend):
    def write_message(self, message):
        self.stream.write(
            f'De: {message.from_email}\n'
            f'Para: {", ".join(message.to)}\n'
            f'Asunto: {message.subject}\n\n'
            f'{message.body}\n'
        )
        self.stream.write('-' * 79 + '\n')
