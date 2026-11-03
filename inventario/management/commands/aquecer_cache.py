"""Prepara análises comuns antes dos acessos; não consulta fontes externas."""
from django.core.management.base import BaseCommand
from inventario.aplicacao.painel import contexto_painel
from inventario.aplicacao.risco import calcular_risco_banco
from inventario.models import Ativo


class Command(BaseCommand):
    help = 'Pré-carrega risco e resumos do painel; opcionalmente o cenário financeiro padrão.'

    def add_arguments(self, parser):
        parser.add_argument('--incluir-financeiro', action='store_true')

    def handle(self, *args, **options):
        for perfil in ('puro', 'operacional'):
            if Ativo.objects.exists():
                try:
                    calcular_risco_banco(perfil=perfil)
                except ValueError as erro:
                    self.stderr.write(f'Risco {perfil} indisponível: {erro}')
            for alertas, certificados in ((False, False), (False, True), (True, False), (True, True)):
                contexto_painel(perfil, alertas, certificados)
        self.stdout.write('Cache aquecido: resumos por permissão (15s); risco quando o inventário permite cálculo. Confira os avisos.')
        if options['incluir_financeiro']:
            from inventario.aplicacao.montecarlo import calcular_montecarlo
            try:
                resultado = calcular_montecarlo()
                self.stdout.write('Financeiro: '+('pronto para 30 dias.' if resultado['disponivel'] else 'dados insuficientes; confira o EPSS.'))
            except ValueError as erro:
                self.stderr.write(f'Financeiro não pré-carregado: {erro}')
