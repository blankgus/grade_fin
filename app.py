import streamlit as st
import pandas as pd
from datetime import time
import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Tuple, Set
from enum import Enum
import random

# ============================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

# HORÁRIOS CORRIGIDOS - 50 MINUTOS CADA
HORARIOS_EM = [
    ("07:00", "07:50"), ("07:50", "08:40"), ("08:40", "09:30"),
    ("09:50", "10:40"), ("10:40", "11:30"), ("11:30", "12:20"),
    ("12:20", "13:10")  # 7 períodos no total
]

HORARIOS_EF_II = [
    ("07:50", "08:40"), ("08:40", "09:30"), ("09:30", "10:20"),
    ("10:40", "11:30"), ("11:30", "12:20"), ("12:20", "13:10"),
    ("13:10", "14:00")  # 7 períodos no total
]

@dataclass
class Professor:
    id: int
    nome: str
    grupo: str = "AMBOS"
    disciplinas: Dict[str, int] = field(default_factory=dict)  # {nome_disciplina: horas_disponiveis}
    max_aulas_dia: int = 5
    min_aulas_dia: int = 0
    disponibilidade: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)
    
    def get_horas_disponiveis(self, disciplina: str) -> int:
        """Retorna horas disponíveis para uma disciplina específica"""
        return self.disciplinas.get(disciplina, 0)
    
    def get_total_horas_disponiveis(self) -> int:
        """Retorna total de horas disponíveis do professor"""
        return sum(self.disciplinas.values())
    
    def get_disciplinas_list(self) -> List[str]:
        """Retorna lista de disciplinas que o professor pode ministrar"""
        return list(self.disciplinas.keys())

@dataclass
class Disciplina:
    id: int
    nome: str
    grupo: str = "AMBOS"
    turmas: List[str] = field(default_factory=list)
    carga_semanal: int = 0  # Em aulas de 50 minutos
    professores: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)
    
    def get_carga_total_necessaria(self) -> int:
        """Calcula carga horária total necessária considerando todas as turmas"""
        return self.carga_semanal * len(self.turmas)

@dataclass
class Turma:
    id: int
    nome: str
    serie: str
    grupo: str = "AMBOS"
    turno: str = "MANHÃ"
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Aula:
    id: int
    turma: str
    disciplina: str
    professor: str
    dia: str
    horario: str
    periodo: int
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Grade:
    id: int
    nome: str
    turmas: List[str] = field(default_factory=list)
    grupo: str = "COMPLETA"
    aulas: List[Aula] = field(default_factory=list)
    status: str = "RASCUNHO"
    
    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "turmas": self.turmas,
            "grupo": self.grupo,
            "status": self.status,
            "aulas": [aula.to_dict() for aula in self.aulas]
        }

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def inicializar_sessao():
    """Inicializa as variáveis de sessão"""
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

def obter_grupo_seguro(obj):
    """Obtém o grupo de um objeto de forma segura"""
    if hasattr(obj, 'grupo'):
        grupo = obj.grupo
        if grupo in ["A", "B", "AMBOS"]:
            return grupo
    return "AMBOS"

def obter_horarios_turma(nome_turma: str):
    """Obtém os horários disponíveis para uma turma"""
    turma = next((t for t in st.session_state.turmas if t.nome == nome_turma), None)
    if not turma:
        return []
    
    if "EM" in turma.serie:
        return HORARIOS_EM
    else:
        return HORARIOS_EF_II

def calcular_carga_maxima(serie: str) -> int:
    """Calcula a carga horária máxima semanal para uma série (em aulas de 50min)"""
    if "EM" in serie:
        return 7 * 5  # 7 períodos por dia, 5 dias = 35 aulas semanais
    else:
        return 7 * 5  # 7 períodos por dia, 5 dias = 35 aulas semanais

def analisar_cobertura_disciplinas():
    """Analisa se todas as disciplinas têm cobertura de professores suficiente"""
    analises = []
    
    for disciplina in st.session_state.disciplinas:
        # Calcular carga total necessária para esta disciplina
        carga_total_necessaria = disciplina.get_carga_total_necessaria()
        
        # Encontrar todos os professores que podem ministrar esta disciplina
        professores_disponiveis = []
        horas_disponiveis_total = 0
        
        for professor in st.session_state.professores:
            horas_prof = professor.get_horas_disponiveis(disciplina.nome)
            if horas_prof > 0:
                professores_disponiveis.append({
                    'nome': professor.nome,
                    'horas': horas_prof,
                    'grupo': professor.grupo
                })
                horas_disponiveis_total += horas_prof
        
        # Verificar compatibilidade de grupos
        horas_compativel = 0
        for prof_info in professores_disponiveis:
            if (prof_info['grupo'] == disciplina.grupo or 
                prof_info['grupo'] == 'AMBOS' or 
                disciplina.grupo == 'AMBOS'):
                horas_compativel += prof_info['horas']
        
        # Determinar status
        if horas_compativel >= carga_total_necessaria:
            status = "✅ Suficiente"
            cor = "green"
        elif horas_compativel > 0:
            status = f"⚠️ Parcial ({horas_compativel}/{carga_total_necessaria})"
            cor = "orange"
        else:
            status = "❌ Sem cobertura"
            cor = "red"
        
        analises.append({
            'Disciplina': disciplina.nome,
            'Grupo': disciplina.grupo,
            'Turmas': len(disciplina.turmas),
            'Carga/Turma': disciplina.carga_semanal,
            'Carga Total': carga_total_necessaria,
            'Professores': len(professores_disponiveis),
            'Horas Disponível': horas_disponiveis_total,
            'Horas Compatível': horas_compativel,
            'Status': status,
            '_cor': cor
        })
    
    return analises

def calcular_necessidade_professores():
    """Calcula se é necessário contratar mais professores ou reduzir carga"""
    recomendacoes = []
    
    for disciplina in st.session_state.disciplinas:
        carga_total = disciplina.get_carga_total_necessaria()
        
        # Somar horas disponíveis de professores compatíveis
        horas_disponiveis = 0
        professores_compativeis = []
        
        for professor in st.session_state.professores:
            horas_prof = professor.get_horas_disponiveis(disciplina.nome)
            if horas_prof > 0:
                # Verificar compatibilidade de grupo
                prof_grupo = professor.grupo
                disc_grupo = disciplina.grupo
                
                if (prof_grupo == disc_grupo or 
                    prof_grupo == 'AMBOS' or 
                    disc_grupo == 'AMBOS'):
                    horas_disponiveis += horas_prof
                    professores_compativeis.append(professor.nome)
        
        deficit = carga_total - horas_disponiveis
        
        if deficit > 0:
            recomendacoes.append({
                'Disciplina': disciplina.nome,
                'Grupo': disciplina.grupo,
                'Carga Necessária': carga_total,
                'Horas Disponível': horas_disponiveis,
                'Deficit': deficit,
                'Professores Compativeis': ', '.join(professores_compativeis) if professores_compativeis else 'Nenhum',
                'Ação Recomendada': f"Adicionar {deficit} aulas de {disciplina.nome} (contratar ou realocar)"
            })
        elif horas_disponiveis == 0:
            recomendacoes.append({
                'Disciplina': disciplina.nome,
                'Grupo': disciplina.grupo,
                'Carga Necessária': carga_total,
                'Horas Disponível': 0,
                'Deficit': carga_total,
                'Professores Compativeis': 'Nenhum',
                'Ação Recomendada': f"URGENTE: Cadastrar professores para {disciplina.nome} ou remover das turmas"
            })
    
    return recomendacoes

