import streamlit as st
import pandas as pd
import database
from session_state import init_session_state
from auto_save import salvar_tudo
from models import Turma, Professor, Disciplina, Sala, DIAS_SEMANA

# ============================================
# CORREÇÃO CRÍTICA: IMPORT DO OR-TOOLS
# ============================================

# Tentar importar OR-Tools com tratamento robusto
try:
    from scheduler_ortools import GradeHorariaORTools
    ORTOOLS_DISPONIVEL = True
except Exception as e:
    ORTOOLS_DISPONIVEL = False
    # Criar classe dummy se não conseguir importar
    class GradeHorariaORTools:
        def __init__(self, *args, **kwargs):
            raise ImportError("OR-Tools não disponível. Use o algoritmo simples.")
        
        def resolver(self):
            return []

from simple_scheduler import SimpleGradeHoraria
import io
import traceback
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Escola Timetable", layout="wide")
st.title("🕒 Gerador Inteligente de Grade Horária")

# Inicialização
try:
    init_session_state()
    st.success("✅ Sistema inicializado com sucesso!")
except Exception as e:
    st.error(f"❌ Erro na inicialização: {str(e)}")
    st.code(traceback.format_exc())
    if st.button("🔄 Resetar Banco de Dados"):
        database.resetar_banco()
        st.rerun()
    st.stop()

# ============================================
# FUNÇÕES AUXILIARES CORRIGIDAS
# ============================================

def obter_grupo_seguro(objeto, opcoes=["A", "B", "AMBOS"]):
    """Obtém o grupo de um objeto de forma segura"""
    try:
        if hasattr(objeto, 'grupo'):
            grupo = objeto.grupo
            if grupo in opcoes:
                return grupo
        return "A"
    except:
        return "A"

def obter_segmento_turma(turma_nome):
    """Determina o segmento da turma baseado no nome - VERSÃO CORRIGIDA"""
    if not turma_nome:
        return "EF_II"
    
    turma_nome_lower = turma_nome.lower()
    
    # Primeiro verificar se é EM
    if 'em' in turma_nome_lower:
        return "EM"
    # Verificar se é EF II
    elif any(x in turma_nome_lower for x in ['6', '7', '8', '9', 'ano', 'ef']):
        return "EF_II"
    else:
        # Default: tentar inferir pela série
        try:
            # Se a turma começa com número, provavelmente é EF II
            if turma_nome_lower[0].isdigit():
                return "EF_II"
            else:
                return "EM"
        except:
            return "EF_II"

def obter_horarios_turma(turma_nome):
    """Retorna os períodos disponíveis para a turma - VERSÃO CORRIGIDA"""
    segmento = obter_segmento_turma(turma_nome)
    if segmento == "EM":
        return [1, 2, 3, 4, 5, 6, 7]  # ✅ 7 períodos para EM
    else:
        return [1, 2, 3, 4, 5]  # ✅ 5 períodos para EF II

def obter_horario_real(turma_nome, periodo):
    """Retorna o horário real formatado - VERSÃO SIMPLIFICADA E CORRETA"""
    segmento = obter_segmento_turma(turma_nome)
    
    if segmento == "EM":
        # EM: 7 períodos de AULA
        horarios = {
            1: "07:00 - 07:50",
            2: "07:50 - 08:40", 
            3: "08:40 - 09:30",
            # INTERVALO: 09:30-09:50 (não tem número)
            4: "09:50 - 10:40",
            5: "10:40 - 11:30",
            6: "11:30 - 12:20",
            7: "12:20 - 13:10"  # ✅ ÚLTIMA AULA DO EM
        }
    else:
        # EF II: 5 períodos de AULA
        horarios = {
            1: "07:50 - 08:40",
            2: "08:40 - 09:30",
            # INTERVALO: 09:30-09:50 (não tem número)
            3: "09:50 - 10:40",
            4: "10:40 - 11:30",
            5: "11:30 - 12:20"  # ✅ ÚLTIMA AULA DO EF II
        }
    
    return horarios.get(periodo, f"Período {periodo}")

def calcular_carga_maxima(serie):
    """Calcula a quantidade MÁXIMA de aulas semanais baseada na série"""
    if not serie:
        return 25
    
    serie_lower = serie.lower()
    if 'em' in serie_lower or serie_lower in ['1em', '2em', '3em']:
        return 35  # EM: máximo de 35 aulas por semana (7 aulas × 5 dias)
    else:
        return 25  # EF II: máximo de 25 aulas por semana (5 aulas × 5 dias)

def converter_dia_para_semana(dia):
    """Converte dia do formato completo para abreviado (DIAS_SEMANA)"""
    if dia == "segunda": return "seg"
    elif dia == "terca": return "ter"
    elif dia == "quarta": return "qua"
    elif dia == "quinta": return "qui"
    elif dia == "sexta": return "sex"
    else: return dia

def converter_dia_para_completo(dia):
    """Converte dia do formato abreviado para completo"""
    if dia == "seg": return "segunda"
    elif dia == "ter": return "terca"
    elif dia == "qua": return "quarta"
    elif dia == "qui": return "quinta"
    elif dia == "sex": return "sexta"
    else: return dia

def converter_disponibilidade_para_semana(disponibilidade):
    """Converte conjunto de disponibilidade para formato DIAS_SEMANA"""
    convertido = []
    for dia in disponibilidade:
        dia_convertido = converter_dia_para_semana(dia)
        if dia_convertido in DIAS_SEMANA:
            convertido.append(dia_convertido)
    return convertido

def converter_disponibilidade_para_completo(disponibilidade):
    """Converte conjunto de disponibilidade para formato completo"""
    convertido = []
    for dia in disponibilidade:
        convertido.append(converter_dia_para_completo(dia))
    return convertido

# ============================================
# FUNÇÕES DE ACESSO SEGURO A AULAS (CORRIGIDO)
# ============================================

def obter_turma_aula(aula):
    """Obtém a turma de uma aula de forma segura (objeto ou dicionário)"""
    if hasattr(aula, 'turma'):
        return aula.turma
    elif isinstance(aula, dict):
        return aula.get('turma')
    return None

def obter_disciplina_aula(aula):
    """Obtém a disciplina de uma aula de forma segura"""
    if hasattr(aula, 'disciplina'):
        return aula.disciplina
    elif isinstance(aula, dict):
        return aula.get('disciplina')
    return None

def obter_professor_aula(aula):
    """Obtém o professor de uma aula de forma segura"""
    if hasattr(aula, 'professor'):
        return aula.professor
    elif isinstance(aula, dict):
        return aula.get('professor')
    return None

def obter_dia_aula(aula):
    """Obtém o dia de uma aula de forma segura"""
    if hasattr(aula, 'dia'):
        return aula.dia
    elif isinstance(aula, dict):
        return aula.get('dia')
    return None

def obter_horario_aula(aula):
    """Obtém o horário de uma aula de forma segura"""
    if hasattr(aula, 'horario'):
        return aula.horario
    elif isinstance(aula, dict):
        return aula.get('horario')
    return None

def obter_segmento_aula(aula):
    """Obtém o segmento de uma aula de forma segura"""
    if hasattr(aula, 'segmento'):
        return aula.segmento
    elif isinstance(aula, dict):
        return aula.get('segmento')
    return None

# ============================================
# SISTEMA DE DIAGNÓSTICO DE GRADE
# ============================================

