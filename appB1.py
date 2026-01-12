# simple_scheduler.py
import random
from datetime import datetime

class SimpleGradeHoraria:
    def __init__(self, turmas, professores, disciplinas, salas):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = disciplinas
        self.salas = salas
        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        
    def gerar_grade(self):
        """Gera uma grade horária simples"""
        aulas = []
        
        for turma in self.turmas:
            # Determinar horários disponíveis para a turma
            if 'EM' in turma.nome or (hasattr(turma, 'segmento') and turma.segmento == 'EM'):
                periodos_disponiveis = list(range(1, 8))  # 7 períodos para EM
            else:
                periodos_disponiveis = list(range(1, 6))  # 5 períodos para EF II
            
            # Obter disciplinas desta turma
            disciplinas_turma = []
            for disc in self.disciplinas:
                if hasattr(disc, 'turmas') and turma.nome in disc.turmas:
                    # Verificar compatibilidade de grupo
                    disc_grupo = getattr(disc, 'grupo', 'A')
                    turma_grupo = getattr(turma, 'grupo', 'A')
                    
                    if disc_grupo == turma_grupo or disc_grupo == "AMBOS":
                        # Adicionar a disciplina múltiplas vezes conforme carga semanal
                        for _ in range(disc.carga_semanal):
                            disciplinas_turma.append(disc)
            
            if not disciplinas_turma:
                continue
            
            # Tenta alocar cada aula
            for disciplina in disciplinas_turma:
                alocada = False
                tentativas = 0
                
                while not alocada and tentativas < 100:
                    # Escolher dia e horário aleatórios
                    dia = random.choice(self.dias)
                    horario = random.choice(periodos_disponiveis)
                    
                    # Verificar se a turma já tem aula neste horário
                    conflito_turma = False
                    for aula_existente in aulas:
                        if (hasattr(aula_existente, 'turma') and aula_existente.turma == turma.nome and
                            aula_existente.dia == dia and aula_existente.horario == horario):
                            conflito_turma = True
                            break
                    
                    if conflito_turma:
                        tentativas += 1
                        continue
                    
                    # Encontrar professor disponível
                    professores_disponiveis = []
                    for professor in self.professores:
                        # Verificar se o professor ministra esta disciplina
                        if disciplina.nome not in professor.disciplinas:
                            continue
                        
                        # Verificar compatibilidade de grupo
                        prof_grupo = getattr(professor, 'grupo', 'AMBOS')
                        if prof_grupo not in [turma.grupo, "AMBOS"]:
                            continue
                        
                        # Verificar disponibilidade no dia
                        if dia not in professor.disponibilidade:
                            continue
                        
                        # Verificar horários bloqueados
                        horario_bloqueado = False
                        if hasattr(professor, 'horarios_indisponiveis'):
                            if f"{dia}_{horario}" in professor.horarios_indisponiveis:
                                horario_bloqueado = True
                        
                        if horario_bloqueado:
                            continue
                        
                        # Verificar se professor já tem aula neste horário
                        professor_ocupado = False
                        for aula_existente in aulas:
                            if (hasattr(aula_existente, 'professor') and 
                                aula_existente.professor == professor.nome and
                                aula_existente.dia == dia and 
                                aula_existente.horario == horario):
                                professor_ocupado = True
                                break
                        
                        if not professor_ocupado:
                            professores_disponiveis.append(professor)
                    
                    if professores_disponiveis:
                        # Escolher um professor aleatório disponível
                        professor_selecionado = random.choice(professores_disponiveis)
                        
                        # Criar aula
                        from models import Aula
                        segmento = 'EM' if 'EM' in turma.nome or (hasattr(turma, 'segmento') and turma.segmento == 'EM') else 'EF_II'
                        
                        nova_aula = Aula(
                            turma=turma.nome,
                            disciplina=disciplina.nome,
                            professor=professor_selecionado.nome,
                            dia=dia,
                            horario=horario,
                            segmento=segmento
                        )
                        
                        aulas.append(nova_aula)
                        alocada = True
                    else:
                        tentativas += 1
        
        return aulas