def carregar_dados_exemplo():
    """Carrega dados de exemplo para testes com balanço 490/490"""
    
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
    
    # ============================================
    # TURMAS DE EXEMPLO (14 turmas)
    # ============================================
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
    
    # ============================================
    # DISCIPLINAS DE EXEMPLO (Ajustadas para 490 aulas)
    # ============================================
    # CAPACIDADE TOTAL: 14 turmas × 35 aulas = 490 períodos
    # Vamos distribuir exatamente 490 aulas
    
    disciplinas_exemplo = [
        # ========== GRUPO A - EF II (4 turmas) ==========
        # Total: 8 disciplinas = 35 aulas/turma
        Disciplina(id=1, nome="Matemática", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=5, professores=[]),  # 4 × 5 = 20
        
        Disciplina(id=2, nome="Português", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=5, professores=[]),  # 4 × 5 = 20
        
        Disciplina(id=3, nome="Ciências", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=4, professores=[]),  # 4 × 4 = 16
        
        Disciplina(id=4, nome="Geografia", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=3, professores=[]),  # 4 × 3 = 12
        
        Disciplina(id=5, nome="História", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=3, professores=[]),  # 4 × 3 = 12
        
        Disciplina(id=6, nome="Inglês", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        Disciplina(id=7, nome="Educação Física", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        Disciplina(id=8, nome="Artes", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=1, professores=[]),  # 4 × 1 = 4
        
        # ========== GRUPO B - EF II (4 turmas) ==========
        Disciplina(id=9, nome="Matemática", grupo="B", 
                  turmas=["6º B", "7º B", "8º B", "9º B"], 
                  carga_semanal=5, professores=[]),  # 4 × 5 = 20
        
        Disciplina(id=10, nome="Português", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=5, professores=[]),  # 4 × 5 = 20
        
        Disciplina(id=11, nome="Ciências", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=4, professores=[]),  # 4 × 4 = 16
        
        Disciplina(id=12, nome="Geografia", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=3, professores=[]),  # 4 × 3 = 12
        
        Disciplina(id=13, nome="História", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=3, professores=[]),  # 4 × 3 = 12
        
        Disciplina(id=14, nome="Inglês", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        Disciplina(id=15, nome="Educação Física", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        Disciplina(id=16, nome="Artes", grupo="B", 
                   turmas=["6º B", "7º B", "8º B", "9º B"], 
                   carga_semanal=1, professores=[]),  # 4 × 1 = 4
        
        # ========== GRUPO A - EM (3 turmas) ==========
        # 10 disciplinas = 35 aulas/turma
        Disciplina(id=17, nome="Matemática", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=5, professores=[]),  # 3 × 5 = 15
        
        Disciplina(id=18, nome="Português", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=5, professores=[]),  # 3 × 5 = 15
        
        Disciplina(id=19, nome="Física", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=20, nome="Química", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=21, nome="Biologia", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=22, nome="História", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=3, professores=[]),  # 3 × 3 = 9
        
        Disciplina(id=23, nome="Geografia", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=3, professores=[]),  # 3 × 3 = 9
        
        Disciplina(id=24, nome="Inglês", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        Disciplina(id=25, nome="Educação Física", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        Disciplina(id=26, nome="Artes", grupo="A", 
                  turmas=["1º EM A", "2º EM A", "3º EM A"], 
                  carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        # ========== GRUPO B - EM (3 turmas) ==========
        Disciplina(id=27, nome="Matemática", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=5, professores=[]),  # 3 × 5 = 15
        
        Disciplina(id=28, nome="Português", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=5, professores=[]),  # 3 × 5 = 15
        
        Disciplina(id=29, nome="Física", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=30, nome="Química", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=31, nome="Biologia", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=4, professores=[]),  # 3 × 4 = 12
        
        Disciplina(id=32, nome="História", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=3, professores=[]),  # 3 × 3 = 9
        
        Disciplina(id=33, nome="Geografia", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=3, professores=[]),  # 3 × 3 = 9
        
        Disciplina(id=34, nome="Inglês", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        Disciplina(id=35, nome="Educação Física", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        Disciplina(id=36, nome="Artes", grupo="B", 
                   turmas=["1º EM B", "2º EM B", "3º EM B"], 
                   carga_semanal=2, professores=[]),  # 3 × 2 = 6
        
        # ========== DISCIPLINAS AMBOS - EM ==========
        Disciplina(id=37, nome="Filosofia", grupo="AMBOS", 
                  turmas=["1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], 
                  carga_semanal=2, professores=[]),  # 6 × 2 = 12
        
        Disciplina(id=38, nome="Sociologia", grupo="AMBOS", 
                  turmas=["1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], 
                  carga_semanal=2, professores=[]),  # 6 × 2 = 12
        
        # ========== ESPANHOL PARA EF II ==========
        Disciplina(id=39, nome="Espanhol", grupo="A", 
                  turmas=["6º A", "7º A", "8º A", "9º A"], 
                  carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        Disciplina(id=40, nome="Espanhol", grupo="B", 
                  turmas=["6º B", "7º B", "8º B", "9º B"], 
                  carga_semanal=2, professores=[]),  # 4 × 2 = 8
        
        # ========== TECNOLOGIA PARA TODOS ==========
        Disciplina(id=41, nome="Tecnologia", grupo="AMBOS", 
                  turmas=["6º A", "6º B", "7º A", "7º B", "8º A", "8º B", "9º A", "9º B",
                         "1º EM A", "1º EM B", "2º EM A", "2º EM B", "3º EM A", "3º EM B"], 
                  carga_semanal=2, professores=[]),  # 14 × 2 = 28
    ]
    
    for disciplina in disciplinas_exemplo:
        st.session_state.disciplinas.append(disciplina)
        st.session_state.proximo_id_disciplina = max(st.session_state.proximo_id_disciplina, disciplina.id + 1)
    
    # ============================================
    # VERIFICAÇÃO E AJUSTE PARA 490 AULAS
    # ============================================
    # Calcular total atual
    total_aulas = sum(d.get_carga_total_necessaria() for d in st.session_state.disciplinas)
    
    # Ajustar se necessário
    if total_aulas != 490:
        # Encontrar disciplina para ajustar (Tecnologia)
        for disc in st.session_state.disciplinas:
            if disc.nome == "Tecnologia":
                # Calcular ajuste necessário
                ajuste = 490 - total_aulas
                # Aumentar ou diminuir carga
                disc.carga_semanal += 1  # Aumenta de 2 para 3
                break
    
    # ============================================
    # PROFESSORES DE EXEMPLO (com 490 horas totais)
    # ============================================
    professores_exemplo = [
        # ========== PROFESSORES GRUPO A ==========
        Professor(id=1, nome="Maria Silva", grupo="A", 
                 disciplinas={"Matemática": 35}, max_aulas_dia=6, min_aulas_dia=2),
        
        Professor(id=2, nome="João Santos", grupo="A", 
                 disciplinas={"Português": 35}, max_aulas_dia=5, min_aulas_dia=3),
        
        Professor(id=3, nome="Ana Costa", grupo="A", 
                 disciplinas={"Ciências": 16, "Biologia": 12}, max_aulas_dia=6, min_aulas_dia=2),
        
        Professor(id=4, nome="Carlos Mendes", grupo="A", 
                 disciplinas={"Geografia": 25, "História": 21}, max_aulas_dia=5, min_aulas_dia=2),
        
        Professor(id=5, nome="Roberto Física", grupo="A", 
                 disciplinas={"Física": 12, "Química": 12}, max_aulas_dia=5, min_aulas_dia=2),
        
        Professor(id=6, nome="Cláudia Idiomas", grupo="A", 
                 disciplinas={"Inglês": 14, "Espanhol": 8}, max_aulas_dia=4, min_aulas_dia=2),
        
        # ========== PROFESSORES GRUPO B ==========
        Professor(id=7, nome="Pedro Oliveira", grupo="B", 
                 disciplinas={"Matemática": 35}, max_aulas_dia=5, min_aulas_dia=3),
        
        Professor(id=8, nome="Carla Souza", grupo="B", 
                 disciplinas={"Português": 35}, max_aulas_dia=6, min_aulas_dia=2),
        
        Professor(id=9, nome="Sofia Lima", grupo="B", 
                 disciplinas={"Ciências": 16, "Biologia": 12}, max_aulas_dia=5, min_aulas_dia=2),
        
        Professor(id=10, nome="Fernando Almeida", grupo="B", 
                  disciplinas={"Geografia": 25, "História": 21}, max_aulas_dia=4, min_aulas_dia=2),
        
        Professor(id=11, nome="Patrícia Química", grupo="B", 
                  disciplinas={"Física": 12, "Química": 12}, max_aulas_dia=5, min_aulas_dia=2),
        
        Professor(id=12, nome="Ricardo Idiomas", grupo="B", 
                  disciplinas={"Inglês": 14, "Espanhol": 8}, max_aulas_dia=4, min_aulas_dia=2),
        
        # ========== PROFESSORES AMBOS ==========
        Professor(id=13, nome="Marcos Ribeiro", grupo="AMBOS", 
                  disciplinas={"Educação Física": 28}, max_aulas_dia=5, min_aulas_dia=3),
        
        Professor(id=14, nome="Patrícia Cardoso", grupo="AMBOS", 
                  disciplinas={"Artes": 20}, max_aulas_dia=5, min_aulas_dia=2),
        
        Professor(id=15, nome="Fernanda Filosofia", grupo="AMBOS", 
                  disciplinas={"Filosofia": 12, "Sociologia": 12}, max_aulas_dia=4, min_aulas_dia=2),
        
        Professor(id=16, nome="Carla Tecnologia", grupo="AMBOS", 
                  disciplinas={"Tecnologia": 28}, max_aulas_dia=6, min_aulas_dia=3),
    ]
    
    for professor in professores_exemplo:
        st.session_state.professores.append(professor)
        st.session_state.proximo_id_professor = max(st.session_state.proximo_id_professor, professor.id + 1)
    
    # ============================================
    # VERIFICAÇÃO FINAL DO BALANÇO
    # ============================================
    # Calcular totais
    capacidade_total = 14 * 35  # 14 turmas × 35 períodos = 490
    
    aulas_necessarias = 0
    for disciplina in st.session_state.disciplinas:
        aulas_necessarias += disciplina.get_carga_total_necessaria()
    
    horas_disponiveis = 0
    for professor in st.session_state.professores:
        horas_disponiveis += professor.get_total_horas_disponiveis()
    
    return True

def verificar_base_vazia():
    """Verifica se a base está vazia"""
    return (len(st.session_state.turmas) == 0 and 
            len(st.session_state.disciplinas) == 0 and 
            len(st.session_state.professores) == 0)

def verificar_balanco_490():
    """Verifica se o sistema está com balanço 490/490/490"""
    # Calcular capacidade total
    capacidade_total = 0
    for turma in st.session_state.turmas:
        horarios = obter_horarios_turma(turma.nome)
        capacidade_total += len(DIAS_SEMANA) * len(horarios)
    
    # Calcular aulas necessárias
    aulas_necessarias = 0
    for disciplina in st.session_state.disciplinas:
        aulas_necessarias += disciplina.get_carga_total_necessaria()
    
    # Calcular horas disponíveis
    horas_disponiveis = 0
    for professor in st.session_state.professores:
        horas_disponiveis += professor.get_total_horas_disponiveis()
    
    return capacidade_total, aulas_necessarias, horas_disponiveis

# ============================================
# FUNÇÕES NOVAS ADICIONADAS
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
                dia_data[f"P{periodo}"] = f"{aula.disciplina}\n{aula.professor}"
            else:
                dia_data[f"P{periodo}"] = "Livre"
        
        grade_data.append(dia_data)
    
    # Converter para DataFrame
    df_grade = pd.DataFrame(grade_data)
    
    # Mostrar grade
    st.subheader(f"📅 Grade Visual - {turma_nome}")
    st.dataframe(df_grade.set_index('Dia'), use_container_width=True)

def exportar_grade_excel(grade):
    """Exporta uma grade para Excel"""
    if not grade.aulas:
        st.warning("Nenhuma aula para exportar")
        return None
    
    # Criar DataFrame com todas as aulas
    dados = []
    for aula in grade.aulas:
        dados.append({
            "ID": aula.id,
            "Turma": aula.turma,
            "Disciplina": aula.disciplina,
            "Professor": aula.professor,
            "Dia": aula.dia,
            "Horário": aula.horario,
            "Período": aula.periodo
        })
    
    df = pd.DataFrame(dados)
    
    # Criar um arquivo Excel com múltiplas abas
    excel_buffer = pd.ExcelWriter('grade_temp.xlsx', engine='openpyxl')
    
    # Aba principal com todas as aulas
    df.to_excel(excel_buffer, sheet_name='Todas Aulas', index=False)
    
    # Abas separadas por turma
    turmas_unicas = df['Turma'].unique()
    for turma in turmas_unicas:
        df_turma = df[df['Turma'] == turma].copy()
        df_turma.to_excel(excel_buffer, sheet_name=turma[:31], index=False)  # Limitando nome da aba
    
    excel_buffer.close()
    
    # Ler o arquivo para download
    with open('grade_temp.xlsx', 'rb') as f:
        excel_data = f.read()
    
    return excel_data

def gerar_relatorio_detalhado():
    """Gera um relatório detalhado do sistema"""
    relatorio = {
        "professores": [],
        "disciplinas": [],
        "turmas": [],
        "grades": []
    }
    
    # Dados dos professores
    for prof in st.session_state.professores:
        relatorio["professores"].append({
            "nome": prof.nome,
            "grupo": prof.grupo,
            "total_horas": prof.get_total_horas_disponiveis(),
            "disciplinas": list(prof.disciplinas.keys())
        })
    
    # Dados das disciplinas
    for disc in st.session_state.disciplinas:
        relatorio["disciplinas"].append({
            "nome": disc.nome,
            "grupo": disc.grupo,
            "carga_semanal": disc.carga_semanal,
            "turmas": disc.turmas,
            "carga_total": disc.get_carga_total_necessaria()
        })
    
    # Dados das turmas
    for turma in st.session_state.turmas:
        relatorio["turmas"].append({
            "nome": turma.nome,
            "serie": turma.serie,
            "grupo": turma.grupo,
            "turno": turma.turno
        })
    
    # Dados das grades
    for grade in st.session_state.grades:
        relatorio["grades"].append({
            "nome": grade.nome,
            "turmas": grade.turmas,
            "total_aulas": len(grade.aulas),
            "status": grade.status
        })
    
    return relatorio

# ============================================
# ALGORITMO DE GERAÇÃO DE GRADE MELHORADO
# ============================================

class GeradorGrade:
    def __init__(self, turmas_filtradas, disciplinas_filtradas, professores_filtrados):
        self.turmas = turmas_filtradas
        self.disciplinas = disciplinas_filtradas
        self.professores = professores_filtrados
        self.proximo_id_aula = st.session_state.proximo_id_aula
        self.aulas_alocadas = []
        self.conflitos = 0
        self.tentativas_maximas = 100
        
        # Controle de horas utilizadas por professor
        self.horas_utilizadas = {}
        for professor in self.professores:
            self.horas_utilizadas[professor.nome] = {}
            for disciplina_nome in professor.disciplinas.keys():
                self.horas_utilizadas[professor.nome][disciplina_nome] = 0
    
    def encontrar_professor_disponivel(self, disciplina_nome: str, grupo_turma: str):
        """Encontra um professor disponível para a disciplina"""
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
            if horas_usadas < horas_disponiveis:
                professores_candidatos.append({
                    'professor': professor,
                    'horas_disponiveis': horas_disponiveis,
                    'horas_usadas': horas_usadas,
                    'prioridade': horas_disponiveis - horas_usadas  # Prioriza quem tem mais horas livres
                })
        
        if professores_candidatos:
            # Ordenar por prioridade (mais horas livres primeiro)
            professores_candidatos.sort(key=lambda x: x['prioridade'], reverse=True)
            return professores_candidatos[0]['professor']
        
        return None
    
    def gerar_grade_simples(self):
        """Algoritmo simples de geração de grade com controle de horas"""
        aulas_por_turma = {turma.nome: [] for turma in self.turmas}
        
        # Para cada turma, distribuir as disciplinas
        for turma in self.turmas:
            grupo_turma = obter_grupo_seguro(turma)
            disciplinas_turma = [
                d for d in self.disciplinas 
                if turma.nome in d.turmas and obter_grupo_seguro(d) == grupo_turma
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
            
            # Distribuir aulas nos horários
            periodo = 0
            for disciplina_nome in aulas_necessarias:
                if periodo >= len(horarios_disponiveis) * len(dias_disponiveis):
                    # Tentar redistribuir em horários já usados
                    for dia in dias_disponiveis:
                        for i, (inicio, fim) in enumerate(horarios_disponiveis):
                            # Verificar se este horário já tem aula
                            horario_str = f"{inicio}-{fim}"
                            existe_aula = any(a for a in aulas_por_turma[turma.nome] 
                                            if a.dia == dia and a.horario == horario_str)
                            
                            if not existe_aula:
                                # Encontrar professor disponível
                                professor = self.encontrar_professor_disponivel(disciplina_nome, grupo_turma)
                                
                                if professor:
                                    professor_nome = professor.nome
                                    # Atualizar horas utilizadas
                                    if disciplina_nome not in self.horas_utilizadas[professor_nome]:
                                        self.horas_utilizadas[professor_nome][disciplina_nome] = 0
                                    self.horas_utilizadas[professor_nome][disciplina_nome] += 1
                                else:
                                    professor_nome = "SEM PROFESSOR"
                                
                                aula = Aula(
                                    id=self.proximo_id_aula,
                                    turma=turma.nome,
                                    disciplina=disciplina_nome,
                                    professor=professor_nome,
                                    dia=dia,
                                    horario=horario_str,
                                    periodo=i + 1
                                )
                                
                                self.aulas_alocadas.append(aula)
                                aulas_por_turma[turma.nome].append(aula)
                                self.proximo_id_aula += 1
                                break
                        else:
                            continue
                        break
                    else:
                        break  # Não há mais horários disponíveis
                    continue
                
                # Distribuição normal
                dia_idx = periodo // len(horarios_disponiveis)
                horario_idx = periodo % len(horarios_disponiveis)
                
                if dia_idx < len(dias_disponiveis):
                    dia = dias_disponiveis[dia_idx]
                    horario = f"{horarios_disponiveis[horario_idx][0]}-{horarios_disponiveis[horario_idx][1]}"
                    
                    # Encontrar professor disponível
                    professor = self.encontrar_professor_disponivel(disciplina_nome, grupo_turma)
                    
                    if professor:
                        professor_nome = professor.nome
                        # Atualizar horas utilizadas
                        if disciplina_nome not in self.horas_utilizadas[professor_nome]:
                            self.horas_utilizadas[professor_nome][disciplina_nome] = 0
                        self.horas_utilizadas[professor_nome][disciplina_nome] += 1
                    else:
                        professor_nome = "SEM PROFESSOR"
                    
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
                    periodo += 1
        
        # Salvar aulas por turma na sessão
        for turma_nome, aulas in aulas_por_turma.items():
            st.session_state.aulas_por_turma[turma_nome] = aulas
        
        return self.aulas_alocadas, aulas_por_turma
    
    def verificar_conflitos(self):
        """Verifica conflitos na grade gerada"""
        conflitos = 0
        
        # Verificar professores em dois lugares ao mesmo tempo
        professor_horarios = {}
        
        for aula in self.aulas_alocadas:
            if aula.professor == "SEM PROFESSOR":
                continue
                
            chave = f"{aula.professor}_{aula.dia}_{aula.horario}"
            if chave in professor_horarios:
                conflitos += 1
            else:
                professor_horarios[chave] = aula
        
        return conflitos
    
    def gerar_relatorio_utilizacao(self):
        """Gera relatório de utilização das horas dos professores"""
        relatorio = []
        
        for professor in self.professores:
            for disciplina_nome, horas_disponiveis in professor.disciplinas.items():
                horas_usadas = self.horas_utilizadas.get(professor.nome, {}).get(disciplina_nome, 0)
                utilizacao = (horas_usadas / horas_disponiveis * 100) if horas_disponiveis > 0 else 0
                
                relatorio.append({
                    'Professor': professor.nome,
                    'Disciplina': disciplina_nome,
                    'Horas Disponível': horas_disponiveis,
                    'Horas Utilizada': horas_usadas,
                    'Utilização (%)': f"{utilizacao:.1f}%",
                    'Status': '✅ OK' if horas_usadas <= horas_disponiveis else '❌ Excedido'
                })
        
        return relatorio

# ============================================
# INTERFACE STREAMLIT PRINCIPAL
# ============================================

def main():
    st.set_page_config(
        page_title="Sistema de Grade Horária",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 Sistema de Grade Horária Escolar")
    st.markdown("---")
    
    # Inicializar sessão
    inicializar_sessao()
    
    # Verificar se base está vazia e mostrar botão para carregar dados de exemplo
    if verificar_base_vazia():
        st.warning("⚠️ A base de dados está vazia!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📥 Carregar Dados de Exemplo (490/490)", type="primary", use_container_width=True):
                with st.spinner("Carregando dados de exemplo..."):
                    carregar_dados_exemplo()
                    st.success("✅ Dados de exemplo carregados com sucesso!")
                    st.rerun()
        
        st.info("💡 Após carregar os dados de exemplo, você pode:")
        st.write("1. Verificar o balanço 490/490 no Dashboard")
        st.write("2. Usar a aba '📊 Análise de Cobertura' para verificar se há horas suficientes")
        st.write("3. Gerar grades na aba '🗓️ Gerar Grade'")
        st.write("4. Adicionar, editar ou remover dados conforme necessário")
        
        st.markdown("---")
    
    # Menu de navegação principal
    st.sidebar.title("📚 Navegação")
    menu = st.sidebar.radio(
        "Selecione a página:",
        ["🏠 Dashboard", "👨‍🏫 Professores", "📚 Disciplinas", 
         "👥 Turmas", "📊 Análise de Cobertura", "🗓️ Gerar Grade", "📋 Visualizar Grades"]
    )
    
    # ============================================
    # BOTÕES DE ADMINISTRAÇÃO NA SIDEBAR
    # ============================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Administração")
    
    # Botão para carregar dados de exemplo
    if st.sidebar.button("📥 Carregar Dados Exemplo", use_container_width=True):
        with st.spinner("Carregando dados de exemplo..."):
            carregar_dados_exemplo()
            st.sidebar.success("✅ Dados carregados!")
            st.rerun()
    
    # Botão para verificar balanço
    if st.sidebar.button("⚖️ Verificar Balanço 490/490", use_container_width=True):
        if st.session_state.turmas:
            capacidade, necessarias, disponiveis = verificar_balanco_490()
            if capacidade == 490 and necessarias == 490 and disponiveis == 490:
                st.sidebar.success("✅ Sistema equilibrado: 490/490/490")
            else:
                st.sidebar.error(f"❌ Desequilibrado: {capacidade}/{necessarias}/{disponiveis}")
    
    # Botão para limpar todos os dados
    if st.sidebar.button("🗑️ Limpar Todos os Dados", type="secondary", use_container_width=True):
        if st.sidebar.checkbox("Confirmar limpeza total"):
            st.session_state.professores = []
            st.session_state.disciplinas = []
            st.session_state.turmas = []
            st.session_state.grades = []
            st.session_state.proximo_id_professor = 1
            st.session_state.proximo_id_disciplina = 1
            st.session_state.proximo_id_turma = 1
            st.session_state.proximo_id_grade = 1
            st.session_state.proximo_id_aula = 1
            st.sidebar.success("✅ Todos os dados foram limpos!")
            st.rerun()
    
    # Botão para gerar relatório
    if st.sidebar.button("📊 Gerar Relatório", use_container_width=True):
        if st.session_state.turmas:
            relatorio = gerar_relatorio_detalhado()
            st.sidebar.success("✅ Relatório gerado!")
            # Aqui você pode implementar a exibição ou download do relatório
    
    # Estatísticas rápidas na sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Estatísticas")
    st.sidebar.write(f"👨‍🏫 Professores: {len(st.session_state.professores)}")
    st.sidebar.write(f"📚 Disciplinas: {len(st.session_state.disciplinas)}")
    st.sidebar.write(f"👥 Turmas: {len(st.session_state.turmas)}")
    st.sidebar.write(f"🗓️ Grades: {len(st.session_state.grades)}")
    
    # Verificar balanço na sidebar
    if st.session_state.turmas:
        capacidade, necessarias, disponiveis = verificar_balanco_490()
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚖️ Balanço")
        st.sidebar.write(f"Capacidade: {capacidade}/490")
        st.sidebar.write(f"Aulas necessárias: {necessarias}/490")
        st.sidebar.write(f"Horas disponíveis: {disponiveis}/490")
        
        if capacidade == 490 and necessarias == 490 and disponiveis == 490:
            st.sidebar.success("✅ Equilibrado!")
        else:
            st.sidebar.error("❌ Desequilibrado")
    
    # ============================================
    # DASHBOARD
    # ============================================
    if menu == "🏠 Dashboard":
        st.header("📊 Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Professores", len(st.session_state.professores))
        with col2:
            st.metric("Disciplinas", len(st.session_state.disciplinas))
        with col3:
            st.metric("Turmas", len(st.session_state.turmas))
        with col4:
            st.metric("Grades Geradas", len(st.session_state.grades))
        
        # Verificação do balanço 490/490
        st.markdown("---")
        st.subheader("⚖️ Verificação do Balanço 490/490/490")
        
        if st.session_state.turmas:
            capacidade, necessarias, disponiveis = verificar_balanco_490()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Capacidade Total", capacidade, delta=f"{capacidade-490}")
            with col2:
                st.metric("Aulas Necessárias", necessarias, delta=f"{necessarias-490}")
            with col3:
                st.metric("Horas Disponíveis", disponiveis, delta=f"{disponiveis-490}")
            
            if capacidade == 490 and necessarias == 490 and disponiveis == 490:
                st.success("✅ PERFEITO! Sistema equilibrado em 490/490/490")
                
                # Teste rápido de geração
                st.markdown("---")
                st.subheader("🧪 Teste Rápido de Geração")
                
                col_test1, col_test2 = st.columns(2)
                with col_test1:
                    if st.button("Testar Grupo A", type="secondary", use_container_width=True):
                        with st.spinner("Testando geração para Grupo A..."):
                            try:
                                turmas_filtradas = [t for t in st.session_state.turmas if obter_grupo_seguro(t) == "A"]
                                disciplinas_filtradas = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == "A"]
                                professores_filtrados = [p for p in st.session_state.professores if obter_grupo_seguro(p) in ["A", "AMBOS"]]
                                
                                gerador = GeradorGrade(turmas_filtradas, disciplinas_filtradas, professores_filtrados)
                                aulas_alocadas, _ = gerador.gerar_grade_simples()
                                
                                total_aulas = sum(d.carga_semanal for d in disciplinas_filtradas 
                                                for turma in turmas_filtradas if turma.nome in d.turmas)
                                
                                st.success(f"✅ Teste OK!")
                                st.write(f"Aulas geradas: {len(aulas_alocadas)} de {total_aulas} necessárias")
                                st.write(f"Conflitos: {gerador.verificar_conflitos()}")
                                st.write(f"Aulas sem professor: {sum(1 for a in aulas_alocadas if a.professor == 'SEM PROFESSOR')}")
                                
                                # Mostrar grade visual da primeira turma
                                if turmas_filtradas and turmas_filtradas[0].nome in st.session_state.aulas_por_turma:
                                    mostrar_grade_visual(turmas_filtradas[0].nome, st.session_state.aulas_por_turma[turmas_filtradas[0].nome])
                                
                            except Exception as e:
                                st.error(f"❌ Erro: {str(e)}")
                
                with col_test2:
                    if st.button("Testar Todas Turmas", type="primary", use_container_width=True):
                        with st.spinner("Testando geração completa..."):
                            try:
                                gerador = GeradorGrade(
                                    st.session_state.turmas,
                                    st.session_state.disciplinas,
                                    st.session_state.professores
                                )
                                aulas_alocadas, _ = gerador.gerar_grade_simples()
                                
                                total_aulas = sum(d.get_carga_total_necessaria() for d in st.session_state.disciplinas)
                                
                                st.success(f"✅ Teste OK!")
                                st.write(f"Aulas geradas: {len(aulas_alocadas)} de {total_aulas} necessárias")
                                st.write(f"Conflitos: {gerador.verificar_conflitos()}")
                                st.write(f"Aulas sem professor: {sum(1 for a in aulas_alocadas if a.professor == 'SEM PROFESSOR')}")
                                
                            except Exception as e:
                                st.error(f"❌ Erro: {str(e)}")
            else:
                st.error("❌ Sistema desequilibrado!")
                st.info("Verifique os dados carregados ou use 'Carregar Dados de Exemplo'")
        
        # Análise rápida de cobertura
        st.markdown("---")
        st.subheader("📈 Análise Rápida de Cobertura")
        
        if st.session_state.disciplinas and st.session_state.professores:
            analises = analisar_cobertura_disciplinas()
            
            if analises:
                # Calcular estatísticas
                total_disciplinas = len(analises)
                disciplinas_ok = sum(1 for a in analises if '✅' in a['Status'])
                disciplinas_parcial = sum(1 for a in analises if '⚠️' in a['Status'])
                disciplinas_problema = sum(1 for a in analises if '❌' in a['Status'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("✅ Cobertas", disciplinas_ok)
                with col2:
                    st.metric("⚠️ Parciais", disciplinas_parcial)
                with col3:
                    st.metric("❌ Críticas", disciplinas_problema)
                
                if disciplinas_problema > 0:
                    st.error(f"⚠️ {disciplinas_problema} disciplina(s) sem cobertura de professores!")
                    st.info("Acesse a aba '📊 Análise de Cobertura' para detalhes.")
    
    # ============================================
    # ABA PROFESSORES
    # ============================================
    elif menu == "👨‍🏫 Professores":
        st.header("👨‍🏫 Gerenciamento de Professores")
        
        # Verificar disciplinas cadastradas primeiro
        disciplinas_existentes = [d.nome for d in st.session_state.disciplinas]
        
        if not disciplinas_existentes:
            st.warning("⚠️ Cadastre disciplinas primeiro para associar aos professores.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Professor")
            
            with st.form("form_professor"):
                nome = st.text_input("Nome do Professor")
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                
                # Configuração de horas por disciplina
                st.markdown("**Horas por Disciplina (aulas de 50min):**")
                disciplinas_horas = {}
                
                if disciplinas_existentes:
                    # Usar um contador único para cada linha
                    contador = 0
                    for disciplina_nome in disciplinas_existentes:
                        contador += 1
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(disciplina_nome)
                        with col_b:
                            # Chave única usando contador + hash
                            horas = st.number_input(
                                f"Horas",
                                min_value=0,
                                max_value=40,
                                value=0,
                                key=f"horas_{contador}_{hash(disciplina_nome)}"
                            )
                            if horas > 0:
                                disciplinas_horas[disciplina_nome] = horas
                else:
                    st.info("Nenhuma disciplina cadastrada")
                
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    max_aulas_dia = st.number_input("Máx Aulas/Dia", 1, 10, 6, key="prof_max_aulas")
                with col_sub2:
                    min_aulas_dia = st.number_input("Mín Aulas/Dia", 0, 5, 0, key="prof_min_aulas")
                
                if st.form_submit_button("💾 Salvar Professor"):
                    if nome:
                        professor = Professor(
                            id=st.session_state.proximo_id_professor,
                            nome=nome,
                            grupo=grupo,
                            disciplinas=disciplinas_horas,
                            max_aulas_dia=max_aulas_dia,
                            min_aulas_dia=min_aulas_dia
                        )
                        
                        st.session_state.professores.append(professor)
                        st.session_state.proximo_id_professor += 1
                        st.success(f"Professor {nome} cadastrado!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Professores")
            
            if st.session_state.professores:
                # Selecionar professor para detalhes
                professores_nomes = [p.nome for p in st.session_state.professores]
                professor_detalhe = st.selectbox("Selecionar professor para detalhes", 
                                               ["Selecione..."] + professores_nomes,
                                               key="select_detalhe_prof")
                
                if professor_detalhe != "Selecione...":
                    professor = next((p for p in st.session_state.professores 
                                    if p.nome == professor_detalhe), None)
                    
                    if professor:
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.write(f"**Nome:** {professor.nome}")
                            st.write(f"**Grupo:** {professor.grupo}")
                        with col_info2:
                            st.write(f"**Máx Aulas/Dia:** {professor.max_aulas_dia}")
                            st.write(f"**Mín Aulas/Dia:** {professor.min_aulas_dia}")
                        
                        st.markdown("**Disciplinas e Horas (aulas de 50min):**")
                        if professor.disciplinas:
                            df_disciplinas = pd.DataFrame(
                                professor.disciplinas.items(),
                                columns=['Disciplina', 'Horas Disponíveis']
                            )
                            st.dataframe(df_disciplinas, use_container_width=True)
                            
                            total_horas = professor.get_total_horas_disponiveis()
                            st.write(f"**Total de horas disponíveis:** {total_horas} aulas")
                        else:
                            st.warning("Este professor não tem disciplinas associadas")
                
                # Lista completa em formato de tabela
                st.markdown("---")
                st.subheader("📊 Todos os Professores")
                
                dados_professores = []
                for prof in st.session_state.professores:
                    total_horas = prof.get_total_horas_disponiveis()
                    num_disciplinas = len(prof.disciplinas)
                    
                    dados_professores.append({
                        "ID": prof.id,
                        "Nome": prof.nome,
                        "Grupo": prof.grupo,
                        "Disciplinas": num_disciplinas,
                        "Total Horas": total_horas,
                        "Máx/Dia": prof.max_aulas_dia,
                        "Mín/Dia": prof.min_aulas_dia
                    })
                
                df = pd.DataFrame(dados_professores)
                st.dataframe(df, use_container_width=True)
                
                # Opção de remover
                st.markdown("---")
                st.subheader("🗑️ Remover Professor")
                professor_remover = st.selectbox("Selecionar professor para remover", 
                                               ["Selecione..."] + professores_nomes,
                                               key="select_remover_prof")
                
                if st.button("🗑️ Remover Professor", type="secondary", key="btn_remover_professor"):
                    if professor_remover != "Selecione...":
                        st.session_state.professores = [p for p in st.session_state.professores 
                                                      if p.nome != professor_remover]
                        st.success(f"Professor {professor_remover} removido!")
                        st.rerun()
            else:
                st.info("📭 Nenhum professor cadastrado ainda.")
    
    # ============================================
    # ABA ANÁLISE DE COBERTURA
    # ============================================
    elif menu == "📊 Análise de Cobertura":
        st.header("📊 Análise de Cobertura de Professores")
        
        if not st.session_state.disciplinas:
            st.warning("Cadastre disciplinas primeiro para fazer a análise.")
        elif not st.session_state.professores:
            st.warning("Cadastre professores primeiro para fazer a análise.")
        else:
            # Análise detalhada
            analises = analisar_cobertura_disciplinas()
            
            if analises:
                # Converter para DataFrame
                df_analise = pd.DataFrame(analises)
                
                # Remover coluna interna de cor
                df_display = df_analise.drop('_cor', axis=1)
                
                # Exibir tabela
                st.dataframe(df_display, use_container_width=True)
                
                # Estatísticas
                st.markdown("---")
                st.subheader("📈 Estatísticas")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_carga = df_analise['Carga Total'].sum()
                    st.metric("Carga Horária Total", total_carga)
                
                with col2:
                    total_horas_disp = df_analise['Horas Disponível'].sum()
                    st.metric("Horas Disponíveis", total_horas_disp)
                
                with col3:
                    total_horas_comp = df_analise['Horas Compatível'].sum()
                    st.metric("Horas Compatíveis", total_horas_comp)
                
                # Recomendações
                st.markdown("---")
                st.subheader("🎯 Recomendações")
                
                recomendacoes = calcular_necessidade_professores()
                
                if recomendacoes:
                    st.warning("⚠️ Ações necessárias:")
                    
                    for rec in recomendacoes:
                        with st.expander(f"{rec['Disciplina']} - Deficit: {rec['Deficit']} aulas"):
                            st.write(f"**Disciplina:** {rec['Disciplina']}")
                            st.write(f"**Grupo:** {rec['Grupo']}")
                            st.write(f"**Carga necessária:** {rec['Carga Necessária']} aulas")
                            st.write(f"**Horas disponíveis:** {rec['Horas Disponível']} aulas")
                            st.write(f"**Deficit:** {rec['Deficit']} aulas")
                            st.write(f"**Professores compatíveis:** {rec['Professores Compativeis']}")
                            st.write(f"**Ação recomendada:** {rec['Ação Recomendada']}")
                            
                            # Sugestões de solução
                            st.info("**Soluções possíveis:**")
                            st.write("1. Contratar novo professor para esta disciplina")
                            st.write("2. Aumentar horas disponíveis de professores existentes")
                            st.write("3. Reduzir carga horária da disciplina nas turmas")
                            st.write("4. Remover disciplina de algumas turmas")
                else:
                    st.success("✅ Todas as disciplinas têm cobertura adequada!")
                
                # Gráfico de status
                st.markdown("---")
                st.subheader("📊 Distribuição por Status")
                
                status_counts = df_analise['Status'].value_counts()
                st.bar_chart(status_counts)
                
                # Exportar análise
                st.markdown("---")
                st.subheader("💾 Exportar Análise")
                
                if st.button("📥 Exportar para CSV"):
                    csv = df_display.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Baixar CSV",
                        data=csv,
                        file_name="analise_cobertura.csv",
                        mime="text/csv"
                    )
    
    # ============================================
    # ABA DISCIPLINAS
    # ============================================
    elif menu == "📚 Disciplinas":
        st.header("📚 Gerenciamento de Disciplinas")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Disciplina")
            
            with st.form("form_disciplina"):
                nome = st.text_input("Nome da Disciplina")
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                carga_semanal = st.number_input("Carga Semanal (aulas de 50min)", 1, 20, 4)
                
                # Selecionar turmas
                turmas_opcoes = [t.nome for t in st.session_state.turmas]
                turmas_selecionadas = st.multiselect("Turmas", turmas_opcoes)
                
                if st.form_submit_button("💾 Salvar Disciplina"):
                    if nome:
                        disciplina = Disciplina(
                            id=st.session_state.proximo_id_disciplina,
                            nome=nome,
                            grupo=grupo,
                            turmas=turmas_selecionadas,
                            carga_semanal=carga_semanal
                        )
                        
                        st.session_state.disciplinas.append(disciplina)
                        st.session_state.proximo_id_disciplina += 1
                        st.success(f"Disciplina {nome} cadastrada!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Disciplinas")
            
            if st.session_state.disciplinas:
                dados_disciplinas = []
                for disc in st.session_state.disciplinas:
                    dados_disciplinas.append({
                        "ID": disc.id,
                        "Nome": disc.nome,
                        "Grupo": disc.grupo,
                        "Carga/Turma": disc.carga_semanal,
                        "Turmas": len(disc.turmas),
                        "Carga Total": disc.get_carga_total_necessaria()
                    })
                
                df = pd.DataFrame(dados_disciplinas)
                st.dataframe(df, use_container_width=True)
                
                # Opção de remover
                disciplinas_nomes = [d.nome for d in st.session_state.disciplinas]
                disciplina_remover = st.selectbox("Selecionar disciplina para remover", 
                                                ["Selecione..."] + disciplinas_nomes)
                
                if st.button("🗑️ Remover Disciplina", type="secondary"):
                    if disciplina_remover != "Selecione...":
                        st.session_state.disciplinas = [d for d in st.session_state.disciplinas 
                                                      if d.nome != disciplina_remover]
                        st.success(f"Disciplina {disciplina_remover} removida!")
                        st.rerun()
            else:
                st.info("📭 Nenhuma disciplina cadastrada ainda.")
    
    # ============================================
    # ABA TURMAS
    # ============================================
    elif menu == "👥 Turmas":
        st.header("👥 Gerenciamento de Turmas")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Adicionar Turma")
            
            with st.form("form_turma"):
                nome = st.text_input("Nome da Turma")
                serie = st.selectbox("Série", ["6º EF", "7º EF", "8º EF", "9º EF", "1º EM", "2º EM", "3º EM"])
                grupo = st.selectbox("Grupo", ["A", "B", "AMBOS"])
                turno = st.selectbox("Turno", ["MANHÃ", "TARDE"])
                
                if st.form_submit_button("💾 Salvar Turma"):
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
                        st.success(f"Turma {nome} cadastrada!")
                        st.rerun()
        
        with col2:
            st.subheader("📋 Lista de Turmas")
            
            if st.session_state.turmas:
                dados_turmas = []
                for turma in st.session_state.turmas:
                    dados_turmas.append({
                        "ID": turma.id,
                        "Nome": turma.nome,
                        "Série": turma.serie,
                        "Grupo": turma.grupo,
                        "Turno": turma.turno
                    })
                
                df = pd.DataFrame(dados_turmas)
                st.dataframe(df, use_container_width=True)
                
                # Opção de remover
                turmas_nomes = [t.nome for t in st.session_state.turmas]
                turma_remover = st.selectbox("Selecionar turma para remover", 
                                           ["Selecione..."] + turmas_nomes)
                
                if st.button("🗑️ Remover Turma", type="secondary"):
                    if turma_remover != "Selecione...":
                        st.session_state.turmas = [t for t in st.session_state.turmas 
                                                 if t.nome != turma_remover]
                        st.success(f"Turma {turma_remover} removida!")
                        st.rerun()
            else:
                st.info("📭 Nenhuma turma cadastrada ainda.")
    
    # ============================================
    # ABA GERAR GRADE
    # ============================================
    elif menu == "🗓️ Gerar Grade":
        st.header("🗓️ Gerar Grade Horária")
        
        # Verificar pré-requisitos
        if not st.session_state.turmas:
            st.error("❌ Cadastre turmas primeiro!")
            return
        if not st.session_state.disciplinas:
            st.error("❌ Cadastre disciplinas primeiro!")
            return
        if not st.session_state.professores:
            st.error("❌ Cadastre professores primeiro!")
            return
        
        st.subheader("🎯 Configurações da Grade")
        
        col1, col2 = st.columns(2)
        with col1:
            tipo_grade = st.selectbox(
                "Tipo de Grade",
                [
                    "Grade Completa - Todas as Turmas",
                    "Grade por Grupo A",
                    "Grade por Grupo B", 
                    "Grade por Turma Específica"
                ]
            )
            
            if tipo_grade == "Grade por Turma Específica":
                turmas_opcoes = [t.nome for t in st.session_state.turmas]
                if turmas_opcoes:
                    turma_selecionada = st.selectbox("Selecionar Turma", turmas_opcoes)
                else:
                    turma_selecionada = None
        
        with col2:
            tipo_algoritmo = st.selectbox(
                "Algoritmo de Geração",
                ["Algoritmo Simples (Rápido)"]
            )
            
            tipo_completador = st.selectbox(
                "Algoritmo de Completude",
                ["Completador Básico", "Completador Avançado (Recomendado)"],
                help="O completador avançado usa múltiplas estratégias para tentar completar grades incompletas"
            )
            
            st.info("📅 **EM: 07:00-13:10 (7 períodos de 50min)**")
            st.info("📅 **EF II: 07:50-14:00 (7 períodos de 50min)**")
        
        # Análise de cobertura antes de gerar
        st.subheader("📊 Análise de Cobertura para Geração")
        
        if tipo_grade == "Grade por Grupo A":
            turmas_filtradas = [t for t in st.session_state.turmas if obter_grupo_seguro(t) == "A"]
            grupo_texto = "Grupo A"
        elif tipo_grade == "Grade por Grupo B":
            turmas_filtradas = [t for t in st.session_state.turmas if obter_grupo_seguro(t) == "B"]
            grupo_texto = "Grupo B"
        elif tipo_grade == "Grade por Turma Específica" and turma_selecionada:
            turmas_filtradas = [t for t in st.session_state.turmas if t.nome == turma_selecionada]
            grupo_texto = f"Turma {turma_selecionada}"
        else:
            turmas_filtradas = st.session_state.turmas
            grupo_texto = "Todas as Turmas"
        
        if tipo_grade == "Grade por Grupo A":
            disciplinas_filtradas = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == "A"]
        elif tipo_grade == "Grade por Grupo B":
            disciplinas_filtradas = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == "B"]
        else:
            disciplinas_filtradas = st.session_state.disciplinas
        
        # Análise de viabilidade
        total_aulas = 0
        aulas_por_turma = {}
        problemas_carga = []
        
        for turma in turmas_filtradas:
            aulas_turma = 0
            grupo_turma = obter_grupo_seguro(turma)
            
            for disc in disciplinas_filtradas:
                disc_grupo = obter_grupo_seguro(disc)
                if turma.nome in disc.turmas and disc_grupo == grupo_turma:
                    aulas_turma += disc.carga_semanal
                    total_aulas += disc.carga_semanal
            
            aulas_por_turma[turma.nome] = aulas_turma
            
            carga_maxima = calcular_carga_maxima(turma.serie)
            if aulas_turma != carga_maxima:
                status = "✅" if aulas_turma == carga_maxima else "⚠️" if aulas_turma <= carga_maxima else "❌"
                problemas_carga.append(f"{turma.nome} [{grupo_turma}]: {aulas_turma}h {status} {carga_maxima}h máximo")
        
        capacidade_total = 0
        for turma in turmas_filtradas:
            horarios_turma = obter_horarios_turma(turma.nome)
            capacidade_total += len(DIAS_SEMANA) * len(horarios_turma)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Turmas", len(turmas_filtradas))
        with col2:
            st.metric("Aulas Necessárias", total_aulas)
        with col3:
            st.metric("Capacidade Disponível", capacidade_total)
        
        if problemas_carga:
            st.warning("⚠️ Observações sobre carga horária:")
            for problema in problemas_carga:
                st.write(f"- {problema}")
        
        # Análise de cobertura específica
        st.subheader("👨‍🏫 Análise de Cobertura de Professores")
        
        # Verificar cobertura para as disciplinas filtradas
        cobertura_problemas = []
        for disc in disciplinas_filtradas:
            carga_total = disc.get_carga_total_necessaria()
            horas_disponiveis = 0
            
            for professor in st.session_state.professores:
                horas_prof = professor.get_horas_disponiveis(disc.nome)
                if horas_prof > 0:
                    # Verificar compatibilidade de grupo
                    prof_grupo = professor.grupo
                    disc_grupo = disc.grupo
                    
                    if (prof_grupo == disc_grupo or 
                        prof_grupo == 'AMBOS' or 
                        disc_grupo == 'AMBOS'):
                        horas_disponiveis += horas_prof
            
            if horas_disponiveis < carga_total:
                deficit = carga_total - horas_disponiveis
                cobertura_problemas.append({
                    'disciplina': disc.nome,
                    'carga_total': carga_total,
                    'horas_disponiveis': horas_disponiveis,
                    'deficit': deficit
                })
        
        if cobertura_problemas:
            st.error("❌ Problemas de cobertura detectados:")
            for problema in cobertura_problemas:
                st.write(f"- **{problema['disciplina']}**: {problema['deficit']} aulas em deficit "
                        f"({problema['horas_disponiveis']}/{problema['carga_total']})")
            
            st.warning("⚠️ Geração de grade pode resultar em aulas sem professor!")
        else:
            st.success("✅ Todas as disciplinas têm cobertura adequada!")
        
        if total_aulas == 0:
            st.error("❌ Nenhuma aula para alocar! Verifique as disciplinas.")
        elif total_aulas > capacidade_total:
            st.error("❌ Capacidade insuficiente! Reduza a carga horária.")
        else:
            st.success("✅ Pronto para gerar grade!")
            
            nome_grade = st.text_input("Nome da Grade", value=f"Grade {grupo_texto}")
            
            if st.button("🚀 Gerar Grade Horária", type="primary", use_container_width=True):
                if not turmas_filtradas:
                    st.error("❌ Nenhuma turma selecionada!")
                elif not disciplinas_filtradas:
                    st.error("❌ Nenhuma disciplina disponível!")
                else:
                    with st.spinner(f"Gerando grade para {grupo_texto}..."):
                        try:
                            # Filtrar professores
                            if tipo_grade == "Grade por Grupo A":
                                professores_filtrados = [p for p in st.session_state.professores 
                                                       if obter_grupo_seguro(p) in ["A", "AMBOS"]]
                            elif tipo_grade == "Grade por Grupo B":
                                professores_filtrados = [p for p in st.session_state.professores 
                                                       if obter_grupo_seguro(p) in ["B", "AMBOS"]]
                            else:
                                professores_filtrados = st.session_state.professores
                            
                            # Gerar grade
                            gerador = GeradorGrade(turmas_filtradas, disciplinas_filtradas, professores_filtrados)
                            aulas_alocadas, aulas_por_turma_dict = gerador.gerar_grade_simples()
                            
                            conflitos = gerador.verificar_conflitos()
                            st.session_state.proximo_id_aula = gerador.proximo_id_aula
                            
                            # Criar objeto Grade
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
                            
                            # Mostrar resultados
                            st.success(f"✅ Grade gerada com sucesso!")
                            
                            # Relatório de utilização
                            st.subheader("📊 Relatório de Utilização")
                            relatorio = gerador.gerar_relatorio_utilizacao()
                            
                            if relatorio:
                                df_relatorio = pd.DataFrame(relatorio)
                                st.dataframe(df_relatorio, use_container_width=True)
                            
                            st.info(f"📊 Estatísticas da grade:")
                            st.write(f"- Total de aulas alocadas: {len(aulas_alocadas)}")
                            st.write(f"- Conflitos detectados: {conflitos}")
                            st.write(f"- Turmas na grade: {len(turmas_filtradas)}")
                            
                            # Contar aulas sem professor
                            aulas_sem_professor = sum(1 for a in aulas_alocadas if a.professor == "SEM PROFESSOR")
                            if aulas_sem_professor > 0:
                                st.warning(f"⚠️ {aulas_sem_professor} aulas sem professor alocado")
                            
                            # Mostrar grade visual para primeira turma
                            if turmas_filtradas:
                                primeira_turma = turmas_filtradas[0].nome
                                if primeira_turma in st.session_state.aulas_por_turma:
                                    mostrar_grade_visual(primeira_turma, st.session_state.aulas_por_turma[primeira_turma])
                            
                            # Mostrar preview
                            st.subheader("👁️ Preview da Grade")
                            if aulas_alocadas:
                                dados_preview = []
                                for aula in aulas_alocadas[:20]:  # Mostrar primeiras 20 aulas
                                    dados_preview.append({
                                        "Turma": aula.turma,
                                        "Disciplina": aula.disciplina,
                                        "Professor": aula.professor,
                                        "Dia": aula.dia,
                                        "Horário": aula.horario,
                                        "Período": aula.periodo
                                    })
                                
                                df_preview = pd.DataFrame(dados_preview)
                                st.dataframe(df_preview, use_container_width=True)
                                
                                if len(aulas_alocadas) > 20:
                                    st.caption(f"Mostrando 20 de {len(aulas_alocadas)} aulas")
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao gerar grade: {str(e)}")
    
    # ============================================
    # ABA VISUALIZAR GRADES
    # ============================================
    elif menu == "📋 Visualizar Grades":
        st.header("📋 Grades Geradas")
        
        if not st.session_state.grades:
            st.info("📭 Nenhuma grade gerada ainda.")
        else:
            # Lista de grades disponíveis
            grades_opcoes = [g.nome for g in st.session_state.grades]
            grade_selecionada = st.selectbox("Selecionar Grade para Visualizar", grades_opcoes)
            
            if grade_selecionada:
                grade = next((g for g in st.session_state.grades if g.nome == grade_selecionada), None)
                
                if grade:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Nome", grade.nome)
                    with col2:
                        st.metric("Status", grade.status)
                    with col3:
                        st.metric("Total Aulas", len(grade.aulas))
                    
                    st.write(f"**Turmas:** {', '.join(grade.turmas)}")
                    st.write(f"**Grupo:** {grade.grupo}")
                    
                    # Contar aulas sem professor
                    aulas_sem_prof = sum(1 for a in grade.aulas if a.professor == "SEM PROFESSOR")
                    if aulas_sem_prof > 0:
                        st.warning(f"⚠️ {aulas_sem_prof} aulas sem professor alocado")
                    
                    # Filtrar por turma
                    turmas_grade = list(set([a.turma for a in grade.aulas]))
                    turma_filtro = st.selectbox("Filtrar por Turma", ["Todas"] + turmas_grade)
                    
                    # Filtrar aulas
                    if turma_filtro == "Todas":
                        aulas_filtradas = grade.aulas
                    else:
                        aulas_filtradas = [a for a in grade.aulas if a.turma == turma_filtro]
                    
                    # Converter para DataFrame
                    if aulas_filtradas:
                        dados_aulas = []
                        for aula in aulas_filtradas:
                            dados_aulas.append({
                                "Turma": aula.turma,
                                "Disciplina": aula.disciplina,
                                "Professor": aula.professor,
                                "Dia": aula.dia,
                                "Horário": aula.horario,
                                "Período": aula.periodo
                            })
                        
                        df = pd.DataFrame(dados_aulas)
                        
                        # Ordenar
                        ordem_dias = {dia: i for i, dia in enumerate(DIAS_SEMANA)}
                        df['Ordem_Dia'] = df['Dia'].map(ordem_dias)
                        df = df.sort_values(['Turma', 'Ordem_Dia', 'Período'])
                        df = df.drop('Ordem_Dia', axis=1)
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # Botão para visualizar grade
                        if turma_filtro != "Todas" and turma_filtro in st.session_state.aulas_por_turma:
                            if st.button("📊 Visualizar Grade da Turma"):
                                mostrar_grade_visual(turma_filtro, st.session_state.aulas_por_turma[turma_filtro])
                        
                        # Opção de exportar
                        st.subheader("💾 Exportar Grade")
                        
                        col_exp1, col_exp2 = st.columns(2)
                        with col_exp1:
                            if st.button("📥 Exportar para Excel"):
                                excel_data = exportar_grade_excel(grade)
                                if excel_data:
                                    st.download_button(
                                        label="Baixar Excel",
                                        data=excel_data,
                                        file_name=f"grade_{grade.nome}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                        
                        with col_exp2:
                            if st.button("🗑️ Excluir Grade"):
                                if st.checkbox("Confirmar exclusão"):
                                    st.session_state.grades = [g for g in st.session_state.grades if g.id != grade.id]
                                    st.success(f"Grade {grade.nome} excluída!")
                                    st.rerun()
                    else:
                        st.warning(f"Nenhuma aula encontrada para o filtro selecionado.")

# ============================================
# EXECUÇÃO
# ============================================

if __name__ == "__main__":
    main()