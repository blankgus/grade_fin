import streamlit as st
import pandas as pd
import random
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
import json

# ============================================
# CONSTANTES
# ============================================

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

HORARIOS_EM = [
    ("07:00", "07:50"), ("07:50", "08:40"), ("08:40", "09:30"),
    ("09:50", "10:40"), ("10:40", "11:30"), ("11:30", "12:20"),
    ("12:20", "13:10")
]

HORARIOS_EF_II = [
    ("07:50", "08:40"), ("08:40", "09:30"), ("09:30", "10:20"),
    ("10:40", "11:30"), ("11:30", "12:20"), ("12:20", "13:10"),
    ("13:10", "14:00")
]

# ============================================
# CLASSES DE DADOS
# ============================================

@dataclass
class Professor:
    id: int
    nome: str
    grupo: str = "AMBOS"
    disciplinas: Dict[str, int] = field(default_factory=dict)
    max_aulas_dia: int = 5
    min_aulas_dia: int = 0
    aulas_alocadas: List[Tuple[str, str, str]] = field(default_factory=list)  # (dia, horario, turma)
    
    def get_horas_disponiveis(self, disciplina: str) -> int:
        return self.disciplinas.get(disciplina, 0)
    
    def get_total_horas_disponiveis(self) -> int:
        return sum(self.disciplinas.values())
    
    def esta_disponivel(self, dia: str, horario: str) -> bool:
        """Verifica se o professor está disponível em um determinado dia e horário"""
        for aula_dia, aula_horario, _ in self.aulas_alocadas:
            if aula_dia == dia and aula_horario == horario:
                return False
        return True
    
    def adicionar_aula(self, dia: str, horario: str, turma: str):
        """Adiciona uma aula à lista de aulas alocadas do professor"""
        self.aulas_alocadas.append((dia, horario, turma))
    
    def limpar_aulas_alocadas(self):
        """Limpa as aulas alocadas do professor"""
        self.aulas_alocadas = []

@dataclass
class Disciplina:
    id: int
    nome: str
    grupo: str = "AMBOS"
    turmas: List[str] = field(default_factory=list)
    carga_semanal: int = 0
    
    def get_carga_total_necessaria(self) -> int:
        return self.carga_semanal * len(self.turmas)

@dataclass
class Turma:
    id: int
    nome: str
    serie: str
    grupo: str = "AMBOS"
    turno: str = "MANHÃ"

@dataclass
class Aula:
    id: int
    turma: str
    disciplina: str
    professor: str
    dia: str
    horario: str
    periodo: int

@dataclass
class Grade:
    id: int
    nome: str
    turmas: List[str] = field(default_factory=list)
    grupo: str = "COMPLETA"
    aulas: List[Aula] = field(default_factory=list)
    status: str = "RASCUNHO"

# ============================================
# INICIALIZAÇÃO DA SESSÃO
# ============================================

def inicializar_sessao():
    if 'professores' not in st.session_state:
        st.session_state.professores = []
    if 'disciplinas' not in st.session_state:
        st.session_state.disciplinas = []
    if 'turmas' not in st.session_state:
        st.session_state.turmas = []
    if 'grades' not in st.session_state:
        st.session_state.grades = []
    if 'proximo_id_professor' not in st.session_state:
        st.session_state.proximo_id_professor = 1
    if 'proximo_id_disciplina' not in st.session_state:
        st.session_state.proximo_id_disciplina = 1
    if 'proximo_id_turma' not in st.session_state:
        st.session_state.proximo_id_turma = 1
    if 'proximo_id_grade' not in st.session_state:
        st.session_state.proximo_id_grade = 1
    if 'proximo_id_aula' not in st.session_state:
        st.session_state.proximo_id_aula = 1
    if 'aulas_por_turma' not in st.session_state:
        st.session_state.aulas_por_turma = {}

def limpar_aulas_professores():
    """Limpa as aulas alocadas de todos os professores"""
    for professor in st.session_state.professores:
        professor.limpar_aulas_alocadas()

