"""Prefeitos e Governadores curados — eleições 2024."""
import unicodedata as _ucd


def _norm(s: str) -> str:
    return _ucd.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower().strip()


def _gov(wid, name, role, party, photo="", wiki_pt="", wiki_en=""):
    """Cria entrada de governador. photo é fallback; wiki_pt é título Wikipedia PT."""
    return {
        "id": wid, "name": name, "role": role, "party": party,
        "photo": photo,
        "wiki_title_pt": wiki_pt or name,
        "wiki_title_en": wiki_en or name,
    }

WM = "https://upload.wikimedia.org/wikipedia/commons/thumb"
GOVERNORS_BY_UF = {
    "AC":  _gov("wd-Q10282903","Gladson Cameli","Governador do Acre","PP", wiki_pt="Gladson Cameli", wiki_en="Gladson Cameli"),
    "AL":  _gov("wd-Q10285716","Paulo Dantas","Governador de Alagoas","MDB", wiki_pt="Paulo Dantas", wiki_en="Paulo Dantas"),
    "AM":  _gov("wd-gov-AM","Wilson Lima","Governador do Amazonas","União Brasil", wiki_pt="Wilson Lima (político)", wiki_en="Wilson Lima"),
    "AP":  _gov("wd-gov-AP","Clécio Luís","Governador do Amapá","SD", wiki_pt="Clécio Luís", wiki_en="Clécio Luís"),
    "BA":  _gov("wd-gov-BA","Jerônimo Rodrigues","Governador da Bahia","PT", wiki_pt="Jerônimo Rodrigues", wiki_en="Jerônimo Rodrigues"),
    "CE":  _gov("wd-gov-CE","Elmano de Freitas","Governador do Ceará","PT", wiki_pt="Elmano de Freitas", wiki_en="Elmano de Freitas"),
    "DF":  _gov("wd-Q10303893","Ibaneis Rocha","Governador do Distrito Federal","MDB", wiki_pt="Ibaneis Rocha", wiki_en="Ibaneis Rocha"),
    "ES":  _gov("wd-Q3730577","Renato Casagrande","Governador do Espírito Santo","PSB", wiki_pt="Renato Casagrande", wiki_en="Renato Casagrande"),
    "GO":  _gov("wd-Q10306753","Ronaldo Caiado","Governador de Goiás","União Brasil", wiki_pt="Ronaldo Caiado", wiki_en="Ronaldo Caiado"),
    "MA":  _gov("wd-Q10306938","Carlos Brandão","Governador do Maranhão","PSB", wiki_pt="Carlos Brandão (político)", wiki_en="Carlos Brandão"),
    "MT":  _gov("wd-Q10308490","Mauro Mendes","Governador do Mato Grosso","União Brasil", wiki_pt="Mauro Mendes", wiki_en="Mauro Mendes"),
    "MS":  _gov("wd-Q10308503","Eduardo Riedel","Governador do Mato Grosso do Sul","PSDB", wiki_pt="Eduardo Riedel", wiki_en="Eduardo Riedel"),
    "MG":  _gov("wd-gov-MG","Romeu Zema","Governador de Minas Gerais","Novo", wiki_pt="Romeu Zema", wiki_en="Romeu Zema"),
    "PA":  _gov("wd-gov-PA","Helder Barbalho","Governador do Pará","MDB", wiki_pt="Helder Barbalho", wiki_en="Helder Barbalho"),
    "PB":  _gov("wd-Q10309964","João Azevêdo","Governador da Paraíba","PSB", wiki_pt="João Azevêdo", wiki_en="João Azevêdo"),
    "PR":  _gov("wd-gov-PR","Ratinho Junior","Governador do Paraná","PSD", wiki_pt="Ratinho Junior", wiki_en="Carlos Ratinho Junior"),
    "PE":  _gov("wd-gov-PE","Raquel Lyra","Governadora de Pernambuco","PSDB", wiki_pt="Raquel Lyra", wiki_en="Raquel Lyra"),
    "PI":  _gov("wd-Q10310123","Rafael Fonteles","Governador do Piauí","PT", wiki_pt="Rafael Fonteles", wiki_en="Rafael Fonteles"),
    "RJ":  _gov("wd-gov-RJ","Cláudio Castro","Governador do Rio de Janeiro","PL", wiki_pt="Cláudio Castro (político)", wiki_en="Cláudio Castro"),
    "RN":  _gov("wd-Q10312022","Fátima Bezerra","Governadora do Rio Grande do Norte","PT", wiki_pt="Fátima Bezerra", wiki_en="Fátima Bezerra"),
    "RS":  _gov("wd-gov-RS","Eduardo Leite","Governador do Rio Grande do Sul","PSDB", wiki_pt="Eduardo Leite (político)", wiki_en="Eduardo Leite"),
    "RO":  _gov("wd-Q10311952","Marcos Rocha","Governador de Rondônia","União Brasil", wiki_pt="Marcos Rocha", wiki_en="Marcos Rocha"),
    "RR":  _gov("wd-Q10312027","Arthur Henrique","Governador de Roraima","MDB", wiki_pt="Arthur Henrique", wiki_en="Arthur Henrique"),
    "SC":  _gov("wd-Q10312568","Jorginho Mello","Governador de Santa Catarina","PL", wiki_pt="Jorginho Mello", wiki_en="Jorginho Mello"),
    "SE":  _gov("wd-Q10314272","Fábio Mitidieri","Governador de Sergipe","PSD", wiki_pt="Fábio Mitidieri", wiki_en="Fábio Mitidieri"),
    "SP":  _gov("wd-gov-SP","Tarcísio de Freitas","Governador de São Paulo","Republicanos", wiki_pt="Tarcísio de Freitas", wiki_en="Tarcísio de Freitas"),
    "TO":  _gov("wd-Q10314456","Wanderlei Barbosa","Governador do Tocantins","Republicanos", wiki_pt="Wanderlei Barbosa", wiki_en="Wanderlei Barbosa"),
}
UF_NAMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins"}

