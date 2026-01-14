# app_corrigido_v2.py - Versão completa com correção de aulas repetidas E superposições de professor
import streamlit as st
import pandas as pd
import database
from session_state import init_session_state
from auto_save import salvar_tudo
from models import Turma, Professor, Disciplina, Sala, DIAS_SEMANA, Aula
import io
import traceback
from datetime import datetime
import random

# ============================================
# CONFIGURAÇÃO DE PÁGINA
# ============================================
st.set_page_config(page_title="Escola Timetable", layout="wide")
st.title("🕒 Gerador Inteligente de Grade Horária")

# ============================================
# VERIFICAÇÃO DE ALGORITMOS
# ============================================
ALGORITMOS_DISPONIVEIS = True
try:
    from simple_scheduler import SimpleGradeHoraria
except ImportError:
    ALGORITMOS_DISPONIVEIS = False
    
    class SimpleGradeHoraria:
        def __init__(self, *args, **kwargs):
            self.turmas = []
            self.professores = []
            self.disciplinas = []
            self.salas = []
        
        def gerar_grade(self):
            st.error("❌ Algoritmo simples não disponível")
            return []

# ============================================
# INICIALIZAÇÃO
# ============================================
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
# CONSTANTES E LIMITES
# ============================================
LIMITE_HORAS_EFII = 25  # horas semanais máximas para professores de EF II
LIMITE_HORAS_EM = 35    # horas semanais máximas para professores de EM

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
    """Determina o segmento da turma baseado no nome"""
    if not turma_nome:
        return "EF_II"
    
    turma_nome_lower = turma_nome.lower()
    
    # Verificar se é EM
    if 'em' in turma_nome_lower:
        return "EM"
    # Verificar se é EF II
    elif any(x in turma_nome_lower for x in ['6', '7', '8', '9', 'ano', 'ef']):
        return "EF_II"
    else:
        try:
            if turma_nome_lower[0].isdigit():
                return "EF_II"
            else:
                return "EM"
        except:
            return "EF_II"

def obter_segmento_professor(professor):
    """Determina o segmento principal do professor baseado nas disciplinas que ministra"""
    if not hasattr(professor, 'disciplinas') or not professor.disciplinas:
        return "AMBOS"
    
    # Verificar disciplinas do professor
    tem_efii = False
    tem_em = False
    
    for disc_nome in professor.disciplinas:
        # Encontrar disciplina correspondente
        for disc in st.session_state.disciplinas:
            if disc.nome == disc_nome:
                # Verificar turmas desta disciplina
                for turma_nome in disc.turmas:
                    segmento = obter_segmento_turma(turma_nome)
                    if segmento == "EF_II":
                        tem_efii = True
                    elif segmento == "EM":
                        tem_em = True
    
    if tem_efii and tem_em:
        return "AMBOS"
    elif tem_efii:
        return "EF_II"
    elif tem_em:
        return "EM"
    else:
        return "AMBOS"

def obter_limite_horas_professor(professor):
    """Retorna o limite de horas semanais para o professor"""
    segmento = obter_segmento_professor(professor)
    
    if segmento == "EF_II":
        return LIMITE_HORAS_EFII
    elif segmento == "EM":
        return LIMITE_HORAS_EM
    else:
        # Para professores que dão aula em ambos, usar o limite maior
        return LIMITE_HORAS_EM

def calcular_horas_professor(professor, aulas):
    """Calcula horas semanais do professor baseado nas aulas"""
    total_horas = 0
    
    for aula in aulas:
        if obter_professor_aula(aula) == professor.nome:
            # Cada aula = 1 hora
            total_horas += 1
    
    return total_horas

def obter_horarios_turma(turma_nome):
    """Retorna os períodos disponíveis para a turma"""
    segmento = obter_segmento_turma(turma_nome)
    if segmento == "EM":
        return [1, 2, 3, 4, 5, 6, 7]  # 7 períodos para EM
    else:
        return [1, 2, 3, 4, 5]  # 5 períodos para EF II

def obter_horario_real(turma_nome, periodo):
    """Retorna o horário real formatado COM INTERVALO CORRETO"""
    segmento = obter_segmento_turma(turma_nome)
    
    if segmento == "EM":
        # Ensino Médio: 7 períodos com intervalo APÓS o 3º período
        horarios_em = {
            1: "07:00 - 07:50",
            2: "07:50 - 08:40", 
            3: "08:40 - 09:30",  # ÚLTIMO ANTES DO INTERVALO
            4: "09:50 - 10:40",  # PRIMEIRO APÓS INTERVALO
            5: "10:40 - 11:30",
            6: "11:30 - 12:20",
            7: "12:20 - 13:10"
        }
        return horarios_em.get(periodo, f"Período {periodo}")
    else:
        # EF II: 5 períodos com intervalo APÓS o 2º período
        horarios_efii = {
            1: "07:50 - 08:40",
            2: "08:40 - 09:30",  # ÚLTIMO ANTES DO INTERVALO
            3: "09:50 - 10:40",  # PRIMEIRO APÓS INTERVALO
            4: "10:40 - 11:30",
            5: "11:30 - 12:20"
        }
        return horarios_efii.get(periodo, f"Período {periodo}")

def calcular_carga_maxima(serie):
    """Calcula a quantidade máxima de aulas semanais"""
    if not serie:
        return 25
    
    serie_lower = serie.lower()
    if 'em' in serie_lower or serie_lower in ['1em', '2em', '3em']:
        return 35  # EM: 7 aulas × 5 dias
    else:
        return 25  # EF II: 5 aulas × 5 dias

def converter_dia_para_semana(dia):
    """Converte dia do formato completo para abreviado"""
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
# FUNÇÕES DE ACESSO SEGURO A AULAS
# ============================================

def obter_turma_aula(aula):
    """Obtém a turma de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.turma
    elif isinstance(aula, dict) and 'turma' in aula:
        return aula['turma']
    elif hasattr(aula, 'turma'):
        return aula.turma
    return None

def obter_disciplina_aula(aula):
    """Obtém a disciplina de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.disciplina
    elif isinstance(aula, dict) and 'disciplina' in aula:
        return aula['disciplina']
    elif hasattr(aula, 'disciplina'):
        return aula.disciplina
    return None

def obter_professor_aula(aula):
    """Obtém o professor de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.professor
    elif isinstance(aula, dict) and 'professor' in aula:
        return aula['professor']
    elif hasattr(aula, 'professor'):
        return aula.professor
    return None

def obter_dia_aula(aula):
    """Obtém o dia de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.dia
    elif isinstance(aula, dict) and 'dia' in aula:
        return aula['dia']
    elif hasattr(aula, 'dia'):
        return aula.dia
    return None

