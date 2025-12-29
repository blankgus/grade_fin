# extrair_pdf.py
import pdfplumber
import pandas as pd
from models import Professor, Disciplina, Turma, Aula
import uuid

def extrair_dados_do_pdf(caminho_pdf="Professores_Manha.pdf"):
    """
    Extrai dados do PDF de horários e retorna listas de professores, disciplinas, turmas e aulas.
    """
    professores_dict = {}  # nome -> Professor
    disciplinas_set = set()  # nomes únicos de disciplinas
    turmas_set = set()  # nomes únicos de turmas
    aulas_list = []  # lista de objetos Aula

    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina_numero, pagina in enumerate(pdf.pages):
                # Extrair texto da página
                texto = pagina.extract_text()
                if not texto:
                    continue
                
                # Dividir o texto em linhas
                linhas = texto.split('\n')
                
                # Procurar o cabeçalho com nome do professor e disciplina
                professor_nome = None
                disciplina_nome = None
                for i, linha in enumerate(linhas):
                    if "Professor:" in linha:
                        try:
                            # Exemplo: "Professor: Luciana Aparecida Barbosa da Silva (Lan)"
                            nome_parte = linha.split("Professor:")[1].strip()
                            if "(" in nome_parte and ")" in nome_parte:
                                nome_completo, apelido = nome_parte.split("(")
                                apelido = apelido.rstrip(")")
                                professor_nome = apelido.strip()
                            else:
                                professor_nome = nome_parte.split()[0]  # Primeiro nome
                        except:
                            professor_nome = f"Professor_{pagina_numero + 1}"
                        break
                
                if not professor_nome:
                    professor_nome = f"Professor_{pagina_numero + 1}"

                # Procurar a disciplina (geralmente na mesma linha ou próxima)
                for i, linha in enumerate(linhas):
                    if "Disciplina:" in linha:
                        try:
                            # Exemplo: "Disciplina: Matemática"
                            disciplina_nome = linha.split("Disciplina:")[1].strip()
                            disciplinas_set.add(disciplina_nome)
                        except:
                            disciplina_nome = "Disciplina_Desconhecida"
                        break
                
                if not disciplina_nome:
                    disciplina_nome = f"Disciplina_Pagina_{pagina_numero + 1}"
                    disciplinas_set.add(disciplina_nome)

                # Criar ou atualizar o professor
                if professor_nome not in professores_dict:
                    professores_dict[professor_nome] = Professor(
                        nome=professor_nome,
                        disciplinas=[disciplina_nome],
                        disponibilidade_dias=set(),  # Será preenchido com base na grade
                        disponibilidade_horarios=set(),
                        restricoes=set()
                    )
                else:
                    # Adicionar disciplina ao professor, se não tiver
                    if disciplina_nome not in professores_dict[professor_nome].disciplinas:
                        professores_dict[professor_nome].disciplinas.append(disciplina_nome)

                # Procurar a tabela de horários
                # Vamos tentar identificar a tabela pelas colunas de dias
                tabelas = pagina.extract_tables()
                if tabelas:
                    tabela = tabelas[0]  # Assume que a primeira tabela é a grade
                    if not tabela or len(tabela) < 2:
                        continue
                    cabecalho = tabela[0]  # Primeira linha é o cabeçalho
                    dias_semana = [d for d in cabecalho if d in ["seg", "ter", "qua", "qui", "sex"]]
                    
                    # Processar cada linha da tabela (exceto o cabeçalho)
                    for linha_tabela in tabela[1:]:
                        if not linha_tabela or len(linha_tabela) < len(cabecalho):
                            continue
                        horario_str = linha_tabela[0]  # Primeira coluna é o horário
                        try:
                            # Converter horário para inteiro (ex: "1" -> 1)
                            horario_int = int(horario_str)
                        except (ValueError, TypeError):
                            continue  # Pula se não for um número
                        
                        # Para cada dia da semana na linha
                        for j, dia in enumerate(dias_semana):
                            # Índice da coluna do dia na tabela (considerando que a primeira coluna é o horário)
                            try:
                                indice_coluna_dia = cabecalho.index(dia)
                            except ValueError:
                                continue
                            conteudo_celula = linha_tabela[indice_coluna_dia] if indice_coluna_dia < len(linha_tabela) else ""
                            
                            # Se a célula não estiver vazia, significa que tem aula
                            if conteudo_celula and conteudo_celula.strip() != "":
                                # Extrair turma (ex: "6anoA")
                                turma_nome = conteudo_celula.strip()
                                turmas_set.add(turma_nome)
                                
                                # Determinar a série com base no nome da turma
                                serie = determinar_serie(turma_nome)
                                
                                # Adicionar dia e horário à disponibilidade do professor
                                professores_dict[professor_nome].disponibilidade_dias.add(dia)
                                professores_dict[professor_nome].disponibilidade_horarios.add(horario_int)
                                
                                # Criar objeto Aula
                                aula = Aula(
                                    turma=turma_nome,
                                    disciplina=disciplina_nome,
                                    professor=professor_nome,
                                    dia=dia,
                                    horario=horario_int,
                                    sala="Sala 1"  # Sala padrão, pode ser ajustada depois
                                )
                                aulas_list.append(aula)
                
    except FileNotFoundError:
        print(f"❌ Arquivo '{caminho_pdf}' não encontrado.")
        return [], [], [], []
    except Exception as e:
        print(f"❌ Erro ao extrair dados do PDF: {e}")
        import traceback
        traceback.print_exc()
        return [], [], [], []
    
    # Converter dict de professores para lista
    professores_list = list(professores_dict.values())
    
    # Criar lista de disciplinas a partir do set
    disciplinas_list = [
        Disciplina(
            nome=nome,
            carga_semanal=3,  # Valor padrão, será recalculado depois
            tipo="media",
            series=[]  # Será preenchido depois
        )
        for nome in disciplinas_set
    ]
    
    # Criar lista de turmas a partir do set
    turmas_list = [
        Turma(
            nome=nome,
            serie=determinar_serie(nome),
            turno="manha"
        )
        for nome in turmas_set
    ]
    
    return professores_list, disciplinas_list, turmas_list, aulas_list

