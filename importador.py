import pandas as pd
from models import Professor

def carregar_professores_do_excel(caminho="prodis.xlsx"):
    try:
        # Listar abas para depuração
        xls = pd.ExcelFile(caminho)
        print("🔍 Abas disponíveis no Excel:", xls.sheet_names)
    except FileNotFoundError:
        print("❌ Arquivo Excel não encontrado!")
        return []
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo: {e}")
        return []

    # Ler a aba "Professores"
    try:
        df = pd.read_excel(caminho, sheet_name="Professores")
        print("✅ Aba 'Professores' encontrada.")
    except ValueError as e:
        print(f"❌ Erro ao ler a aba 'Professores': {e}")
        return []
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return []

    # Verificar se as colunas 'nome' e 'disciplinas' existem
    if "nome" not in df.columns or "disciplinas" not in df.columns:
        print("❌ Colunas 'nome' ou 'disciplinas' não encontradas no Excel.")
        print("Colunas disponíveis:", df.columns.tolist())
        return []

    print(f"✅ Dados lidos: {len(df)} linhas encontradas.")
    print("Primeiras 5 linhas:")
    print(df.head())

    professores = []
    for _, row in df.iterrows():
        nome = row["nome"]
        # Assume que a coluna "disciplinas" tem os nomes separados por vírgula
        disciplinas_str = row["disciplinas"]
        if pd.isna(disciplinas_str):  # Verifica se a célula está vazia
            print(f"⚠️ Linha com nome '{nome}' tem disciplinas vazias. Pulando...")
            continue
        disciplinas = [d.strip() for d in str(disciplinas_str).split(",")]

        # Criar professor com disponibilidade padrão (todos os dias e horários)
        prof = Professor(
            nome=nome,
            disciplinas=disciplinas,
            disponibilidade_dias={"seg", "ter", "qua", "qui", "sex"},
            disponibilidade_horarios={1, 2, 3, 5, 6, 7}
        )
        professores.append(prof)

    print(f"✅ {len(professores)} professores carregados do Excel.")
    return professores