def obter_horario_aula(aula):
    """Obtém o horário de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.horario
    elif isinstance(aula, dict) and 'horario' in aula:
        return aula['horario']
    elif hasattr(aula, 'horario'):
        return aula.horario
    return None

def obter_segmento_aula(aula):
    """Obtém o segmento de uma aula de forma segura"""
    if isinstance(aula, Aula):
        return aula.segmento if hasattr(aula, 'segmento') else None
    elif isinstance(aula, dict) and 'segmento' in aula:
        return aula['segmento']
    elif hasattr(aula, 'segmento'):
        return aula.segmento
    return None

# ============================================
# FUNÇÕES PARA PROFESSORES POR DISCIPLINA
# ============================================

def obter_professores_para_disciplina(disciplina_nome, grupo=None):
    """Retorna lista de professores que podem ministrar uma disciplina"""
    professores_disponiveis = []
    
    for professor in st.session_state.professores:
        if disciplina_nome in professor.disciplinas:
            # Verificar se o grupo do professor é compatível
            if grupo:
                prof_grupo = obter_grupo_seguro(professor)
                if prof_grupo in [grupo, "AMBOS"]:
                    professores_disponiveis.append(professor)
            else:
                professores_disponiveis.append(professor)
    
    return professores_disponiveis

def calcular_disponibilidade_professor(professor):
    """Calcula disponibilidade semanal do professor em horas"""
    dias_disponiveis = len(professor.disponibilidade) if hasattr(professor, 'disponibilidade') else 0
    horarios_indisponiveis = len(professor.horarios_indisponiveis) if hasattr(professor, 'horarios_indisponiveis') else 0
    
    # Cada dia tem 7 períodos possíveis
    total_periodos = dias_disponiveis * 7
    periodos_disponiveis = total_periodos - horarios_indisponiveis
    
    return periodos_disponiveis

def verificar_professor_comprometido(professor, disciplina_nome, grupo):
    """Verifica se um professor está comprometido com outras disciplinas"""
    # Obter todas as disciplinas que o professor ministra
    disciplinas_prof = professor.disciplinas
    
    if disciplina_nome not in disciplinas_prof:
        return False  # Não ministra esta disciplina
    
    # Verificar se há outras disciplinas no mesmo grupo
    outras_disciplinas = [d for d in disciplinas_prof if d != disciplina_nome]
    
    if not outras_disciplinas:
        return False  # Só ministra esta disciplina
    
    # Verificar se outras disciplinas são do mesmo grupo
    for outra_disc_nome in outras_disciplinas:
        # Encontrar a disciplina
        for disc in st.session_state.disciplinas:
            if disc.nome == outra_disc_nome:
                disc_grupo = obter_grupo_seguro(disc)
                if disc_grupo == grupo:
                    return True  # Está comprometido com outra disciplina do mesmo grupo
    
    return False

# ============================================
# FUNÇÕES PARA VERIFICAÇÃO E CORREÇÃO DE CONFLITOS
# ============================================

def verificar_conflitos_horarios(aulas):
    """Verifica se há horários sobrepostos na mesma turma"""
    conflitos = []
    horarios_por_turma = {}
    
    for aula in aulas:
        turma = obter_turma_aula(aula)
        dia = obter_dia_aula(aula)
        horario = obter_horario_aula(aula)
        
        if not turma or not dia or not horario:
            continue
            
        chave = f"{turma}|{dia}|{horario}"
        
        if chave not in horarios_por_turma:
            horarios_por_turma[chave] = []
        
        horarios_por_turma[chave].append(aula)
        
        if len(horarios_por_turma[chave]) > 1:
            # CONFLITO DETECTADO!
            conflitos.append({
                'turma': turma,
                'dia': dia,
                'horario': horario,
                'aulas': horarios_por_turma[chave].copy(),
                'chave': chave
            })
    
    return conflitos

def verificar_professor_superposto(aulas):
    """Verifica se o mesmo professor tem aulas em horários sobrepostos"""
    superposicoes = []
    horarios_por_professor = {}
    
    for aula in aulas:
        professor = obter_professor_aula(aula)
        dia = obter_dia_aula(aula)
        horario = obter_horario_aula(aula)
        
        if not professor or not dia or not horario:
            continue
            
        chave = f"{professor}|{dia}|{horario}"
        
        if chave not in horarios_por_professor:
            horarios_por_professor[chave] = []
        
        horarios_por_professor[chave].append(aula)
        
        if len(horarios_por_professor[chave]) > 1:
            # SUPERPOSIÇÃO DETECTADA! Professor em dois lugares ao mesmo tempo
            superposicoes.append({
                'professor': professor,
                'dia': dia,
                'horario': horario,
                'aulas': horarios_por_professor[chave].copy(),
                'turmas': [obter_turma_aula(a) for a in horarios_por_professor[chave]],
                'disciplinas': [obter_disciplina_aula(a) for a in horarios_por_professor[chave]],
                'chave': chave
            })
    
    return superposicoes

def verificar_limites_professores(aulas):
    """Verifica se algum professor excedeu o limite de horas"""
    problemas = []
    
    for professor in st.session_state.professores:
        horas_atual = calcular_horas_professor(professor, aulas)
        limite = obter_limite_horas_professor(professor)
        
        if horas_atual > limite:
            problemas.append({
                'professor': professor.nome,
                'horas_atual': horas_atual,
                'limite': limite,
                'segmento': obter_segmento_professor(professor)
            })
    
    return problemas

# ============================================
# FUNÇÃO NOVA: REMOVER AULAS REPETIDAS
# ============================================

def remover_aulas_repetidas(aulas):
    """Remove aulas repetidas da mesma disciplina para a mesma turma"""
    if not aulas:
        return aulas
    
    aulas_filtradas = []
    contador = {}
    
    for aula in aulas:
        turma = obter_turma_aula(aula)
        disciplina = obter_disciplina_aula(aula)
        
        if not turma or not disciplina:
            aulas_filtradas.append(aula)  # Mantém se não puder identificar
            continue
            
        chave = f"{turma}|{disciplina}"
        
        # Obter carga semanal necessária
        carga_necessaria = 0
        for disc in st.session_state.disciplinas:
            if disc.nome == disciplina and turma in disc.turmas:
                carga_necessaria = disc.carga_semanal
                break
        
        # Inicializar contador se não existir
        if chave not in contador:
            contador[chave] = 0
        
        # Adicionar apenas se não exceder a carga necessária
        if contador[chave] < carga_necessaria:
            aulas_filtradas.append(aula)
            contador[chave] += 1
        else:
            # Aula repetida - não adicionar
            continue
    
    return aulas_filtradas

# ============================================
# FUNÇÃO NOVA: CORRIGIR SUPERPOSIÇÕES DE PROFESSOR
# ============================================

def corrigir_superposicoes_professor(aulas, superposicoes):
    """Corrige superposições onde o mesmo professor tem aulas no mesmo horário"""
    if not superposicoes:
        return aulas
    
    # Converter para lista de dicionários para facilitar manipulação
    aulas_dict = []
    for aula in aulas:
        aulas_dict.append({
            'turma': obter_turma_aula(aula),
            'disciplina': obter_disciplina_aula(aula),
            'professor': obter_professor_aula(aula),
            'dia': obter_dia_aula(aula),
            'horario': obter_horario_aula(aula),
            'segmento': obter_segmento_aula(aula) or obter_segmento_turma(obter_turma_aula(aula)),
            'id_temporario': len(aulas_dict)  # Para rastrear a aula original
        })
    
    # Para cada superposição, tentar encontrar horário livre
    for superposicao in superposicoes:
        professor = superposicao['professor']
        dia = superposicao['dia']
        horario_superposto = superposicao['horario']
        
        # Encontrar todas as aulas deste professor neste dia/horário
        aulas_superpostas = []
        for i, aula in enumerate(aulas_dict):
            if aula['professor'] == professor and aula['dia'] == dia and aula['horario'] == horario_superposto:
                aulas_superpostas.append((i, aula))
        
        # Se tiver mais de uma aula no mesmo horário, mover as extras
        if len(aulas_superpostas) > 1:
            st.info(f"Corrigindo superposição: Professor {professor} tem {len(aulas_superpostas)} aulas às {dia}, {horario_superposto}º")
            
            # Manter a primeira, mover as outras
            manter_idx, manter_aula = aulas_superpostas[0]
            
            for idx, aula in aulas_superpostas[1:]:
                turma = aula['turma']
                
                # Encontrar horários possíveis para esta turma
                segmento = obter_segmento_turma(turma)
                if segmento == "EM":
                    horarios_possiveis = list(range(1, 8))
                else:
                    horarios_possiveis = list(range(1, 6))
                
                # Encontrar horários já ocupados nesta turma/dia
                horarios_ocupados_turma = set()
                # E horários já ocupados por este professor
                horarios_ocupados_prof = set()
                
                for a in aulas_dict:
                    if a['turma'] == turma and a['dia'] == dia:
                        horarios_ocupados_turma.add(a['horario'])
                    
                    if a['professor'] == professor and a['dia'] == dia:
                        horarios_ocupados_prof.add(a['horario'])
                
                # Prioridade 1: Encontrar horário livre no MESMO DIA
                horario_livre = None
                for h in horarios_possiveis:
                    if h not in horarios_ocupados_turma and h not in horarios_ocupados_prof:
                        horario_livre = h
                        break
                
                # Se encontrou horário livre no mesmo dia, mover a aula
                if horario_livre:
                    aulas_dict[idx]['horario'] = horario_livre
                    st.success(f"  • Movida aula de {aula['disciplina']} (Turma {turma}) para horário {horario_livre}º")
                
                else:
                    # Prioridade 2: Tentar outro dia
                    dias_semana = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
                    dias_semana.remove(dia)  # Remover o dia atual
                    
                    encontrou_novo_dia = False
                    for novo_dia in dias_semana:
                        # Verificar se turma tem horário livre neste novo dia
                        turma_horarios_livres = []
                        for h in horarios_possiveis:
                            turma_ocupada = False
                            prof_ocupado = False
                            
                            for a in aulas_dict:
                                if a['turma'] == turma and a['dia'] == novo_dia and a['horario'] == h:
                                    turma_ocupada = True
                                if a['professor'] == professor and a['dia'] == novo_dia and a['horario'] == h:
                                    prof_ocupado = True
                            
                            if not turma_ocupada and not prof_ocupado:
                                turma_horarios_livres.append(h)
                        
                        if turma_horarios_livres:
                            # Escolher o primeiro horário livre
                            novo_horario = turma_horarios_livres[0]
                            aulas_dict[idx]['dia'] = novo_dia
                            aulas_dict[idx]['horario'] = novo_horario
                            encontrou_novo_dia = True
                            st.success(f"  • Movida aula de {aula['disciplina']} (Turma {turma}) para {novo_dia}, {novo_horario}º")
                            break
                    
                    if not encontrou_novo_dia:
                        st.warning(f"  ⚠️ Não foi possível realocar aula de {aula['disciplina']} (Turma {turma}). Mantendo no horário original.")
    
    # Remover ID temporário
    for aula in aulas_dict:
        if 'id_temporario' in aula:
            del aula['id_temporario']
    
    # Converter de volta para objetos Aula
    aulas_corrigidas = []
    for aula_dict in aulas_dict:
        aulas_corrigidas.append(Aula(
            turma=aula_dict['turma'],
            disciplina=aula_dict['disciplina'],
            professor=aula_dict['professor'],
            dia=aula_dict['dia'],
            horario=aula_dict['horario'],
            segmento=aula_dict['segmento']
        ))
    
    return aulas_corrigidas

def corrigir_conflitos_automaticamente(aulas, conflitos):
    """Tenta corrigir conflitos de horário automaticamente"""
    if not conflitos:
        return aulas
    
    # Converter para lista de dicionários para facilitar manipulação
    aulas_dict = []
    for aula in aulas:
        aulas_dict.append({
            'turma': obter_turma_aula(aula),
            'disciplina': obter_disciplina_aula(aula),
            'professor': obter_professor_aula(aula),
            'dia': obter_dia_aula(aula),
            'horario': obter_horario_aula(aula),
            'segmento': obter_segmento_aula(aula) or obter_segmento_turma(obter_turma_aula(aula))
        })
    
    # Para cada conflito, tentar encontrar horário livre
    for conflito in conflitos:
        turma = conflito['turma']
        dia = conflito['dia']
        horario_conflito = conflito['horario']
        
        # Encontrar aulas conflitantes
        aulas_conflitantes = []
        for i, aula in enumerate(aulas_dict):
            if aula['turma'] == turma and aula['dia'] == dia and aula['horario'] == horario_conflito:
                aulas_conflitantes.append((i, aula))
        
        # Se tiver mais de uma aula no mesmo horário, mover as extras
        if len(aulas_conflitantes) > 1:
            # Manter a primeira, mover as outras
            for idx, aula in aulas_conflitantes[1:]:
                # Encontrar horários possíveis para esta turma
                segmento = obter_segmento_turma(turma)
                if segmento == "EM":
                    horarios_possiveis = list(range(1, 8))
                else:
                    horarios_possiveis = list(range(1, 6))
                
                # Encontrar horários já ocupados nesta turma/dia
                horarios_ocupados = set()
                for a in aulas_dict:
                    if a['turma'] == turma and a['dia'] == dia:
                        horarios_ocupados.add(a['horario'])
                
                # Encontrar horário livre
                horario_livre = None
                for h in horarios_possiveis:
                    if h not in horarios_ocupados:
                        horario_livre = h
                        break
                
                # Se encontrou horário livre, mover a aula
                if horario_livre:
                    aulas_dict[idx]['horario'] = horario_livre
    
    # Converter de volta para objetos Aula
    aulas_corrigidas = []
    for aula_dict in aulas_dict:
        aulas_corrigidas.append(Aula(
            turma=aula_dict['turma'],
            disciplina=aula_dict['disciplina'],
            professor=aula_dict['professor'],
            dia=aula_dict['dia'],
            horario=aula_dict['horario'],
            segmento=aula_dict['segmento']
        ))
    
    return aulas_corrigidas

def corrigir_csv_export(df):
    """Corrige problemas de formatação no CSV exportado"""
    # Remover coluna de índice se existir
    if '' in df.columns or df.columns[0] == '':
        if '' in df.columns:
            df = df.drop(columns=[''])
        elif df.columns[0] == '':
            df = df.drop(columns=[df.columns[0]])
    
    # Ordenar por dia e horário
    ordem_dias = {"Segunda": 1, "Terca": 2, "Quarta": 3, "Quinta": 4, "Sexta": 5}
    
    # Extrair número do período do horário para ordenação
    def extrair_periodo(horario):
        try:
            return int(str(horario).split('º')[0])
        except:
            return 0
    
    if 'Horário' in df.columns:
        df['Periodo'] = df['Horário'].apply(extrair_periodo)
    else:
        df['Periodo'] = 0
    
    if 'Dia' in df.columns:
        df['Dia_Ordem'] = df['Dia'].map(ordem_dias)
        df = df.sort_values(['Dia_Ordem', 'Periodo'])
        df = df.drop(['Dia_Ordem', 'Periodo'], axis=1)
    else:
        df = df.sort_values(['Periodo'])
        df = df.drop(['Periodo'], axis=1)
    
    return df

# ============================================
# SISTEMA DE DIAGNÓSTICO DE GRADE (MELHORADO)
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
        'horarios_conflitantes': [],
        'conflitos_detectados': [],
        'professores_limite_excedido': [],
        'aulas_repetidas': [],
        'professores_superpostos': []  # NOVO
    }
    
    if not aulas_alocadas:
        return diagnostico
    
    # Verificar conflitos de horário primeiro
    conflitos = verificar_conflitos_horarios(aulas_alocadas)
    diagnostico['conflitos_detectados'] = conflitos
    
    # Verificar limites de horas dos professores
    problemas_limites = verificar_limites_professores(aulas_alocadas)
    diagnostico['professores_limite_excedido'] = problemas_limites
    
    # Verificar superposições de professor (CRÍTICO!)
    superposicoes = verificar_professor_superposto(aulas_alocadas)
    diagnostico['professores_superpostos'] = superposicoes
    
    # Verificar aulas repetidas
    aulas_por_disciplina_turma = {}
    for aula in aulas_alocadas:
        turma = obter_turma_aula(aula)
        disciplina = obter_disciplina_aula(aula)
        
        if not turma or not disciplina:
            continue
            
        chave = f"{turma}|{disciplina}"
        
        if chave not in aulas_por_disciplina_turma:
            aulas_por_disciplina_turma[chave] = []
        
        aulas_por_disciplina_turma[chave].append(aula)
        
        # Obter carga semanal necessária
        carga_necessaria = 0
        for disc in disciplinas:
            if disc.nome == disciplina and turma in disc.turmas:
                carga_necessaria = disc.carga_semanal
                break
        
        # Se tem mais aulas do que o necessário
        if len(aulas_por_disciplina_turma[chave]) > carga_necessaria:
            # Adicionar à lista de repetidas
            diagnostico['aulas_repetidas'].append({
                'turma': turma,
                'disciplina': disciplina,
                'quantidade': len(aulas_por_disciplina_turma[chave]),
                'necessario': carga_necessaria,
                'excesso': len(aulas_por_disciplina_turma[chave]) - carga_necessaria
            })
    
    # Converter todas as aulas para formato consistente
    aulas_consistente = []
    for aula in aulas_alocadas:
        aulas_consistente.append({
            'turma': obter_turma_aula(aula),
            'disciplina': obter_disciplina_aula(aula),
            'professor': obter_professor_aula(aula),
            'dia': obter_dia_aula(aula),
            'horario': obter_horario_aula(aula),
            'segmento': obter_segmento_aula(aula) or obter_segmento_turma(obter_turma_aula(aula))
        })
    
    # 1. ANÁLISE POR TURMA
    total_aulas_necessarias = 0
    total_aulas_alocadas = len(aulas_consistente)
    
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
        aulas_turma = [a for a in aulas_consistente if a['turma'] == turma_nome]
        aulas_alocadas_turma = len(aulas_turma)
        
        # Calcular completude da turma
        completude_turma = (aulas_alocadas_turma / aulas_necessarias_turma * 100) if aulas_necessarias_turma > 0 else 0
        
        # Detalhar por disciplina
        faltas_disciplinas = []
        for disc in disciplinas_da_turma:
            aulas_disc = len([a for a in aulas_turma if a['disciplina'] == disc.nome])
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
        aulas_professor = len([a for a in aulas_consistente if a['professor'] == professor.nome])
        
        # Verificar disponibilidade
        dias_disponiveis = len(professor.disponibilidade) if hasattr(professor, 'disponibilidade') else 0
        horarios_indisponiveis = len(professor.horarios_indisponiveis) if hasattr(professor, 'horarios_indisponiveis') else 0
        
        # Calcular capacidade máxima baseada em disponibilidade
        capacidade_maxima = dias_disponiveis * 7 - horarios_indisponiveis
        
        # Calcular limite baseado no segmento
        limite_segmento = obter_limite_horas_professor(professor)
        capacidade_maxima = min(capacidade_maxima, limite_segmento)
        
        if capacidade_maxima <= aulas_professor:
            diagnostico['professores_saturados'].append({
                'nome': professor.nome,
                'aulas': aulas_professor,
                'capacidade': capacidade_maxima,
                'dias_disponiveis': dias_disponiveis,
                'horarios_bloqueados': horarios_indisponiveis,
                'limite_segmento': limite_segmento,
                'segmento': obter_segmento_professor(professor)
            })
    
    # 4. IDENTIFICAR PROBLEMAS PRINCIPAIS
    for turma_nome, info in diagnostico['detalhes_por_turma'].items():
        if info['faltas_disciplinas']:
            turma_obj = next((t for t in turmas if t.nome == turma_nome), None)
            grupo_turma = turma_obj.grupo if turma_obj else 'A'
            
            for falta in info['faltas_disciplinas']:
                disc_nome = falta.split(' (')[0]
                
                # Verificar professores para esta disciplina
                professores_disc = obter_professores_para_disciplina(disc_nome, grupo_turma)
                
                if not professores_disc:
                    diagnostico['problemas'].append(f"❌ **{turma_nome}**: Nenhum professor para **{disc_nome}**")
                    diagnostico['sugestoes'].append(f"👉 Adicione um professor que ministre **{disc_nome}** no grupo **{grupo_turma}**")
                else:
                    # Verificar comprometimento dos professores
                    professores_livres = []
                    professores_comprometidos = []
                    
                    for prof in professores_disc:
                        if verificar_professor_comprometido(prof, disc_nome, grupo_turma):
                            professores_comprometidos.append(prof.nome)
                        else:
                            professores_livres.append(prof.nome)
                    
                    if not professores_livres:
                        diagnostico['problemas'].append(f"⚠️ **{turma_nome}**: Todos professores para **{disc_nome}** estão comprometidos com outras disciplinas")
                        diagnostico['sugestoes'].append(f"👉 Adicione mais professores para **{disc_nome}** ou libere professores comprometidos")
                    elif len(professores_livres) == 1:
                        diagnostico['problemas'].append(f"⚠️ **{turma_nome}**: Apenas 1 professor livre para **{disc_nome}** ({professores_livres[0]})")
                        diagnostico['sugestoes'].append(f"👉 Adicione um segundo professor para **{disc_nome}** ou aumente a disponibilidade de **{professores_livres[0]}**")
    
    # 5. Conflitos de horário
    horarios_turma = {}
    for aula in aulas_consistente:
        chave = f"{aula['turma']}|{aula['dia']}|{aula['horario']}"
        if chave not in horarios_turma:
            horarios_turma[chave] = []
        horarios_turma[chave].append(aula)
    
    for chave, aulas_conflito in horarios_turma.items():
        if len(aulas_conflito) > 1:
            turma = aulas_conflito[0]['turma']
            dia = aulas_conflito[0]['dia']
            horario = aulas_conflito[0]['horario']
            disciplinas = [a['disciplina'] for a in aulas_conflito]
            professores = [a['professor'] for a in aulas_conflito]
            diagnostico['horarios_conflitantes'].append({
                'turma': turma,
                'dia': dia,
                'horario': horario,
                'disciplinas': disciplinas,
                'professores': professores
            })
    
    # 6. Aulas repetidas (adicionar aos problemas)
    if diagnostico['aulas_repetidas']:
        for repetida in diagnostico['aulas_repetidas'][:3]:
            diagnostico['problemas'].append(
                f"❌ **AULA REPETIDA**: {repetida['disciplina']} na turma {repetida['turma']} "
                f"tem {repetida['quantidade']} aulas (necessário: {repetida['necessario']})"
            )
        
        # Adicionar sugestão específica
        total_excesso = sum([r['excesso'] for r in diagnostico['aulas_repetidas']])
        diagnostico['sugestoes'].append(
            f"👉 **Remova {total_excesso} aulas repetidas** usando o botão 'Remover Aulas Repetidas'"
        )
    
    # 7. Superposições de professor (CRÍTICO!)
    if superposicoes:
        for sup in superposicoes[:3]:
            turmas_str = ", ".join(sup['turmas'][:2])
            if len(sup['turmas']) > 2:
                turmas_str += f" (+{len(sup['turmas'])-2} mais)"
            
            diagnostico['problemas'].append(
                f"❌ **SUPERPOSIÇÃO CRÍTICA**: Professor **{sup['professor']}** tem {len(sup['aulas'])} aulas "
                f"no mesmo horário ({sup['dia']}, {sup['horario']}º) nas turmas: {turmas_str}"
            )
        
        diagnostico['sugestoes'].append(
            "👉 **CORRIJA IMEDIATAMENTE** usando o botão 'Corrigir Superposições de Professor'"
        )
    
    # 8. DEFINIR STATUS FINAL
    status_critico = len(superposicoes) > 0
    status_incompleto = diagnostico['completude'] < 100
    status_problemas = len(conflitos) > 0 or len(problemas_limites) > 0 or len(diagnostico['aulas_repetidas']) > 0
    
    if status_critico:
        diagnostico['status'] = '❌ CRÍTICO (Professor sobreposto)'
    elif not status_incompleto and not status_problemas:
        diagnostico['status'] = '✅ COMPLETA'
    elif diagnostico['completude'] >= 90:
        diagnostico['status'] = '⚠️ QUASE COMPLETA'
    elif diagnostico['completude'] >= 70:
        diagnostico['status'] = '⚠️ PARCIAL'
    else:
        diagnostico['status'] = '❌ INCOMPLETA'
    
    # 9. SUGESTÕES AUTOMÁTICAS
    if conflitos:
        diagnostico['problemas'].insert(0, f"❌ **CONFLITOS DETECTADOS**: {len(conflitos)} horários sobrepostos")
        diagnostico['sugestoes'].insert(0, "👉 Use o botão 'Corrigir Conflitos Automaticamente' para resolver")
    
    if problemas_limites:
        for problema in problemas_limites[:2]:
            diagnostico['problemas'].append(f"❌ **LIMITE EXCEDIDO**: Professor **{problema['professor']}** tem {problema['horas_atual']}h (limite: {problema['limite']}h para {problema['segmento']})")
            diagnostico['sugestoes'].append(f"👉 Reduza carga do professor **{problema['professor']}** ou redistribua aulas")
    
    if diagnostico['professores_saturados']:
        for prof in diagnostico['professores_saturados'][:3]:
            diagnostico['sugestoes'].append(f"👉 Professor **{prof['nome']}** está com {prof['aulas']}/{prof['capacidade']} aulas. Aumente disponibilidade ou reduza carga.")
    
    if total_aulas_necessarias > total_aulas_alocadas:
        faltam = total_aulas_necessarias - total_aulas_alocadas
        diagnostico['sugestoes'].append(f"👉 **Faltam {faltam} aulas no total**. Verifique disponibilidade de professores.")
    
    return diagnostico

# ============================================
# ALGORITMO AVANÇADO PARA COMPLETAR GRADES
# ============================================

class CompletadorDeGradeAvancado:
    """Algoritmo avançado para completar grades incompletas"""
    
    def __init__(self, turmas, professores, disciplinas):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = disciplinas
        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        self.max_iteracoes = 500
    
    def completar_grade(self, aulas_atuais):
        """Tenta completar uma grade existente"""
        if not aulas_atuais:
            return self._gerar_grade_do_zero()
        
        # Remover aulas repetidas primeiro
        aulas_atuais = remover_aulas_repetidas(aulas_atuais)
        
        # Corrigir superposições de professor
        superposicoes = verificar_professor_superposto(aulas_atuais)
        if superposicoes:
            aulas_atuais = corrigir_superposicoes_professor(aulas_atuais, superposicoes)
        
        # Converter para formato consistente
        aulas = self._converter_para_dict(aulas_atuais)
        
        # Verificar e corrigir conflitos primeiro
        conflitos = self._verificar_conflitos(aulas)
        if conflitos:
            aulas = self._corrigir_conflitos_internos(aulas, conflitos)
        
        # Verificar limites de professores
        limites_excedidos = self._verificar_limites_professores(aulas)
        if limites_excedidos:
            aulas = self._corrigir_limites_professores(aulas, limites_excedidos)
        
        # Analisar estado atual
        analise = self._analisar_estado(aulas)
        
        # Se já está completa, retornar
        if analise['completude'] == 100:
            return self._converter_para_aulas(aulas)
        
        # Tentar múltiplas estratégias
        estrategias = [
            self._estrategia_preencher_buracos,
            self._estrategia_rebalancear_professores,
            self._estrategia_permutar_horarios,
            self._estrategia_busca_local
        ]
        
        for estrategia in estrategias:
            st.info(f"Tentando estratégia: {estrategia.__name__}")
            nova_aulas = estrategia(aulas, analise)
            nova_analise = self._analisar_estado(nova_aulas)
            
            if nova_analise['completude'] > analise['completude']:
                aulas = nova_aulas
                analise = nova_analise
                
                if analise['completude'] == 100:
                    break
        
        # Converter de volta para objetos Aula
        return self._converter_para_aulas(aulas)
    
    def _converter_para_dict(self, aulas):
        """Converte aulas para formato dicionário"""
        aulas_dict = []
        for aula in aulas:
            aulas_dict.append({
                'turma': obter_turma_aula(aula),
                'disciplina': obter_disciplina_aula(aula),
                'professor': obter_professor_aula(aula),
                'dia': obter_dia_aula(aula),
                'horario': obter_horario_aula(aula),
                'segmento': obter_segmento_aula(aula) or obter_segmento_turma(obter_turma_aula(aula))
            })
        return aulas_dict
    
    def _converter_para_aulas(self, aulas_dict):
        """Converte dicionários para objetos Aula"""
        aulas_objetos = []
        for aula in aulas_dict:
            aulas_objetos.append(Aula(
                turma=aula['turma'],
                disciplina=aula['disciplina'],
                professor=aula['professor'],
                dia=aula['dia'],
                horario=aula['horario'],
                segmento=aula['segmento']
            ))
        return aulas_objetos
    
    def _verificar_conflitos(self, aulas):
        """Verifica conflitos internos"""
        conflitos = []
        horarios_por_turma = {}
        
        for aula in aulas:
            chave = f"{aula['turma']}|{aula['dia']}|{aula['horario']}"
            if chave not in horarios_por_turma:
                horarios_por_turma[chave] = []
            horarios_por_turma[chave].append(aula)
            
            if len(horarios_por_turma[chave]) > 1:
                conflitos.append({
                    'chave': chave,
                    'aulas': horarios_por_turma[chave].copy()
                })
        
        return conflitos
    
    def _verificar_limites_professores(self, aulas):
        """Verifica se professores excederam limites"""
        problemas = []
        
        for professor in self.professores:
            # Contar aulas do professor
            aulas_prof = len([a for a in aulas if a['professor'] == professor.nome])
            
            # Obter limite
            limite = obter_limite_horas_professor(professor)
            
            if aulas_prof > limite:
                problemas.append({
                    'professor': professor,
                    'aulas_atual': aulas_prof,
                    'limite': limite
                })
        
        return problemas
    
    def _corrigir_conflitos_internos(self, aulas, conflitos):
        """Corrige conflitos internos no algoritmo"""
        aulas_corrigidas = aulas.copy()
        
        for conflito in conflitos:
            turma = conflito['aulas'][0]['turma']
            dia = conflito['aulas'][0]['dia']
            horario_conflito = conflito['aulas'][0]['horario']
            
            # Encontrar horários possíveis
            segmento = obter_segmento_turma(turma)
            if segmento == "EM":
                horarios_possiveis = list(range(1, 8))
            else:
                horarios_possiveis = list(range(1, 6))
            
            # Encontrar horários ocupados
            horarios_ocupados = set()
            for aula in aulas_corrigidas:
                if aula['turma'] == turma and aula['dia'] == dia:
                    horarios_ocupados.add(aula['horario'])
            
            # Para cada aula conflitante (exceto a primeira)
            for i, aula in enumerate(aulas_corrigidas):
                if aula['turma'] == turma and aula['dia'] == dia and aula['horario'] == horario_conflito:
                    # Se não for a primeira ocorrência, tentar mover
                    encontrou_primeira = False
                    for j, a in enumerate(aulas_corrigidas):
                        if a['turma'] == turma and a['dia'] == dia and a['horario'] == horario_conflito:
                            if j == i:
                                encontrou_primeira = True
                            elif encontrou_primeira:
                                # Encontrar horário livre
                                for h in horarios_possiveis:
                                    if h not in horarios_ocupados:
                                        aulas_corrigidas[i]['horario'] = h
                                        horarios_ocupados.add(h)
                                        break
        
        return aulas_corrigidas
    
    def _corrigir_limites_professores(self, aulas, limites_excedidos):
        """Corrige professores que excederam limites"""
        aulas_corrigidas = aulas.copy()
        
        for problema in limites_excedidos:
            professor = problema['professor']
            limite = problema['limite']
            aulas_atual = problema['aulas_atual']
            
            # Encontrar aulas deste professor
            aulas_prof = [a for a in aulas_corrigidas if a['professor'] == professor.nome]
            
            # Se excedeu limite, remover aulas mais recentes
            if aulas_atual > limite:
                # Ordenar aulas por turma/disciplina menos crítica
                aulas_para_remover = aulas_atual - limite
                
                # Remover as últimas aulas alocadas
                for i in range(len(aulas_corrigidas)-1, -1, -1):
                    if aulas_corrigidas[i]['professor'] == professor.nome and aulas_para_remover > 0:
                        aulas_corrigidas.pop(i)
                        aulas_para_remover -= 1
        
        return aulas_corrigidas
    
    def _analisar_estado(self, aulas):
        """Analisa o estado atual da grade"""
        analise = {
            'completude': 0,
            'total_necessario': 0,
            'total_alocado': len(aulas),
            'faltas_por_turma': {},
            'horarios_livres_por_turma': {},
            'professores_carga': {},
            'professores_limite': {}
        }
        
        # Calcular total necessário
        for turma in self.turmas:
            turma_nome = turma.nome
            grupo_turma = turma.grupo
            
            aulas_necessarias = 0
            for disc in self.disciplinas:
                if turma_nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                    aulas_necessarias += disc.carga_semanal
            
            analise['total_necessario'] += aulas_necessarias
            
            # Contar aulas alocadas
            aulas_turma = [a for a in aulas if a['turma'] == turma_nome]
            
            # Calcular horários livres
            horarios_turma = obter_horarios_turma(turma_nome)
            horarios_ocupados = set()
            for aula in aulas_turma:
                horarios_ocupados.add((aula['dia'], aula['horario']))
            
            horarios_livres = []
            for dia in self.dias:
                for horario in horarios_turma:
                    if (dia, horario) not in horarios_ocupados:
                        horarios_livres.append((dia, horario))
            
            analise['horarios_livres_por_turma'][turma_nome] = horarios_livres
            
            # Calcular faltas
            faltas = []
            for disc in self.disciplinas:
                if turma_nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                    aulas_disc = len([a for a in aulas_turma if a['disciplina'] == disc.nome])
                    if aulas_disc < disc.carga_semanal:
                        faltas.append({
                            'disciplina': disc.nome,
                            'faltam': disc.carga_semanal - aulas_disc,
                            'prioridade': self._calcular_prioridade(disc.nome, grupo_turma)
                        })
            
            analise['faltas_por_turma'][turma_nome] = faltas
        
        # Calcular completude
        if analise['total_necessario'] > 0:
            analise['completude'] = (analise['total_alocado'] / analise['total_necessario']) * 100
        
        # Calcular carga e limite dos professores
        for professor in self.professores:
            aulas_prof = len([a for a in aulas if a['professor'] == professor.nome])
            analise['professores_carga'][professor.nome] = aulas_prof
            analise['professores_limite'][professor.nome] = obter_limite_horas_professor(professor)
        
        return analise
    
    def _calcular_prioridade(self, disciplina, grupo):
        """Calcula prioridade para alocação"""
        # Contar professores disponíveis
        professores_disponiveis = 0
        professores_livres = 0
        
        for prof in self.professores:
            if disciplina in prof.disciplinas:
                if prof.grupo in [grupo, "AMBOS"]:
                    professores_disponiveis += 1
                    # Verificar se não está comprometido
                    if not verificar_professor_comprometido(prof, disciplina, grupo):
                        professores_livres += 1
        
        # Quanto menos professores livres, maior a prioridade
        return (10 - professores_livres) * 2 + (5 - professores_disponiveis)
    
    def _estrategia_preencher_buracos(self, aulas, analise):
        """Preenche buracos óbvios na grade"""
        nova_grade = aulas.copy()
        
        # Ordenar turmas por número de faltas
        turmas_ordenadas = []
        for turma_nome, faltas in analise['faltas_por_turma'].items():
            if faltas:
                turmas_ordenadas.append((turma_nome, len(faltas)))
        
        turmas_ordenadas.sort(key=lambda x: x[1], reverse=True)
        
        for turma_nome, _ in turmas_ordenadas:
            faltas = analise['faltas_por_turma'][turma_nome]
            horarios_livres = analise['horarios_livres_por_turma'].get(turma_nome, [])
            
            # Ordenar faltas por prioridade
            faltas_ordenadas = sorted(faltas, key=lambda x: x['prioridade'])
            
            for falta in faltas_ordenadas:
                disciplina = falta['disciplina']
                
                # Encontrar professores LIVRES (não comprometidos)
                professores_candidatos = []
                turma_obj = next((t for t in self.turmas if t.nome == turma_nome), None)
                grupo_turma = turma_obj.grupo if turma_obj else 'A'
                
                for prof in self.professores:
                    if disciplina in prof.disciplinas:
                        if prof.grupo in [grupo_turma, "AMBOS"]:
                            # Verificar se não está comprometido
                            if not verificar_professor_comprometido(prof, disciplina, grupo_turma):
                                # Verificar limite do professor
                                carga_atual = analise['professores_carga'].get(prof.nome, 0)
                                limite = analise['professores_limite'].get(prof.nome, 35)
                                
                                if carga_atual < limite:
                                    professores_candidatos.append(prof)
                
                # Ordenar professores por carga (menos carregado primeiro)
                professores_candidatos.sort(key=lambda p: analise['professores_carga'].get(p.nome, 0))
                
                # Tentar cada horário livre
                for dia, horario in horarios_livres:
                    # Verificar se já alocou todas as faltas desta disciplina
                    if falta['faltam'] <= 0:
                        break
                    
                    # Tentar cada professor
                    for professor in professores_candidatos:
                        # Verificar disponibilidade do professor
                        if self._professor_disponivel(nova_grade, professor.nome, dia, horario):
                            # Verificar se não está bloqueado
                            if f"{dia}_{horario}" in professor.horarios_indisponiveis:
                                continue
                            
                            # Verificar limite do professor
                            carga_atual = analise['professores_carga'].get(professor.nome, 0)
                            limite = analise['professores_limite'].get(professor.nome, 35)
                            
                            if carga_atual >= limite:
                                continue  # Professor já atingiu limite
                            
                            # Alocar aula
                            nova_grade.append({
                                'turma': turma_nome,
                                'disciplina': disciplina,
                                'professor': professor.nome,
                                'dia': dia,
                                'horario': horario,
                                'segmento': obter_segmento_turma(turma_nome)
                            })
                            
                            # Atualizar contadores
                            falta['faltam'] -= 1
                            horarios_livres.remove((dia, horario))
                            analise['professores_carga'][professor.nome] = analise['professores_carga'].get(professor.nome, 0) + 1
                            break
                    
                    if falta['faltam'] <= 0:
                        break
        
        return nova_grade
    
    def _estrategia_rebalancear_professores(self, aulas, analise):
        """Rebalanceia carga entre professores"""
        nova_grade = aulas.copy()
        
        # Encontrar professores sobrecarregados
        professores_sobrecarregados = []
        for nome, carga in analise['professores_carga'].items():
            professor_obj = next((p for p in self.professores if p.nome == nome), None)
            if professor_obj:
                limite = analise['professores_limite'].get(nome, 35)
                
                if carga > limite * 0.9:  # Mais de 90% do limite
                    professores_sobrecarregados.append((nome, carga, limite))
        
        # Ordenar por sobrecarga
        professores_sobrecarregados.sort(key=lambda x: x[1] / x[2] if x[2] > 0 else 0, reverse=True)
        
        for prof_nome, carga, limite in professores_sobrecarregados[:3]:  # Apenas os 3 mais sobrecarregados
            # Encontrar aulas deste professor
            aulas_prof = [a for a in nova_grade if a['professor'] == prof_nome]
            
            for aula in aulas_prof:
                disciplina = aula['disciplina']
                turma_nome = aula['turma']
                
                # Encontrar professores alternativos LIVRES
                professores_alternativos = []
                turma_obj = next((t for t in self.turmas if t.nome == turma_nome), None)
                grupo_turma = turma_obj.grupo if turma_obj else 'A'
                
                for prof in self.professores:
                    if prof.nome != prof_nome and disciplina in prof.disciplinas:
                        if prof.grupo in [grupo_turma, "AMBOS"]:
                            # Verificar se não está comprometido
                            if not verificar_professor_comprometido(prof, disciplina, grupo_turma):
                                # Verificar disponibilidade no mesmo horário
                                if self._professor_disponivel(nova_grade, prof.nome, aula['dia'], aula['horario']):
                                    if f"{aula['dia']}_{aula['horario']}" not in prof.horarios_indisponiveis:
                                        # Verificar limite do professor
                                        carga_alternativo = analise['professores_carga'].get(prof.nome, 0)
                                        limite_alternativo = analise['professores_limite'].get(prof.nome, 35)
                                        
                                        if carga_alternativo < limite_alternativo:
                                            professores_alternativos.append(prof)
                
                # Se encontrou alternativo, transferir
                if professores_alternativos:
                    # Escolher o menos carregado
                    professores_alternativos.sort(key=lambda p: analise['professores_carga'].get(p.nome, 0))
                    novo_professor = professores_alternativos[0]
                    
                    # Atualizar aula
                    for i, a in enumerate(nova_grade):
                        if (a['turma'] == turma_nome and a['disciplina'] == disciplina and 
                            a['dia'] == aula['dia'] and a['horario'] == aula['horario']):
                            nova_grade[i]['professor'] = novo_professor.nome
                            break
                    
                    # Atualizar cargas
                    analise['professores_carga'][prof_nome] -= 1
                    analise['professores_carga'][novo_professor.nome] = analise['professores_carga'].get(novo_professor.nome, 0) + 1
                    break
        
        return nova_grade
    
    def _estrategia_permutar_horarios(self, aulas, analise):
        """Permuta horários para criar espaços"""
        nova_grade = aulas.copy()
        
        # Para cada turma com faltas
        for turma_nome, faltas in analise['faltas_por_turma'].items():
            if not faltas:
                continue
            
            # Encontrar aulas desta turma
            aulas_turma = [a for a in nova_grade if a['turma'] == turma_nome]
            
            # Tentar permutar com outras turmas
            for aula in aulas_turma:
                # Encontrar outra aula em horário diferente
                for outra_aula in nova_grade:
                    if outra_aula['turma'] != turma_nome:
                        # Tentar trocar horários
                        if self._permutacao_valida(nova_grade, aula, outra_aula):
                            # Realizar troca
                            dia_temp = aula['dia']
                            horario_temp = aula['horario']
                            
                            aula['dia'] = outra_aula['dia']
                            aula['horario'] = outra_aula['horario']
                            
                            outra_aula['dia'] = dia_temp
                            outra_aula['horario'] = horario_temp
        
        return nova_grade
    
    def _estrategia_busca_local(self, aulas, analise):
        """Busca local por melhorias"""
        melhor_grade = aulas.copy()
        melhor_completude = analise['completude']
        
        for _ in range(50):  # 50 iterações
            grade_tentativa = melhor_grade.copy()
            
            # Aplicar operação aleatória
            operacao = random.choice(['mover', 'trocar', 'realocar'])
            
            if operacao == 'mover' and len(grade_tentativa) > 0:
                # Mover uma aula para horário livre
                aula_idx = random.randrange(len(grade_tentativa))
                aula = grade_tentativa[aula_idx]
                
                turma_nome = aula['turma']
                horarios_livres = analise['horarios_livres_por_turma'].get(turma_nome, [])
                
                if horarios_livres:
                    novo_dia, novo_horario = random.choice(horarios_livres)
                    
                    # Verificar se professor está disponível
                    if self._professor_disponivel(grade_tentativa, aula['professor'], novo_dia, novo_horario):
                        grade_tentativa[aula_idx]['dia'] = novo_dia
                        grade_tentativa[aula_idx]['horario'] = novo_horario
            
            elif operacao == 'trocar' and len(grade_tentativa) >= 2:
                # Trocar duas aulas de lugar
                idx1, idx2 = random.sample(range(len(grade_tentativa)), 2)
                aula1 = grade_tentativa[idx1]
                aula2 = grade_tentativa[idx2]
                
                # Verificar se troca é válida
                if (self._professor_disponivel(grade_tentativa, aula1['professor'], aula2['dia'], aula2['horario']) and
                    self._professor_disponivel(grade_tentativa, aula2['professor'], aula1['dia'], aula1['horario'])):
                    
                    # Trocar horários
                    dia_temp = aula1['dia']
                    horario_temp = aula1['horario']
                    
                    grade_tentativa[idx1]['dia'] = aula2['dia']
                    grade_tentativa[idx1]['horario'] = aula2['horario']
                    
                    grade_tentativa[idx2]['dia'] = dia_temp
                    grade_tentativa[idx2]['horario'] = horario_temp
            
            # Avaliar nova grade
            nova_analise = self._analisar_estado(grade_tentativa)
            
            if nova_analise['completude'] > melhor_completude:
                melhor_grade = grade_tentativa
                melhor_completude = nova_analise['completude']
        
        return melhor_grade
    
    def _professor_disponivel(self, grade, professor_nome, dia, horario):
        """Verifica se professor está disponível em determinado horário"""
        for aula in grade:
            if aula['professor'] == professor_nome:
                if aula['dia'] == dia and aula['horario'] == horario:
                    return False
        return True
    
    def _permutacao_valida(self, grade, aula1, aula2):
        """Verifica se permutação entre duas aulas é válida"""
        # Verificar disponibilidade dos professores nos novos horários
        prof1_livre = self._professor_disponivel(grade, aula1['professor'], aula2['dia'], aula2['horario'])
        prof2_livre = self._professor_disponivel(grade, aula2['professor'], aula1['dia'], aula1['horario'])
        
        # Verificar se turmas estão livres nos novos horários
        turma1_livre = True
        turma2_livre = True
        
        for aula in grade:
            if aula['turma'] == aula1['turma']:
                if aula['dia'] == aula2['dia'] and aula['horario'] == aula2['horario']:
                    turma1_livre = False
            
            if aula['turma'] == aula2['turma']:
                if aula['dia'] == aula1['dia'] and aula['horario'] == aula1['horario']:
                    turma2_livre = False
        
        return prof1_livre and prof2_livre and turma1_livre and turma2_livre
    
    def _gerar_grade_do_zero(self):
        """Gera uma grade completa do zero"""
        from simple_scheduler import SimpleGradeHoraria
        
        simple_grade = SimpleGradeHoraria(
            turmas=self.turmas,
            professores=self.professores,
            disciplinas=self.disciplinas,
            salas=[]
        )
        
        return simple_grade.gerar_grade()

# ============================================
# FUNÇÕES ADICIONAIS
# ============================================

def salvar_grade_como(nome, aulas, config):
    """Salva uma grade com um nome específico"""
    if not hasattr(st.session_state, 'grades_salvas'):
        st.session_state.grades_salvas = {}
    
    # Converter para dicionários
    aulas_dict = []
    for aula in aulas:
        if isinstance(aula, Aula):
            aulas_dict.append({
                'turma': aula.turma,
                'disciplina': aula.disciplina,
                'professor': aula.professor,
                'dia': aula.dia,
                'horario': aula.horario,
                'segmento': aula.segmento if hasattr(aula, 'segmento') else obter_segmento_turma(aula.turma)
            })
        elif isinstance(aula, dict):
            aulas_dict.append(aula)
        else:
            aulas_dict.append({
                'turma': obter_turma_aula(aula),
                'disciplina': obter_disciplina_aula(aula),
                'professor': obter_professor_aula(aula),
                'dia': obter_dia_aula(aula),
                'horario': obter_horario_aula(aula),
                'segmento': obter_segmento_aula(aula)
            })
    
    st.session_state.grades_salvas[nome] = {
        'aulas': aulas_dict,
        'config': config,
        'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_aulas': len(aulas_dict)
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
    
    st.subheader("📊 Estatísticas por Segmento")
    
    turmas_efii = [t for t in st.session_state.turmas if obter_segmento_turma(t.nome) == "EF_II"]
    turmas_em = [t for t in st.session_state.turmas if obter_segmento_turma(t.nome) == "EM"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Ensino Fundamental II**")
        st.write(f"Turmas: {len(turmas_efii)}")
        st.write(f"Horário: 07:50 - 12:20")
        st.write(f"Aulas: 5 por dia + intervalo")
        st.write(f"Limite professor: {LIMITE_HORAS_EFII}h semanais")
        
    with col2:
        st.write("**Ensino Médio**")
        st.write(f"Turmas: {len(turmas_em)}")
        st.write(f"Horário: 07:00 - 13:10")
        st.write(f"Aulas: 7 por dia + intervalo")
        st.write(f"Limite professor: {LIMITE_HORAS_EM}h semanais")
    
    st.subheader("📈 Verificação de Carga de Aulas")
    
    for turma in st.session_state.turmas:
        carga_total = 0
        disciplinas_turma = []
        grupo_turma = obter_grupo_seguro(turma)
        segmento = obter_segmento_turma(turma.nome)
        
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
# ABA DISCIPLINAS - COM VISUALIZAÇÃO DE PROFESSORES
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
            
            # Mostrar professores disponíveis para esta disciplina
            if nome and turmas_selecionadas:
                st.subheader("👨‍🏫 Professores Disponíveis")
                
                # Determinar grupo para filtragem
                grupo_filtro_prof = grupo
                
                professores_disponiveis = []
                for prof in st.session_state.professores:
                    # Verificar se professor ministra alguma disciplina
                    # (não podemos verificar ainda se ministra esta disciplina específica)
                    prof_grupo = obter_grupo_seguro(prof)
                    if prof_grupo in [grupo_filtro_prof, "AMBOS"]:
                        professores_disponiveis.append(prof)
                
                if professores_disponiveis:
                    st.write(f"**{len(professores_disponiveis)} professores disponíveis no grupo {grupo}:**")
                    for prof in professores_disponiveis[:5]:  # Mostrar apenas 5
                        st.write(f"- {prof.nome} ({obter_segmento_professor(prof)})")
                    if len(professores_disponiveis) > 5:
                        st.write(f"... e mais {len(professores_disponiveis) - 5}")
                else:
                    st.warning(f"⚠️ Nenhum professor disponível no grupo {grupo}")
            
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
        with st.expander(f"📖 {disc.nome} [{obter_grupo_seguro(disc)}] - Carga: {disc.carga_semanal}h", expanded=False):
            
            # SEÇÃO 1: INFORMAÇÕES DA DISCIPLINA
            st.write("### 📋 Informações da Disciplina")
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
            
            # SEÇÃO 2: PROFESSORES DISPONÍVEIS
            st.write("### 👨‍🏫 Professores Disponíveis")
            
            grupo_disc = obter_grupo_seguro(disc)
            
            # Obter professores que podem ministrar esta disciplina
            professores_disponiveis = obter_professores_para_disciplina(disc.nome, grupo_disc)
            
            if professores_disponiveis:
                # Dividir em professores livres e comprometidos
                professores_livres = []
                professores_comprometidos = []
                
                for prof in professores_disponiveis:
                    if verificar_professor_comprometido(prof, disc.nome, grupo_disc):
                        professores_comprometidos.append(prof)
                    else:
                        professores_livres.append(prof)
                
                # Mostrar estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", len(professores_disponiveis))
                with col2:
                    st.metric("Livres", len(professores_livres))
                with col3:
                    st.metric("Comprometidos", len(professores_comprometidos))
                
                # Mostrar professores livres
                if professores_livres:
                    st.write("#### ✅ Professores Livres (Podem ministrar):")
                    for prof in professores_livres:
                        segmento = obter_segmento_professor(prof)
                        limite = obter_limite_horas_professor(prof)
                        disponibilidade = calcular_disponibilidade_professor(prof)
                        
                        # Calcular carga atual (se houver aulas na grade)
                        carga_atual = 0
                        if hasattr(st.session_state, 'aulas') and st.session_state.aulas:
                            carga_atual = calcular_horas_professor(prof, st.session_state.aulas)
                        
                        status = "✅" if carga_atual < limite else "⚠️" if carga_atual == limite else "❌"
                        
                        st.write(f"- **{prof.nome}** ({segmento}): {carga_atual}/{limite}h {status}")
                        st.caption(f"  Disponibilidade: {disponibilidade} períodos/semana | Grupo: {obter_grupo_seguro(prof)}")
                
                # Mostrar professores comprometidos
                if professores_comprometidos:
                    st.write("#### ⚠️ Professores Comprometidos:")
                    for prof in professores_comprometidos:
                        # Descobrir com quais outras disciplinas está comprometido
                        outras_disciplinas = []
                        for outra_disc_nome in prof.disciplinas:
                            if outra_disc_nome != disc.nome:
                                # Verificar se é do mesmo grupo
                                for d in st.session_state.disciplinas:
                                    if d.nome == outra_disc_nome:
                                        if obter_grupo_seguro(d) == grupo_disc:
                                            outras_disciplinas.append(outra_disc_nome)
                                            break
                        
                        st.write(f"- **{prof.nome}**: Comprometido com {', '.join(outras_disciplinas[:2])}{'...' if len(outras_disciplinas) > 2 else ''}")
            else:
                st.warning(f"⚠️ Nenhum professor pode ministrar **{disc.nome}** no grupo **{grupo_disc}**")
                st.write("**Sugestões:**")
                st.write("1. Adicione professores que ministrem esta disciplina")
                st.write("2. Mude professores existentes para o grupo correto")
                st.write("3. Adicione a disciplina à lista de disciplinas dos professores")
            
            # SEÇÃO 3: TURMAS QUE CURSAM ESTA DISCIPLINA
            st.write("### 🎒 Turmas que Cursam esta Disciplina")
            
            if disc.turmas:
                for turma_nome in disc.turmas:
                    # Encontrar turma
                    turma_obj = next((t for t in st.session_state.turmas if t.nome == turma_nome), None)
                    if turma_obj:
                        segmento = obter_segmento_turma(turma_nome)
                        grupo_turma = obter_grupo_seguro(turma_obj)
                        
                        # Verificar compatibilidade de grupos
                        grupo_compativel = (grupo_disc == grupo_turma)
                        
                        st.write(f"- **{turma_nome}** ({segmento}, Grupo {grupo_turma}) {'✅' if grupo_compativel else '❌'}")
                        
                        if not grupo_compativel:
                            st.caption(f"  ⚠️ A disciplina é do grupo {grupo_disc}, mas a turma é do grupo {grupo_turma}")
            else:
                st.info("📝 Nenhuma turma atribuída a esta disciplina")

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
            
            # Mostrar limites de horas baseado nas disciplinas
            if disciplinas:
                # Determinar segmento do professor
                segmento = "AMBOS"
                tem_efii = False
                tem_em = False
                
                for disc_nome in disciplinas:
                    # Verificar turmas desta disciplina
                    for disc in st.session_state.disciplinas:
                        if disc.nome == disc_nome:
                            for turma_nome in disc.turmas:
                                if obter_segmento_turma(turma_nome) == "EF_II":
                                    tem_efii = True
                                elif obter_segmento_turma(turma_nome) == "EM":
                                    tem_em = True
                
                if tem_efii and not tem_em:
                    segmento = "EF_II"
                    limite = LIMITE_HORAS_EFII
                elif tem_em and not tem_efii:
                    segmento = "EM"
                    limite = LIMITE_HORAS_EM
                else:
                    segmento = "AMBOS"
                    limite = LIMITE_HORAS_EM  # Usar limite maior
                
                st.info(f"💡 Este professor será do segmento **{segmento}** com limite de **{limite}h** semanais")
            
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
            
            # Calcular informações do professor
            segmento = obter_segmento_professor(prof)
            limite = obter_limite_horas_professor(prof)
            disponibilidade_horas = calcular_disponibilidade_professor(prof)
            
            # Calcular carga atual (se houver aulas na grade)
            carga_atual = 0
            if hasattr(st.session_state, 'aulas') and st.session_state.aulas:
                carga_atual = calcular_horas_professor(prof, st.session_state.aulas)
            
            # Mostrar informações
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Segmento", segmento)
            with col2:
                st.metric("Carga Atual", f"{carga_atual}/{limite}h")
            with col3:
                st.metric("Disponibilidade", f"{disponibilidade_horas} períodos")
            
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
                
                # Mostrar novo segmento se disciplinas mudarem
                if novas_disciplinas != disciplinas_validas:
                    # Recalcular segmento
                    novo_segmento = "AMBOS"
                    tem_efii = False
                    tem_em = False
                    
                    for disc_nome in novas_disciplinas:
                        for disc in st.session_state.disciplinas:
                            if disc.nome == disc_nome:
                                for turma_nome in disc.turmas:
                                    if obter_segmento_turma(turma_nome) == "EF_II":
                                        tem_efii = True
                                    elif obter_segmento_turma(turma_nome) == "EM":
                                        tem_em = True
                    
                    if tem_efii and not tem_em:
                        novo_segmento = "EF_II"
                        novo_limite = LIMITE_HORAS_EFII
                    elif tem_em and not tem_efii:
                        novo_segmento = "EM"
                        novo_limite = LIMITE_HORAS_EM
                    else:
                        novo_segmento = "AMBOS"
                        novo_limite = LIMITE_HORAS_EM
                    
                    st.info(f"💡 Novo segmento: **{novo_segmento}** com limite de **{novo_limite}h**")
                
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
# ABA TURMAS (manter igual)
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
# ABA SALAS (manter igual)
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
# ABA GERAR GRADE (COM TODAS AS CORREÇÕES)
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
            ["Algoritmo Simples (Rápido)"]
        )
        
        tipo_completador = st.selectbox(
            "Algoritmo de Completude",
            ["Completador Básico", "Completador Avançado (Recomendado)"],
            help="O completador avançado usa múltiplas estratégias para tentar completar grades incompletas"
        )
        
        st.info("📅 **EM: 07:00-13:10 (7 períodos)**")
        st.info("📅 **EF II: 07:50-12:20 (5 períodos)**")
        st.info("📊 **Limites:** EF II: 25h | EM: 35h")
    
    st.subheader("📊 Pré-análise de Viabilidade")
    
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
    
    # Calcular capacidade dos professores
    if tipo_grade == "Grade por Grupo A":
        professores_filtrados = [p for p in st.session_state.professores 
                               if obter_grupo_seguro(p) in ["A", "AMBOS"]]
    elif tipo_grade == "Grade por Grupo B":
        professores_filtrados = [p for p in st.session_state.professores 
                               if obter_grupo_seguro(p) in ["B", "AMBOS"]]
    else:
        professores_filtrados = st.session_state.professores
    
    capacidade_professores = 0
    for prof in professores_filtrados:
        limite = obter_limite_horas_professor(prof)
        capacidade_professores += limite
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Turmas", len(turmas_filtradas))
    with col2:
        st.metric("Aulas Necessárias", total_aulas)
    with col3:
        st.metric("Capacidade Horários", capacidade_total)
    with col4:
        st.metric("Capacidade Professores", capacidade_professores)
    
    if problemas_carga:
        st.warning("⚠️ Observações sobre carga horária:")
        for problema in problemas_carga:
            st.write(f"- {problema}")
    
    if total_aulas == 0:
        st.error("❌ Nenhuma aula para alocar! Verifique as disciplinas.")
    elif total_aulas > capacidade_total:
        st.error("❌ Capacidade de horários insuficiente! Reduza a carga horária.")
    elif total_aulas > capacidade_professores:
        st.error("❌ Capacidade dos professores insuficiente! Adicione mais professores ou aumente limites.")
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
                        # Gerar grade
                        if not ALGORITMOS_DISPONIVEIS:
                            st.error("❌ Algoritmo de geração não disponível!")
                            st.stop()
                        
                        simple_grade = SimpleGradeHoraria(
                            turmas=turmas_filtradas,
                            professores=professores_filtrados,
                            disciplinas=disciplinas_filtradas,
                            salas=st.session_state.salas
                        )
                        aulas = simple_grade.gerar_grade()
                        metodo = "Algoritmo Simples"
                        
                        # ============================================
                        # ETAPA 1: REMOVER AULAS REPETIDAS
                        # ============================================
                        aulas_antes_repetidas = len(aulas)
                        aulas = remover_aulas_repetidas(aulas)
                        aulas_depois_repetidas = len(aulas)
                        
                        if aulas_antes_repetidas > aulas_depois_repetidas:
                            st.info(f"ℹ️ Removidas {aulas_antes_repetidas - aulas_depois_repetidas} aulas repetidas automaticamente")
                        
                        # Filtrar por turma específica se necessário
                        if tipo_grade == "Grade por Turma Específica" and turma_selecionada:
                            aulas = [a for a in aulas if obter_turma_aula(a) == turma_selecionada]
                        
                        # ============================================
                        # ETAPA 2: VERIFICAR SUPERPOSIÇÕES DE PROFESSOR (CRÍTICO!)
                        # ============================================
                        superposicoes = verificar_professor_superposto(aulas)
                        
                        if superposicoes:
                            st.error(f"❌ **PROBLEMA CRÍTICO**: {len(superposicoes)} superposições de professor detectadas!")
                            st.error("⚠️ **Um professor NÃO PODE dar aula em dois lugares ao mesmo tempo!**")
                            
                            # Mostrar exemplos
                            with st.expander("📋 Ver Superposições Críticas", expanded=True):
                                for i, sup in enumerate(superposicoes[:5]):
                                    st.write(f"**Professor {sup['professor']}**: {len(sup['aulas'])} aulas no mesmo horário ({sup['dia']}, {sup['horario']}º)")
                                    for j, aula in enumerate(sup['aulas']):
                                        st.write(f"  {j+1}. Turma: {obter_turma_aula(aula)}, Disciplina: {obter_disciplina_aula(aula)}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔧 CORRIGIR SUPERPOSIÇÕES AGORA", type="primary", use_container_width=True):
                                    with st.spinner("Corrigindo superposições críticas..."):
                                        aulas_corrigidas = corrigir_superposicoes_professor(aulas, superposicoes)
                                        
                                        # Verificar se corrigiu
                                        novas_superposicoes = verificar_professor_superposto(aulas_corrigidas)
                                        if not novas_superposicoes:
                                            st.success("✅ Todas as superposições foram corrigidas!")
                                            aulas = aulas_corrigidas
                                        else:
                                            st.warning(f"⚠️ Ainda restam {len(novas_superposicoes)} superposições")
                                    
                                    st.rerun()
                            
                            with col2:
                                if st.button("⏭️ Ignorar e Continuar", type="secondary", use_container_width=True):
                                    st.warning("⚠️ Continuando com superposições. A grade pode ter problemas graves!")
                        
                        # ============================================
                        # ETAPA 3: VERIFICAÇÃO DE CONFLITOS E LIMITES
                        # ============================================
                        conflitos = verificar_conflitos_horarios(aulas)
                        limites_excedidos = verificar_limites_professores(aulas)
                        
                        if conflitos or limites_excedidos:
                            st.warning(f"⚠️ **PROBLEMAS DETECTADOS:**")
                            
                            if conflitos:
                                st.write(f"- **Conflitos:** {len(conflitos)} horários sobrepostos na mesma turma")
                            
                            if limites_excedidos:
                                st.write(f"- **Limites excedidos:** {len(limites_excedidos)} professores")
                                for problema in limites_excedidos[:2]:
                                    st.write(f"  - {problema['professor']}: {problema['horas_atual']}h > {problema['limite']}h ({problema['segmento']})")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔧 Corrigir Todos os Problemas", type="primary", use_container_width=True):
                                    with st.spinner("Corrigindo problemas..."):
                                        # Corrigir conflitos
                                        if conflitos:
                                            aulas = corrigir_conflitos_automaticamente(aulas, conflitos)
                                        
                                        # Para limites excedidos, usar completador avançado
                                        if limites_excedidos:
                                            completador = CompletadorDeGradeAvancado(turmas_filtradas, professores_filtrados, disciplinas_filtradas)
                                            aulas = completador.completar_grade(aulas)
                                        
                                        novos_conflitos = verificar_conflitos_horarios(aulas)
                                        novos_limites = verificar_limites_professores(aulas)
                                        novas_superposicoes = verificar_professor_superposto(aulas)
                                        
                                        if not novos_conflitos and not novos_limites and not novas_superposicoes:
                                            st.success("✅ Todos os problemas foram corrigidos!")
                                        else:
                                            problemas_restantes = []
                                            if novos_conflitos:
                                                problemas_restantes.append(f"{len(novos_conflitos)} conflitos")
                                            if novos_limites:
                                                problemas_restantes.append(f"{len(novos_limites)} limites")
                                            if novas_superposicoes:
                                                problemas_restantes.append(f"{len(novas_superposicoes)} superposições")
                                            
                                            st.warning(f"⚠️ Ainda restam: {', '.join(problemas_restantes)}")
                        
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
                                status_color = "green" if "COMPLETA" in diagnostico['status'] else "red" if "CRÍTICO" in diagnostico['status'] else "orange"
                                st.metric("Status", diagnostico['status'])
                            with col2:
                                st.metric("Completude", f"{diagnostico['completude']}%")
                            with col3:
                                st.metric("Aulas", f"{diagnostico['estatisticas']['total_alocado']}/{diagnostico['estatisticas']['total_necessario']}")
                            
                            # Mostrar alertas críticos primeiro
                            if "CRÍTICO" in diagnostico['status']:
                                st.error("🚨 **ALERTA CRÍTICO**: Existem professores com aulas sobrepostas!")
                                st.error("👉 Corrija imediatamente usando os botões acima")
                            
                            # Botão para tentar completar automaticamente
                            if diagnostico['completude'] < 100:
                                st.warning(f"⚠️ **Grade incompleta!** Faltam {diagnostico['estatisticas']['faltam']} aulas.")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("🔧 TENTAR COMPLETAR GRADE", type="primary", use_container_width=True):
                                        with st.spinner("Tentando completar a grade..."):
                                            if tipo_completador == "Completador Avançado (Recomendado)":
                                                completador = CompletadorDeGradeAvancado(turmas_filtradas, professores_filtrados, disciplinas_filtradas)
                                            else:
                                                # Completador básico (versão simplificada)
                                                class CompletadorDeGradeBasico:
                                                    def __init__(self, turmas, professores, disciplinas):
                                                        self.turmas = turmas
                                                        self.professores = professores
                                                        self.disciplinas = disciplinas
                                                        self.dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
                                                    
                                                    def completar_grade(self, aulas):
                                                        return aulas  # Básico: não faz nada
                                                
                                                completador = CompletadorDeGradeBasico(turmas_filtradas, professores_filtrados, disciplinas_filtradas)
                                            
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
                                    # Botão para salvar grade atual
                                    nome_grade = st.text_input("Nome para salvar esta grade:", value=f"Grade_{grupo_texto}_{datetime.now().strftime('%H%M')}")
                                    if st.button("💾 SALVAR GRADE", type="secondary", use_container_width=True):
                                        if salvar_grade_como(nome_grade, aulas, {'tipo': tipo_grade, 'algoritmo': metodo}):
                                            st.success(f"✅ Grade '{nome_grade}' salva!")
                            
                            # Mostrar problemas e sugestões
                            if diagnostico['problemas']:
                                with st.expander("📋 PROBLEMAS DETECTADOS", expanded=True):
                                    for problema in diagnostico['problemas'][:5]:
                                        st.markdown(problema)
                            
                            if diagnostico['sugestoes']:
                                with st.expander("💡 SUGESTÕES PARA CORRIGIR", expanded=True):
                                    for sugestao in diagnostico['sugestoes'][:5]:
                                        st.markdown(sugestao)
                            
                            # Detalhes por turma
                            with st.expander("📊 DETALHES POR TURMA"):
                                for turma_nome, info in diagnostico['detalhes_por_turma'].items():
                                    status = "✅" if info['completude'] == 100 else "⚠️" if info['completude'] >= 80 else "❌"
                                    st.write(f"{status} **{turma_nome}** ({info['segmento']}): {info['alocadas']}/{info['necessarias']} aulas ({info['completude']:.1f}%)")
                                    
                                    if info['faltas_disciplinas']:
                                        st.caption(f"Faltam: {', '.join(info['faltas_disciplinas'])}")
                            
                            # Professores saturados, limites e superposições
                            if (diagnostico['professores_saturados'] or 
                                diagnostico['professores_limite_excedido'] or 
                                diagnostico['aulas_repetidas'] or
                                diagnostico['professores_superpostos']):
                                
                                with st.expander("👨‍🏫 ANÁLISE DE PROFESSORES"):
                                    # Superposições (CRÍTICO)
                                    if diagnostico['professores_superpostos']:
                                        st.write("#### 🚨 **SUPERPOSIÇÕES CRÍTICAS**")
                                        for sup in diagnostico['professores_superpostos'][:3]:
                                            st.write(f"❌ **{sup['professor']}**: {len(sup['aulas'])} aulas às {sup['dia']}, {sup['horario']}º")
                                            for aula in sup['aulas'][:2]:
                                                st.write(f"  - Turma: {obter_turma_aula(aula)}, Disciplina: {obter_disciplina_aula(aula)}")
                                    
                                    # Limites excedidos
                                    if diagnostico['professores_limite_excedido']:
                                        st.write("#### ❌ **LIMITES EXCEDIDOS**")
                                        for prof in diagnostico['professores_limite_excedido'][:3]:
                                            st.write(f"❌ **{prof['professor']}**: {prof['horas_atual']}/{prof['limite']}h LIMITE EXCEDIDO!")
                                    
                                    # Professores saturados
                                    if diagnostico['professores_saturados']:
                                        st.write("#### ⚠️ **PROFESSORES SATURADOS**")
                                        for prof in diagnostico['professores_saturados'][:3]:
                                            st.write(f"⚠️ **{prof['nome']}**: {prof['aulas']}/{prof['capacidade']} aulas (limite: {prof['limite_segmento']}h para {prof['segmento']})")
                                    
                                    # Aulas repetidas
                                    if diagnostico['aulas_repetidas']:
                                        st.write("#### 🔄 **AULAS REPETIDAS**")
                                        for repetida in diagnostico['aulas_repetidas'][:3]:
                                            st.write(f"❌ **{repetida['disciplina']}** na turma **{repetida['turma']}**: {repetida['quantidade']} aulas (necessário: {repetida['necessario']})")
                        
                        # ============================================
                        # VISUALIZAÇÃO DA GRADE HORÁRIA
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
                                
                                # CSS para estilizar a tabela
                                st.markdown("""
                                <style>
                                .grade-table {
                                    width: 100%;
                                    border-collapse: collapse;
                                    margin: 10px 0;
                                    font-size: 14px;
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
                                    border-radius: 4px;
                                    padding: 10px;
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
                                    margin-bottom: 2px;
                                }
                                .professor {
                                    font-size: 12px;
                                    color: #666;
                                    font-style: italic;
                                }
                                .horario-cell {
                                    background-color: #f0f7ff;
                                    font-weight: bold;
                                }
                                </style>
                                """, unsafe_allow_html=True)
                                
                                # Construir tabela HTML
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
                                    table_html += f"<tr><td class='horario-cell'><strong>{horario_real}</strong></td>"
                                    
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
                                            
                                            # Encontrar cor da disciplina
                                            cor_fundo = "#e8f5e9"  # Default
                                            cor_fonte = "#2e7d32"  # Default
                                            for disc in st.session_state.disciplinas:
                                                if disc.nome == disciplina:
                                                    if hasattr(disc, 'cor_fundo') and disc.cor_fundo:
                                                        cor_fundo = disc.cor_fundo
                                                    if hasattr(disc, 'cor_fonte') and disc.cor_fonte:
                                                        cor_fonte = disc.cor_fonte
                                                    break
                                            
                                            table_html += f"""<td class='aula-cell' style='background-color: {cor_fundo}; color: {cor_fonte};'>
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
                                    # Corrigir formatação antes de exportar
                                    df_export = corrigir_csv_export(df_aulas.copy())
                                    df_export.to_excel(writer, sheet_name="Grade_Completa", index=False)
                                
                                st.download_button(
                                    "📥 Baixar Grade em Excel",
                                    output.getvalue(),
                                    f"grade_{grupo_texto.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            except ImportError:
                                # Para CSV
                                df_export = corrigir_csv_export(df_aulas.copy())
                                csv = df_export.to_csv(index=False)
                                st.download_button(
                                    "📥 Baixar Grade em CSV",
                                    csv,
                                    f"grade_{grupo_texto.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                    "text/csv"
                                )
                        else:
                            st.warning("⚠️ Nenhuma aula foi gerada.")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar grade: {str(e)}")
                        st.code(traceback.format_exc())

# ============================================
# ABA GRADE POR PROFESSOR (manter igual)
# ============================================
with abas[6]:
    st.header("👨‍🏫 Grade Horária por Professor")
    
    if not st.session_state.get('aulas'):
        st.info("ℹ️ Gere uma grade horária primeiro na aba 'Gerar Grade'.")
    else:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
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
            # Filtrar aulas do professor
            aulas_professor = [a for a in st.session_state.aulas if obter_professor_aula(a) == professor_selecionado]
            
            if not aulas_professor:
                st.warning(f"ℹ️ Professor {professor_selecionado} não tem aulas alocadas.")
            else:
                # Calcular informações do professor
                segmento = obter_segmento_professor(
                    next((p for p in st.session_state.professores if p.nome == professor_selecionado), None)
                )
                limite = obter_limite_horas_professor(
                    next((p for p in st.session_state.professores if p.nome == professor_selecionado), None)
                )
                
                st.success(f"📊 Professor {professor_selecionado} ({segmento}): {len(aulas_professor)}/{limite}h")
                
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
# ABA DIAGNÓSTICO (MELHORADO COM TODAS AS VERIFICAÇÕES)
# ============================================
with abas[7]:
    st.header("🔧 DIAGNÓSTICO AVANÇADO DO SISTEMA")
    
    st.subheader("📊 Análise de Capacidade")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_necessario = 0
        for turma in st.session_state.turmas:
            grupo_turma = obter_grupo_seguro(turma)
            for disc in st.session_state.disciplinas:
                if turma.nome in disc.turmas and obter_grupo_seguro(disc) == grupo_turma:
                    total_necessario += disc.carga_semanal
        st.metric("Aulas Necessárias", total_necessario)
    
    with col2:
        capacidade_total = 0
        for turma in st.session_state.turmas:
            horarios = obter_horarios_turma(turma.nome)
            capacidade_total += len(horarios) * 5
        st.metric("Capacidade Horários", capacidade_total)
    
    with col3:
        capacidade_professores = 0
        for professor in st.session_state.professores:
            capacidade_professores += obter_limite_horas_professor(professor)
        st.metric("Capacidade Professores", capacidade_professores)
    
    with col4:
        if capacidade_total >= total_necessario and capacidade_professores >= total_necessario:
            st.success("✅ Capacidade OK")
        else:
            problemas = []
            if capacidade_total < total_necessario:
                problemas.append(f"Horários: -{total_necessario - capacidade_total}")
            if capacidade_professores < total_necessario:
                problemas.append(f"Professores: -{total_necessario - capacidade_professores}")
            st.error(f"❌ Déficit: {', '.join(problemas)}")
    
    # Análise de professores
    st.subheader("👨‍🏫 Análise de Professores")
    
    professores_problema = []
    for prof in st.session_state.professores:
        dias_disponiveis = len(prof.disponibilidade) if hasattr(prof, 'disponibilidade') else 0
        segmento = obter_segmento_professor(prof)
        limite = obter_limite_horas_professor(prof)
        
        if dias_disponiveis < 3:
            professores_problema.append(f"**{prof.nome}** ({segmento}): Apenas {dias_disponiveis} dia(s) | Limite: {limite}h")
    
    if professores_problema:
        st.warning("⚠️ Professores com pouca disponibilidade:")
        for problema in professores_problema[:3]:
            st.markdown(f"- {problema}")
        if len(professores_problema) > 3:
            st.caption(f"... e mais {len(professores_problema) - 3}")
    else:
        st.success("✅ Todos professores têm disponibilidade razoável")
    
    # Botões para correção de problemas
    st.subheader("🔄 Ferramentas de Correção")
    
    if st.session_state.get('aulas'):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔧 Remover Aulas Repetidas", use_container_width=True):
                with st.spinner("Removendo aulas repetidas..."):
                    aulas_original = len(st.session_state.aulas)
                    st.session_state.aulas = remover_aulas_repetidas(st.session_state.aulas)
                    aulas_final = len(st.session_state.aulas)
                    
                    if aulas_final < aulas_original:
                        st.success(f"✅ Removidas {aulas_original - aulas_final} aulas repetidas!")
                        st.success(f"✅ Total de aulas agora: {aulas_final}")
                        if salvar_tudo():
                            st.success("✅ Grade atualizada no banco de dados!")
                        st.rerun()
                    else:
                        st.info("ℹ️ Não foram encontradas aulas repetidas para remover.")
        
        with col2:
            if st.button("🚨 Corrigir Superposições", use_container_width=True):
                with st.spinner("Verificando superposições..."):
                    superposicoes = verificar_professor_superposto(st.session_state.aulas)
                    
                    if superposicoes:
                        st.error(f"❌ Encontradas {len(superposicoes)} superposições de professor!")
                        
                        # Mostrar exemplos
                        with st.expander("📋 Ver Superposições", expanded=True):
                            for i, sup in enumerate(superposicoes[:3]):
                                st.write(f"**Professor {sup['professor']}**: {len(sup['aulas'])} aulas às {sup['dia']}, {sup['horario']}º")
                                for aula in sup['aulas']:
                                    st.write(f"  - Turma: {obter_turma_aula(aula)}, Disciplina: {obter_disciplina_aula(aula)}")
                        
                        if st.button("✅ Corrigir Agora", type="primary"):
                            with st.spinner("Corrigindo superposições..."):
                                aulas_corrigidas = corrigir_superposicoes_professor(st.session_state.aulas, superposicoes)
                                st.session_state.aulas = aulas_corrigidas
                                st.success("✅ Superposições corrigidas!")
                                st.rerun()
                    else:
                        st.success("✅ Nenhuma superposição encontrada!")
        
        with col3:
            if st.button("📊 Verificar Conflitos", use_container_width=True):
                # Executar diagnóstico completo
                diagnostico = diagnosticar_grade(
                    st.session_state.turmas,
                    st.session_state.professores,
                    st.session_state.disciplinas,
                    st.session_state.aulas
                )
                
                # Mostrar resultados
                st.subheader("📋 Resultado da Verificação")
                
                st.metric("Status", diagnostico['status'])
                st.metric("Completude", f"{diagnostico['completude']}%")
                
                if diagnostico['problemas']:
                    st.error("❌ Problemas encontrados:")
                    for problema in diagnostico['problemas'][:5]:
                        st.write(f"- {problema}")
                else:
                    st.success("✅ Nenhum problema encontrado!")
    
    # Botão para otimização manual
    st.subheader("⚙️ Otimização Avançada")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Rebalancear Professores", use_container_width=True):
            st.info("""
            **Sugestões de rebalanceamento:**
            
            1. Verifique professores com muitas disciplinas
            2. Distribua disciplinas entre professores do mesmo grupo
            3. Considere professores 'AMBOS' para cobrir falta
            4. Respeite limites: EF II (25h) | EM (35h)
            5. **EVITE** que professores tenham aulas no mesmo horário
            """)
    
    with col2:
        if st.button("📅 Analisar Grade Completa", use_container_width=True):
            if st.session_state.get('aulas'):
                # Executar todas as verificações
                conflitos = verificar_conflitos_horarios(st.session_state.aulas)
                superposicoes = verificar_professor_superposto(st.session_state.aulas)
                limites_excedidos = verificar_limites_professores(st.session_state.aulas)
                
                st.subheader("📊 Resultado da Análise")
                
                problemas_totais = len(conflitos) + len(superposicoes) + len(limites_excedidos)
                
                if problemas_totais == 0:
                    st.success("✅ Grade perfeita! Nenhum problema encontrado.")
                else:
                    st.error(f"❌ Encontrados {problemas_totais} problemas:")
                    
                    if superposicoes:
                        st.write(f"🚨 **SUPERPOSIÇÕES CRÍTICAS**: {len(superposicoes)}")
                        for sup in superposicoes[:2]:
                            st.write(f"  - Professor {sup['professor']}: {len(sup['aulas'])} aulas às {sup['dia']}, {sup['horario']}º")
                    
                    if conflitos:
                        st.write(f"⚠️ **Conflitos de horário**: {len(conflitos)}")
                    
                    if limites_excedidos:
                        st.write(f"❌ **Limites excedidos**: {len(limites_excedidos)}")
                        for problema in limites_excedidos[:2]:
                            st.write(f"  - {problema['professor']}: {problema['horas_atual']}h > {problema['limite']}h")
                    
                    # Botão para corrigir tudo
                    if st.button("🔧 Corrigir Todos os Problemas", type="primary"):
                        aulas_corrigidas = st.session_state.aulas.copy()
                        
                        # 1. Corrigir superposições (mais crítico)
                        if superposicoes:
                            aulas_corrigidas = corrigir_superposicoes_professor(aulas_corrigidas, superposicoes)
                        
                        # 2. Corrigir conflitos
                        if conflitos:
                            aulas_corrigidas = corrigir_conflitos_automaticamente(aulas_corrigidas, conflitos)
                        
                        # 3. Para limites, usar completador
                        if limites_excedidos:
                            completador = CompletadorDeGradeAvancado(
                                st.session_state.turmas,
                                st.session_state.professores,
                                st.session_state.disciplinas
                            )
                            aulas_corrigidas = completador.completar_grade(aulas_corrigidas)
                        
                        st.session_state.aulas = aulas_corrigidas
                        st.success("✅ Problemas corrigidos! Recarregue a página.")
                        st.rerun()
            else:
                st.info("ℹ️ Gere uma grade primeiro para usar esta ferramenta.")
    
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
st.sidebar.write(f"- Limite professor: {LIMITE_HORAS_EFII}h")
st.sidebar.write("**EM:** 07:00-13:10")
st.sidebar.write("- 7 períodos + intervalo")
st.sidebar.write(f"- Limite professor: {LIMITE_HORAS_EM}h")

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