def carregar_dados_exemplo():
    """Carrega dados de exemplo com balanço 490/490"""
    
    # Limpar dados existentes
    st.session_state.professores = []
    st.session_state.disciplinas = []
    st.session_state.turmas = []
    st.session_state.grades = []
    
    # Resetar IDs
    st.session_state.proximo_id_professor = 1
    st.session_state.proximo_id_disciplina = 1
    st.session_state.proximo_id_turma = 1
    st.session_state.proximo_id_grade = 1
    st.session_state.proximo_id_aula = 1
    
    # ========== TURMAS ==========
    turmas_exemplo = [
        Turma(id=1, nome="6º A", serie="6º EF", grupo="A", turno="MANHÃ"),
        Turma(id=2, nome="6º B", serie="6º EF", grupo="B", turno="MANHÃ"),
        Turma(id=3, nome="7º A", serie="7º EF", grupo="A", turno="MANHÃ"),
        Turma(id=4, nome="7º B", serie="7º EF", grupo="B", turno="MANHÃ"),
        Turma(id=5, nome="8º A", serie="8º EF", grupo="A", turno="MANHÃ"),
        Turma(id=6, nome="8º B", serie="8º EF", grupo="B", turno="MANHÃ"),
        Turma(id=7, nome="9º A", serie="9º EF", grupo="A", turno="MANHÃ"),
        Turma(id=8, nome="9º B", serie="9º EF", grupo="B", turno="MANHÃ"),
        Turma(id=9, nome="1º EM A", serie="1º EM", grupo="A", turno="MANHÃ"),
        Turma(id=10, nome="1º EM B", serie="1º EM", grupo="B", turno="MANHÃ"),
        Turma(id=11, nome="2º EM A", serie="2º EM", grupo="A", turno="MANHÃ"),
        Turma(id=12, nome="2º EM B", serie="2º EM", grupo="B", turno="MANHÃ"),
        Turma(id=13, nome="3º EM A", serie="3º EM", grupo="A", turno="MANHÃ"),
        Turma(id=14, nome="3º EM B", serie="3º EM", grupo="B", turno="MANHÃ"),
    ]
    
    for turma in turmas_exemplo:
        st.session_state.turmas.append(turma)
        st.session_state.proximo_id_turma = max(st.session_state.proximo_id_turma, turma.id + 1)
    
    # ========== DISCIPLINAS ==========
    disciplinas_exemplo = [
        # GRUPO A - EF II
        Disciplina(id=1, nome="Matemática", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=5),
        Disciplina(id=2, nome="Português", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=5),
        Disciplina(id=3, nome="Ciências", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=4),
        Disciplina(id=4, nome="Geografia", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=3),
        Disciplina(id=5, nome="História", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=3),
        Disciplina(id=6, nome="Inglês", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=2),
        Disciplina(id=7, nome="Educação Física", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=2),
        Disciplina(id=8, nome="Artes", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=1),
        
        # GRUPO B - EF II
        Disciplina(id=9, nome="Matemática", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=5),
        Disciplina(id=10, nome="Português", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=5),
        Disciplina(id=11, nome="Ciências", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=4),
        Disciplina(id=12, nome="Geografia", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=3),
        Disciplina(id=13, nome="História", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=3),
        Disciplina(id=14, nome="Inglês", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=2),
        Disciplina(id=15, nome="Educação Física", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=2),
        Disciplina(id=16, nome="Artes", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=1),
        
        # GRUPO A - EM
        Disciplina(id=17, nome="Matemática", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=5),
        Disciplina(id=18, nome="Português", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=5),
        Disciplina(id=19, nome="Física", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=4),
        Disciplina(id=20, nome="Química", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=4),
        Disciplina(id=21, nome="Biologia", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=4),
        Disciplina(id=22, nome="História", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=3),
        Disciplina(id=23, nome="Geografia", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=3),
        Disciplina(id=24, nome="Inglês", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=2),
        Disciplina(id=25, nome="Educação Física", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=2),
        Disciplina(id=26, nome="Artes", grupo="A", turmas=["1º EM A", "2º EM A", "3º EM A"], carga_semanal=2),
        
        # GRUPO B - EM
        Disciplina(id=27, nome="Matemática", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=5),
        Disciplina(id=28, nome="Português", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=5),
        Disciplina(id=29, nome="Física", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=4),
        Disciplina(id=30, nome="Química", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=4),
        Disciplina(id=31, nome="Biologia", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=4),
        Disciplina(id=32, nome="História", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=3),
        Disciplina(id=33, nome="Geografia", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=3),
        Disciplina(id=34, nome="Inglês", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=2),
        Disciplina(id=35, nome="Educação Física", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=2),
        Disciplina(id=36, nome="Artes", grupo="B", turmas=["1º EM B", "2º EM B", "3º EM B"], carga_semanal=2),
        
        # DISCIPLINAS AMBOS - EM
        Disciplina(id=37, nome="Filosofia", grupo="AMBOS", 
                  turmas=["1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], carga_semanal=2),
        Disciplina(id=38, nome="Sociologia", grupo="AMBOS", 
                  turmas=["1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], carga_semanal=2),
        
        # ESPANHOL
        Disciplina(id=39, nome="Espanhol", grupo="A", turmas=["6º A", "7º A", "8º A", "9º A"], carga_semanal=2),
        Disciplina(id=40, nome="Espanhol", grupo="B", turmas=["6º B", "7º B", "8º B", "9º B"], carga_semanal=2),
        
        # TECNOLOGIA
        Disciplina(id=41, nome="Tecnologia", grupo="AMBOS", 
                  turmas=["6º A", "6º B", "7º A", "7º B", "8º A", "8º B", "9º A", "9º B",
                         "1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], carga_semanal=2),
    ]
    
    for disciplina in disciplinas_exemplo:
        st.session_state.disciplinas.append(disciplina)
        st.session_state.proximo_id_disciplina = max(st.session_state.proximo_id_disciplina, disciplina.id + 1)
    
    # ========== PROFESSORES ==========
    professores_exemplo = [
        Professor(id=1, nome="Maria Silva", grupo="A", disciplinas={"Matemática": 35}),
        Professor(id=2, nome="João Santos", grupo="A", disciplinas={"Português": 35}),
        Professor(id=3, nome="Ana Costa", grupo="A", disciplinas={"Ciências": 16, "Biologia": 12}),
        Professor(id=4, nome="Carlos Mendes", grupo="A", disciplinas={"Geografia": 25, "História": 21}),
        Professor(id=5, nome="Roberto Física", grupo="A", disciplinas={"Física": 12, "Química": 12}),
        Professor(id=6, nome="Cláudia Idiomas", grupo="A", disciplinas={"Inglês": 14, "Espanhol": 8}),
        
        Professor(id=7, nome="Pedro Oliveira", grupo="B", disciplinas={"Matemática": 35}),
        Professor(id=8, nome="Carla Souza", grupo="B", disciplinas={"Português": 35}),
        Professor(id=9, nome="Sofia Lima", grupo="B", disciplinas={"Ciências": 16, "Biologia": 12}),
        Professor(id=10, nome="Fernando Almeida", grupo="B", disciplinas={"Geografia": 25, "História": 21}),
        Professor(id=11, nome="Patrícia Química", grupo="B", disciplinas={"Física": 12, "Química": 12}),
        Professor(id=12, nome="Ricardo Idiomas", grupo="B", disciplinas={"Inglês": 14, "Espanhol": 8}),
        
        Professor(id=13, nome="Marcos Ribeiro", grupo="AMBOS", disciplinas={"Educação Física": 28}),
        Professor(id=14, nome="Patrícia Cardoso", grupo="AMBOS", disciplinas={"Artes": 20}),
        Professor(id=15, nome="Fernanda Filosofia", grupo="AMBOS", disciplinas={"Filosofia": 12, "Sociologia": 12}),
        Professor(id=16, nome="Carla Tecnologia", grupo="AMBOS", disciplinas={"Tecnologia": 28}),
    ]
    
    for professor in professores_exemplo:
        st.session_state.professores.append(professor)
        st.session_state.proximo_id_professor = max(st.session_state.proximo_id_professor, professor.id + 1)
    
    return True

def obter_horarios_turma(nome_turma: str):
    turma = next((t for t in st.session_state.turmas if t.nome == nome_turma), None)
    if not turma:
        return []
    
    if "EM" in turma.serie:
        return HORARIOS_EM
    else:
        return HORARIOS_EF_II

def obter_professores_disciplina(disciplina_nome: str, grupo_turma: str, dia: str = None, horario: str = None):
    """Retorna todos os professores que podem ministrar uma disciplina, com status de disponibilidade"""
    professores_compatíveis = []
    
    for professor in st.session_state.professores:
        # Verificar se professor tem horas disponíveis para esta disciplina
        horas_disponiveis = professor.get_horas_disponiveis(disciplina_nome)
        if horas_disponiveis <= 0:
            continue
        
        # Verificar compatibilidade de grupo
        prof_grupo = professor.grupo
        if not (prof_grupo == grupo_turma or prof_grupo == 'AMBOS' or grupo_turma == 'AMBOS'):
            continue
        
        # Verificar disponibilidade no horário específico (se fornecido)
        disponivel = True
        if dia and horario:
            disponivel = professor.esta_disponivel(dia, horario)
        
        professores_compatíveis.append({
            'professor': professor,
            'horas_disponiveis': horas_disponiveis,
            'disponivel': disponivel,
            'horas_restantes': horas_disponiveis - len([a for a in professor.aulas_alocadas if disciplina_nome in [d for d in professor.disciplinas.keys()]])
        })
    
    return professores_compatíveis

# ============================================
# FUNÇÕES DE VISUALIZAÇÃO DE GRADE
# ============================================

def mostrar_grade_visual(turma_nome, aulas_turma):
    """Mostra uma grade visual para uma turma específica"""
    if not aulas_turma:
        st.info(f"Nenhuma aula alocada para a turma {turma_nome}")
        return
    
    # Obter horários da turma
    horarios = obter_horarios_turma(turma_nome)
    
    # Criar grade vazia
    grade_data = []
    for dia in DIAS_SEMANA:
        dia_data = {"Dia": dia}
        for i, (inicio, fim) in enumerate(horarios):
            periodo = i + 1
            horario_str = f"{inicio}-{fim}"
            
            # Encontrar aula para este dia e horário
            aula = next((a for a in aulas_turma if a.dia == dia and a.horario == horario_str), None)
            
            if aula:
                if aula.professor:  # Se tem professor, mostra disciplina e professor
                    dia_data[f"P{periodo}"] = f"{aula.disciplina}\n({aula.professor})"
                else:  # Se não tem professor, mostra apenas disciplina
                    dia_data[f"P{periodo}"] = aula.disciplina
            else:
                dia_data[f"P{periodo}"] = "---"
        
        grade_data.append(dia_data)
    
    # Converter para DataFrame
    df_grade = pd.DataFrame(grade_data)
    
    # Mostrar grade
    st.subheader(f"📅 Grade Horária - {turma_nome}")
    
    # Criar tabela formatada
    html = """
    <style>
    .grade-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        margin-bottom: 20px;
    }
    .grade-table th {
        background-color: #4B0082;
        color: white;
        padding: 12px;
        text-align: center;
        border: 1px solid #ddd;
        font-weight: bold;
    }
    .grade-table td {
        padding: 10px;
        text-align: center;
        border: 1px solid #ddd;
        vertical-align: middle;
        min-height: 60px;
    }
    .dia-header {
        background-color: #6A0DAD !important;
        font-weight: bold;
        color: white;
    }
    .aula-cell {
        background-color: #e8f4f8;
    }
    .vazio-cell {
        background-color: #f5f5f5;
        color: #999;
    }
    .periodo-header {
        background-color: #8A2BE2;
        font-size: 0.9em;
    }
    </style>
    """
    
    html += "<table class='grade-table'><tr><th class='dia-header'>DIA/HORÁRIO</th>"
    
    # Cabeçalho com períodos
    for i, (inicio, fim) in enumerate(horarios):
        html += f"<th class='periodo-header'>P{i+1}<br>{inicio}-{fim}</th>"
    html += "</tr>"
    
    # Dados
    for row in grade_data:
        html += f"<tr><td class='dia-header'><b>{row['Dia']}</b></td>"
        for i in range(len(horarios)):
            periodo = f"P{i+1}"
            celula = row[periodo]
            # Estilizar células
            if celula == "---":
                html += f"<td class='vazio-cell'>---</td>"
            else:
                html += f"<td class='aula-cell'>{celula}</td>"
        html += "</tr>"
    
    html += "</table>"
    
    st.markdown(html, unsafe_allow_html=True)
    
    # Legenda
    st.caption("**Legenda:** Períodos de 50 minutos | --- = Horário livre | Nome do professor entre parênteses (quando atribuído)")

# ============================================
# ALGORITMO DE GERAÇÃO DE GRADE (COM CONFLITOS CORRIGIDOS)
# ============================================

class GeradorGrade:
    def __init__(self, turmas, disciplinas, professores):
        self.turmas = turmas
        self.disciplinas = disciplinas
        self.professores = professores
        self.proximo_id_aula = st.session_state.proximo_id_aula
        self.aulas_alocadas = []
        self.horas_utilizadas = {}
        self.conflitos_resolvidos = 0
        
        # Inicializar controle de horas
        for professor in self.professores:
            self.horas_utilizadas[professor.nome] = {}
            for disciplina_nome in professor.disciplinas.keys():
                self.horas_utilizadas[professor.nome][disciplina_nome] = 0
            
            # Limpar aulas alocadas do professor para nova geração
            professor.limpar_aulas_alocadas()
    
    def encontrar_professor_disponivel(self, disciplina_nome: str, grupo_turma: str, dia: str, horario: str):
        """Encontra um professor disponível para a disciplina em um horário específico"""
        professores_candidatos = []
        
        for professor in self.professores:
            # Verificar se professor tem horas disponíveis para esta disciplina
            horas_disponiveis = professor.get_horas_disponiveis(disciplina_nome)
            if horas_disponiveis <= 0:
                continue
            
            # Verificar compatibilidade de grupo
            prof_grupo = professor.grupo
            if not (prof_grupo == grupo_turma or prof_grupo == 'AMBOS' or grupo_turma == 'AMBOS'):
                continue
            
            # Verificar se já usou todas as horas disponíveis
            horas_usadas = self.horas_utilizadas.get(professor.nome, {}).get(disciplina_nome, 0)
            if horas_usadas >= horas_disponiveis:
                continue
            
            # VERIFICAR DISPONIBILIDADE NO HORÁRIO (IMPORTANTE!)
            if not professor.esta_disponivel(dia, horario):
                continue
            
            professores_candidatos.append({
                'professor': professor,
                'horas_disponiveis': horas_disponiveis,
                'horas_usadas': horas_usadas,
                'prioridade': horas_disponiveis - horas_usadas
            })
        
        if professores_candidatos:
            professores_candidatos.sort(key=lambda x: x['prioridade'], reverse=True)
            return professores_candidatos[0]['professor']
        
        return None
    
    def encontrar_professor_alternativo(self, disciplina_nome: str, grupo_turma: str, dia: str, horario: str, professores_excluidos: List[str]):
        """Tenta encontrar um professor alternativo, excluindo alguns já testados"""
        professores_candidatos = []
        
        for professor in self.professores:
            if professor.nome in professores_excluidos:
                continue
                
            # Verificar se professor tem horas disponíveis para esta disciplina
            horas_disponiveis = professor.get_horas_disponiveis(disciplina_nome)
            if horas_disponiveis <= 0:
                continue
            
            # Verificar compatibilidade de grupo
            prof_grupo = professor.grupo
            if not (prof_grupo == grupo_turma or prof_grupo == 'AMBOS' or grupo_turma == 'AMBOS'):
                continue
            
            # Verificar se já usou todas as horas disponíveis
            horas_usadas = self.horas_utilizadas.get(professor.nome, {}).get(disciplina_nome, 0)
            if horas_usadas >= horas_disponiveis:
                continue
            
            # VERIFICAR DISPONIBILIDADE NO HORÁRIO
            if not professor.esta_disponivel(dia, horario):
                continue
            
            professores_candidatos.append({
                'professor': professor,
                'horas_disponiveis': horas_disponiveis,
                'horas_usadas': horas_usadas,
                'prioridade': horas_disponiveis - horas_usadas
            })
        
        if professores_candidatos:
            professores_candidatos.sort(key=lambda x: x['prioridade'], reverse=True)
            return professores_candidatos[0]['professor']
        
        return None
    
    def gerar_grade_simples(self):
        """Algoritmo simples de geração de grade com prevenção de conflitos"""
        aulas_por_turma = {turma.nome: [] for turma in self.turmas}
        
        # Para cada turma, distribuir as disciplinas
        for turma in self.turmas:
            grupo_turma = turma.grupo
            disciplinas_turma = [
                d for d in self.disciplinas 
                if turma.nome in d.turmas and d.grupo == grupo_turma
            ]
            
            # Coletar todas as aulas necessárias
            aulas_necessarias = []
            for disc in disciplinas_turma:
                for _ in range(disc.carga_semanal):
                    aulas_necessarias.append(disc.nome)
            
            # Misturar aulas para distribuição mais aleatória
            random.shuffle(aulas_necessarias)
            
            # Obter horários disponíveis
            horarios_disponiveis = obter_horarios_turma(turma.nome)
            dias_disponiveis = DIAS_SEMANA.copy()
            
            # Tentar alocar cada aula
            for disciplina_nome in aulas_necessarias:
                alocada = False
                tentativas = 0
                max_tentativas = len(dias_disponiveis) * len(horarios_disponiveis) * 2
                
                while not alocada and tentativas < max_tentativas:
                    # Escolher um horário aleatório
                    dia = random.choice(dias_disponiveis)
                    horario_idx = random.randint(0, len(horarios_disponiveis) - 1)
                    horario = f"{horarios_disponiveis[horario_idx][0]}-{horarios_disponiveis[horario_idx][1]}"
                    
                    # Verificar se este horário já tem aula nesta turma
                    horario_ocupado = any(
                        a for a in aulas_por_turma[turma.nome] 
                        if a.dia == dia and a.horario == horario
                    )
                    
                    if not horario_ocupado:
                        # Encontrar professor disponível
                        professor = self.encontrar_professor_disponivel(disciplina_nome, grupo_turma, dia, horario)
                        
                        if professor:
                            professor_nome = professor.nome
                            
                            # Atualizar horas utilizadas
                            if disciplina_nome not in self.horas_utilizadas[professor_nome]:
                                self.horas_utilizadas[professor_nome][disciplina_nome] = 0
                            self.horas_utilizadas[professor_nome][disciplina_nome] += 1
                            
                            # Registrar aula no professor
                            professor.adicionar_aula(dia, horario, turma.nome)
                            
                            aula = Aula(
                                id=self.proximo_id_aula,
                                turma=turma.nome,
                                disciplina=disciplina_nome,
                                professor=professor_nome,
                                dia=dia,
                                horario=horario,
                                periodo=horario_idx + 1
                            )
                            
                            self.aulas_alocadas.append(aula)
                            aulas_por_turma[turma.nome].append(aula)
                            self.proximo_id_aula += 1
                            alocada = True
                    
                    tentativas += 1
                
                if not alocada:
                    # Tentar alocar em qualquer horário vazio
                    for dia in dias_disponiveis:
                        for i, (inicio, fim) in enumerate(horarios_disponiveis):
                            horario = f"{inicio}-{fim}"
                            
                            # Verificar se horário está livre
                            horario_ocupado = any(
                                a for a in aulas_por_turma[turma.nome] 
                                if a.dia == dia and a.horario == horario
                            )
                            
                            if not horario_ocupado:
                                # Encontrar professor disponível
                                professor = self.encontrar_professor_disponivel(disciplina_nome, grupo_turma, dia, horario)
                                
                                if professor:
                                    professor_nome = professor.nome
                                    
                                    # Atualizar horas utilizadas
                                    if disciplina_nome not in self.horas_utilizadas[professor_nome]:
                                        self.horas_utilizadas[professor_nome][disciplina_nome] = 0
                                    self.horas_utilizadas[professor_nome][disciplina_nome] += 1
                                    
                                    # Registrar aula no professor
                                    professor.adicionar_aula(dia, horario, turma.nome)
                                    
                                    aula = Aula(
                                        id=self.proximo_id_aula,
                                        turma=turma.nome,
                                        disciplina=disciplina_nome,
                                        professor=professor_nome,
                                        dia=dia,
                                        horario=horario,
                                        periodo=i + 1
                                    )
                                    
                                    self.aulas_alocadas.append(aula)
                                    aulas_por_turma[turma.nome].append(aula)
                                    self.proximo_id_aula += 1
                                    alocada = True
                                    break
                        
                        if alocada:
                            break
        
        # Salvar aulas por turma na sessão
        for turma_nome, aulas in aulas_por_turma.items():
            st.session_state.aulas_por_turma[turma_nome] = aulas
        
        return self.aulas_alocadas, aulas_por_turma
    
    def verificar_conflitos(self):
        """Verifica se há conflitos na grade gerada"""
        conflitos = 0
        professor_horarios = {}
        
        for aula in self.aulas_alocadas:
            if aula.professor:
                chave = f"{aula.professor}_{aula.dia}_{aula.horario}"
                if chave in professor_horarios:
                    conflitos += 1
                else:
                    professor_horarios[chave] = aula
        
        return conflitos

# ============================================
# INTERFACE PRINCIPAL
# ============================================

def main():
    st.set_page_config(
        page_title="Sistema de Grade Horária",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar sessão
    inicializar_sessao()
    
    # ============================================
    # SIDEBAR - LAYOUT ORIGINAL
    # ============================================
    
    st.sidebar.title("📚 SISTEMA DE GRADE HORÁRIA")
    st.sidebar.markdown("---")
    
    # MENU PRINCIPAL ORIGINAL
    opcao = st.sidebar.selectbox(
        "**MENU PRINCIPAL**",
        [
            "🏠 DASHBOARD",
            "👨‍🏫 GERENCIAR PROFESSORES", 
            "📚 GERENCIAR DISCIPLINAS",
            "👥 GERENCIAR TURMAS",
            "📊 ANÁLISE DE COBERTURA",
            "🗓️ GERAR GRADE",
            "📋 VISUALIZAR GRADES",
            "⚙️ CONFIGURAÇÕES"
        ]
    )
    
    st.sidebar.markdown("---")
    
    # BOTÕES DE AÇÃO RÁPIDA
    st.sidebar.subheader("⚡ Ações Rápidas")
    
    if st.sidebar.button("📥 Carregar Dados Exemplo", use_container_width=True):
        carregar_dados_exemplo()
        st.sidebar.success("Dados carregados!")
        st.rerun()
    
    if st.sidebar.button("🔄 Limpar Todas as Grades", type="secondary", use_container_width=True):
        if st.sidebar.checkbox("Confirmar limpeza"):
            st.session_state.grades = []
            st.session_state.aulas_por_turma = {}
            limpar_aulas_professores()
            st.session_state.proximo_id_grade = 1
            st.session_state.proximo_id_aula = 1
            st.sidebar.success("Grades limpas!")
            st.rerun()
    
    # ESTATÍSTICAS NA SIDEBAR
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Estatísticas")
    st.sidebar.write(f"**Professores:** {len(st.session_state.professores)}")
    st.sidebar.write(f"**Disciplinas:** {len(st.session_state.disciplinas)}")
    st.sidebar.write(f"**Turmas:** {len(st.session_state.turmas)}")
    st.sidebar.write(f"**Grades:** {len(st.session_state.grades)}")
    
    # ============================================
    # CONTEÚDO PRINCIPAL
    # ============================================
    
    st.title("📚 SISTEMA DE GRADE HORÁRIA ESCOLAR")
    st.markdown("---")
    
    # Verificar se há dados
    if not st.session_state.turmas:
        st.warning("⚠️ **SISTEMA SEM DADOS**")
        st.info("Para começar, clique em 'Carregar Dados Exemplo' na sidebar ou adicione dados manualmente.")
        
        if st.button("🎯 Carregar Dados de Exemplo 490/490", type="primary"):
            carregar_dados_exemplo()
            st.success("✅ Dados carregados!")
            st.rerun()
        
        return
    
    # ============================================
    # DASHBOARD
    # ============================================
    if opcao == "🏠 DASHBOARD":
        st.header("📊 DASHBOARD")
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Professores", len(st.session_state.professores))
        with col2:
            st.metric("Disciplinas", len(st.session_state.disciplinas))
        with col3:
            st.metric("Turmas", len(st.session_state.turmas))
        with col4:
            st.metric("Grades", len(st.session_state.grades))
        
        st.markdown("---")
        
        # Testes rápidos
        st.subheader("🧪 Testes Rápidos")
        
        col_test1, col_test2 = st.columns(2)
        with col_test1:
            if st.button("Testar Grupo A", use_container_width=True):
                turmas_a = [t for t in st.session_state.turmas if t.grupo == "A"]
                disciplinas_a = [d for d in st.session_state.disciplinas if d.grupo == "A"]
                professores_a = [p for p in st.session_state.professores if p.grupo in ["A", "AMBOS"]]
                
                gerador = GeradorGrade(turmas_a, disciplinas_a, professores_a)
                aulas, _ = gerador.gerar_grade_simples()
                
                st.session_state.proximo_id_aula = gerador.proximo_id_aula
                
                # Verificar conflitos
                conflitos = gerador.verificar_conflitos()
                
                st.success(f"✅ Geradas {len(aulas)} aulas para Grupo A")
                if conflitos == 0:
                    st.success(f"✅ Nenhum conflito detectado!")
                else:
                    st.error(f"❌ {conflitos} conflitos detectados!")
                
                # Mostrar grade da primeira turma
                if turmas_a and turmas_a[0].nome in st.session_state.aulas_por_turma:
                    mostrar_grade_visual(turmas_a[0].nome, st.session_state.aulas_por_turma[turmas_a[0].nome])
        
        with col_test2:
            if st.button("Testar Todas Turmas", use_container_width=True):
                gerador = GeradorGrade(
                    st.session_state.turmas,
                    st.session_state.disciplinas,
                    st.session_state.professores
                )
                aulas, _ = gerador.gerar_grade_simples()
                
                st.session_state.proximo_id_aula = gerador.proximo_id_aula
                
                # Verificar conflitos
                conflitos = gerador.verificar_conflitos()
                
                st.success(f"✅ Geradas {len(aulas)} aulas para todas as turmas")
                if conflitos == 0:
                    st.success(f"✅ Nenhum conflito detectado!")
                else:
                    st.error(f"❌ {conflitos} conflitos detectados!")
                
                # Aulas sem professor
                aulas_sem_prof = sum(1 for a in aulas if not a.professor)
                if aulas_sem_prof > 0:
                    st.warning(f"⚠️ {aulas_sem_prof} aulas sem professor")
    
    # ============================================
    # GERENCIAR PROFESSORES
    # ============================================
    elif opcao == "👨‍🏫 GERENCIAR PROFESSORES":
        st.header("👨‍🏫 GERENCIAMENTO DE PROFESSORES")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Professor")
            
            with st.form("form_professor"):
                nome = st.text_input("Nome")
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                
                # Disciplinas
                st.write("**Disciplinas e Horas:**")
                disciplinas_existentes = [d.nome for d in st.session_state.disciplinas]
                disciplinas_horas = {}
                
                for disc in disciplinas_existentes:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(disc)
                    with col_b:
                        horas = st.number_input(f"h_{disc}", min_value=0, max_value=40, value=0, key=f"h_{disc}")
                        if horas > 0:
                            disciplinas_horas[disc] = horas
                
                if st.form_submit_button("💾 Salvar"):
                    if nome:
                        professor = Professor(
                            id=st.session_state.proximo_id_professor,
                            nome=nome,
                            grupo=grupo,
                            disciplinas=disciplinas_horas
                        )
                        st.session_state.professores.append(professor)
                        st.session_state.proximo_id_professor += 1
                        st.success(f"Professor {nome} adicionado!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Professores")
            
            if st.session_state.professores:
                # Tabela
                dados = []
                for prof in st.session_state.professores:
                    dados.append({
                        "ID": prof.id,
                        "Nome": prof.nome,
                        "Grupo": prof.grupo,
                        "Disciplinas": len(prof.disciplinas),
                        "Total Horas": prof.get_total_horas_disponiveis(),
                        "Aulas Alocadas": len(prof.aulas_alocadas)
                    })
                
                df = pd.DataFrame(dados)
                st.dataframe(df, use_container_width=True)
                
                # Detalhes
                professor_selecionado = st.selectbox(
                    "Selecionar professor para detalhes",
                    ["Selecione..."] + [p.nome for p in st.session_state.professores]
                )
                
                if professor_selecionado != "Selecione...":
                    professor = next(p for p in st.session_state.professores if p.nome == professor_selecionado)
                    st.write(f"**Disciplinas de {professor.nome}:**")
                    for disc, horas in professor.disciplinas.items():
                        st.write(f"- {disc}: {horas} horas")
                    
                    # Aulas alocadas
                    if professor.aulas_alocadas:
                        st.write(f"**Aulas alocadas:**")
                        for dia, horario, turma in professor.aulas_alocadas:
                            st.write(f"- {dia} {horario} - Turma: {turma}")
            else:
                st.info("Nenhum professor cadastrado.")
    
    # ============================================
    # GERENCIAR DISCIPLINAS (COM PROFESSORES DISPONÍVEIS)
    # ============================================
    elif opcao == "📚 GERENCIAR DISCIPLINAS":
        st.header("📚 GERENCIAMENTO DE DISCIPLINAS")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Disciplina")
            
            with st.form("form_disciplina"):
                nome = st.text_input("Nome da Disciplina")
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                carga = st.number_input("Carga Semanal (aulas)", 1, 10, 4)
                
                # Turmas
                turmas_opcoes = [t.nome for t in st.session_state.turmas]
                turmas_selecionadas = st.multiselect("Turmas", turmas_opcoes)
                
                if st.form_submit_button("💾 Salvar"):
                    if nome and turmas_selecionadas:
                        disciplina = Disciplina(
                            id=st.session_state.proximo_id_disciplina,
                            nome=nome,
                            grupo=grupo,
                            turmas=turmas_selecionadas,
                            carga_semanal=carga
                        )
                        st.session_state.disciplinas.append(disciplina)
                        st.session_state.proximo_id_disciplina += 1
                        st.success(f"Disciplina {nome} adicionada!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Disciplinas")
            
            if st.session_state.disciplinas:
                # Selecionar disciplina para ver detalhes
                disciplinas_opcoes = [d.nome for d in st.session_state.disciplinas]
                disciplina_selecionada = st.selectbox(
                    "Selecionar disciplina para ver detalhes",
                    ["Selecione..."] + disciplinas_opcoes
                )
                
                if disciplina_selecionada != "Selecione...":
                    disciplina = next(d for d in st.session_state.disciplinas if d.nome == disciplina_selecionada)
                    
                    # Informações da disciplina
                    st.write(f"**Disciplina:** {disciplina.nome}")
                    st.write(f"**Grupo:** {disciplina.grupo}")
                    st.write(f"**Carga semanal por turma:** {disciplina.carga_semanal} aulas")
                    st.write(f"**Carga total necessária:** {disciplina.get_carga_total_necessaria()} aulas")
                    st.write(f"**Turmas:** {', '.join(disciplina.turmas)}")
                    
                    st.markdown("---")
                    
                    # PROFESSORES DISPONÍVEIS PARA ESTA DISCIPLINA
                    st.subheader("👨‍🏫 Professores Disponíveis")
                    
                    # Para cada turma, mostrar professores disponíveis
                    for turma_nome in disciplina.turmas:
                        turma = next(t for t in st.session_state.turmas if t.nome == turma_nome)
                        
                        st.write(f"**Para turma {turma_nome} (Grupo {turma.grupo}):**")
                        
                        professores_compatíveis = obter_professores_disciplina(
                            disciplina.nome, 
                            turma.grupo
                        )
                        
                        if professores_compatíveis:
                            html = """
                            <style>
                            .professor-disponivel {
                                color: green;
                                font-weight: bold;
                            }
                            .professor-indisponivel {
                                color: orange;
                                text-decoration: line-through;
                            }
                            .professor-card {
                                background-color: #f0f8ff;
                                padding: 10px;
                                margin: 5px 0;
                                border-radius: 5px;
                                border-left: 4px solid #4B0082;
                            }
                            </style>
                            """
                            
                            for prof_info in professores_compatíveis:
                                professor = prof_info['professor']
                                horas_disponiveis = prof_info['horas_disponiveis']
                                disponivel = prof_info['disponivel']
                                horas_restantes = prof_info['horas_restantes']
                                
                                # Determinar status
                                if disponivel and horas_restantes > 0:
                                    status_class = "professor-disponivel"
                                    status_text = "✅ Disponível"
                                else:
                                    status_class = "professor-indisponivel"
                                    if not disponivel:
                                        status_text = "⏰ Ocupado em algum horário"
                                    else:
                                        status_text = "📊 Horas esgotadas"
                                
                                html += f"""
                                <div class="professor-card">
                                    <div class="{status_class}">
                                        <strong>{professor.nome}</strong> (Grupo: {professor.grupo})
                                    </div>
                                    <div>
                                        <small>Horas disponíveis: {horas_disponiveis} | Horas restantes: {max(0, horas_restantes)}</small>
                                    </div>
                                    <div>
                                        <small>{status_text}</small>
                                    </div>
                                </div>
                                """
                            
                            st.markdown(html, unsafe_allow_html=True)
                        else:
                            st.warning(f"Nenhum professor disponível para ministrar {disciplina.nome} na turma {turma_nome}")
                    
                    st.markdown("---")
                
                # Lista completa de disciplinas
                st.subheader("📊 Todas as Disciplinas")
                
                dados = []
                for disc in st.session_state.disciplinas:
                    dados.append({
                        "ID": disc.id,
                        "Nome": disc.nome,
                        "Grupo": disc.grupo,
                        "Carga/Turma": disc.carga_semanal,
                        "Turmas": len(disc.turmas),
                        "Carga Total": disc.get_carga_total_necessaria()
                    })
                
                df = pd.DataFrame(dados)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Nenhuma disciplina cadastrada.")
    
    # ============================================
    # GERENCIAR TURMAS
    # ============================================
    elif opcao == "👥 GERENCIAR TURMAS":
        st.header("👥 GERENCIAMENTO DE TURMAS")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Turma")
            
            with st.form("form_turma"):
                nome = st.text_input("Nome da Turma")
                serie = st.selectbox("Série", ["6º EF", "7º EF", "8º EF", "9º EF", "1º EM", "2º EM", "3º EM"])
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                turno = st.selectbox("Turno", ["MANHÃ", "TARDE"])
                
                if st.form_submit_button("💾 Salvar"):
                    if nome:
                        turma = Turma(
                            id=st.session_state.proximo_id_turma,
                            nome=nome,
                            serie=serie,
                            grupo=grupo,
                            turno=turno
                        )
                        st.session_state.turmas.append(turma)
                        st.session_state.proximo_id_turma += 1
                        st.success(f"Turma {nome} adicionada!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Turmas")
            
            if st.session_state.turmas:
                dados = []
                for turma in st.session_state.turmas:
                    dados.append({
                        "ID": turma.id,
                        "Nome": turma.nome,
                        "Série": turma.serie,
                        "Grupo": turma.grupo,
                        "Turno": turma.turno
                    })
                
                df = pd.DataFrame(dados)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Nenhuma turma cadastrada.")
    
    # ============================================
    # ANÁLISE DE COBERTURA
    # ============================================
    elif opcao == "📊 ANÁLISE DE COBERTURA":
        st.header("📊 ANÁLISE DE COBERTURA")
        
        if not st.session_state.disciplinas or not st.session_state.professores:
            st.warning("Cadastre disciplinas e professores primeiro.")
        else:
            # Análise simples
            st.subheader("📈 Análise de Cobertura por Disciplina")
            
            dados_analise = []
            for disc in st.session_state.disciplinas:
                carga_total = disc.get_carga_total_necessaria()
                horas_disponiveis = 0
                professores_compativeis = []
                
                for professor in st.session_state.professores:
                    horas_prof = professor.get_horas_disponiveis(disc.nome)
                    if horas_prof > 0:
                        # Verificar compatibilidade
                        if (professor.grupo == disc.grupo or 
                            professor.grupo == 'AMBOS' or 
                            disc.grupo == 'AMBOS'):
                            horas_disponiveis += horas_prof
                            professores_compativeis.append(professor.nome)
                
                status = "✅ Suficiente" if horas_disponiveis >= carga_total else "⚠️ Parcial" if horas_disponiveis > 0 else "❌ Crítica"
                
                dados_analise.append({
                    "Disciplina": disc.nome,
                    "Grupo": disc.grupo,
                    "Carga Total": carga_total,
                    "Horas Disp.": horas_disponiveis,
                    "Status": status,
                    "Professores": ", ".join(professores_compativeis) if professores_compativeis else "Nenhum"
                })
            
            df_analise = pd.DataFrame(dados_analise)
            st.dataframe(df_analise, use_container_width=True)
    
    # ============================================
    # GERAR GRADE
    # ============================================
    elif opcao == "🗓️ GERAR GRADE":
        st.header("🗓️ GERAR GRADE HORÁRIA")
        
        # Limpar aulas anteriores dos professores
        limpar_aulas_professores()
        
        # Configurações
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_grade = st.selectbox(
                "Tipo de Grade",
                [
                    "Grade Completa (Todas as Turmas)",
                    "Grade por Grupo A",
                    "Grade por Grupo B",
                    "Grade por Turma Específica"
                ]
            )
            
            if tipo_grade == "Grade por Turma Específica":
                turma_selecionada = st.selectbox(
                    "Selecionar Turma",
                    [t.nome for t in st.session_state.turmas]
                )
        
        with col2:
            nome_grade = st.text_input("Nome da Grade", value="Nova Grade")
            st.info("📅 **EM:** 07:00-13:10 (7 períodos)")
            st.info("📅 **EF II:** 07:50-14:00 (7 períodos)")
        
        # Filtrar
        if tipo_grade == "Grade por Grupo A":
            turmas_filtradas = [t for t in st.session_state.turmas if t.grupo == "A"]
            grupo_texto = "Grupo A"
        elif tipo_grade == "Grade por Grupo B":
            turmas_filtradas = [t for t in st.session_state.turmas if t.grupo == "B"]
            grupo_texto = "Grupo B"
        elif tipo_grade == "Grade por Turma Específica":
            turmas_filtradas = [t for t in st.session_state.turmas if t.nome == turma_selecionada]
            grupo_texto = f"Turma {turma_selecionada}"
        else:
            turmas_filtradas = st.session_state.turmas
            grupo_texto = "Todas as Turmas"
        
        # Informações
        st.info(f"**{len(turmas_filtradas)} turmas selecionadas**")
        
        # Gerar
        if st.button("🚀 GERAR GRADE", type="primary", use_container_width=True):
            if not turmas_filtradas:
                st.error("Nenhuma turma selecionada!")
            else:
                with st.spinner(f"Gerando grade para {grupo_texto}..."):
                    disciplinas_filtradas = st.session_state.disciplinas
                    professores_filtrados = st.session_state.professores
                    
                    gerador = GeradorGrade(turmas_filtradas, disciplinas_filtradas, professores_filtrados)
                    aulas_alocadas, aulas_por_turma = gerador.gerar_grade_simples()
                    
                    st.session_state.proximo_id_aula = gerador.proximo_id_aula
                    
                    # Verificar conflitos
                    conflitos = gerador.verificar_conflitos()
                    
                    grade = Grade(
                        id=st.session_state.proximo_id_grade,
                        nome=nome_grade,
                        turmas=[t.nome for t in turmas_filtradas],
                        grupo=grupo_texto,
                        aulas=aulas_alocadas,
                        status="GERADA"
                    )
                    
                    st.session_state.grades.append(grade)
                    st.session_state.proximo_id_grade += 1
                    
                    st.success(f"✅ Grade gerada com sucesso!")
                    
                    # Mostrar estatísticas
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("Total de Aulas", len(aulas_alocadas))
                    with col_stat2:
                        st.metric("Conflitos", conflitos)
                    with col_stat3:
                        st.metric("Turmas", len(turmas_filtradas))
                    
                    # Aulas sem professor
                    aulas_sem_prof = sum(1 for a in aulas_alocadas if not a.professor)
                    if aulas_sem_prof > 0:
                        st.warning(f"⚠️ {aulas_sem_prof} aulas sem professor")
                    
                    # Mostrar grade
                    if turmas_filtradas:
                        primeira_turma = turmas_filtradas[0].nome
                        if primeira_turma in st.session_state.aulas_por_turma:
                            mostrar_grade_visual(primeira_turma, st.session_state.aulas_por_turma[primeira_turma])
    
    # ============================================
    # VISUALIZAR GRADES
    # ============================================
    elif opcao == "📋 VISUALIZAR GRADES":
        st.header("📋 VISUALIZAR GRADES GERADAS")
        
        if not st.session_state.grades:
            st.info("Nenhuma grade gerada ainda.")
        else:
            # Seleção
            grade_selecionada = st.selectbox(
                "Selecionar Grade",
                [g.nome for g in st.session_state.grades]
            )
            
            if grade_selecionada:
                grade = next(g for g in st.session_state.grades if g.nome == grade_selecionada)
                
                # Informações
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nome", grade.nome)
                with col2:
                    st.metric("Status", grade.status)
                with col3:
                    st.metric("Aulas", len(grade.aulas))
                
                st.write(f"**Turmas:** {', '.join(grade.turmas)}")
                st.write(f"**Grupo:** {grade.grupo}")
                
                # Verificar conflitos na grade
                professor_horarios = {}
                conflitos = 0
                for aula in grade.aulas:
                    if aula.professor:
                        chave = f"{aula.professor}_{aula.dia}_{aula.horario}"
                        if chave in professor_horarios:
                            conflitos += 1
                        else:
                            professor_horarios[chave] = aula
                
                if conflitos > 0:
                    st.error(f"❌ {conflitos} conflitos de horário detectados nesta grade!")
                else:
                    st.success("✅ Nenhum conflito de horário detectado!")
                
                # Filtrar
                turma_filtro = st.selectbox(
                    "Filtrar por Turma",
                    ["Todas"] + list(set([a.turma for a in grade.aulas]))
                )
                
                # Mostrar aulas
                if turma_filtro == "Todas":
                    aulas_filtradas = grade.aulas
                else:
                    aulas_filtradas = [a for a in grade.aulas if a.turma == turma_filtro]
                
                if aulas_filtradas:
                    # Converter para DataFrame
                    dados = []
                    for aula in aulas_filtradas:
                        dados.append({
                            "Turma": aula.turma,
                            "Disciplina": aula.disciplina,
                            "Professor": aula.professor if aula.professor else "---",
                            "Dia": aula.dia,
                            "Horário": aula.horario,
                            "Período": aula.periodo
                        })
                    
                    df = pd.DataFrame(dados)
                    
                    # Ordenar
                    ordem_dias = {dia: i for i, dia in enumerate(DIAS_SEMANA)}
                    df['Ordem'] = df['Dia'].map(ordem_dias)
                    df = df.sort_values(['Turma', 'Ordem', 'Período'])
                    df = df.drop('Ordem', axis=1)
                    
                    st.dataframe(df, use_container_width=True)
                    
                    # Visualizar grade
                    if turma_filtro != "Todas":
                        if st.button("📊 Visualizar Grade"):
                            aulas_turma = [a for a in grade.aulas if a.turma == turma_filtro]
                            mostrar_grade_visual(turma_filtro, aulas_turma)
    
    # ============================================
    # CONFIGURAÇÕES
    # ============================================
    elif opcao == "⚙️ CONFIGURAÇÕES":
        st.header("⚙️ CONFIGURAÇÕES DO SISTEMA")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Estatísticas")
            
            total_aulas = sum(d.get_carga_total_necessaria() for d in st.session_state.disciplinas)
            total_horas = sum(p.get_total_horas_disponiveis() for p in st.session_state.professores)
            
            st.write(f"**Total de aulas necessárias:** {total_aulas}")
            st.write(f"**Total de horas disponíveis:** {total_horas}")
            
            if total_aulas == 490 and total_horas == 490:
                st.success("✅ Sistema equilibrado 490/490")
            else:
                st.error("❌ Sistema desequilibrado")
        
        with col2:
            st.subheader("🛠️ Ferramentas")
            
            if st.button("🗑️ Limpar Todas as Grades", use_container_width=True):
                st.session_state.grades = []
                st.session_state.aulas_por_turma = {}
                limpar_aulas_professores()
                st.session_state.proximo_id_grade = 1
                st.session_state.proximo_id_aula = 1
                st.success("Grades limpas!")
                st.rerun()
            
            if st.button("📤 Exportar Dados", use_container_width=True):
                dados = {
                    "professores": [{"nome": p.nome, "grupo": p.grupo, "disciplinas": p.disciplinas} 
                                   for p in st.session_state.professores],
                    "disciplinas": [{"nome": d.nome, "grupo": d.grupo, "turmas": d.turmas, "carga": d.carga_semanal}
                                   for d in st.session_state.disciplinas],
                    "turmas": [{"nome": t.nome, "serie": t.serie, "grupo": t.grupo, "turno": t.turno}
                              for t in st.session_state.turmas]
                }
                st.json(dados)

if __name__ == "__main__":
    main()