COUNTRY_FLAGS = {
    "BR":"🇧🇷","US":"🇺🇸","FR":"🇫🇷","DE":"🇩🇪","GB":"🇬🇧","AR":"🇦🇷","PT":"🇵🇹",
    "MX":"🇲🇽","JP":"🇯🇵","CN":"🇨🇳","RU":"🇷🇺","IT":"🇮🇹","ES":"🇪🇸","UY":"🇺🇾",
    "CL":"🇨🇱","CO":"🇨🇴","VE":"🇻🇪","PE":"🇵🇪","BO":"🇧🇴","PY":"🇵🇾",
}



# Prefeitos curados — eleições 2024
# IDs: QIDs verificados para políticos conhecidos; "mayor-{slug}" para os demais
# wiki_title_pt garante foto via Wikipedia REST API
MAYORS_BY_CITY = {
    # ── RIO DE JANEIRO ──────────────────────────────────────────
    # NOTA: IDs usam "mayor-{slug}" para garantir carregamento via CURATED_POLITICIANS
    # NUNCA use QIDs não verificados aqui — causa o bug do "prefeito gastrópode"
    "Rio de Janeiro":           {"id":"mayor-rio-de-janeiro", "name":"Eduardo Paes", "role":"Prefeito do Rio de Janeiro", "party":"PSD", "uf":"RJ", "photo":"", "wiki_title_pt":"Eduardo Paes", "wiki_title_en":"Eduardo Paes"},
    "Niterói":                  {"id":"mayor-niteroi", "name":"Rodrigo Neves", "role":"Prefeito de Niterói", "party":"PDT", "uf":"RJ", "photo":"", "wiki_title_pt":"Rodrigo Neves", "wiki_title_en":"Rodrigo Neves"},
    "Nova Iguaçu":              {"id":"mayor-nova-iguacu", "name":"Duarte Júnior", "role":"Prefeito de Nova Iguaçu", "party":"PSD", "uf":"RJ", "photo":"", "wiki_title_pt":"Duarte Júnior", "wiki_title_en":"Duarte Júnior"},
    "Duque de Caxias":          {"id":"mayor-duque-de-caxias", "name":"Wilson Reis", "role":"Prefeito de Duque de Caxias", "party":"MDB", "uf":"RJ", "photo":"", "wiki_title_pt":"Wilson Reis", "wiki_title_en":"Wilson Reis"},
    "São Gonçalo":              {"id":"mayor-sao-goncalo", "name":"Capitão Nelson", "role":"Prefeito de São Gonçalo", "party":"PL", "uf":"RJ", "photo":"", "wiki_title_pt":"Capitão Nelson", "wiki_title_en":"Capitão Nelson"},
    "Petrópolis":               {"id":"mayor-petropolis", "name":"Rubens Bomtempo", "role":"Prefeito de Petrópolis", "party":"PSB", "uf":"RJ", "photo":"", "wiki_title_pt":"Rubens Bomtempo", "wiki_title_en":"Rubens Bomtempo"},
    "Teresópolis":              {"id":"mayor-teresopolis", "name":"Vinicius Claussen", "role":"Prefeito de Teresópolis", "party":"PSD", "uf":"RJ", "photo":"", "wiki_title_pt":"Vinicius Claussen", "wiki_title_en":"Vinicius Claussen"},
    "Volta Redonda":            {"id":"mayor-volta-redonda", "name":"Neto", "role":"Prefeito de Volta Redonda", "party":"MDB", "uf":"RJ", "photo":"", "wiki_title_pt":"Neto (Volta Redonda)", "wiki_title_en":"Neto"},
    "Resende":                  {"id":"mayor-resende", "name":"Alexandre Fonseca", "role":"Prefeito de Resende", "party":"PRD", "uf":"RJ", "photo":"", "wiki_title_pt":"Alexandre Fonseca", "wiki_title_en":"Alexandre Fonseca"},
    "Macaé":                    {"id":"mayor-macae", "name":"Dr. Welberth Rezende", "role":"Prefeito de Macaé", "party":"Podemos", "uf":"RJ", "photo":"", "wiki_title_pt":"Welberth Rezende", "wiki_title_en":"Welberth Rezende"},
    "Campos dos Goytacazes":    {"id":"mayor-campos-dos-goytacazes", "name":"Wladimir Garotinho", "role":"Prefeito de Campos dos Goytacazes", "party":"PRD", "uf":"RJ", "photo":"", "wiki_title_pt":"Wladimir Garotinho", "wiki_title_en":"Wladimir Garotinho"},
    "Angra dos Reis":           {"id":"mayor-angra-dos-reis", "name":"Fábio do Pastel", "role":"Prefeito de Angra dos Reis", "party":"Solidariedade", "uf":"RJ", "photo":"", "wiki_title_pt":"Fábio do Pastel", "wiki_title_en":"Fábio do Pastel"},
    "Cabo Frio":                {"id":"mayor-cabo-frio", "name":"Renatinho Vianna", "role":"Prefeito de Cabo Frio", "party":"MDB", "uf":"RJ", "photo":"", "wiki_title_pt":"Renatinho Vianna", "wiki_title_en":"Renatinho Vianna"},
    "Barra Mansa":              {"id":"mayor-barra-mansa", "name":"Rodrigo Drable", "role":"Prefeito de Barra Mansa", "party":"AVANTE", "uf":"RJ", "photo":"", "wiki_title_pt":"Rodrigo Drable", "wiki_title_en":"Rodrigo Drable"},
    "Itaperuna":                {"id":"mayor-itaperuna", "name":"Ontiveiro Júnior", "role":"Prefeito de Itaperuna", "party":"MDB", "uf":"RJ", "photo":"", "wiki_title_pt":"Ontiveiro Júnior", "wiki_title_en":"Ontiveiro Júnior"},
    # ── SÃO PAULO ────────────────────────────────────────────────
    "São Paulo":                {"id":"mayor-sao-paulo", "name":"Ricardo Nunes", "role":"Prefeito de São Paulo", "party":"MDB", "uf":"SP", "photo":"", "wiki_title_pt":"Ricardo Nunes", "wiki_title_en":"Ricardo Nunes"},
    "Campinas":                 {"id":"mayor-campinas", "name":"Dario Saadi", "role":"Prefeito de Campinas", "party":"Republicanos", "uf":"SP", "photo":"", "wiki_title_pt":"Dario Saadi", "wiki_title_en":"Dario Saadi"},
    "Guarulhos":                {"id":"mayor-guarulhos", "name":"Guti", "role":"Prefeito de Guarulhos", "party":"PSD", "uf":"SP", "photo":"", "wiki_title_pt":"Gustavo Henrique Gomes", "wiki_title_en":"Guti"},
    "Santo André":              {"id":"mayor-santo-andre", "name":"Gilvan Junior", "role":"Prefeito de Santo André", "party":"PL", "uf":"SP", "photo":"", "wiki_title_pt":"Gilvan Junior", "wiki_title_en":"Gilvan Junior"},
    "São Bernardo do Campo":    {"id":"mayor-sao-bernardo-do-campo", "name":"Orlando Morando", "role":"Prefeito de São Bernardo do Campo", "party":"PSDB", "uf":"SP", "photo":"", "wiki_title_pt":"Orlando Morando", "wiki_title_en":"Orlando Morando"},
    "Osasco":                   {"id":"mayor-osasco", "name":"Rogério Lins", "role":"Prefeito de Osasco", "party":"Podemos", "uf":"SP", "photo":"", "wiki_title_pt":"Rogério Lins", "wiki_title_en":"Rogério Lins"},
    "Ribeirão Preto":           {"id":"mayor-ribeirao-preto", "name":"Marcos Antonio", "role":"Prefeito de Ribeirão Preto", "party":"PSD", "uf":"SP", "photo":"", "wiki_title_pt":"Marcos Vieira", "wiki_title_en":"Marcos Antonio"},
    "Sorocaba":                 {"id":"mayor-sorocaba", "name":"Rodrigo Manga", "role":"Prefeito de Sorocaba", "party":"Republicanos", "uf":"SP", "photo":"", "wiki_title_pt":"Rodrigo Manga", "wiki_title_en":"Rodrigo Manga"},
    # ── MINAS GERAIS ─────────────────────────────────────────────
    "Belo Horizonte":           {"id":"mayor-belo-horizonte", "name":"Fuad Noman", "role":"Prefeito de Belo Horizonte", "party":"PSD", "uf":"MG", "photo":"", "wiki_title_pt":"Fuad Noman", "wiki_title_en":"Fuad Noman"},
    "Contagem":                 {"id":"mayor-contagem", "name":"Marília Campos", "role":"Prefeita de Contagem", "party":"PT", "uf":"MG", "photo":"", "wiki_title_pt":"Marília Campos", "wiki_title_en":"Marília Campos"},
    "Uberlândia":               {"id":"mayor-uberlandia", "name":"Sérgio Rezende", "role":"Prefeito de Uberlândia", "party":"PSD", "uf":"MG", "photo":"", "wiki_title_pt":"Sérgio Rezende", "wiki_title_en":"Sérgio Rezende"},
    # ── BAHIA ────────────────────────────────────────────────────
    "Salvador":                 {"id":"mayor-salvador", "name":"Bruno Reis", "role":"Prefeito de Salvador", "party":"União Brasil", "uf":"BA", "photo":"", "wiki_title_pt":"Bruno Reis (político)", "wiki_title_en":"Bruno Reis"},
    "Feira de Santana":         {"id":"mayor-feira-de-santana", "name":"Zé Ronaldo", "role":"Prefeito de Feira de Santana", "party":"União Brasil", "uf":"BA", "photo":"", "wiki_title_pt":"José Ronaldo (Feira de Santana)", "wiki_title_en":"José Ronaldo"},
    # ── RIO GRANDE DO SUL ────────────────────────────────────────
    "Porto Alegre":             {"id":"mayor-porto-alegre", "name":"Sebastião Melo", "role":"Prefeito de Porto Alegre", "party":"MDB", "uf":"RS", "photo":"", "wiki_title_pt":"Sebastião Melo", "wiki_title_en":"Sebastião Melo"},
    "Caxias do Sul":            {"id":"mayor-caxias-do-sul", "name":"Adiló Didomenico", "role":"Prefeito de Caxias do Sul", "party":"PSDB", "uf":"RS", "photo":"", "wiki_title_pt":"Adiló Didomenico", "wiki_title_en":"Adiló Didomenico"},
    # ── PARANÁ ───────────────────────────────────────────────────
    "Curitiba":                 {"id":"mayor-curitiba", "name":"Eduardo Pimentel", "role":"Prefeito de Curitiba", "party":"PSD", "uf":"PR", "photo":"", "wiki_title_pt":"Eduardo Pimentel (político)", "wiki_title_en":"Eduardo Pimentel"},
    "Londrina":                 {"id":"mayor-londrina", "name":"Marcelo Belinati", "role":"Prefeito de Londrina", "party":"PP", "uf":"PR", "photo":"", "wiki_title_pt":"Marcelo Belinati", "wiki_title_en":"Marcelo Belinati"},
    # ── SANTA CATARINA ───────────────────────────────────────────
    "Florianópolis":            {"id":"mayor-florianopolis", "name":"Topázio Neto", "role":"Prefeito de Florianópolis", "party":"PSD", "uf":"SC", "photo":"", "wiki_title_pt":"Topázio Neto", "wiki_title_en":"Topázio Neto"},
    "Joinville":                {"id":"mayor-joinville", "name":"Adriano Silva", "role":"Prefeito de Joinville", "party":"PSD", "uf":"SC", "photo":"", "wiki_title_pt":"Adriano Silva (político)", "wiki_title_en":"Adriano Silva"},
    # ── PERNAMBUCO ───────────────────────────────────────────────
    "Recife":                   {"id":"mayor-recife", "name":"João Campos", "role":"Prefeito do Recife", "party":"PSB", "uf":"PE", "photo":"", "wiki_title_pt":"João Campos (político)", "wiki_title_en":"João Campos"},
    # ── CEARÁ ────────────────────────────────────────────────────
    "Fortaleza":                {"id":"mayor-fortaleza", "name":"Evandro Leitão", "role":"Prefeito de Fortaleza", "party":"PT", "uf":"CE", "photo":"", "wiki_title_pt":"Evandro Leitão", "wiki_title_en":"Evandro Leitão"},
    # ── AMAZONAS ─────────────────────────────────────────────────
    "Manaus":                   {"id":"mayor-manaus", "name":"David Almeida", "role":"Prefeito de Manaus", "party":"Avante", "uf":"AM", "photo":"", "wiki_title_pt":"David Almeida (político)", "wiki_title_en":"David Almeida"},
    # ── PARÁ ─────────────────────────────────────────────────────
    "Belém":                    {"id":"mayor-belem", "name":"Igor Normando", "role":"Prefeito de Belém", "party":"MDB", "uf":"PA", "photo":"", "wiki_title_pt":"Igor Normando", "wiki_title_en":"Igor Normando"},
    # ── GOIÁS ────────────────────────────────────────────────────
    "Goiânia":                  {"id":"mayor-goiania", "name":"Sandro Mabel", "role":"Prefeito de Goiânia", "party":"União Brasil", "uf":"GO", "photo":"", "wiki_title_pt":"Sandro Mabel", "wiki_title_en":"Sandro Mabel"},
    # ── MARANHÃO ─────────────────────────────────────────────────
    "São Luís":                 {"id":"mayor-sao-luis", "name":"Eduardo Braide", "role":"Prefeito de São Luís", "party":"PSD", "uf":"MA", "photo":"", "wiki_title_pt":"Eduardo Braide", "wiki_title_en":"Eduardo Braide"},
    # ── MATO GROSSO DO SUL ───────────────────────────────────────
    "Campo Grande":             {"id":"mayor-campo-grande", "name":"Adriane Lopes", "role":"Prefeita de Campo Grande", "party":"PP", "uf":"MS", "photo":"", "wiki_title_pt":"Adriane Lopes", "wiki_title_en":"Adriane Lopes"},
    # ── ALAGOAS ──────────────────────────────────────────────────
    "Maceió":                   {"id":"mayor-maceio", "name":"João Henrique Caldas", "role":"Prefeito de Maceió", "party":"PL", "uf":"AL", "photo":"", "wiki_title_pt":"João Henrique Caldas", "wiki_title_en":"João Henrique Caldas"},
    # ── PIAUÍ ────────────────────────────────────────────────────
    "Teresina":                 {"id":"mayor-teresina", "name":"Dr. Silvio Mendes", "role":"Prefeito de Teresina", "party":"União Brasil", "uf":"PI", "photo":"", "wiki_title_pt":"Silvio Mendes", "wiki_title_en":"Silvio Mendes"},
    # ── PARAÍBA ──────────────────────────────────────────────────
    "João Pessoa":              {"id":"mayor-joao-pessoa", "name":"Cícero Lucena", "role":"Prefeito de João Pessoa", "party":"PP", "uf":"PB", "photo":"", "wiki_title_pt":"Cícero Lucena", "wiki_title_en":"Cícero Lucena"},
    # ── RIO GRANDE DO NORTE ──────────────────────────────────────
    "Natal":                    {"id":"mayor-natal", "name":"Paulinho Freire", "role":"Prefeito de Natal", "party":"União Brasil", "uf":"RN", "photo":"", "wiki_title_pt":"Paulinho Freire", "wiki_title_en":"Paulinho Freire"},
    # ── SERGIPE ──────────────────────────────────────────────────
    "Aracaju":                  {"id":"mayor-aracaju", "name":"Emília Corrêa", "role":"Prefeita de Aracaju", "party":"PL", "uf":"SE", "photo":"", "wiki_title_pt":"Emília Corrêa", "wiki_title_en":"Emília Corrêa"},
    # ── DISTRITO FEDERAL ─────────────────────────────────────────
    "Brasília":                 {"id":"wd-Q10303893", "name":"Ibaneis Rocha", "role":"Governador do DF", "party":"MDB", "uf":"DF", "photo":"", "wiki_title_pt":"Ibaneis Rocha", "wiki_title_en":"Ibaneis Rocha"},
    # ── ESPÍRITO SANTO ───────────────────────────────────────────
    "Vitória":                  {"id":"mayor-vitoria", "name":"Lorenzo Pazolini", "role":"Prefeito de Vitória", "party":"Republicanos", "uf":"ES", "photo":"", "wiki_title_pt":"Lorenzo Pazolini", "wiki_title_en":"Lorenzo Pazolini"},
    # ── MATO GROSSO ──────────────────────────────────────────────
    "Cuiabá":                   {"id":"mayor-cuiaba", "name":"Abilio Brunini", "role":"Prefeito de Cuiabá", "party":"PL", "uf":"MT", "photo":"", "wiki_title_pt":"Abilio Brunini", "wiki_title_en":"Abilio Brunini"},
    # ── AMAPÁ ────────────────────────────────────────────────────
    "Macapá":                   {"id":"mayor-macapa", "name":"Dr. Furlan", "role":"Prefeito de Macapá", "party":"MDB", "uf":"AP", "photo":"", "wiki_title_pt":"Furlan (político)", "wiki_title_en":"Furlan"},
    # ── RONDÔNIA ─────────────────────────────────────────────────
    "Porto Velho":              {"id":"mayor-porto-velho", "name":"Hildon Chaves", "role":"Prefeito de Porto Velho", "party":"PSDB", "uf":"RO", "photo":"", "wiki_title_pt":"Hildon Chaves", "wiki_title_en":"Hildon Chaves"},
    # ── RORAIMA ──────────────────────────────────────────────────
    "Boa Vista":                {"id":"mayor-boa-vista", "name":"Arthur Henrique", "role":"Prefeito de Boa Vista", "party":"MDB", "uf":"RR", "photo":"", "wiki_title_pt":"Arthur Henrique", "wiki_title_en":"Arthur Henrique"},
    # ── TOCANTINS ────────────────────────────────────────────────
    "Palmas":                   {"id":"mayor-palmas", "name":"Eduardo Siqueira Campos", "role":"Prefeito de Palmas", "party":"Podemos", "uf":"TO", "photo":"", "wiki_title_pt":"Eduardo Siqueira Campos", "wiki_title_en":"Eduardo Siqueira Campos"},
    # ── ACRE ─────────────────────────────────────────────────────
    "Rio Branco":               {"id":"mayor-rio-branco", "name":"Tião Bocalom", "role":"Prefeito de Rio Branco", "party":"PP", "uf":"AC", "photo":"", "wiki_title_pt":"Tião Bocalom", "wiki_title_en":"Tião Bocalom"},
    # ── MINAS GERAIS — INTERIOR ──────────────────────────────────
    "Juiz de Fora":             {"id":"mayor-juiz-de-fora", "name":"Margarida Salomão", "role":"Prefeita de Juiz de Fora", "party":"PT", "uf":"MG", "photo":"", "wiki_title_pt":"Margarida Salomão", "wiki_title_en":"Margarida Salomão"},
    "Betim":                    {"id":"mayor-betim", "name":"Vittório Medioli", "role":"Prefeito de Betim", "party":"PSD", "uf":"MG", "photo":"", "wiki_title_pt":"Vittório Medioli", "wiki_title_en":"Vittório Medioli"},
    "Montes Claros":            {"id":"mayor-montes-claros", "name":"Humberto Souto", "role":"Prefeito de Montes Claros", "party":"Cidadania", "uf":"MG", "photo":"", "wiki_title_pt":"Humberto Souto", "wiki_title_en":"Humberto Souto"},
    # ── PARÁ — INTERIOR ──────────────────────────────────────────
    "Ananindeua":               {"id":"mayor-ananindeua", "name":"Daniel Santos", "role":"Prefeito de Ananindeua", "party":"MDB", "uf":"PA", "photo":"", "wiki_title_pt":"Daniel Santos (político)", "wiki_title_en":"Daniel Santos"},
    "Santarém":                 {"id":"mayor-santarem", "name":"Nélio Aguiar", "role":"Prefeito de Santarém", "party":"PSD", "uf":"PA", "photo":"", "wiki_title_pt":"Nélio Aguiar", "wiki_title_en":"Nélio Aguiar"},
    # ── GOIÁS — INTERIOR ─────────────────────────────────────────
    "Aparecida de Goiânia":     {"id":"mayor-aparecida-de-goiania", "name":"Gustavo Mendanha", "role":"Prefeito de Aparecida de Goiânia", "party":"MDB", "uf":"GO", "photo":"", "wiki_title_pt":"Gustavo Mendanha", "wiki_title_en":"Gustavo Mendanha"},
    "Anápolis":                 {"id":"mayor-anapolis", "name":"Roberto Naves", "role":"Prefeito de Anápolis", "party":"PP", "uf":"GO", "photo":"", "wiki_title_pt":"Roberto Naves", "wiki_title_en":"Roberto Naves"},
    # ── SÃO PAULO — INTERIOR ─────────────────────────────────────
    "Santos":                   {"id":"mayor-santos", "name":"Rogério Santos", "role":"Prefeito de Santos", "party":"PSDB", "uf":"SP", "photo":"", "wiki_title_pt":"Rogério Santos (político)", "wiki_title_en":"Rogério Santos"},
    "São José dos Campos":      {"id":"mayor-sao-jose-dos-campos", "name":"Anderson Farias", "role":"Prefeito de São José dos Campos", "party":"MDB", "uf":"SP", "photo":"", "wiki_title_pt":"Anderson Farias", "wiki_title_en":"Anderson Farias"},
    "Mogi das Cruzes":          {"id":"mayor-mogi-das-cruzes", "name":"Caio Cunha", "role":"Prefeito de Mogi das Cruzes", "party":"Podemos", "uf":"SP", "photo":"", "wiki_title_pt":"Caio Cunha", "wiki_title_en":"Caio Cunha"},
    "Jundiaí":                  {"id":"mayor-jundiai", "name":"Gustavo Martinelli", "role":"Prefeito de Jundiaí", "party":"Podemos", "uf":"SP", "photo":"", "wiki_title_pt":"Gustavo Martinelli", "wiki_title_en":"Gustavo Martinelli"},
    "Piracicaba":               {"id":"mayor-piracicaba", "name":"Luciano Almeida", "role":"Prefeito de Piracicaba", "party":"PSD", "uf":"SP", "photo":"", "wiki_title_pt":"Luciano Almeida", "wiki_title_en":"Luciano Almeida"},
    "Bauru":                    {"id":"mayor-bauru", "name":"Suéllen Rosim", "role":"Prefeita de Bauru", "party":"PL", "uf":"SP", "photo":"", "wiki_title_pt":"Suéllen Rosim", "wiki_title_en":"Suéllen Rosim"},
    "Franca":                   {"id":"mayor-franca", "name":"Alexandre Ferreira", "role":"Prefeito de Franca", "party":"MDB", "uf":"SP", "photo":"", "wiki_title_pt":"Alexandre Ferreira (político)", "wiki_title_en":"Alexandre Ferreira"},
    "São José do Rio Preto":    {"id":"mayor-sao-jose-do-rio-preto", "name":"Edinho Araújo", "role":"Prefeito de São José do Rio Preto", "party":"MDB", "uf":"SP", "photo":"", "wiki_title_pt":"Edinho Araújo", "wiki_title_en":"Edinho Araújo"},
    "São Vicente":              {"id":"mayor-sao-vicente", "name":"Guilherme Gomes", "role":"Prefeito de São Vicente", "party":"Podemos", "uf":"SP", "photo":"", "wiki_title_pt":"Guilherme Gomes (político)", "wiki_title_en":"Guilherme Gomes"},
    "Praia Grande":             {"id":"mayor-praia-grande", "name":"Raquel Chini", "role":"Prefeita de Praia Grande", "party":"PL", "uf":"SP", "photo":"", "wiki_title_pt":"Raquel Chini", "wiki_title_en":"Raquel Chini"},
    "Diadema":                  {"id":"mayor-diadema", "name":"José de Filippi Júnior", "role":"Prefeito de Diadema", "party":"PT", "uf":"SP", "photo":"", "wiki_title_pt":"Filippi Júnior", "wiki_title_en":"Filippi Júnior"},
    # ── PERNAMBUCO — INTERIOR ────────────────────────────────────
    "Olinda":                   {"id":"mayor-olinda", "name":"Vitor Marinho", "role":"Prefeito de Olinda", "party":"MDB", "uf":"PE", "photo":"", "wiki_title_pt":"Vitor Marinho", "wiki_title_en":"Vitor Marinho"},
    "Caruaru":                  {"id":"mayor-caruaru", "name":"Rodrigo Pinheiro", "role":"Prefeito de Caruaru", "party":"PSD", "uf":"PE", "photo":"", "wiki_title_pt":"Rodrigo Pinheiro", "wiki_title_en":"Rodrigo Pinheiro"},
    # ── PARAÍBA — INTERIOR ───────────────────────────────────────
    "Campina Grande":           {"id":"mayor-campina-grande", "name":"Bruno Cunha Lima", "role":"Prefeito de Campina Grande", "party":"União Brasil", "uf":"PB", "photo":"", "wiki_title_pt":"Bruno Cunha Lima", "wiki_title_en":"Bruno Cunha Lima"},
    # ── CEARÁ — INTERIOR ─────────────────────────────────────────
    "Caucaia":                  {"id":"mayor-caucaia", "name":"Naumi Amorim", "role":"Prefeito de Caucaia", "party":"PSD", "uf":"CE", "photo":"", "wiki_title_pt":"Naumi Amorim", "wiki_title_en":"Naumi Amorim"},
    "Juazeiro do Norte":        {"id":"mayor-juazeiro-do-norte", "name":"Glêdson Bezerra", "role":"Prefeito de Juazeiro do Norte", "party":"Podemos", "uf":"CE", "photo":"", "wiki_title_pt":"Glêdson Bezerra", "wiki_title_en":"Glêdson Bezerra"},
    # ── ESPÍRITO SANTO — INTERIOR ────────────────────────────────
    "Serra":                    {"id":"mayor-serra", "name":"Sergio Vidigal", "role":"Prefeito de Serra", "party":"PDT", "uf":"ES", "photo":"", "wiki_title_pt":"Sergio Vidigal", "wiki_title_en":"Sergio Vidigal"},
    # ── SANTA CATARINA — INTERIOR ────────────────────────────────
    "Blumenau":                 {"id":"mayor-blumenau", "name":"Mário Hildebrandt", "role":"Prefeito de Blumenau", "party":"PSD", "uf":"SC", "photo":"", "wiki_title_pt":"Mário Hildebrandt", "wiki_title_en":"Mário Hildebrandt"},
    # ── PARANÁ — INTERIOR ────────────────────────────────────────
    "Cascavel":                 {"id":"mayor-cascavel", "name":"Leonaldo Paranhos", "role":"Prefeito de Cascavel", "party":"PP", "uf":"PR", "photo":"", "wiki_title_pt":"Leonaldo Paranhos", "wiki_title_en":"Leonaldo Paranhos"},
    "Foz do Iguaçu":            {"id":"mayor-foz-do-iguacu", "name":"Chico Brasileiro", "role":"Prefeito de Foz do Iguaçu", "party":"PSD", "uf":"PR", "photo":"", "wiki_title_pt":"Chico Brasileiro", "wiki_title_en":"Chico Brasileiro"},
    # ── BAHIA — INTERIOR ─────────────────────────────────────────
    "Camaçari":                 {"id":"mayor-camacari", "name":"Mário Alexandre", "role":"Prefeito de Camaçari", "party":"PSD", "uf":"BA", "photo":"", "wiki_title_pt":"Mário Alexandre", "wiki_title_en":"Mário Alexandre"},
    "Vitória da Conquista":     {"id":"mayor-vitoria-da-conquista", "name":"Herzem Gusmão", "role":"Prefeito de Vitória da Conquista", "party":"MDB", "uf":"BA", "photo":"", "wiki_title_pt":"Herzem Gusmão", "wiki_title_en":"Herzem Gusmão"},
    # ── MATO GROSSO — INTERIOR ───────────────────────────────────
    "Rondonópolis":             {"id":"mayor-rondonopolis", "name":"Eduardo Botelho", "role":"Prefeito de Rondonópolis", "party":"União Brasil", "uf":"MT", "photo":"", "wiki_title_pt":"Eduardo Botelho", "wiki_title_en":"Eduardo Botelho"},
    # ── RIO GRANDE DO SUL — INTERIOR ─────────────────────────────
    "Canoas":                   {"id":"mayor-canoas", "name":"Jairo Jorge", "role":"Prefeito de Canoas", "party":"PSD", "uf":"RS", "photo":"", "wiki_title_pt":"Jairo Jorge", "wiki_title_en":"Jairo Jorge"},
    # ── RIO DE JANEIRO — INTERIOR ────────────────────────────────
    "São João de Meriti":       {"id":"mayor-sao-joao-de-meriti", "name":"Dr. João", "role":"Prefeito de São João de Meriti", "party":"Avante", "uf":"RJ", "photo":"", "wiki_title_pt":"Dr. João (São João de Meriti)", "wiki_title_en":"Dr. João"},
    "Belford Roxo":             {"id":"mayor-belford-roxo", "name":"Wagner dos Santos Carneiro", "role":"Prefeito de Belford Roxo", "party":"PL", "uf":"RJ", "photo":"", "wiki_title_pt":"Wagner Carneiro", "wiki_title_en":"Wagner Carneiro"},
}


_MAYORS_NORMALIZED: dict[str, str] = {
    _norm(k): k for k in MAYORS_BY_CITY
}


def get_mayor_data(city: str) -> dict | None:
    """Lookup no dict curado com tolerância a acentuação."""
    if not city:
        return None
    if city in MAYORS_BY_CITY:
        return MAYORS_BY_CITY[city]
    return MAYORS_BY_CITY.get(_MAYORS_NORMALIZED.get(_norm(city), ""))
