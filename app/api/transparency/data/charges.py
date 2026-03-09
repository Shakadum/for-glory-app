"""
For Glory — Portal da Transparência
Módulo: Banco de Acusações
"""
_CHARGES_DB: dict[str, list[str]] = {

    # ── BOLSONARO, JAIR ────────────────────────────────────────────────────────
    "Jair Bolsonaro": [
        "Investigado pela PGR por tentativa de golpe de Estado — incluindo suposto plano de assassinato de Lula, Alckmin e Barroso (STF, Inq. 4.874, 2024) — indiciado pela PF em nov/2024; aguarda decisão do PGR sobre denúncia",
        "Condenado pelo TSE por abuso de poder político ao usar reunião com embaixadores para atacar o sistema eleitoral (TSE, 2023) — inelegível até 2030",
        "Condenado pelo TSE por abuso de poder nas redes sociais durante as eleições de 2022 (TSE, 2023) — inelegível até 2030",
        "Investigado no STF por tentativa de fraude nos cartões de vacina da COVID-19 (STF, Inq. 4.831, 2023) — em apuração",
        "Investigado no STF por suposta omissão diante de atos de terrorismo do 8 de Janeiro (STF, AP 1.298, 2023) — em apuração",
        "Investigado pela CPI da Covid-19 por crimes contra a saúde pública durante a pandemia (Senado Federal, 2021) — relatório aprovado; PGR arquivou pedido de denúncia",
        "Condenado em 1ª instância na Justiça do Trabalho por danos morais coletivos ao fazer declarações machistas contra jornalista (TRT-10, 2016)",
    ],

    # ── BOLSONARO, FLÁVIO ──────────────────────────────────────────────────────
    "Flávio Bolsonaro": [
        "Investigado pelo GAECO/MP-RJ pelo esquema das 'rachadinhas' — desvio de salários de funcionários fantasmas do gabinete na ALERJ (2007–2018) — STJ determinou reabertura do inquérito em 2020; MP-RJ apresentou denúncia em 2021; ação penal em curso no RJ",
        "Investigado pelo COAF/MP-RJ por movimentações financeiras atípicas de R$ 1,2 milhão sem justificativa (2018–2019) — parte das investigações das rachadinhas",
        "STF rejeitou transferir o processo para a Corte em 2021 (não há prerrogativa de foro como senador para fatos anteriores ao mandato) — processo permanece na 1ª instância do RJ",
    ],

    # ── BOLSONARO, CARLOS ──────────────────────────────────────────────────────
    "Carlos Bolsonaro": [
        "Investigado pelo GAECO/MP-RJ por suspeita de participação no esquema das rachadinhas no gabinete de Flávio Bolsonaro na ALERJ — uso de funcionários do gabinete para atividades particulares (2007–2018) — inquérito em andamento",
        "Investigado pelo TCE-RJ por gastos irregulares de verba indenizatória na Câmara dos Vereadores do Rio de Janeiro (2022)",
    ],

    # ── BOLSONARO, EDUARDO ─────────────────────────────────────────────────────
    "Eduardo Bolsonaro": [
        "Investigado no STF pelo inquérito das fake news (Inq. 4.781) por suposta divulgação de informações falsas e ataques ao STF (2020–2022) — inquérito encerrado sem denúncia em 2023",
        "Alvo de representação no Conselho de Ética da Câmara por declarações sobre fechamento do STF (2020) — arquivado",
    ],

    # ── LULA ──────────────────────────────────────────────────────────────────
    "Luiz Inácio Lula da Silva": [
        "Condenado em 3 instâncias (TRF-4, STJ) no caso do triplex do Guarujá por corrupção passiva e lavagem de dinheiro (Operação Lava Jato, 2017–2019) — STF anulou as condenações em 2021 por suspeição do ex-juiz Sergio Moro; STF reconheceu nulidade do processo por violação ao juiz natural (2023)",
        "Condenado em 2 instâncias no caso do sítio de Atibaia por corrupção passiva e lavagem de dinheiro (Operação Lava Jato, 2019–2020) — STF anulou a condenação em 2023 pela mesma razão de suspeição de Moro",
        "Ficha limpa: após anulações pelo STF, registros de condenações foram extintos; Lula voltou à elegibilidade em 2021",
    ],

    # ── TEMER ─────────────────────────────────────────────────────────────────
    "Michel Temer": [
        "Indiciado pela PF e denunciado pela PGR por corrupção passiva, obstrução de Justiça e organização criminosa — caso JBS/frigoríficos (2017) — Câmara dos Deputados derrubou duas denúncias pelo voto da maioria (2017)",
        "Preso preventivamente em março de 2019 por suspeita de receber propina de empresas de infraestrutura portuária — solto dias depois por habeas corpus do STJ",
        "Denunciado pela PGR por corrupção passiva no caso do Decreto dos Portos (2019) — ação penal em curso no STJ",
        "Condenado pelo TRF-2 em 2023 por corrupção e lavagem de dinheiro no caso das usinas nucleares Angra 3 — recurso pendente no STJ",
    ],

    # ── DILMA ─────────────────────────────────────────────────────────────────
    "Dilma Rousseff": [
        "Sofreu processo de impeachment no Congresso Nacional por crime de responsabilidade fiscal — pedaladas fiscais (2016) — Senado votou pelo afastamento (61×20) mas permitiu que ela mantivesse os direitos políticos",
        "Investigada na Operação Lava Jato como presidente da Petrobras durante o período dos contratos fraudulentos (2014–2016) — PGR não apresentou denúncia por falta de provas diretas",
    ],

    # ── MORAES ────────────────────────────────────────────────────────────────
    "Alexandre de Moraes": [
        "Alvo de representação na OAB por supostos excessos nas decisões monocráticas no STF — suspensão de redes sociais e bloqueio de contas sem decisão colegiada (2023–2024) — sem punição efetiva",
        "Acusado formalmente pelo empresário Elon Musk (Twitter/X) de censura inconstitucional ao bloquear perfis no Brasil (2024) — STF manteve as decisões; Moraes abriu inquérito contra Musk",
        "Acusado pelo partido Novo de parcialidade no julgamento do 8 de Janeiro por ter sido vítima dos atos — pedido de suspeição rejeitado pelo Plenário do STF (2023)",
    ],

    # ── BARROSO ───────────────────────────────────────────────────────────────
    "Luís Roberto Barroso": [
        "Alvo de suposto plano de assassinato investigado pela PF junto com Lula e Alckmin (2022) — como vítima, não réu",
        "Questionado por ministros e parlamentares da direita por supostos excessos jurisdicionais em matéria eleitoral (2022–2024) — sem processo formal",
    ],

    # ── RENAN CALHEIROS ───────────────────────────────────────────────────────
    "Renan Calheiros": [
        "Absolvido pelo STF em ação penal por peculato — suposto uso de pensão alimentícia de lobista para pagar despesas pessoais (AP 565, 2016) — absolvido por prescrição em 2021",
        "Investigado em múltiplos inquéritos da Lava Jato por corrupção passiva — denúncias rejeitadas pelo STF por insuficiência de provas (2017–2020)",
        "Condenado em 1ª instância no RJ por difamação contra o promotor que o investigou (2018) — aguarda julgamento em 2ª instância",
    ],

    # ── SERGIO MORO ───────────────────────────────────────────────────────────
    "Sergio Moro": [
        "Declarado parcial e suspeito pelo STF por ter coordenado acusação e defesa no processo do ex-presidente Lula — mensagens do 'Vaza Jato' revelaram comunicação indevida com o MPF (2021)",
        "Investigado pelo CNJ por suposta parcialidade sistêmica na condução dos processos da Lava Jato (2021) — processo disciplinar em andamento",
        "Ação penal por improbidade administrativa ajuizada pelo PT no STJ (2022) — em tramitação",
    ],

    # ── RODRIGO PACHECO ───────────────────────────────────────────────────────
    "Rodrigo Pacheco": [
        "Investigado no STF por suspeita de uso de avião da FAB para fins particulares (2022) — PGR não encontrou irregularidade; inquérito arquivado",
    ],

    # ── ARTHUR LIRA ───────────────────────────────────────────────────────────
    "Arthur Lira": [
        "Investigado pelo STF no inquérito do mensalão do PSB-AL por suposta cobrança de propina de empreiteiras no Alagoas (Inq. 3.983, 2015–2020) — PGR pediu arquivamento; STF arquivou em 2020",
        "Investigado pela PGR por suposto envolvimento em corrupção em contratos da Petrobras — incluído em delação premiada de executivo da UTC Engenharia (2016) — inquérito arquivado",
    ],

    # ── GLEISI HOFFMANN ───────────────────────────────────────────────────────
    "Gleisi Hoffmann": [
        "Denunciada pelo MPF por corrupção passiva e lavagem de dinheiro no caso JBS/Odebrecht — recebimento de R$ 1 milhão para campanha ao governo do Paraná (STF, AP 924, 2015) — absolvida pelo STF em 2020 por insuficiência de provas",
    ],

    # ── PAULO GUEDES ──────────────────────────────────────────────────────────
    "Paulo Guedes": [
        "Investigado pela CVM (Comissão de Valores Mobiliários) por suspeita de conflito de interesse por manter fundo de investimentos no exterior enquanto era Ministro da Economia (2021) — respondeu à CVM; caso sem punição",
        "Investigado no TCU por irregularidades na gestão do Fundo de Amparo ao Trabalhador durante a pandemia (2020–2021)",
    ],

    # ── TASSO JEREISSATI ──────────────────────────────────────────────────────
    "Tasso Jereissati": [
        "Investigado pelo STF no âmbito da Operação Lava Jato por suposto recebimento de propina da Odebrecht para campanha eleitoral no Ceará (2016) — PGR pediu arquivamento; STF arquivou em 2019",
    ],

    # ── AÉCIO NEVES ───────────────────────────────────────────────────────────
    "Aécio Neves": [
        "Denunciado pelo MPF por corrupção passiva — gravação em que pedia R$ 2 milhões ao empresário Joesley Batista (JBS) (STF, 2017) — STF condenou por corrupção passiva em 2023; aguarda julgamento dos embargos de declaração",
        "Investigado pelo STF por obstrução de Justiça — tentativa de interferir nas investigações da Lava Jato (Inq. 4.327, 2017) — em tramitação",
    ],

    # ── CHIQUINHO BRAZÃO / BRAZÃO ──────────────────────────────────────────────
    "Chiquinho Brazão": [
        "Preso preventivamente em março de 2024 como mandante do assassinato da vereadora Marielle Franco e do motorista Anderson Gomes (STF, AP 1.486, 2024) — ação penal em curso no STF",
    ],
    "Domingos Brazão": [
        "Preso preventivamente em março de 2024 como co-mandante do assassinato de Marielle Franco e Anderson Gomes (STF, AP 1.486, 2024) — ação penal em curso no STF",
    ],

    # ── RONNIE LESSA ──────────────────────────────────────────────────────────
    "Ronnie Lessa": [
        "Executante confesso do assassinato da vereadora Marielle Franco e do motorista Anderson Gomes (24/03/2018) — preso em março de 2024; celebrou acordo de delação premiada com o MPF; julgamento pelo Tribunal do Júri em 2024",
    ],

    # ── ZEMA ──────────────────────────────────────────────────────────────────
    "Romeu Zema": [
        "Investigado pelo TCU por irregularidades no repasse de recursos federais para MG durante a pandemia (2020–2021)",
        "Alvo de ação no STF por descumprimento de determinação judicial para pagamento de precatórios do estado de MG (2023) — em tramitação",
    ],

    # ── CIRO GOMES ────────────────────────────────────────────────────────────
    "Ciro Gomes": [
        "Réu em ação por calúnia e injúria movida pelo ex-presidente Lula após declarações durante a campanha eleitoral de 2018 (Justiça Federal do CE) — conciliação em 2021",
        "Investigado pelo MP-CE por suposta irregularidade em concessões de postos de combustíveis durante gestão no governo do Ceará (1991–1994) — prescrito",
    ],

    # ── PAULO CÂMARA ──────────────────────────────────────────────────────────
    "Paulo Câmara": [
        "Investigado pelo MP-PE por irregularidades em contratos de tecnologia do estado de PE durante a pandemia (2020–2022) — em apuração",
    ],

    # ── WILSON WITZEL ─────────────────────────────────────────────────────────
    "Wilson Witzel": [
        "Sofreu processo de impeachment no estado do RJ por corrupção na compra de respiradores e hospitais de campanha durante a COVID-19 (2020) — afastado pelo STJ em agosto/2020; impeachment aprovado pela ALERJ em maio/2021",
        "Denunciado pelo MP-RJ e MPF por corrupção passiva, lavagem de dinheiro e peculato (2021) — ação penal em curso",
    ],

    # ── GAROTINHO ─────────────────────────────────────────────────────────────
    "Anthony Garotinho": [
        "Preso duas vezes durante campanha eleitoral em 2016 por suspeita de compra de votos no RJ (Operação Chequinho) — solto por habeas corpus; condenado em 1ª instância por compra de votos (TRE-RJ, 2018); recursos pendentes no TSE",
    ],

    # ── MÁRCIO FRENCH / DEGENHARDT ────────────────────────────────────────────
    "Waguinho": [
        "Investigado pelo MP-RJ por suspeita de irregularidades em contratos municipais de saúde em Belford Roxo (2022) — em apuração",
    ],

    # ── MARCOS DO VAL ────────────────────────────────────────────────────────
    "Marcos do Val": [
        "Investigado pelo STF por suposto envolvimento em reunião para discutir um golpe de Estado após as eleições de 2022 — relatos de que apresentou plano para prender ministros do STF (Inq. 4.874, 2022–2023) — delação premiada rescindida pela PGR; status em apuração",
    ],

    # ── PAULO PIMENTA ─────────────────────────────────────────────────────────
    "Wladimir Garotinho": [
        "Investigado pelo GAECO/MP-RJ por suspeita de corrupção em contratos da Prefeitura de Campos dos Goytacazes (2023) — em apuração",
    ],

}  # fim _CHARGES_DB

def _get_charges(name: str, full_name: str = "") -> list[str]:
    """Retorna lista de processos para um político pelo nome.
    Tenta nome parlamentar, nome completo e variações."""
    if not name and not full_name: return []
    for key in [name, full_name, name.split(" ")[0] + " " + name.split(" ")[-1] if name else ""]:
        if key and key in _CHARGES_DB:
            return _CHARGES_DB[key]
    # Busca parcial — nome de família
    if name:
        sobrenome = name.split()[-1] if name.split() else ""
        for k, v in _CHARGES_DB.items():
            if sobrenome and sobrenome.lower() in k.lower() and len(sobrenome) > 4:
                return v
    return []

# Salário presidente: Lei 13.752/2018 — R$ 30.934,70/mês
# Salário ministro STF: R$ 46.366,19/mês (teto constitucional)
# Salário dep/sen: R$ 46.366,19/mês

