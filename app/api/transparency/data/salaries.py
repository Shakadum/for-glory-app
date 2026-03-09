"""Salários e benefícios de parlamentares brasileiros."""

SALARY_BR = {
    "camara": {
        "cargo": "Deputado Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal bruto (teto constitucional)",
        "beneficios": [
            {"nome": "Cota Parlamentar (CEAP)", "valor": "até R$ 50.112/mês", "descricao": "Verba para custeio de atividades parlamentares: combustível, passagens, alimentação, hospedagem, telefone etc."},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para deputados que não utilizam imóvel funcional em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Até 84 bilhetes/mês", "descricao": "Viagens entre o domicílio eleitoral e Brasília, e em atividades parlamentares"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado integralmente pela Câmara", "descricao": "Para o parlamentar e dependentes legais"},
            {"nome": "Seguro de Vida", "valor": "Custeado pela Câmara", "descricao": "Apólice individual"},
            {"nome": "Aposentadoria parlamentar", "valor": "Proporcional ao mandato", "descricao": "Após 8 anos de mandato com 60 anos de idade"},
        ],
        "beneficios_abdicados_info": "Parlamentares podem renunciar ao auxílio-moradia declarando imóvel próprio em Brasília ou utilizando imóvel funcional da Câmara. A Cota Parlamentar pode ser reduzida voluntariamente. Todos os gastos são publicados no Portal da Transparência.",
        "fonte": "https://www2.camara.leg.br/transparencia",
    },
    "senado": {
        "cargo": "Senador Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal bruto — idêntico ao dos Deputados Federais por determinação constitucional",
        "beneficios": [
            {"nome": "Verba de Gabinete", "valor": "até R$ 155.520/mês", "descricao": "Para custeio de pessoal (até 8 assessores) e atividades do gabinete"},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para senadores sem imóvel em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Ilimitadas em missões oficiais", "descricao": "Viagens a serviço do mandato"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado pelo Senado", "descricao": "Para o parlamentar e dependentes"},
            {"nome": "Verba de Representação", "valor": "R$ 9.273,24/mês", "descricao": "Exclusivo para membros da Mesa Diretora e líderes de bancada"},
        ],
        "beneficios_abdicados_info": "Senadores podem abrir mão do auxílio-moradia e da verba de representação (quando aplicável). Todos os gastos são publicados no Portal da Transparência do Senado.",
        "fonte": "https://www12.senado.leg.br/transparencia",
    },
}
