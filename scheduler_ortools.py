"""
GradeHorariaORTools - Versão otimizada para OR-Tools
"""

from ortools.sat.python import cp_model
from collections import defaultdict
import streamlit as st

class GradeHorariaORTools:
    def __init__(self, turmas, professores, disciplinas, relaxar_horario_ideal=False):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = {d.nome: d for d in disciplinas}
        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        self.relaxar_horario_ideal = relaxar_horario_ideal
        
        # Configurações por segmento
        self.config_segmento = {
            "EF_II": {
                "total_periodos": 5,
                "horarios_reais": {
                    1: "07:50-08:40",
                    2: "08:40-09:30",
                    3: "09:50-10:40", 
                    4: "10:40-11:30",
                    5: "11:30-12:20"
                }
            },
            "EM": {
                "total_periodos": 7,
                "horarios_reais": {
                    1: "07:00-07:50",
                    2: "07:50-08:40",
                    3: "08:40-09:30",
                    4: "09:50-10:40",
                    5: "10:40-11:30",
                    6: "11:30-12:20",
                    7: "12:20-13:10"
                }
            }
        }
        
        # Inicializar modelo
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solver.parameters.max_time_in_seconds = 120.0
        
        self.variaveis = {}
        self.atribuicoes_possiveis = {}
        
        # Processar dados
        self._processar_dados()
        self._criar_variaveis()
        self._adicionar_restricoes()
    
    def _obter_segmento(self, turma_nome):
        """Retorna segmento da turma"""
        turma_obj = next((t for t in self.turmas if t.nome == turma_nome), None)
        if turma_obj and hasattr(turma_obj, 'segmento'):
            return turma_obj.segmento
        return "EF_II" if "ef" in turma_nome.lower() or "ano" in turma_nome.lower() else "EM"
    
    def _processar_dados(self):
        """Processa todos os dados para criar combinações possíveis"""
        st.info("🔧 Processando dados...")
        
        # Criar lista de disciplinas por turma
        disciplinas_por_turma = defaultdict(list)
        for turma in self.turmas:
            for disc_nome, disc in self.disciplinas.items():
                if turma.nome in disc.turmas:
                    for _ in range(disc.carga_semanal):
                        disciplinas_por_turma[turma.nome].append(disc_nome)
        
        # Para cada turma, criar combinações possíveis
        for turma_nome, disciplinas in disciplinas_por_turma.items():
            segmento = self._obter_segmento(turma_nome)
            config = self.config_segmento[segmento]
            periodos_disponiveis = list(range(1, config["total_periodos"] + 1))
            
            # Para cada disciplina necessária
            for disc_nome in set(disciplinas):
                disc_obj = self.disciplinas.get(disc_nome)
                
                # Para cada dia e período
                for dia in self.dias:
                    for periodo in periodos_disponiveis:
                        # Encontrar professores disponíveis
                        profs_disponiveis = []
                        for prof in self.professores:
                            # Verificar se professor ministra a disciplina
                            if disc_nome not in prof.disciplinas:
                                continue
                            
                            # Verificar disponibilidade no dia
                            if dia not in prof.disponibilidade:
                                continue
                            
                            # Verificar horários indisponíveis
                            horario_str = f"{dia}_{periodo}"
                            if isinstance(prof.horarios_indisponiveis, set):
                                if horario_str in prof.horarios_indisponiveis:
                                    continue
                            elif isinstance(prof.horarios_indisponiveis, list):
                                if horario_str in prof.horarios_indisponiveis:
                                    continue
                            
                            # Verificar grupo
                            prof_grupo = getattr(prof, 'grupo', 'A')
                            turma_grupo = next((t.grupo for t in self.turmas if t.nome == turma_nome), 'A')
                            if prof_grupo not in [turma_grupo, "AMBOS"]:
                                continue
                            
                            profs_disponiveis.append(prof.nome)
                        
                        if profs_disponiveis:
                            chave = (turma_nome, disc_nome, dia, periodo)
                            self.atribuicoes_possiveis[chave] = profs_disponiveis
        
        st.info(f"📊 Criadas {len(self.atribuicoes_possiveis)} combinações possíveis")
    
    def _criar_variaveis(self):
        """Cria variáveis de decisão"""
        st.info("🎲 Criando variáveis...")
        
        for (turma, disc, dia, periodo), profs in self.atribuicoes_possiveis.items():
            for prof in profs:
                var = self.model.NewBoolVar(f'aula_{turma}_{disc}_{dia}_{periodo}_{prof}')
                self.variaveis[(turma, disc, dia, periodo, prof)] = var
    
    def _adicionar_restricoes(self):
        """Adiciona restrições ao modelo"""
        st.info("🔒 Adicionando restrições...")
        
        # 1. Cada aula pendente deve ser alocada
        contagem_por_turma_disc = defaultdict(int)
        for turma in self.turmas:
            for disc_nome, disc in self.disciplinas.items():
                if turma.nome in disc.turmas:
                    contagem_por_turma_disc[(turma.nome, disc_nome)] = disc.carga_semanal
        
        # Para cada par (turma, disciplina), garantir que tenha o número correto de aulas
        for (turma_nome, disc_nome), total_necessario in contagem_por_turma_disc.items():
            vars_turma_disc = []
            for (t, d, di, p, prof), var in self.variaveis.items():
                if t == turma_nome and d == disc_nome:
                    vars_turma_disc.append(var)
            
            if vars_turma_disc:
                self.model.Add(sum(vars_turma_disc) == total_necessario)
        
        # 2. Professor não pode dar duas aulas ao mesmo tempo
        for prof in self.professores:
            for dia in self.dias:
                for periodo in range(1, 8):  # 1-7 períodos
                    vars_prof = []
                    for (t, d, di, p, pr), var in self.variaveis.items():
                        if pr == prof.nome and di == dia and p == periodo:
                            vars_prof.append(var)
                    
                    if len(vars_prof) > 1:
                        self.model.Add(sum(vars_prof) <= 1)
        
        # 3. Turma não pode ter duas aulas ao mesmo tempo
        for turma in self.turmas:
            for dia in self.dias:
                for periodo in range(1, 8):  # 1-7 períodos
                    vars_turma = []
                    for (t, d, di, p, pr), var in self.variaveis.items():
                        if t == turma.nome and di == dia and p == periodo:
                            vars_turma.append(var)
                    
                    if len(vars_turma) > 1:
                        self.model.Add(sum(vars_turma) <= 1)
    
    def resolver(self):
        """Resolve o modelo"""
        st.info("🎯 Resolvendo...")
        
        status = self.solver.Solve(self.model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            st.success("✅ Solução encontrada!")
            
            # Coletar resultados
            aulas = []
            for (turma, disc, dia, periodo, prof), var in self.variaveis.items():
                if self.solver.Value(var) == 1:
                    segmento = self._obter_segmento(turma)
                    
                    aula = {
                        'turma': turma,
                        'disciplina': disc,
                        'professor': prof,
                        'dia': dia,
                        'horario': periodo,  # Número do período
                        'segmento': segmento
                    }
                    aulas.append(aula)
            
            st.success(f"📊 {len(aulas)} aulas alocadas")
            return aulas
        else:
            st.error("❌ Nenhuma solução encontrada")
            return []