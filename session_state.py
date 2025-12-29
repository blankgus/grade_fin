import streamlit as st
from models import Turma, Professor, Disciplina, Sala, DIAS_SEMANA
import database

def init_session_state():
    """Inicializa todos os estados da sessão"""
    database.init_db()
    
    # Carregar turmas
    if "turmas" not in st.session_state:
        turmas_carregadas = database.carregar_turmas()
        if turmas_carregadas:
            st.session_state.turmas = turmas_carregadas
        else:
            # Dados padrão se não houver nada no banco
            st.session_state.turmas = [
                Turma("6anoA", "6ano", "manha", "A", "EF_II"),
                Turma("6anoB", "6ano", "manha", "B", "EF_II"),
                Turma("7anoA", "7ano", "manha", "A", "EF_II"),
                Turma("7anoB", "7ano", "manha", "B", "EF_II"),
                Turma("8anoA", "8ano", "manha", "A", "EF_II"),
                Turma("8anoB", "8ano", "manha", "B", "EF_II"),
                Turma("9anoA", "9ano", "manha", "A", "EF_II"),
                Turma("9anoB", "9ano", "manha", "B", "EF_II"),
                Turma("1emA", "1em", "manha", "A", "EM"),
                Turma("1emB", "1em", "manha", "B", "EM"),
                Turma("2emA", "2em", "manha", "A", "EM"),
                Turma("2emB", "2em", "manha", "B", "EM"),
                Turma("3emA", "3em", "manha", "A", "EM"),
                Turma("3emB", "3em", "manha", "B", "EM"),
            ]
    
    # Carregar professores
    if "professores" not in st.session_state:
        professores_carregados = database.carregar_professores()
        if professores_carregados:
            st.session_state.professores = professores_carregados
        else:
            st.session_state.professores = []
    
    # Carregar disciplinas
    if "disciplinas" not in st.session_state:
        disciplinas_carregadas = database.carregar_disciplinas()
        if disciplinas_carregadas:
            st.session_state.disciplinas = disciplinas_carregadas
        else:
            st.session_state.disciplinas = []
    
    # Carregar salas
    if "salas" not in st.session_state:
        salas_carregadas = database.carregar_salas()
        if salas_carregadas:
            st.session_state.salas = salas_carregadas
        else:
            st.session_state.salas = [
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
                Sala("Laboratório de Ciências", 25, "laboratório"),
                Sala("Auditório", 100, "auditório"),
            ]
    
    # Carregar grade
    if "aulas" not in st.session_state:
        aulas_carregadas = database.carregar_grade()
        st.session_state.aulas = aulas_carregadas if aulas_carregadas else []
    
    # Carregar feriados
    if "feriados" not in st.session_state:
        feriados_carregados = database.carregar_feriados()
        st.session_state.feriados = feriados_carregados if feriados_carregados else []
    
    # Carregar períodos
    if "periodos" not in st.session_state:
        periodos_carregados = database.carregar_periodos()
        st.session_state.periodos = periodos_carregados if periodos_carregados else []