import csv
import os
from django.core.management.base import BaseCommand
from importservice.models import RepresentacaoGrafica

class Command(BaseCommand):
    help = "Importa os dados do representacao_grafica.csv para a tabela RepresentacaoGrafica"

    def handle(self, *args, **kwargs):
        # Caminho para o CSV
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        csv_path = os.path.join(base_dir, "data", "representacao_grafica.csv")

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"Arquivo CSV não encontrado em {csv_path}"))
            return

        with open(csv_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")  # agora usa vírgula
            count = 0
            for row in reader:
                esquema = row.get("esquema")
                classe = row.get("classe")
                grupo_representacao = row.get("grupo_representacao")

                if not (esquema and classe and grupo_representacao):
                    self.stdout.write(self.style.WARNING(f"Linha inválida ignorada: {row}"))
                    continue

                RepresentacaoGrafica.objects.update_or_create(
                    classe=classe,
                    defaults={
                        "esquema": esquema,
                        "grupo_representacao": grupo_representacao
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Importação concluída! {count} registros adicionados/atualizados."))
