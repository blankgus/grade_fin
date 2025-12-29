import streamlit as st
import database

def salvar_tudo():
    """Salva todos os dados no banco automaticamente"""
    try:
        database.salvar_turmas(st.session_state.turmas)
        database.salvar_professores(st.session_state.professores)
        database.salvar_disciplinas(st.session_state.disciplinas)
        database.salvar_salas(st.session_state.salas)
        database.salvar_periodos(st.session_state.periodos)
        database.salvar_feriados(st.session_state.feriados)
        if "aulas" in st.session_state and st.session_state.aulas:
            database.salvar_grade(st.session_state.aulas)
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {str(e)}")
        return False