"""
Algoritmo simples de geração de grade horária
"""

import random
import streamlit as st

class SimpleGradeHoraria:
    def __init__(self, turmas, professores, disciplinas, salas=None):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = {d.nome: d for d in disciplinas}
        self.salas = salas or []
        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        self.grade = {}
        self.aulas = []
        
    def _obter_segmento(self, turma_nome):
        """Retorna segmento da turma"""
        turma_obj = next((t for t in self.turmas if t.nome == turma_nome), None)
        if turma_obj and hasattr(turma_obj, 'segmento'):
            return turma_obj.segmento
        return "EF_II" if "ef" in turma_nome.lower() or "ano" in turma_nome.lower() else "EM"
    
    def _obter_periodos_turma(self, turma_nome):
        """Retorna períodos disponíveis"""
        segmento = self._obter_segmento(turma_nome)
        if segmento == "EM":
            return list(range(1, 8))  # 1-7
        else:
            return list(range(1, 6))  # 1-5
    
    def gerar_grade(self):
        """Gera grade horária usando algoritmo simples"""
        try:
            # Preparar disciplinas por turma
            disciplinas_por_turma = {}
            for turma in self.turmas:
                disciplinas_turma = []
                for nome_disc, disc in self.disciplinas.items():
                    if turma.nome in disc.turmas:
                        for _ in range(disc.carga_semanal):
                            disciplinas_turma.append(disc)
                random.shuffle(disciplinas_turma)
                disciplinas_por_turma[turma.nome] = disciplinas_turma
            
            # Alocar aulas
            aulas = []
            for turma in self.turmas:
                turma_nome = turma.nome
                grupo_turma = turma.grupo
                
                for dia in self.dias:
                    periodos = self._obter_periodos_turma(turma_nome)
                    
                    for periodo in periodos:
                        # Verificar se há disciplinas para alocar
                        if not disciplinas_por_turma[turma_nome]:
                            break
                        
                        # Pegar próxima disciplina
                        disc = disciplinas_por_turma[turma_nome].pop(0)
                        
                        # Encontrar professor
                        professor = self._encontrar_professor(disc.nome, grupo_turma, dia, periodo)
                        if not professor:
                            # Devolver disciplina se não encontrar professor
                            disciplinas_por_turma[turma_nome].append(disc)
                            continue
                        
                        # Criar aula
                        aula = {
                            'turma': turma_nome,
                            'disciplina': disc.nome,
                            'professor': professor,
                            'dia': dia,
                            'horario': periodo,
                            'segmento': self._obter_segmento(turma_nome)
                        }
                        aulas.append(aula)
            
            st.success(f"✅ {len(aulas)} aulas alocadas com algoritmo simples!")
            return aulas
            
        except Exception as e:
            st.error(f"Erro no algoritmo simples: {str(e)}")
            return []
    
    def _encontrar_professor(self, disciplina_nome, grupo_turma, dia, horario):
        """Encontra professor disponível"""
        professores_candidatos = []
        
        for prof in self.professores:
            # Verificar competência
            if disciplina_nome not in prof.disciplinas:
                continue
            
            # Verificar grupo
            if prof.grupo != "AMBOS" and prof.grupo != grupo_turma:
                continue
            
            # Verificar disponibilidade
            if dia not in prof.disponibilidade:
                continue
            
            # Verificar horários indisponíveis
            if f"{dia}_{horario}" in prof.horarios_indisponiveis:
                continue
            
            professores_candidatos.append(prof.nome)
        
        return random.choice(professores_candidatos) if professores_candidatos else None