def determinar_serie(nome_turma):
    """
    Determina a série com base no nome da turma.
    """
    # Mapeamento básico
    if "6ano" in nome_turma:
        return "6ano"
    elif "7ano" in nome_turma:
        return "7ano"
    elif "8ano" in nome_turma:
        return "8ano"
    elif "9ano" in nome_turma:
        return "9ano"
    elif "1em" in nome_turma:
        return "1em"
    elif "2em" in nome_turma:
        return "2em"
    elif "3em" in nome_turma:
        return "3em"
    else:
        return "serie_desconhecida"

# Exemplo de uso
if __name__ == "__main__":
    caminho = "Professores_Manha.pdf"
    try:
        profs, discs, turmas, aulas = extrair_dados_do_pdf(caminho)
        print(f"✅ Extraídos {len(profs)} professores")
        print(f"✅ Extraídas {len(discs)} disciplinas")
        print(f"✅ Extraídas {len(turmas)} turmas")
        print(f"✅ Extraídas {len(aulas)} aulas")
        
        # Exibir alguns exemplos
        print("\n--- Exemplos de Professores ---")
        for p in profs[:3]:
            print(f"Nome: {p.nome}, Disciplinas: {p.disciplinas}")
            print(f"  Dias disponíveis: {sorted(p.disponibilidade_dias)}")
            print(f"  Horários disponíveis: {sorted(p.disponibilidade_horarios)}")
        
        print("\n--- Exemplos de Turmas ---")
        for t in turmas[:3]:
            print(f"Nome: {t.nome}, Série: {t.serie}")
        
        print("\n--- Exemplos de Aulas ---")
        for a in aulas[:5]:
            print(f"{a.professor} dá {a.disciplina} para {a.turma} ({a.dia}, horário {a.horario})")
            
    except Exception as e:
        print(f"❌ Erro ao extrair dados: {str(e)}")
        import traceback
        traceback.print_exc()