def diagnosticar_grade(turmas, professores, disciplinas, aulas_alocadas):
    """Diagnóstico completo do que impede a grade de ficar 100% completa"""
    diagnostico = {
        'status': '❌ INCOMPLETA',
        'completude': 0,
        'problemas': [],
        'sugestoes': [],
        'estatisticas': {},
        'detalhes_por_turma': {},
        'professores_saturados': [],
        'horarios_conflitantes': []
    }
    
    if not aulas_alocadas:
        return diagnostico
    
    # 1. ANÁLISE POR TURMA
    total_aulas_necessarias = 0
    total_aulas_alocadas = len(aulas_alocadas)
    
    for turma in turmas:
        turma_nome = turma.nome
        grupo_turma = turma.grupo
        segmento = obter_segmento_turma(turma_nome)
        
        # Calcular aulas necessárias para esta turma
        aulas_necessarias_turma = 0
        disciplinas_da_turma = []
        
        for disc in disciplinas:
            if turma_nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                aulas_necessarias_turma += disc.carga_semanal
                disciplinas_da_turma.append(disc)
        
        total_aulas_necessarias += aulas_necessarias_turma
        
        # Contar aulas alocadas para esta turma
        aulas_turma = [a for a in aulas_alocadas if obter_turma_aula(a) == turma_nome]
        aulas_alocadas_turma = len(aulas_turma)
        
        # Calcular completude da turma
        completude_turma = (aulas_alocadas_turma / aulas_necessarias_turma * 100) if aulas_necessarias_turma > 0 else 0
        
        # Detalhar por disciplina
        faltas_disciplinas = []
        for disc in disciplinas_da_turma:
            aulas_disc = len([a for a in aulas_turma if obter_disciplina_aula(a) == disc.nome])
            if aulas_disc < disc.carga_semanal:
                faltas = disc.carga_semanal - aulas_disc
                faltas_disciplinas.append(f"{disc.nome} ({aulas_disc}/{disc.carga_semanal})")
        
        diagnostico['detalhes_por_turma'][turma_nome] = {
            'necessarias': aulas_necessarias_turma,
            'alocadas': aulas_alocadas_turma,
            'completude': completude_turma,
            'faltas_disciplinas': faltas_disciplinas,
            'segmento': segmento,
            'grupo': grupo_turma
        }
    
    # 2. CALCULAR COMPLETUDE GERAL
    if total_aulas_necessarias > 0:
        completude_geral = (total_aulas_alocadas / total_aulas_necessarias * 100)
        diagnostico['completude'] = round(completude_geral, 1)
        diagnostico['estatisticas']['total_necessario'] = total_aulas_necessarias
        diagnostico['estatisticas']['total_alocado'] = total_aulas_alocadas
        diagnostico['estatisticas']['faltam'] = total_aulas_necessarias - total_aulas_alocadas
    
    # 3. ANÁLISE DE PROFESSORES
    for professor in professores:
        # Contar aulas do professor
        aulas_professor = len([a for a in aulas_alocadas if obter_professor_aula(a) == professor.nome])
        
        # Verificar disponibilidade
        dias_disponiveis = len(professor.disponibilidade) if hasattr(professor, 'disponibilidade') else 0
        horarios_indisponiveis = len(professor.horarios_indisponiveis) if hasattr(professor, 'horarios_indisponiveis') else 0
        
        # Calcular capacidade máxima (5 dias × 7 períodos = 35)
        capacidade_maxima = dias_disponiveis * 7 - horarios_indisponiveis
        
        if capacidade_maxima <= aulas_professor:
            diagnostico['professores_saturados'].append({
                'nome': professor.nome,
                'aulas': aulas_professor,
                'capacidade': capacidade_maxima,
                'dias_disponiveis': dias_disponiveis,
                'horarios_bloqueados': horarios_indisponiveis
            })
    
    # 4. IDENTIFICAR PROBLEMAS PRINCIPAIS
    # Problema 1: Professores insuficientes para disciplinas
    for turma_nome, info in diagnostico['detalhes_por_turma'].items():
        if info['faltas_disciplinas']:
            turma_obj = next((t for t in turmas if t.nome == turma_nome), None)
            grupo_turma = turma_obj.grupo if turma_obj else 'A'
            
            for falta in info['faltas_disciplinas']:
                disc_nome = falta.split(' (')[0]
                
                # Verificar professores para esta disciplina
                professores_disc = []
                for prof in professores:
                    if disc_nome in prof.disciplinas:
                        if prof.grupo in [grupo_turma, "AMBOS"]:
                            professores_disc.append(prof.nome)
                
                if not professores_disc:
                    diagnostico['problemas'].append(f"❌ **{turma_nome}**: Nenhum professor para **{disc_nome}**")
                    diagnostico['sugestoes'].append(f"👉 Adicione um professor que ministre **{disc_nome}** no grupo **{grupo_turma}**")
                elif len(professores_disc) == 1:
                    diagnostico['problemas'].append(f"⚠️ **{turma_nome}**: Apenas 1 professor para **{disc_nome}** ({professores_disc[0]})")
                    diagnostico['sugestoes'].append(f"👉 Adicione um segundo professor para **{disc_nome}** ou aumente a disponibilidade de **{professores_disc[0]}**")
    
    # Problema 2: Conflitos de horário
    # Verificar se há múltiplas aulas no mesmo horário para mesma turma
    horarios_turma = {}
    for aula in aulas_alocadas:
        chave = f"{obter_turma_aula(aula)}|{obter_dia_aula(aula)}|{obter_horario_aula(aula)}"
        if chave not in horarios_turma:
            horarios_turma[chave] = []
        horarios_turma[chave].append(aula)
    
    for chave, aulas_conflito in horarios_turma.items():
        if len(aulas_conflito) > 1:
            turma = obter_turma_aula(aulas_conflito[0])
            dia = obter_dia_aula(aulas_conflito[0])
            horario = obter_horario_aula(aulas_conflito[0])
            disciplinas = [obter_disciplina_aula(a) for a in aulas_conflito]
            diagnostico['horarios_conflitantes'].append({
                'turma': turma,
                'dia': dia,
                'horario': horario,
                'disciplinas': disciplinas
            })
    
    # 5. DEFINIR STATUS FINAL
    if diagnostico['completude'] == 100:
        diagnostico['status'] = '✅ COMPLETA'
    elif diagnostico['completude'] >= 90:
        diagnostico['status'] = '⚠️ QUASE COMPLETA'
    elif diagnostico['completude'] >= 70:
        diagnostico['status'] = '⚠️ PARCIAL'
    else:
        diagnostico['status'] = '❌ INCOMPLETA'
    
    # 6. SUGESTÕES AUTOMÁTICAS
    if diagnostico['professores_saturados']:
        for prof in diagnostico['professores_saturados'][:3]:  # Top 3 mais saturados
            diagnostico['sugestoes'].append(f"👉 Professor **{prof['nome']}** está com {prof['aulas']}/{prof['capacidade']} aulas. Aumente disponibilidade ou reduza carga.")
    
    if total_aulas_necessarias > total_aulas_alocadas:
        faltam = total_aulas_necessarias - total_aulas_alocadas
        diagnostico['sugestoes'].append(f"👉 **Faltam {faltam} aulas no total**. Verifique disponibilidade de professores.")
    
    return diagnostico

# ============================================
# ALGORITMO FORÇA-BRUTA para Completar Grades
# ============================================

