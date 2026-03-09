"""
For Glory — Portal da Transparência
Módulo: Fotos de Fallback Verificadas
"""
_FALLBACK_PHOTOS: dict[str, str] = {
    "Luiz Inácio Lula da Silva":        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/400px-Lula_-_foto_oficial_2023.jpg",
    "Geraldo Alckmin":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Geraldo_Alckmin_-_foto_oficial_2023.jpg/400px-Geraldo_Alckmin_-_foto_oficial_2023.jpg",
    "Luís Roberto Barroso":             "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg/400px-Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg",
    "Alexandre de Moraes":              "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Alexandre_de_Moraes_-_foto_oficial_2023.jpg/400px-Alexandre_de_Moraes_-_foto_oficial_2023.jpg",
    "Cármen Lúcia Antunes Rocha":       "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg/400px-C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg",
    "Cármen Lúcia":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg/400px-C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg",
    "Dias Toffoli":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Dias_Toffoli_%282023%29.jpg/400px-Dias_Toffoli_%282023%29.jpg",
    "Gilmar Ferreira Mendes":           "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/400px-Gilmar_Mendes_%282023%29.jpg",
    "Gilmar Mendes":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/400px-Gilmar_Mendes_%282023%29.jpg",
    "Edson Fachin":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Edson_Fachin_2023.jpg/400px-Edson_Fachin_2023.jpg",
    "André Mendonça (ministro)":        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Andr%C3%A9_Mendon%C3%A7a_2023.jpg/400px-Andr%C3%A9_Mendon%C3%A7a_2023.jpg",
    "André Mendonça":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Andr%C3%A9_Mendon%C3%A7a_2023.jpg/400px-Andr%C3%A9_Mendon%C3%A7a_2023.jpg",
    "Kassio Nunes Marques":             "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Kassio_Nunes_Marques_2023.jpg/400px-Kassio_Nunes_Marques_2023.jpg",
    "Flávio Dino":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg/400px-Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg",
    "Cristiano Zanin Martins":          "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Cristiano_Zanin_2023.jpg/400px-Cristiano_Zanin_2023.jpg",
    "Cristiano Zanin":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Cristiano_Zanin_2023.jpg/400px-Cristiano_Zanin_2023.jpg",
    "Jair Bolsonaro":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Jair_Bolsonaro_2019.jpg/400px-Jair_Bolsonaro_2019.jpg",
    "Tarcísio de Freitas":              "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Tarc%C3%ADsio_de_Freitas_-_foto_oficial_2022_%28cropped%29.jpg/400px-Tarc%C3%ADsio_de_Freitas_-_foto_oficial_2022_%28cropped%29.jpg",
    "Arthur Lira":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Arthur_Lira_-_foto_oficial_2023.jpg/400px-Arthur_Lira_-_foto_oficial_2023.jpg",
    "Rodrigo Pacheco":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Rodrigo_Pacheco_-_foto_oficial_2021.jpg/400px-Rodrigo_Pacheco_-_foto_oficial_2021.jpg",
    "Michel Temer":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Michel_Temer_-_foto_oficial_2016.jpg/400px-Michel_Temer_-_foto_oficial_2016.jpg",
    "Dilma Rousseff":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Dilma_Rousseff_-_foto_oficial_2011.jpg/400px-Dilma_Rousseff_-_foto_oficial_2011.jpg",
    "Romeu Zema":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Romeu_Zema_-_foto_oficial_2019.jpg/400px-Romeu_Zema_-_foto_oficial_2019.jpg",
    "Raquel Lyra":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Raquel_Lyra_-_foto_oficial_2023.jpg/400px-Raquel_Lyra_-_foto_oficial_2023.jpg",
    "Helder Barbalho":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Helder_Barbalho_-_foto_oficial_2019.jpg/400px-Helder_Barbalho_-_foto_oficial_2019.jpg",
    "Eduardo Leite (político)":         "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Eduardo_Leite_-_foto_oficial_2023.jpg/400px-Eduardo_Leite_-_foto_oficial_2023.jpg",
}
