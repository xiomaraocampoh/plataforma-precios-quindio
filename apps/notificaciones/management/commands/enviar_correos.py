"""Reintenta los correos pendientes de la cola (máximo 3 intentos con espera creciente).

Uso:
    python manage.py enviar_correos              # una pasada (cron cada minuto)
    python manage.py enviar_correos --continuo   # proceso aparte, una pasada cada 30 s
"""

import argparse
import time

from django.core.management.base import BaseCommand

from apps.notificaciones import services


class Command(BaseCommand):
    help = "Envía los correos pendientes de la cola (outbox) con reintentos."

    def add_arguments(self, parser):
        parser.add_argument("--continuo", action="store_true", help="Repite cada --intervalo s.")
        parser.add_argument("--intervalo", type=int, default=30, help="Segundos entre pasadas.")
        # --pasadas solo existe para probar --continuo sin un bucle infinito
        parser.add_argument("--pasadas", type=int, default=0, help=argparse.SUPPRESS)

    def handle(self, *args, continuo, intervalo, pasadas, **options):
        hechas = 0
        while True:
            resumen = services.enviar_pendientes()
            self.stdout.write(
                f"Enviados: {resumen['enviados']} · con error: {resumen['fallidos']} · "
                f"inciertos sin reintento: {resumen['inciertos']}"
            )
            hechas += 1
            if not continuo or (pasadas and hechas >= pasadas):
                return
            time.sleep(intervalo)
