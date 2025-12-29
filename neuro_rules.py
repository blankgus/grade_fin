def eh_horario_ideal(tipo_disciplina: str, horario: int, segmento: str) -> bool:
    """
    Horários ideais considerando:
    - EF II: 5 períodos (1-5)
    - EM: 7 períodos (1-7)
    O intervalo NÃO tem número de período.
    """
    if segmento == "EF_II":
        # Períodos EF II: 1(07:50), 2(08:40), 3(09:50), 4(10:40), 5(11:30)
        if tipo_disciplina == "pesada":
            return horario in [1, 2]  # Manhã, antes do intervalo
        elif tipo_disciplina == "pratica":
            return horario in [4, 5]  # Tarde, após intervalo
        else:
            return horario in [1, 2, 3, 4, 5]
    
    else:  # EM
        # Períodos EM: 1(07:00), 2(07:50), 3(08:40), 4(09:50), 5(10:40), 6(11:30), 7(12:20)
        if tipo_disciplina == "pesada":
            return horario in [1, 2, 3]  # Antes do intervalo
        elif tipo_disciplina == "pratica":
            return horario in [5, 6, 7]  # Após intervalo
        else:
            return horario in [1, 2, 3, 4, 5, 6, 7]