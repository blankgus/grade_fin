# Teste simples no Python
from utils import obter_segmento_turma, obter_horario_real

print("Teste 3emA (EM):")
print(f"Segmento: {obter_segmento_turma('3emA')}")
for i in range(1, 8):
    print(f"Período {i}: {obter_horario_real('3emA', i)}")

print("\nTeste 8anoA (EF II):")
print(f"Segmento: {obter_segmento_turma('8anoA')}")
for i in range(1, 6):
    print(f"Período {i}: {obter_horario_real('8anoA', i)}")