class CompletadorDeGrade:
    """Algoritmo força-bruta para tentar completar grades incompletas"""
    
    def __init__(self, turmas, professores, disciplinas):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = disciplinas
        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        self.max_tentativas = 1000
        
    def completar_grade(self, aulas_atuais):
        """Tenta completar uma grade existente"""
        aulas = aulas_atuais.copy() if aulas_atuais else []
        
        # Calcular o que falta
        faltas = self._calcular_faltas(aulas)
        
        if not faltas:
            return aulas  # Já está completa
        
        # Tentativa 1: Algoritmo inteligente
        aulas = self._tentativa_inteligente(aulas, faltas)
        
        # Verificar se completou
        faltas_pos_tentativa = self._calcular_faltas(aulas)
        if not faltas_pos_tentativa:
            return aulas
        
        # Tentativa 2: Algoritmo força-bruta (limitado)
        aulas = self._tentativa_forca_bruta(aulas, faltas_pos_tentativa)
        
        return aulas
    
    def _calcular_faltas(self, aulas):
        """Calcula exatamente quais aulas faltam"""
        faltas = []
        
        for turma in self.turmas:
            turma_nome = turma.nome
            grupo_turma = turma.grupo
            
            # Contar aulas alocadas por disciplina para esta turma
            contagem_atual = {}
            for aula in aulas:
                if obter_turma_aula(aula) == turma_nome:
                    disc = obter_disciplina_aula(aula)
                    if disc:
                        contagem_atual[disc] = contagem_atual.get(disc, 0) + 1
            
            # Verificar cada disciplina que a turma deve ter
            for disc in self.disciplinas:
                if turma_nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                    alocadas = contagem_atual.get(disc.nome, 0)
                    if alocadas < disc.carga_semanal:
                        for _ in range(disc.carga_semanal - alocadas):
                            faltas.append({
                                'turma': turma_nome,
                                'disciplina': disc.nome,
                                'grupo': grupo_turma,
                                'necessarias': disc.carga_semanal,
                                'alocadas': alocadas
                            })
        
        return faltas
    
    def _tentativa_inteligente(self, aulas, faltas):
        """Tentativa inteligente de alocação"""
        # Ordenar faltas por dificuldade (disciplinas com menos professores primeiro)
        faltas_ordenadas = []
        for falta in faltas:
            # Contar professores disponíveis para esta disciplina e grupo
            professores_disponiveis = 0
            for prof in self.professores:
                if falta['disciplina'] in prof.disciplinas:
                    if prof.grupo in [falta['grupo'], "AMBOS"]:
                        professores_disponiveis += 1
            
            faltas_ordenadas.append({
                **falta,
                'dificuldade': 10 - professores_disponiveis,  # Quanto maior, mais difícil
                'professores_disponiveis': professores_disponiveis
            })
        
        # Ordenar do mais difícil para o mais fácil
        faltas_ordenadas.sort(key=lambda x: x['dificuldade'], reverse=True)
        
        # Tentar alocar cada falta
        for falta in faltas_ordenadas:
            if falta['professores_disponiveis'] == 0:
                continue  # Não tem professor, pular
            
            # Encontrar professores candidatos
            professores_candidatos = []
            for prof in self.professores:
                if falta['disciplina'] in prof.disciplinas:
                    if prof.grupo in [falta['grupo'], "AMBOS"]:
                        professores_candidatos.append(prof)
            
            # Tentar cada professor
            for professor in professores_candidatos:
                # Tentar cada dia disponível
                for dia in professor.disponibilidade:
                    # Tentar cada período
                    segmento = obter_segmento_turma(falta['turma'])
                    periodos = obter_horarios_turma(falta['turma'])
                    
                    for periodo in periodos:
                        # Verificar se já tentou muito
                        if len(aulas) > 500:  # Limite de segurança
                            return aulas
                        
                        # Verificar restrições
                        if not self._pode_alocar(aulas, falta['turma'], professor.nome, dia, periodo):
                            continue
                        
                        # Alocar!
                        from models import Aula
                        nova_aula = Aula(
                            turma=falta['turma'],
                            disciplina=falta['disciplina'],
                            professor=professor.nome,
                            dia=dia,
                            horario=periodo,
                            segmento=segmento
                        )
                        aulas.append(nova_aula)
                        
                        # Parar de tentar para esta falta
                        break
                    else:
                        continue
                    break
                else:
                    continue
                break
        
        return aulas
    
    def _tentativa_forca_bruta(self, aulas, faltas, max_iteracoes=100):
        """Tentativa força-bruta limitada"""
        import random
        
        for _ in range(max_iteracoes):
            if not faltas:
                break
            
            # Pegar uma falta aleatória
            falta = random.choice(faltas)
            
            # Encontrar professores candidatos
            professores_candidatos = []
            for prof in self.professores:
                if falta['disciplina'] in prof.disciplinas:
                    if prof.grupo in [falta['grupo'], "AMBOS"]:
                        professores_candidatos.append(prof)
            
            if not professores_candidatos:
                continue
            
            # Escolher professor aleatório
            professor = random.choice(professores_candidatos)
            
            # Escolher dia aleatório da disponibilidade
            if not professor.disponibilidade:
                continue
            dia = random.choice(list(professor.disponibilidade))
            
            # Escolher período aleatório
            segmento = obter_segmento_turma(falta['turma'])
            periodos = obter_horarios_turma(falta['turma'])
            periodo = random.choice(periodos)
            
            # Verificar se pode alocar
            if self._pode_alocar(aulas, falta['turma'], professor.nome, dia, periodo):
                from models import Aula
                nova_aula = Aula(
                    turma=falta['turma'],
                    disciplina=falta['disciplina'],
                    professor=professor.nome,
                    dia=dia,
                    horario=periodo,
                    segmento=segmento
                )
                aulas.append(nova_aula)
                
                # Recalcular faltas
                faltas = self._calcular_faltas(aulas)
        
        return aulas
    
    def _pode_alocar(self, aulas, turma, professor, dia, horario):
        """Verifica se uma aula pode ser alocada sem conflitos"""
        # Verificar se turma já tem aula neste horário
        for aula in aulas:
            if obter_turma_aula(aula) == turma and obter_dia_aula(aula) == dia and obter_horario_aula(aula) == horario:
                return False
        
        # Verificar se professor já tem aula neste horário
        for aula in aulas:
            if obter_professor_aula(aula) == professor and obter_dia_aula(aula) == dia and obter_horario_aula(aula) == horario:
                return False
        
        # Verificar se professor tem este horário bloqueado
        prof_obj = next((p for p in self.professores if p.nome == professor), None)
        if prof_obj and f"{dia}_{horario}" in prof_obj.horarios_indisponiveis:
            return False
        
        return True

# ============================================
# FUNÇÕES ADICIONAIS
# ============================================

def salvar_grade_como(nome, aulas, config):
    """Salva uma grade com um nome específico"""
    if not hasattr(st.session_state, 'grades_salvas'):
        st.session_state.grades_salvas = {}
    
    # Converter para dicionários se for objetos
    aulas_dict = []
    for aula in aulas:
        if hasattr(aula, '__dict__'):
            aulas_dict.append(aula.__dict__)
        elif isinstance(aula, dict):
            aulas_dict.append(aula)
        else:
            # Tentar extrair atributos
            aula_dict = {
                'turma': obter_turma_aula(aula),
                'disciplina': obter_disciplina_aula(aula),
                'professor': obter_professor_aula(aula),
                'dia': obter_dia_aula(aula),
                'horario': obter_horario_aula(aula),
                'segmento': obter_segmento_aula(aula)
            }
            aulas_dict.append(aula_dict)
    
    st.session_state.grades_salvas[nome] = {
        'aulas': aulas_dict,
        'config': config,
        'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_aulas': len(aulas)
    }
    
    return True

# ============================================
# MENU DE ABAS
# ============================================

abas = st.tabs(["🏠 Início", "📚 Disciplinas", "👩‍🏫 Professores", "🎒 Turmas", "🏫 Salas", "🗓️ Gerar Grade", "👨‍🏫 Grade por Professor", "🔧 Diagnóstico"])

# ============================================
# ABA INÍCIO
# ============================================

