"""Extensão sintética do cenário pequeno; nunca importa inteligência externa."""
from inventario.models import Ativo, Dependencia, Incidencia, Sala, Vulnerabilidade

FONTE = 'Empresa Aurora fictícia'


def ampliar_empresa():
    sala = Sala.objects.create(id='SALA-DEMO', nome='Aurora — ambiente fictício', tipos_permitidos=list('123456789'))
    extras = [
        ('INJ', 'Injeção em aplicação', 8.1), ('INFO', 'Exposição de informação', 6.5),
        ('CFG', 'Configuração de rede inadequada', 7.0), ('AUTH', 'Controle de acesso insuficiente', 8.0),
    ]
    vulnerabilidades = list(Vulnerabilidade.objects.order_by('id'))
    for numero, (categoria, descricao, nota) in enumerate(extras, 1):
        vulnerabilidades.append(Vulnerabilidade.objects.create(
            id=f'VUL-DEMO-{numero:04}', descricao=f'FICTÍCIO: {descricao}', categoria=categoria,
            cvss=nota, fonte=FONTE))
    tipos = [('1', 'Servidor'), ('2', 'Notebook'), ('3', 'Estação'), ('4', 'Switch'),
             ('5', 'Roteador'), ('6', 'Impressora'), ('7', 'Aplicação web'),
             ('8', 'Banco de dados'), ('9', 'Software')]
    ativos = []
    for i in range(27):
        tipo, nome = tipos[i % len(tipos)]
        ativo = Ativo.objects.create(tipo=tipo, nome=f'DEMO Aurora · {nome} {i + 1:02}',
            fabricante='Aurora', modelo='Fictício', sala=sala, responsavel='Equipe fictícia',
            criticidade=1 + i % 4, atributos={'origem': 'demonstração fictícia'})
        ativos.append(ativo)
        for j in range(1 + (i % 3 == 0)):
            Incidencia.objects.create(id=f'INC-DEMO-{i:03}-{j}', ativo=ativo,
                vulnerabilidade=vulnerabilidades[(i + j) % len(vulnerabilidades)],
                observacoes='Dado fictício para apresentação; não é achado real.')
    # Dependências dirigidas com soma máxima de pesos < 1 por dependente.
    fornecedores = list(Ativo.objects.filter(pk__in=['7N00001', '1D00001', '8P00001', '4H00001']).order_by('pk'))
    for i, ativo in enumerate(ativos):
        for fornecedor, peso in ((fornecedores[i % len(fornecedores)], .18),
                                 (fornecedores[(i + 1) % len(fornecedores)], .12)):
            Dependencia.objects.create(dependente=ativo, fornecedor=fornecedor, peso=peso,
                                       descricao='Demonstração fictícia; peso hipotético')
        if i >= 3:
            Dependencia.objects.create(dependente=ativo, fornecedor=ativos[i - 3], peso=.12,
                                       descricao='Demonstração fictícia; peso hipotético')
