# utils.py - Funções auxiliares para horários
import streamlit as st

def obter_segmento_turma(turma_nome):
    """Determina o segmento da turma baseado no nome"""
    turma_nome_lower = turma_nome.lower()
    if 'em' in turma_nome_lower or '1em' in turma_nome_lower or '2em' in turma_nome_lower or '3em' in turma_nome_lower:
        return "EM"
    elif 'ano' in turma_nome_lower or '6' in turma_nome_lower or '7' in turma_nome_lower or '8' in turma_nome_lower or '9' in turma_nome_lower:
        return "EF_II"
    else:
        # Tentar inferir
        if any(s in turma_nome_lower for s in ['fundamental', 'ef', 'ii']):
            return "EF_II"
        else:
            return "EM"  # Default para EM se não conseguir determinar

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
            7: "12:20 - 13:10"
        }
    else:
        # EF II: 5 períodos de AULA
        horarios = {
            1: "07:50 - 08:40",
            2: "08:40 - 09:30",
            # INTERVALO: 09:30-09:50 (não tem número)
            3: "09:50 - 10:40",
            4: "10:40 - 11:30",
            5: "11:30 - 12:20"
        }
    
    return horarios.get(periodo, f"Período {periodo}")

def obter_periodos_disponiveis(turma_nome):
    """Retorna lista de períodos disponíveis"""
    segmento = obter_segmento_turma(turma_nome)
    if segmento == "EM":
        return list(range(1, 8))  # 1-7
    else:
        return list(range(1, 6))  # 1-5

def calcular_carga_maxima(serie):
    """Calcula carga horária máxima"""
    serie_lower = serie.lower()
    if 'em' in serie_lower or serie_lower in ['1em', '2em', '3em']:
        return 35  # 7×5
    else:
        return 25  # 5×5

def validar_grade(aulas):
    """Valida se a grade gerada está correta"""
    if not aulas:
        return False, "Nenhuma aula gerada"
    
    # Agrupar por turma
    turmas = {}
    for aula in aulas:
        if aula['turma'] not in turmas:
            turmas[aula['turma']] = []
        turmas[aula['turma']].append(aula)
    
    erros = []
    
    for turma_nome, aulas_turma in turmas.items():
        segmento = obter_segmento_turma(turma_nome)
        periodos_por_dia = 7 if segmento == "EM" else 5
        total_esperado = periodos_por_dia * 5
        
        # Verificar total
        if len(aulas_turma) != total_esperado:
            erros.append(f"{turma_nome}: {len(aulas_turma)} aulas (esperado: {total_esperado})")
        
        # Verificar por dia
        dias = {}
        for aula in aulas_turma:
            if aula['dia'] not in dias:
                dias[aula['dia']] = 0
            dias[aula['dia']] += 1
        
        for dia, count in dias.items():
            if count != periodos_por_dia:
                erros.append(f"{turma_nome} ({dia}): {count} aulas (esperado: {periodos_por_dia})")
    
    if erros:
        return False, erros
    else:
        return True, "Grade válida"