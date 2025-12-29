# relatorio_professor.py
import pandas as pd
from typing import List
from models import Aula # Certifique-se de que o caminho para models.py está correto

def gerar_relatorio_professor(professor_nome: str, aulas: List[Aula], dia_semana: str = "sex") -> pd.DataFrame:
    """
    Gera um DataFrame representando o horário de um professor em um dia específico.

    Args:
        professor_nome: Nome do professor.
        aulas: Lista completa de aulas geradas.
        dia_semana: Dia da semana ('seg', 'ter', 'qua', 'qui', 'sex'). Default 'sex'.

    Returns:
        pd.DataFrame: Tabela com horários nas linhas e status nas colunas.
    """
    # Definir os horários do dia (ex: 1 a 8, ajuste conforme sua necessidade)
    horarios_do_dia = list(range(1, 9)) # De 1 a 8

    # Dicionário para armazenar o que o professor faz em cada horário
    agenda_do_dia = {}

    # Definir eventos fixos (exemplo)
    EVENTOS_FIXOS = {4: "Intervalo"} # Intervalo no horário 4

    for h in horarios_do_dia:
        # Verificar eventos fixos primeiro
        if h in EVENTOS_FIXOS:
            agenda_do_dia[h] = EVENTOS_FIXOS[h]
        else:
            # Procurar aula do professor nesse horário e dia
            aula_do_professor = next(
                (a for a in aulas if a.professor == professor_nome and a.dia == dia_semana and a.horario == h),
                None
            )
            if aula_do_professor:
                # Lógica para identificar "Inglês do Integral" etc.
                if "Integral" in aula_do_professor.turma or "integral" in aula_do_professor.disciplina.lower():
                     agenda_do_dia[h] = f"{aula_do_professor.turma} - {aula_do_professor.disciplina}"
                else:
                     agenda_do_dia[h] = f"{aula_do_professor.turma} - {aula_do_professor.disciplina}"
            else:
                agenda_do_dia[h] = "Livre" # Ou "Disponível"

    # Criar DataFrame
    df_agenda = pd.DataFrame.from_dict(agenda_do_dia, orient='index', columns=[dia_semana.capitalize()])
    df_agenda.index.name = "Horário"
    # Mapear números dos horários para os horários reais (ajuste conforme sua necessidade)
    MAPA_HORARIOS = {
        1: "07:10-08:00",
        2: "08:00-08:50",
        3: "08:50-09:40",
        4: "09:40-10:00", # Intervalo
        5: "10:00-10:50",
        6: "10:50-11:40",
        7: "11:40-12:30",
        8: "12:30-13:20"
        # Adicione mais se necessário
    }
    df_agenda.index = df_agenda.index.map(MAPA_HORARIOS).fillna("Horário Inválido")

    return df_agenda
