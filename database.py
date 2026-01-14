import json
import os
from models import Turma, Professor, Disciplina, Sala, Aula

# Arquivo de database
DB_FILE = "escola_database.json"

def criar_dados_iniciais():
    """Cria dados iniciais para teste"""
    
    # ✅ CORREÇÃO: Professores com nomes EXATOS das disciplinas e grupo AMBOS
    professores = [
        Professor("Heliana", ["Português A", "Português B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Deise", ["Português A", "Português B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Loide", ["Português A", "Português B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Tatiane", ["Matemática A", "Matemática B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Ricardo", ["Matemática A", "Matemática B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Laís", ["História A", "História B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Waldemar", ["História A", "História B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Rene", ["Geografia A", "Geografia B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Vladmir", ["Química A", "Química B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Zabuor", ["Química A", "Química B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Gisele", ["Geografia A", "Geografia B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Marina", ["Biologia A", "Biologia B", "Ciências A", "Ciências B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Santiago", ["Matemática A EF_II", "Matemática B EF_II","Matemática A EM", "Matemática B EM"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Andréia Lucia", ["Matemática A", "Matemática B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("César", ["Informática A", "Informática B", "Física A", "Física B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Anna Maria", ["Filosofia A", "Filosofia B", "Sociologia A", "Sociologia B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Marcão", ["Educação Física A", "Educação Física B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Andréia", ["Educação Física A", "Educação Física B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Vanessa", ["Arte A", "Arte B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Maria Luiza", ["Inglês A", "Inglês B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
        Professor("Andréia Barreto", ["Dinâmica A", "Dinâmica B", "Vida Pratica A", "Vida Pratica B"], {"segunda", "terca", "quarta", "quinta", "sexta"}, "AMBOS"),
    ]
    
    # ✅ CORREÇÃO: Turmas com segmento correto
    turmas = [
        Turma("6anoA", "6ano", "manha", "A", "EF_II"),
        Turma("7anoA", "7ano", "manha", "A", "EF_II"),
        Turma("8anoA", "8ano", "manha", "A", "EF_II"),
        Turma("9anoA", "9ano", "manha", "A", "EF_II"),
        Turma("1emA", "1em", "manha", "A", "EM"),
        Turma("2emA", "2em", "manha", "A", "EM"),
        Turma("3emA", "3em", "manha", "A", "EM"),
        Turma("6anoB", "6ano", "manha", "B", "EF_II"),
        Turma("7anoB", "7ano", "manha", "B", "EF_II"),
        Turma("8anoB", "8ano", "manha", "B", "EF_II"),
        Turma("9anoB", "9ano", "manha", "B", "EF_II"),
        Turma("1emB", "1em", "manha", "B", "EM"),
        Turma("2emB", "2em", "manha", "B", "EM"),
        Turma("3emB", "3em", "manha", "B", "EM"),
    ]
    
    # ✅ CORREÇÃO: Disciplinas vinculadas às turmas específicas
    disciplinas = [
        # GRUPO A - TURMAS A
        Disciplina("Português A", 5, "pesada", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Matemática A EF_II", 4, "pesada", ["6anoA", "7anoA", "8anoA", "9anoA" ], "A"),
        Disciplina("Matemática A EM", 5, "pesada", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("História A", 2, "media", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Geografia A", 2, "media", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Ciências A", 2, "media", ["6anoA", "7anoA", "8anoA", "9anoA"], "A"),
        Disciplina("Biologia A", 3, "media", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("Física A", 3, "pesada", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("Química A", 3, "pesada", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("Inglês A", 2, "leve", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Arte A", 2, "leve", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Educação Física A", 2, "pratica", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Filosofia A", 2, "media", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("Sociologia A", 2, "media", ["1emA", "2emA", "3emA"], "A"),
        Disciplina("Informática A", 2, "leve", ["6anoA", "7anoA", "8anoA", "9anoA", "1emA", "2emA", "3emA"], "A"),
        Disciplina("Dinâmica A", 1, "leve", ["6anoA", "7anoA", "8anoA", "9anoA"], "A"),
        Disciplina("Vida Pratica A", 1, "leve", ["6anoA", "7anoA", "8anoA", "9anoA"], "A"),
        
        # GRUPO B - TURMAS B
        Disciplina("Português B", 5, "pesada", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Matemática B", 5, "pesada", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Matemática B", 4, "pesada", ["6anoB", "7anoB", "8anoB", "9anoB"], "B"),
        Disciplina("História B", 2, "media", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Geografia B", 2, "media", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Ciências B", 2, "media", ["6anoB", "7anoB", "8anoB", "9anoB"], "B"),
        Disciplina("Biologia B", 3, "media", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Física B", 3, "pesada", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Química B", 3, "pesada", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Inglês B", 2, "leve", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Arte B", 2, "leve", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Educação Física B", 2, "pratica", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Filosofia B", 2, "media", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Sociologia B", 2, "media", ["1emB", "2emB", "3emB"], "B"),
        Disciplina("Informática B", 2, "leve", ["6anoB", "7anoB", "8anoB", "9anoB", "1emB", "2emB", "3emB"], "B"),
        Disciplina("Dinâmica B", 1, "leve", ["6anoB", "7anoB", "8anoB", "9anoB"], "B"),
        Disciplina("Vida Pratica B", 1, "leve", ["6anoB", "7anoB", "8anoB", "9anoB"], "B"),
    ]

    
    salas = [
        Sala("Sala 1", 30, "normal"),
        Sala("Sala 2", 30, "normal"),
        Sala("Sala 3", 30, "normal"),
        Sala("Sala 4", 30, "normal"),
        Sala("Sala 5", 30, "normal"),
        Sala("Sala 6", 30, "normal"),
        Sala("Sala 7", 30, "normal"),
        Sala("Sala 8", 30, "normal"),
        Sala("Sala 9", 30, "normal"),
        Sala("Sala 10", 30, "normal"),
        Sala("Sala 11", 30, "normal"),
        Sala("Sala 12", 30, "normal"),
        Sala("Sala 13", 30, "normal"),
        Sala("Sala 14", 30, "normal"),
        Sala("Laboratório de Ciências", 25, "laboratório"),
        Sala("Auditório", 100, "auditório"),
    ]
    
    return {
        "professores": [p.__dict__ for p in professores],
        "disciplinas": [d.__dict__ for d in disciplinas],
        "turmas": [t.__dict__ for t in turmas],
        "salas": [s.__dict__ for s in salas],
        "aulas": [],
        "feriados": [],
        "periodos": []
    }

def init_db():
    """Inicializa o banco de dados com dados padrão se não existir"""
    if not os.path.exists(DB_FILE):
        dados_iniciais = criar_dados_iniciais()
        salvar_tudo(dados_iniciais)

def carregar_tudo():
    """Carrega todos os dados do banco"""
    if not os.path.exists(DB_FILE):
        init_db()
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return criar_dados_iniciais()

def salvar_tudo(dados):
    """Salva todos os dados no banco"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return False

# Funções de carregamento
def carregar_turmas():
    dados = carregar_tudo()
    turmas = dados.get("turmas", [])
    resultado = []
    
    for item in turmas:
        if isinstance(item, dict):
            resultado.append(Turma(**item))
        elif hasattr(item, 'nome') and hasattr(item, 'serie'):
            resultado.append(item)
        else:
            print(f"Item inválido em turmas: {item}")
    
    return resultado

def carregar_professores():
    dados = carregar_tudo()
    professores = dados.get("professores", [])
    resultado = []
    
    for item in professores:
        if isinstance(item, dict):
            resultado.append(Professor(**item))
        elif hasattr(item, 'nome') and hasattr(item, 'disciplinas'):
            resultado.append(item)
        else:
            print(f"Item inválido em professores: {item}")
    
    return resultado

def carregar_disciplinas():
    dados = carregar_tudo()
    disciplinas = dados.get("disciplinas", [])
    resultado = []
    
    for item in disciplinas:
        if isinstance(item, dict):
            resultado.append(Disciplina(**item))
        elif hasattr(item, 'nome') and hasattr(item, 'carga_semanal'):
            resultado.append(item)
        else:
            print(f"Item inválido em disciplinas: {item}")
    
    return resultado

def carregar_salas():
    dados = carregar_tudo()
    salas = dados.get("salas", [])
    resultado = []
    
    for item in salas:
        if isinstance(item, dict):
            resultado.append(Sala(**item))
        elif hasattr(item, 'nome') and hasattr(item, 'capacidade'):
            resultado.append(item)
        else:
            print(f"Item inválido em salas: {item}")
    
    return resultado

def carregar_grade():
    dados = carregar_tudo()
    aulas = dados.get("aulas", [])
    resultado = []
    
    for item in aulas:
        if isinstance(item, dict):
            resultado.append(Aula(**item))
        elif hasattr(item, 'turma') and hasattr(item, 'disciplina'):
            resultado.append(item)
        else:
            print(f"Item inválido em aulas: {item}")
    
    return resultado

def carregar_feriados():
    dados = carregar_tudo()
    return dados.get("feriados", [])

def carregar_periodos():
    dados = carregar_tudo()
    return dados.get("periodos", [])

# Funções de salvamento
def _converter_para_dict(obj):
    """Converte objeto para dicionário se for um objeto models"""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return obj

def salvar_turmas(turmas):
    dados = carregar_tudo()
    dados["turmas"] = [_converter_para_dict(t) for t in turmas]
    return salvar_tudo(dados)

def salvar_professores(professores):
    dados = carregar_tudo()
    dados["professores"] = [_converter_para_dict(p) for p in professores]
    return salvar_tudo(dados)

def salvar_disciplinas(disciplinas):
    dados = carregar_tudo()
    dados["disciplinas"] = [_converter_para_dict(d) for d in disciplinas]
    return salvar_tudo(dados)

def salvar_salas(salas):
    dados = carregar_tudo()
    dados["salas"] = [_converter_para_dict(s) for s in salas]
    return salvar_tudo(dados)

def salvar_grade(aulas):
    dados = carregar_tudo()
    dados["aulas"] = [_converter_para_dict(a) for a in aulas]
    return salvar_tudo(dados)

def salvar_feriados(feriados):
    dados = carregar_tudo()
    dados["feriados"] = feriados
    return salvar_tudo(dados)

def salvar_periodos(periodos):
    dados = carregar_tudo()
    dados["periodos"] = periodos
    return salvar_tudo(dados)

def resetar_banco():
    """Reseta o banco de dados para os valores iniciais"""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()
    return True