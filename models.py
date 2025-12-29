"""
Modelos de dados para o sistema de grade horária
"""

import uuid
from typing import List
from dataclasses import dataclass, asdict

# Constantes
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex"]

# Horários reais por período e segmento (para referência, não usados diretamente)
HORARIOS_REAIS = {
    "EF_II": {
        1: "07:50 - 08:40",
        2: "08:40 - 09:30",
        3: "09:50 - 10:40",
        4: "10:40 - 11:30",
        5: "11:30 - 12:20"
    },
    "EM": {
        1: "07:00 - 07:50",
        2: "07:50 - 08:40",
        3: "08:40 - 09:30",
        4: "09:50 - 10:40",
        5: "10:40 - 11:30",
        6: "11:30 - 12:20",
        7: "12:20 - 13:10"
    }
}

@dataclass
class Aula:
    """Representa uma aula alocada na grade horária"""
    turma: str
    disciplina: str
    professor: str
    dia: str
    horario: int  # Número do período (1-7 para EM, 1-5 para EF II)
    periodo: int = None  # Para compatibilidade, mesmo que horario
    segmento: str = None  # Segmento: "EF_II" ou "EM"
    sala: str = "Sala 1"
    grupo: str = "A"
    cor_fundo: str = "#4A90E2"
    cor_fonte: str = "#FFFFFF"
    
    def __post_init__(self):
        # Se periodo não foi fornecido, usa o mesmo valor de horario
        if self.periodo is None:
            self.periodo = self.horario
        # Se segmento não foi fornecido, tenta inferir
        if self.segmento is None:
            if 'em' in self.turma.lower():
                self.segmento = "EM"
            else:
                self.segmento = "EF_II"
    
    def to_dict(self):
        return asdict(self)

class Turma:
    def __init__(self, nome: str, serie: str, turno: str, grupo: str, segmento: str = None, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.serie = serie
        self.turno = turno
        self.grupo = grupo
        self.segmento = segmento or self._determinar_segmento()
    
    def _determinar_segmento(self):
        """Determina o segmento baseado na série"""
        if 'em' in self.serie.lower() or 'medio' in self.serie.lower():
            return "EM"
        else:
            return "EF_II"
    
    def get_horarios_disponiveis(self):
        """Retorna os períodos disponíveis para esta turma"""
        if self.segmento == "EM":
            return list(range(1, 8))  # Períodos 1-7
        else:
            return list(range(1, 6))  # Períodos 1-5
    
    def get_carga_maxima(self):
        """Retorna a carga horária máxima semanal"""
        if self.segmento == "EM":
            return 35  # 7 aulas × 5 dias
        else:
            return 25  # 5 aulas × 5 dias
    
    def __repr__(self):
        return f"Turma({self.nome}, {self.serie}, {self.grupo}, {self.segmento})"

class Professor:
    def __init__(self, nome: str, disciplinas: List[str], disponibilidade: List[str], 
                 grupo: str = "AMBOS", horarios_indisponiveis: List[str] = None, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.disciplinas = disciplinas
        self.disponibilidade = disponibilidade
        self.grupo = grupo
        self.horarios_indisponiveis = horarios_indisponiveis or []
    
    def __repr__(self):
        return f"Professor({self.nome}, {self.disciplinas})"

class Disciplina:
    def __init__(self, nome: str, carga_semanal: int, tipo: str, 
                 turmas: List[str], grupo: str = "A", 
                 cor_fundo: str = "#4A90E2", cor_fonte: str = "#FFFFFF", id: str = None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.carga_semanal = carga_semanal
        self.tipo = tipo
        self.turmas = turmas
        self.grupo = grupo
        self.cor_fundo = cor_fundo
        self.cor_fonte = cor_fonte
    
    def __repr__(self):
        return f"Disciplina({self.nome}, {self.carga_semanal}h, {self.grupo})"

class Sala:
    def __init__(self, nome: str, capacidade: int, tipo: str = "normal", id: str = None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.capacidade = capacidade
        self.tipo = tipo
    
    def __repr__(self):
        return f"Sala({self.nome}, {self.capacidade}, {self.tipo})"