with abas[0]:
    st.header("Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Turmas", len(st.session_state.turmas))
    with col2:
        st.metric("Professores", len(st.session_state.professores))
    with col3:
        st.metric("Disciplinas", len(st.session_state.disciplinas))
    with col4:
        st.metric("Salas", len(st.session_state.salas))
    
    # Estatísticas por segmento
    st.subheader("📊 Estatísticas por Segmento")
    
    turmas_efii = [t for t in st.session_state.turmas if obter_segmento_turma(t.nome) == "EF_II"]
    turmas_em = [t for t in st.session_state.turmas if obter_segmento_turma(t.nome) == "EM"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Ensino Fundamental II**")
        st.write(f"Turmas: {len(turmas_efii)}")
        st.write(f"Horário: 07:50 - 12:20")
        st.write(f"Aulas: 5 por dia + intervalo")
        
    with col2:
        st.write("**Ensino Médio**")
        st.write(f"Turmas: {len(turmas_em)}")
        st.write(f"Horário: 07:00 - 13:10")
        st.write(f"Aulas: 7 por dia + intervalo")
    
    # Verificação de carga horária
    st.subheader("📈 Verificação de Carga de Aulas")
    
    for turma in st.session_state.turmas:
        carga_total = 0
        disciplinas_turma = []
        grupo_turma = obter_grupo_seguro(turma)
        segmento = obter_segmento_turma(turma.nome)
        
        # Contar disciplinas vinculadas
        for disc in st.session_state.disciplinas:
            if turma.nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                carga_total += disc.carga_semanal
                disciplinas_turma.append(f"{disc.nome} ({disc.carga_semanal}a)")
        
        carga_maxima = calcular_carga_maxima(turma.serie)
        status = "✅" if carga_total == carga_maxima else "⚠️" if carga_total <= carga_maxima else "❌"
        
        st.write(f"**{turma.nome}** [{grupo_turma}] ({segmento}): {carga_total}/{carga_maxima} aulas {status}")
        
        if disciplinas_turma:
            st.caption(f"Disciplinas: {', '.join(disciplinas_turma[:3])}{'...' if len(disciplinas_turma) > 3 else ''}")
        else:
            st.caption("⚠️ Nenhuma disciplina atribuída")
    
    if st.button("💾 Salvar Tudo no Banco"):
        try:
            if salvar_tudo():
                st.success("✅ Todos os dados salvos!")
            else:
                st.error("❌ Erro ao salvar dados")
        except Exception as e:
            st.error(f"❌ Erro ao salvar: {str(e)}")

# ============================================
# ABA DISCIPLINAS
# ============================================

with abas[1]:
    st.header("📚 Disciplinas")
    
    grupo_filtro = st.selectbox("Filtrar por Grupo", ["Todos", "A", "B"], key="filtro_disc")
    
    with st.expander("➕ Adicionar Nova Disciplina", expanded=False):
        with st.form("add_disc"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome da Disciplina*")
                carga = st.number_input("Carga Semanal*", 1, 10, 3)
                tipo = st.selectbox("Tipo*", ["pesada", "media", "leve", "pratica"])
            with col2:
                turmas_opcoes = [t.nome for t in st.session_state.turmas]
                turmas_selecionadas = st.multiselect("Turmas*", turmas_opcoes)
                grupo = st.selectbox("Grupo*", ["A", "B"])
                cor_fundo = st.color_picker("Cor de Fundo", "#4A90E2")
                cor_fonte = st.color_picker("Cor da Fonte", "#FFFFFF")
            
            if st.form_submit_button("✅ Adicionar Disciplina"):
                if nome and turmas_selecionadas:
                    try:
                        nova_disciplina = Disciplina(
                            nome, carga, tipo, turmas_selecionadas, grupo, cor_fundo, cor_fonte
                        )
                        st.session_state.disciplinas.append(nova_disciplina)
                        if salvar_tudo():
                            st.success(f"✅ Disciplina '{nome}' adicionada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar disciplina: {str(e)}")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
    
    st.subheader("📋 Lista de Disciplinas")
    
    disciplinas_exibir = st.session_state.disciplinas
    if grupo_filtro != "Todos":
        disciplinas_exibir = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == grupo_filtro]
    
    if not disciplinas_exibir:
        st.info("📝 Nenhuma disciplina cadastrada.")
    
    for disc in disciplinas_exibir:
        with st.expander(f"📖 {disc.nome} [{obter_grupo_seguro(disc)}]", expanded=False):
            with st.form(f"edit_disc_{disc.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome", disc.nome, key=f"nome_{disc.id}")
                    nova_carga = st.number_input("Carga Semanal", 1, 10, disc.carga_semanal, key=f"carga_{disc.id}")
                    novo_tipo = st.selectbox(
                        "Tipo", 
                        ["pesada", "media", "leve", "pratica"],
                        index=["pesada", "media", "leve", "pratica"].index(disc.tipo),
                        key=f"tipo_{disc.id}"
                    )
                with col2:
                    turmas_opcoes = [t.nome for t in st.session_state.turmas]
                    turmas_selecionadas = st.multiselect(
                        "Turmas", 
                        turmas_opcoes,
                        default=disc.turmas,
                        key=f"turmas_{disc.id}"
                    )
                    novo_grupo = st.selectbox(
                        "Grupo", 
                        ["A", "B"],
                        index=0 if obter_grupo_seguro(disc) == "A" else 1,
                        key=f"grupo_{disc.id}"
                    )
                    nova_cor_fundo = st.color_picker("Cor de Fundo", disc.cor_fundo, key=f"cor_fundo_{disc.id}")
                    nova_cor_fonte = st.color_picker("Cor da Fonte", disc.cor_fonte, key=f"cor_fonte_{disc.id}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if novo_nome and turmas_selecionadas:
                            try:
                                disc.nome = novo_nome
                                disc.carga_semanal = nova_carga
                                disc.tipo = novo_tipo
                                disc.turmas = turmas_selecionadas
                                disc.grupo = novo_grupo
                                disc.cor_fundo = nova_cor_fundo
                                disc.cor_fonte = nova_cor_fonte
                                
                                if salvar_tudo():
                                    st.success("✅ Disciplina atualizada!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
                        else:
                            st.error("❌ Preencha todos os campos obrigatórios")
                
                with col2:
                    if st.form_submit_button("🗑️ Excluir Disciplina", type="secondary"):
                        try:
                            st.session_state.disciplinas.remove(disc)
                            if salvar_tudo():
                                st.success("✅ Disciplina excluída!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao excluir: {str(e)}")

# ============================================
# ABA PROFESSORES
# ============================================

with abas[2]:
    st.header("👩‍🏫 Professores")
    
    grupo_filtro = st.selectbox("Filtrar por Grupo", ["Todos", "A", "B", "AMBOS"], key="filtro_prof")
    disc_nomes = [d.nome for d in st.session_state.disciplinas]
    
    with st.expander("➕ Adicionar Novo Professor", expanded=False):
        with st.form("add_prof"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome do Professor*")
                disciplinas = st.multiselect("Disciplinas*", disc_nomes)
                grupo = st.selectbox("Grupo*", ["A", "B", "AMBOS"])
            with col2:
                disponibilidade = st.multiselect("Dias Disponíveis*", DIAS_SEMANA, default=DIAS_SEMANA)
                st.write("**Horários Indisponíveis:**")
                
                horarios_indisponiveis = []
                for dia in DIAS_SEMANA:
                    with st.container():
                        st.write(f"**{dia.upper()}:**")
                        horarios_cols = st.columns(4)
                        horarios_todos = list(range(1, 8))
                        for i, horario in enumerate(horarios_todos):
                            with horarios_cols[i % 4]:
                                if st.checkbox(f"{horario}º", key=f"add_{dia}_{horario}"):
                                    horarios_indisponiveis.append(f"{dia}_{horario}")
            
            if st.form_submit_button("✅ Adicionar Professor"):
                if nome and disciplinas and disponibilidade:
                    try:
                        disponibilidade_completa = converter_disponibilidade_para_completo(disponibilidade)
                        
                        novo_professor = Professor(
                            nome, 
                            disciplinas, 
                            disponibilidade_completa,
                            grupo,
                            horarios_indisponiveis
                        )
                        st.session_state.professores.append(novo_professor)
                        if salvar_tudo():
                            st.success(f"✅ Professor '{nome}' adicionado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar professor: {str(e)}")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
    
    st.subheader("📋 Lista de Professores")
    
    professores_exibir = st.session_state.professores
    if grupo_filtro != "Todos":
        professores_exibir = [p for p in st.session_state.professores if obter_grupo_seguro(p) == grupo_filtro]
    
    if not professores_exibir:
        st.info("📝 Nenhum professor cadastrado.")
    
    for prof in professores_exibir:
        with st.expander(f"👨‍🏫 {prof.nome} [{obter_grupo_seguro(prof)}]", expanded=False):
            disciplinas_validas = [d for d in prof.disciplinas if d in disc_nomes]
            
            with st.form(f"edit_prof_{prof.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome", prof.nome, key=f"nome_prof_{prof.id}")
                    novas_disciplinas = st.multiselect(
                        "Disciplinas", 
                        disc_nomes, 
                        default=disciplinas_validas,
                        key=f"disc_prof_{prof.id}"
                    )
                    novo_grupo = st.selectbox(
                        "Grupo", 
                        ["A", "B", "AMBOS"],
                        index=["A", "B", "AMBOS"].index(obter_grupo_seguro(prof)),
                        key=f"grupo_prof_{prof.id}"
                    )
                with col2:
                    disponibilidade_convertida = converter_disponibilidade_para_semana(prof.disponibilidade)
                    
                    nova_disponibilidade = st.multiselect(
                        "Dias Disponíveis", 
                        DIAS_SEMANA, 
                        default=disponibilidade_convertida,
                        key=f"disp_prof_{prof.id}"
                    )
                    
                    st.write("**Horários Indisponíveis:**")
                    novos_horarios_indisponiveis = []
                    horarios_todos = list(range(1, 8))
                    for dia in DIAS_SEMANA:
                        with st.container():
                            st.write(f"**{dia.upper()}:**")
                            horarios_cols = st.columns(4)
                            for i, horario in enumerate(horarios_todos):
                                with horarios_cols[i % 4]:
                                    checked = False
                                    horario_str = f"{dia}_{horario}"
                                    if hasattr(prof, 'horarios_indisponiveis'):
                                        if isinstance(prof.horarios_indisponiveis, (list, set)):
                                            checked = horario_str in prof.horarios_indisponiveis
                                    
                                    if st.checkbox(
                                        f"{horario}º", 
                                        value=checked,
                                        key=f"edit_{prof.id}_{dia}_{horario}"
                                    ):
                                        novos_horarios_indisponiveis.append(horario_str)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if novo_nome and novas_disciplinas and nova_disponibilidade:
                            try:
                                prof.nome = novo_nome
                                prof.disciplinas = novas_disciplinas
                                prof.grupo = novo_grupo
                                
                                disponibilidade_completa = converter_disponibilidade_para_completo(nova_disponibilidade)
                                
                                prof.disponibilidade = disponibilidade_completa
                                prof.horarios_indisponiveis = novos_horarios_indisponiveis
                                
                                if salvar_tudo():
                                    st.success("✅ Professor atualizado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
                        else:
                            st.error("❌ Preencha todos os campos obrigatórios")
                
                with col2:
                    if st.form_submit_button("🗑️ Excluir Professor", type="secondary"):
                        try:
                            st.session_state.professores.remove(prof)
                            if salvar_tudo():
                                st.success("✅ Professor excluído!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao excluir: {str(e)}")

# ============================================
# ABA TURMAS
# ============================================

with abas[3]:
    st.header("🎒 Turmas")
    
    grupo_filtro = st.selectbox("Filtrar por Grupo", ["Todos", "A", "B"], key="filtro_turma")
    
    with st.expander("➕ Adicionar Nova Turma", expanded=False):
        with st.form("add_turma"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome da Turma* (ex: 8anoA)")
                serie = st.text_input("Série* (ex: 8ano)")
            with col2:
                turno = st.selectbox("Turno*", ["manha"], disabled=True)
                grupo = st.selectbox("Grupo*", ["A", "B"])
            
            # Determinar segmento automaticamente
            segmento = "EM" if serie and 'em' in serie.lower() else "EF_II"
            st.info(f"💡 Segmento: {segmento} - {calcular_carga_maxima(serie)}h semanais máximas")
            
            if st.form_submit_button("✅ Adicionar Turma"):
                if nome and serie:
                    try:
                        nova_turma = Turma(nome, serie, "manha", grupo, segmento)
                        st.session_state.turmas.append(nova_turma)
                        if salvar_tudo():
                            st.success(f"✅ Turma '{nome}' adicionada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar turma: {str(e)}")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
    
    st.subheader("📋 Lista de Turmas")
    
    turmas_exibir = st.session_state.turmas
    if grupo_filtro != "Todos":
        turmas_exibir = [t for t in st.session_state.turmas if obter_grupo_seguro(t) == grupo_filtro]
    
    if not turmas_exibir:
        st.info("📝 Nenhuma turma cadastrada.")
    
    for turma in turmas_exibir:
        with st.expander(f"🎒 {turma.nome} [{obter_grupo_seguro(turma)}]", expanded=False):
            with st.form(f"edit_turma_{turma.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome", turma.nome, key=f"nome_turma_{turma.id}")
                    nova_serie = st.text_input("Série", turma.serie, key=f"serie_turma_{turma.id}")
                with col2:
                    st.text_input("Turno", "manha", disabled=True, key=f"turno_turma_{turma.id}")
                    novo_grupo = st.selectbox(
                        "Grupo", 
                        ["A", "B"],
                        index=0 if obter_grupo_seguro(turma) == "A" else 1,
                        key=f"grupo_turma_{turma.id}"
                    )
                
                # Mostrar informações da turma
                segmento = obter_segmento_turma(turma.nome)
                horarios = obter_horarios_turma(turma.nome)
                st.write(f"**Segmento:** {segmento}")
                st.write(f"**Horários disponíveis:** {len(horarios)} períodos")
                
                grupo_turma = obter_grupo_seguro(turma)
                carga_atual = 0
                disciplinas_turma = []
                
                for disc in st.session_state.disciplinas:
                    if turma.nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                        carga_atual += disc.carga_semanal
                        disciplinas_turma.append(disc.nome)
                
                carga_maxima = calcular_carga_maxima(turma.serie)
                st.write(f"**Carga horária atual:** {carga_atual}/{carga_maxima}h")
                if disciplinas_turma:
                    st.caption(f"Disciplinas: {', '.join(disciplinas_turma[:3])}{'...' if len(disciplinas_turma) > 3 else ''}")
                else:
                    st.caption("⚠️ Nenhuma disciplina atribuída")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if novo_nome and nova_serie:
                            try:
                                turma.nome = novo_nome
                                turma.serie = nova_serie
                                turma.grupo = novo_grupo
                                
                                if salvar_tudo():
                                    st.success("✅ Turma atualizada!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
                        else:
                            st.error("❌ Preencha todos os campos obrigatórios")
                
                with col2:
                    if st.form_submit_button("🗑️ Excluir Turma", type="secondary"):
                        try:
                            st.session_state.turmas.remove(turma)
                            if salvar_tudo():
                                st.success("✅ Turma excluída!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao excluir: {str(e)}")

# ============================================
# ABA SALAS
# ============================================

with abas[4]:
    st.header("🏫 Salas")
    
    with st.expander("➕ Adicionar Nova Sala", expanded=False):
        with st.form("add_sala"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome da Sala*")
                capacidade = st.number_input("Capacidade*", 1, 100, 30)
            with col2:
                tipo = st.selectbox("Tipo*", ["normal", "laboratório", "auditório"])
            
            if st.form_submit_button("✅ Adicionar Sala"):
                if nome:
                    try:
                        nova_sala = Sala(nome, capacidade, tipo)
                        st.session_state.salas.append(nova_sala)
                        if salvar_tudo():
                            st.success(f"✅ Sala '{nome}' adicionada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar sala: {str(e)}")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios (*)")
    
    st.subheader("📋 Lista de Salas")
    
    if not st.session_state.salas:
        st.info("📝 Nenhuma sala cadastrada.")
    
    for sala in st.session_state.salas:
        with st.expander(f"🏫 {sala.nome}", expanded=False):
            with st.form(f"edit_sala_{sala.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome", sala.nome, key=f"nome_sala_{sala.id}")
                    nova_capacidade = st.number_input("Capacidade", 1, 100, sala.capacidade, key=f"cap_sala_{sala.id}")
                with col2:
                    novo_tipo = st.selectbox(
                        "Tipo", 
                        ["normal", "laboratório", "auditório"],
                        index=["normal", "laboratório", "auditório"].index(sala.tipo),
                        key=f"tipo_sala_{sala.id}"
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if novo_nome:
                            try:
                                sala.nome = novo_nome
                                sala.capacidade = nova_capacidade
                                sala.tipo = novo_tipo
                                
                                if salvar_tudo():
                                    st.success("✅ Sala atualizada!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
                        else:
                            st.error("❌ Preencha todos os campos obrigatórios")
                
                with col2:
                    if st.form_submit_button("🗑️ Excluir Sala", type="secondary"):
                        try:
                            st.session_state.salas.remove(sala)
                            if salvar_tudo():
                                st.success("✅ Sala excluída!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao excluir: {str(e)}")

# ============================================
# ABA GERAR GRADE - VERSÃO FINAL CORRIGIDA
# ============================================

with abas[5]:
    st.header("🗓️ Gerar Grade Horária")
    
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
            ["Algoritmo Simples (Rápido)", "Google OR-Tools (Otimizado)"]
        )
        
        st.info("📅 **EM: 07:00-13:10 (7 períodos)**")
        st.info("📅 **EF II: 07:50-12:20 (5 períodos)**")
    
    st.subheader("📊 Pré-análise de Viabilidade")
    
    # Calcular carga horária conforme seleção
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
    
    # Filtrar disciplinas pelo grupo correto
    if tipo_grade == "Grade por Grupo A":
        disciplinas_filtradas = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == "A"]
    elif tipo_grade == "Grade por Grupo B":
        disciplinas_filtradas = [d for d in st.session_state.disciplinas if obter_grupo_seguro(d) == "B"]
    else:
        disciplinas_filtradas = st.session_state.disciplinas
    
    # Calcular total de aulas necessárias
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
    
    # Capacidade com horários reais
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
    
    if total_aulas == 0:
        st.error("❌ Nenhuma aula para alocar! Verifique as disciplinas.")
    elif total_aulas > capacidade_total:
        st.error("❌ Capacidade insuficiente! Reduza a carga horária.")
    else:
        st.success("✅ Pronto para gerar grade!")
        
        if st.button("🚀 Gerar Grade Horária", type="primary", width='stretch'):
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
                        if tipo_algoritmo == "Google OR-Tools (Otimizado)" and ORTOOLS_DISPONIVEL:
                            try:
                                grade = GradeHorariaORTools(
                                    turmas_filtradas,
                                    professores_filtrados,
                                    disciplinas_filtradas,
                                    relaxar_horario_ideal=False
                                )
                                aulas = grade.resolver()
                                metodo = "Google OR-Tools"
                            except Exception as e:
                                st.warning(f"⚠️ OR-Tools falhou: {str(e)}. Usando algoritmo simples...")
                                simple_grade = SimpleGradeHoraria(
                                    turmas=turmas_filtradas,
                                    professores=professores_filtrados,
                                    disciplinas=disciplinas_filtradas,
                                    salas=st.session_state.salas
                                )
                                aulas = simple_grade.gerar_grade()
                                metodo = "Algoritmo Simples (fallback)"
                        else:
                            simple_grade = SimpleGradeHoraria(
                                turmas=turmas_filtradas,
                                professores=professores_filtrados,
                                disciplinas=disciplinas_filtradas,
                                salas=st.session_state.salas
                            )
                            aulas = simple_grade.gerar_grade()
                            metodo = "Algoritmo Simples"
                        
                        # Filtrar por turma específica se necessário
                        if tipo_grade == "Grade por Turma Específica" and turma_selecionada:
                            # Filtrar usando função segura
                            aulas = [a for a in aulas if obter_turma_aula(a) == turma_selecionada]
                        
                        # Salvar no estado da sessão
                        st.session_state.aulas = aulas
                        
                        if salvar_tudo():
                            st.success(f"✅ Grade {grupo_texto} gerada com {metodo}! ({len(aulas)} aulas)")
                        
                        # ============================================
                        # DIAGNÓSTICO E COMPLETUDE DA GRADE
                        # ============================================
                        
                        if aulas:
                            st.subheader("🔍 DIAGNÓSTICO DA GRADE")
                            
                            # Executar diagnóstico
                            diagnostico = diagnosticar_grade(turmas_filtradas, professores_filtrados, disciplinas_filtradas, aulas)
                            
                            # Mostrar status
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Status", diagnostico['status'])
                            with col2:
                                st.metric("Completude", f"{diagnostico['completude']}%")
                            with col3:
                                st.metric("Aulas", f"{diagnostico['estatisticas']['total_alocado']}/{diagnostico['estatisticas']['total_necessario']}")
                            
                            # Botão para tentar completar automaticamente
                            if diagnostico['completude'] < 100:
                                st.warning(f"⚠️ **Grade incompleta!** Faltam {diagnostico['estatisticas']['faltam']} aulas.")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("🔧 TENTAR COMPLETAR GRADE", type="primary", use_container_width=True):
                                        with st.spinner("Tentando completar a grade..."):
                                            completador = CompletadorDeGrade(turmas_filtradas, professores_filtrados, disciplinas_filtradas)
                                            aulas_completas = completador.completar_grade(aulas)
                                            
                                            # Verificar se melhorou
                                            novo_diagnostico = diagnosticar_grade(turmas_filtradas, professores_filtrados, disciplinas_filtradas, aulas_completas)
                                            
                                            if novo_diagnostico['completude'] > diagnostico['completude']:
                                                st.session_state.aulas = aulas_completas
                                                st.success(f"✅ Melhorado para {novo_diagnostico['completude']}%! Atualize a página para ver a nova grade.")
                                                st.rerun()
                                            else:
                                                st.error("❌ Não foi possível melhorar a grade automaticamente.")
                                
                                with col2:
                                    # Botão para salvar grade atual (mesmo incompleta)
                                    nome_grade = st.text_input("Nome para salvar esta grade:", value=f"Grade_{grupo_texto}_{datetime.now().strftime('%H%M')}")
                                    if st.button("💾 SALVAR GRADE", type="secondary", use_container_width=True):
                                        if salvar_grade_como(nome_grade, aulas, {'tipo': tipo_grade, 'algoritmo': metodo}):
                                            st.success(f"✅ Grade '{nome_grade}' salva!")
                            
                            # Mostrar problemas e sugestões
                            if diagnostico['problemas']:
                                with st.expander("📋 PROBLEMAS DETECTADOS", expanded=True):
                                    for problema in diagnostico['problemas'][:5]:  # Mostrar até 5 problemas
                                        st.markdown(problema)
                            
                            if diagnostico['sugestoes']:
                                with st.expander("💡 SUGESTÕES PARA COMPLETAR", expanded=True):
                                    for sugestao in diagnostico['sugestoes'][:5]:  # Mostrar até 5 sugestões
                                        st.markdown(sugestao)
                            
                            # Detalhes por turma
                            with st.expander("📊 DETALHES POR TURMA"):
                                for turma_nome, info in diagnostico['detalhes_por_turma'].items():
                                    status = "✅" if info['completude'] == 100 else "⚠️" if info['completude'] >= 80 else "❌"
                                    st.write(f"{status} **{turma_nome}** ({info['segmento']}): {info['alocadas']}/{info['necessarias']} aulas ({info['completude']:.1f}%)")
                                    
                                    if info['faltas_disciplinas']:
                                        st.caption(f"Faltam: {', '.join(info['faltas_disciplinas'])}")
                            
                            # Professores saturados
                            if diagnostico['professores_saturados']:
                                with st.expander("👨‍🏫 PROFESSORES SATURADOS"):
                                    for prof in diagnostico['professores_saturados']:
                                        st.write(f"⚠️ **{prof['nome']}**: {prof['aulas']}/{prof['capacidade']} aulas (máximo: {prof['dias_disponiveis']} dias × 7 - {prof['horarios_bloqueados']} bloqueios)")
                        
                        # ============================================
                        # VISUALIZAÇÃO DA GRADE HORÁRIA (CORRIGIDA)
                        # ============================================
                        if aulas:
                            st.subheader("📅 Visualização da Grade Horária")
                            
                            # Usar função segura para obter turmas
                            turmas_com_aulas = []
                            for a in aulas:
                                turma = obter_turma_aula(a)
                                if turma and turma not in turmas_com_aulas:
                                    turmas_com_aulas.append(turma)
                            
                            for turma_nome in turmas_com_aulas:
                                st.write(f"#### 🎒 Grade da Turma: {turma_nome}")
                                
                                # Filtrar aulas da turma
                                aulas_turma = [a for a in aulas if obter_turma_aula(a) == turma_nome]
                                
                                # Determinar segmento e períodos
                                segmento = obter_segmento_turma(turma_nome)
                                if segmento == "EM":
                                    periodos = list(range(1, 8))  # 1-7
                                else:
                                    periodos = list(range(1, 6))  # 1-5
                                
                                # Dias da semana
                                dias_ordenados = ["segunda", "terca", "quarta", "quinta", "sexta"]
                                
                                st.markdown("""
                                <style>
                                .grade-table {
                                    width: 100%;
                                    border-collapse: collapse;
                                    margin: 10px 0;
                                }
                                .grade-table th, .grade-table td {
                                    border: 1px solid #ddd;
                                    padding: 8px;
                                    text-align: center;
                                    vertical-align: middle;
                                }
                                .grade-table th {
                                    background-color: #4A90E2;
                                    color: white;
                                    font-weight: bold;
                                }
                                .aula-cell {
                                    background-color: #e8f5e9;
                                    color: #2e7d32;
                                    font-size: 14px;
                                }
                                .livre-cell {
                                    background-color: #f5f5f5;
                                    color: #999;
                                    font-style: italic;
                                }
                                .intervalo-row {
                                    background-color: #e3f2fd;
                                    color: #1565c0;
                                    font-weight: bold;
                                    text-align: center;
                                }
                                .disciplina {
                                    font-weight: bold;
                                    font-size: 14px;
                                }
                                .professor {
                                    font-size: 11px;
                                    color: #666;
                                }
                                </style>
                                """, unsafe_allow_html=True)
                                
                                # Construir tabela HTML CORRETA
                                table_html = """<table class='grade-table'>
<tr>
<th>Horário</th>
<th>Segunda</th>
<th>Terça</th>
<th>Quarta</th>
<th>Quinta</th>
<th>Sexta</th>
</tr>"""
                                
                                # Adicionar períodos de aula
                                for periodo in periodos:
                                    horario_real = obter_horario_real(turma_nome, periodo)
                                    table_html += f"<tr><td><strong>{horario_real}</strong></td>"
                                    
                                    for dia in dias_ordenados:
                                        # Procurar aula
                                        aula_encontrada = None
                                        for aula in aulas_turma:
                                            if obter_dia_aula(aula) == dia and obter_horario_aula(aula) == periodo:
                                                aula_encontrada = aula
                                                break
                                        
                                        if aula_encontrada:
                                            # Obter dados da aula
                                            disciplina = str(obter_disciplina_aula(aula_encontrada)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                            professor = str(obter_professor_aula(aula_encontrada)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                            
                                            table_html += f"""<td class='aula-cell'>
<div class='disciplina'>{disciplina}</div>
<div class='professor'>{professor}</div>
</td>"""
                                        else:
                                            table_html += f"<td class='livre-cell'>LIVRE</td>"
                                    
                                    table_html += "</tr>"
                                    
                                    # Adicionar linha do intervalo no lugar correto
                                    if segmento == "EM" and periodo == 3:
                                        table_html += """<tr class='intervalo-row'>
<td colspan='6'>🕛 INTERVALO: 09:30 - 09:50</td>
</tr>"""
                                    elif segmento == "EF_II" and periodo == 2:
                                        table_html += """<tr class='intervalo-row'>
<td colspan='6'>🕛 INTERVALO: 09:30 - 09:50</td>
</tr>"""
                                
                                table_html += "</table>"
                                
                                # Mostrar tabela
                                st.markdown(table_html, unsafe_allow_html=True)
                                
                                # Resumo
                                st.caption(f"✅ {len(aulas_turma)} aulas alocadas | Segmento: {segmento}")
                                st.markdown("---")
                            
                            # Dataframe detalhado
                            df_aulas = pd.DataFrame([
                                {
                                    "Turma": obter_turma_aula(a),
                                    "Disciplina": obter_disciplina_aula(a), 
                                    "Professor": obter_professor_aula(a),
                                    "Dia": obter_dia_aula(a),
                                    "Horário": f"{obter_horario_aula(a)}º ({obter_horario_real(obter_turma_aula(a), obter_horario_aula(a))})",
                                    "Segmento": obter_segmento_aula(a) or obter_segmento_turma(obter_turma_aula(a))
                                }
                                for a in aulas
                            ])
                            
                            df_aulas = df_aulas.sort_values(["Turma", "Dia", "Horário"])
                            st.subheader("📊 Lista Detalhada das Aulas")
                            st.dataframe(df_aulas, width='stretch')
                            
                            # Download
                            try:
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    df_aulas.to_excel(writer, sheet_name="Grade_Completa", index=False)
                                
                                st.download_button(
                                    "📥 Baixar Grade em Excel",
                                    output.getvalue(),
                                    f"grade_{grupo_texto.replace(' ', '_')}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            except ImportError:
                                csv = df_aulas.to_csv(index=False)
                                st.download_button(
                                    "📥 Baixar Grade em CSV",
                                    csv,
                                    f"grade_{grupo_texto.replace(' ', '_')}.csv",
                                    "text/csv"
                                )
                        else:
                            st.warning("⚠️ Nenhuma aula foi gerada.")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar grade: {str(e)}")
                        st.code(traceback.format_exc())

# ============================================
# ABA GRADE POR PROFESSOR - VERSÃO CORRIGIDA
# ============================================

with abas[6]:
    st.header("👨‍🏫 Grade Horária por Professor")
    
    if not st.session_state.get('aulas'):
        st.info("ℹ️ Gere uma grade horária primeiro na aba 'Gerar Grade'.")
    else:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            # CORREÇÃO: Usar função segura para obter professores
            options_set = set()
            for a in st.session_state.aulas:
                prof = obter_professor_aula(a)
                if prof:
                    options_set.add(prof)
            options = list(sorted(options_set))
            
            professor_selecionado = st.selectbox(
                "Selecionar Professor",
                options=options,
                key="filtro_professor_grade"
            )
        
        if professor_selecionado:
            # Filtrar aulas do professor (usando função segura)
            aulas_professor = [a for a in st.session_state.aulas if obter_professor_aula(a) == professor_selecionado]
            
            if not aulas_professor:
                st.warning(f"ℹ️ Professor {professor_selecionado} não tem aulas alocadas.")
            else:
                st.success(f"📊 Professor {professor_selecionado}: {len(aulas_professor)} aulas")
                
                # Criar dataframe
                df_professor = pd.DataFrame([
                    {
                        "Dia": (obter_dia_aula(a) or "").capitalize(),
                        "Horário": f"{obter_horario_aula(a)}º ({obter_horario_real(obter_turma_aula(a), obter_horario_aula(a))})",
                        "Turma": obter_turma_aula(a),
                        "Disciplina": obter_disciplina_aula(a),
                        "Segmento": obter_segmento_aula(a) or obter_segmento_turma(obter_turma_aula(a))
                    }
                    for a in aulas_professor
                ])
                
                # Ordenar
                ordem_dias = {"Segunda": 1, "Terca": 2, "Quarta": 3, "Quinta": 4, "Sexta": 5}
                df_professor['Ordem'] = df_professor['Dia'].map(ordem_dias)
                df_professor = df_professor.sort_values(['Ordem', 'Horário']).drop('Ordem', axis=1)
                
                st.dataframe(df_professor, width='stretch')

# ============================================
# ABA DIAGNÓSTICO
# ============================================

with abas[7]:
    st.header("🔧 DIAGNÓSTICO AVANÇADO DO SISTEMA")
    
    st.subheader("📊 Análise de Capacidade")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Total de aulas necessárias
        total_necessario = 0
        for turma in st.session_state.turmas:
            grupo_turma = obter_grupo_seguro(turma)
            for disc in st.session_state.disciplinas:
                if turma.nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                    total_necessario += disc.carga_semanal
        st.metric("Aulas Necessárias", total_necessario)
    
    with col2:
        # Capacidade total do sistema
        capacidade_total = 0
        for turma in st.session_state.turmas:
            horarios = obter_horarios_turma(turma.nome)
            capacidade_total += len(horarios) * 5  # 5 dias na semana
        st.metric("Capacidade Disponível", capacidade_total)
    
    with col3:
        # Status
        if capacidade_total >= total_necessario:
            st.success("✅ Capacidade OK")
        else:
            st.error(f"❌ Déficit: {total_necessario - capacidade_total} aulas")
    
    # Análise de professores
    st.subheader("👨‍🏫 Análise de Professores")
    
    professores_problema = []
    for prof in st.session_state.professores:
        # Verificar disponibilidade mínima
        dias_disponiveis = len(prof.disponibilidade) if hasattr(prof, 'disponibilidade') else 0
        if dias_disponiveis < 3:  # Menos de 3 dias
            professores_problema.append(f"**{prof.nome}**: Apenas {dias_disponiveis} dia(s) disponível(is)")
    
    if professores_problema:
        st.warning("⚠️ Professores com pouca disponibilidade:")
        for problema in professores_problema:
            st.markdown(f"- {problema}")
    else:
        st.success("✅ Todos professores têm disponibilidade razoável")
    
    # Botão para otimização manual
    st.subheader("⚙️ Ferramentas de Otimização")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Rebalancear Professores", use_container_width=True):
            # Sugere realocação de disciplinas entre professores
            st.info("""
            **Sugestões de rebalanceamento:**
            
            1. Verifique professores com muitas disciplinas
            2. Distribua disciplinas entre professores do mesmo grupo
            3. Considere professores 'AMBOS' para cobrir falta
            """)
    
    with col2:
        if st.button("📅 Analisar Conflitos", use_container_width=True):
            if st.session_state.get('aulas'):
                diagnostico = diagnosticar_grade(
                    st.session_state.turmas,
                    st.session_state.professores,
                    st.session_state.disciplinas,
                    st.session_state.aulas
                )
                
                if diagnostico['horarios_conflitantes']:
                    st.error("Conflitos encontrados:")
                    for conflito in diagnostico['horarios_conflitantes']:
                        st.write(f"- {conflito['turma']} ({conflito['dia']}, {conflito['horario']}º): {', '.join(conflito['disciplinas'])}")
                else:
                    st.success("✅ Nenhum conflito de horário encontrado")
    
    # Grades salvas
    if hasattr(st.session_state, 'grades_salvas') and st.session_state.grades_salvas:
        st.subheader("💾 Grades Salvas")
        
        for nome_grade, dados_grade in st.session_state.grades_salvas.items():
            with st.expander(f"📁 {nome_grade} ({dados_grade['total_aulas']} aulas)"):
                st.write(f"**Data:** {dados_grade['data']}")
                st.write(f"**Configuração:** {dados_grade['config']}")
                
                if st.button(f"Carregar Grade '{nome_grade}'", key=f"load_{nome_grade}"):
                    st.session_state.aulas = dados_grade['aulas']
                    st.success(f"✅ Grade '{nome_grade}' carregada!")
                    st.rerun()

# ============================================
# SIDEBAR
# ============================================

st.sidebar.title("⚙️ Configurações")
if st.sidebar.button("🔄 Resetar Banco de Dados"):
    try:
        database.resetar_banco()
        st.sidebar.success("✅ Banco resetado! Recarregue a página.")
    except Exception as e:
        st.sidebar.error(f"❌ Erro ao resetar: {str(e)}")

st.sidebar.write("### Status do Sistema:")
st.sidebar.write(f"**Turmas:** {len(st.session_state.turmas)}")
st.sidebar.write(f"**Professores:** {len(st.session_state.professores)}")
st.sidebar.write(f"**Disciplinas:** {len(st.session_state.disciplinas)}")
st.sidebar.write(f"**Salas:** {len(st.session_state.salas)}")
st.sidebar.write(f"**Aulas na Grade:** {len(st.session_state.get('aulas', []))}")

st.sidebar.write("### 💡 Informações dos Horários:")
st.sidebar.write("**EF II:** 07:50-12:20")
st.sidebar.write("- 5 períodos + intervalo")
st.sidebar.write("**EM:** 07:00-13:10")
st.sidebar.write("- 7 períodos + intervalo")

st.sidebar.write("### 🕒 Horários Reais:")
st.sidebar.write("**EM (7 períodos):**")
st.sidebar.write("1º: 07:00-07:50")
st.sidebar.write("2º: 07:50-08:40")
st.sidebar.write("3º: 08:40-09:30")
st.sidebar.write("🕛 INTERVALO: 09:30-09:50")
st.sidebar.write("4º: 09:50-10:40")
st.sidebar.write("5º: 10:40-11:30")
st.sidebar.write("6º: 11:30-12:20")
st.sidebar.write("7º: 12:20-13:10")

st.sidebar.write("**EF II (5 períodos):**")
st.sidebar.write("1º: 07:50-08:40")
st.sidebar.write("2º: 08:40-09:30")
st.sidebar.write("🕛 INTERVALO: 09:30-09:50")
st.sidebar.write("3º: 09:50-10:40")
st.sidebar.write("4º: 10:40-11:30")
st.sidebar.write("5º: 11:30-12:20")