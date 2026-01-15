# simple_scheduler_final.py - ALGORITMO DEFINITIVO COM TODAS AS REGRAS
import random
from datetime import datetime, time
from models import Aula

class SimpleGradeHorariaFinal:
    """Algoritmo definitivo com todas as regras de uma grade escolar real"""
    
    def __init__(self, turmas, professores, disciplinas, salas):
        self.turmas = turmas
        self.professores = professores
        self.disciplinas = disciplinas
        self.salas = salas
        self.dias_semana = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
        
        # Contadores para monitoramento
        self.tentativas_falhas = 0
        self.regras_violadas = []
    
    # ============================================
    # REGRA 1: HORÁRIOS REAIS E CONVERSÃO
    # ============================================
    
    def obter_segmento_turma(self, turma_nome):
        """Determina o segmento da turma baseado no nome"""
        if not turma_nome:
            return "EF_II"
        
        turma_nome_lower = turma_nome.lower()
        
        # Ensino Médio
        if 'em' in turma_nome_lower:
            return "EM"
        
        # Ensino Fundamental II
        if any(x in turma_nome_lower for x in ['6', '7', '8', '9', 'ano', 'ef']):
            return "EF_II"
        
        # Fallback
        try:
            if turma_nome_lower[0].isdigit():
                return "EF_II"
            else:
                return "EM"
        except:
            return "EF_II"
    
    def obter_horario_real_intervalos(self, segmento, periodo):
        """
        Retorna horário real como objetos time para comparação
        Retorna: (inicio_time, fim_time, intervalo_antes, intervalo_depois)
        """
        if segmento == "EM":
            horarios = {
                1: ("07:00", "07:50", False, False),
                2: ("07:50", "08:40", False, False), 
                3: ("08:40", "09:30", False, True),   # Intervalo DEPOIS
                4: ("09:50", "10:40", True, False),   # Intervalo ANTES
                5: ("10:40", "11:30", False, False),
                6: ("11:30", "12:20", False, False),
                7: ("12:20", "13:10", False, False)
            }
        else:  # EF_II
            horarios = {
                1: ("07:50", "08:40", False, False),
                2: ("08:40", "09:30", False, True),   # Intervalo DEPOIS
                3: ("09:50", "10:40", True, False),   # Intervalo ANTES
                4: ("10:40", "11:30", False, False),
                5: ("11:30", "12:20", False, False)
            }
        
        hora_str, fim_str, intervalo_antes, intervalo_depois = horarios.get(
            periodo, ("00:00", "00:00", False, False)
        )
        
        # Converter para objetos time para comparação
        inicio_time = datetime.strptime(hora_str, "%H:%M").time()
        fim_time = datetime.strptime(fim_str, "%H:%M").time()
        
        return inicio_time, fim_time, intervalo_antes, intervalo_depois
    
    def horarios_colidem(self, inicio1, fim1, inicio2, fim2):
        """Verifica se dois horários se sobrepõem"""
        return not (fim1 <= inicio2 or fim2 <= inicio1)
    
    # ============================================
    # REGRA 2: VALIDAÇÃO DE PROFESSOR
    # ============================================
    
    def professor_disponivel_horario_real(self, aulas_existentes, professor_nome, 
                                         dia, segmento_nova_aula, periodo_nova_aula):
        """
        VERIFICAÇÃO CRÍTICA: Professor não pode estar em dois lugares no mesmo horário REAL
        """
        # Obter horário REAL da nova aula
        inicio_novo, fim_novo, _, _ = self.obter_horario_real_intervalos(
            segmento_nova_aula, periodo_nova_aula
        )
        
        for aula in aulas_existentes:
            if aula.professor == professor_nome and aula.dia == dia:
                # Obter horário REAL da aula existente
                seg_existente = self.obter_segmento_turma(aula.turma)
                inicio_existente, fim_existente, _, _ = self.obter_horario_real_intervalos(
                    seg_existente, aula.horario
                )
                
                # Verificar colisão de horários REAIS
                if self.horarios_colidem(inicio_novo, fim_novo, inicio_existente, fim_existente):
                    return False  # CONFLITO DETECTADO!
        
        return True
    
    def professor_atingiu_limite(self, aulas_existentes, professor_obj):
        """Verifica se professor atingiu limite de horas semanais"""
        # Contar aulas do professor
        aulas_professor = [a for a in aulas_existentes if a.professor == professor_obj.nome]
        
        # Determinar limite baseado no segmento
        limite = self.obter_limite_professor(professor_obj)
        
        return len(aulas_professor) >= limite
    
    def obter_limite_professor(self, professor):
        """Retorna limite de horas baseado no segmento principal do professor"""
        # Analisar disciplinas do professor
        tem_efii = False
        tem_em = False
        
        for disc_nome in professor.disciplinas:
            # Encontrar disciplina
            for disc in self.disciplinas:
                if disc.nome == disc_nome:
                    # Verificar turmas
                    for turma_nome in disc.turmas:
                        segmento = self.obter_segmento_turma(turma_nome)
                        if segmento == "EF_II":
                            tem_efii = True
                        elif segmento == "EM":
                            tem_em = True
        
        # Determinar limite
        if tem_efii and not tem_em:
            return 25  # EF II
        elif tem_em and not tem_efii:
            return 35  # EM
        else:
            return 35  # Ambos - usar limite maior
    
    # ============================================
    # REGRA 3: VALIDAÇÃO DE TURMA
    # ============================================
    
    def turma_tem_horario_livre(self, aulas_existentes, turma_nome, dia, periodo):
        """Verifica se turma tem horário livre"""
        for aula in aulas_existentes:
            if aula.turma == turma_nome and aula.dia == dia and aula.horario == periodo:
                return False
        return True
    
    def disciplina_ja_dada_hoje(self, aulas_existentes, turma_nome, dia, disciplina_nome):
        """Evita mesma disciplina mais de 1 vez por dia (exceto carga > 3)"""
        contador = 0
        for aula in aulas_existentes:
            if (aula.turma == turma_nome and 
                aula.dia == dia and 
                aula.disciplina == disciplina_nome):
                contador += 1
        
        # Se disciplina tem carga > 3, pode ter 2 aulas no mesmo dia
        for disc in self.disciplinas:
            if disc.nome == disciplina_nome:
                if disc.carga_semanal > 3:
                    return contador >= 2  # Máximo 2 por dia
                else:
                    return contador >= 1  # Máximo 1 por dia
        
        return contador >= 1
    
    # ============================================
    # REGRA 4: DISTRIBUIÇÃO INTELIGENTE
    # ============================================
    
    def classificar_disciplinas(self, disciplinas_turma):
        """Classifica disciplinas por tipo para distribuição equilibrada"""
        pesadas = []
        medias = []
        leves = []
        praticas = []
        
        for disc in disciplinas_turma:
            if disc.tipo == "pesada":
                pesadas.append(disc)
            elif disc.tipo == "media":
                medias.append(disc)
            elif disc.tipo == "pratica":
                praticas.append(disc)
            else:  # leve
                leves.append(disc)
        
        # Intercalar tipos para evitar concentração
        resultado = []
        max_len = max(len(pesadas), len(medias), len(leves), len(praticas))
        
        for i in range(max_len):
            if i < len(pesadas):
                resultado.append(pesadas[i])
            if i < len(medias):
                resultado.append(medias[i])
            if i < len(leves):
                resultado.append(leves[i])
            if i < len(praticas):
                resultado.append(praticas[i])
        
        return resultado
    
    def distribuir_periodos_ideais(self, segmento, disciplina_tipo):
        """
        Distribui disciplinas nos períodos ideais:
        - Pesadas: 1º-3º períodos (manhã)
        - Práticas: evitar 1º período
        - Leves: tarde (períodos finais)
        """
        if segmento == "EM":
            if disciplina_tipo == "pesada":
                return [1, 2, 3, 4]  # Manhã
            elif disciplina_tipo == "pratica":
                return [4, 5, 6, 7]  # Evitar 1º período
            elif disciplina_tipo == "leve":
                return [5, 6, 7]  # Tarde
            else:  # media
                return list(range(1, 8))
        else:  # EF_II
            if disciplina_tipo == "pesada":
                return [1, 2, 3]  # Manhã
            elif disciplina_tipo == "pratica":
                return [3, 4, 5]  # Evitar 1º período
            elif disciplina_tipo == "leve":
                return [4, 5]  # Tarde
            else:  # media
                return list(range(1, 6))
    
    # ============================================
    # ALGORITMO PRINCIPAL COM BACKTRACKING
    # ============================================
        def gerar_grade(self):
        """
        GERAÇÃO INTELIGENTE: Aloca apenas o necessário, deixa VAGA quando não é possível
        Não força alocações impossíveis, respeita limites reais
        """
        aulas = []
        
        st.info(f"🔍 Iniciando geração inteligente para {len(self.turmas)} turmas")
        
        # FASE 1: Validar viabilidade de cada turma
        turmas_validas = []
        problemas = []
        
        for turma in self.turmas:
            turma_nome = turma.nome
            grupo_turma = turma.grupo if hasattr(turma, 'grupo') else "A"
            
            valido, mensagem = self.validar_viabilidade_turma(turma_nome, grupo_turma)
            if valido:
                turmas_validas.append(turma)
                st.success(mensagem)
            else:
                problemas.append(mensagem)
                st.error(mensagem)
        
        if problemas:
            st.warning(f"⚠️ {len(problemas)} turmas com problemas de viabilidade")
        
        if not turmas_validas:
            st.error("❌ Nenhuma turma viável para gerar grade!")
            return []
        
        # FASE 2: Para cada turma válida, alocar disciplinas
        for turma in turmas_validas:
            turma_nome = turma.nome
            grupo_turma = turma.grupo
            segmento = self.obter_segmento_turma(turma_nome)
            
            st.info(f"📅 Alocando turma {turma_nome} ({segmento}, Grupo {grupo_turma})")
            
            # Obter disciplinas desta turma
            disciplinas_turma = []
            for disc in self.disciplinas:
                if turma_nome in disc.turmas:
                    disc_grupo = disc.grupo if hasattr(disc, 'grupo') else "A"
                    if disc_grupo == grupo_turma:
                        # Adicionar múltiplas entradas conforme carga semanal
                        for _ in range(disc.carga_semanal):
                            disciplinas_turma.append(disc)
            
            if not disciplinas_turma:
                st.warning(f"⚠️ Turma {turma_nome} não tem disciplinas!")
                continue
            
            # Embaralhar disciplinas para distribuição aleatória
            random.shuffle(disciplinas_turma)
            
            # FASE 3: Tentar alocar cada aula da turma
            aulas_alocadas_turma = 0
            aulas_nao_alocadas = []
            
            for disciplina in disciplinas_turma:
                alocado = False
                
                # Tentar dias da semana
                for dia in self.dias_semana:
                    if alocado:
                        break
                    
                    # Períodos disponíveis para esta turma
                    if segmento == "EM":
                        periodos = list(range(1, 8))
                    else:
                        periodos = list(range(1, 6))
                    
                    # Ordenar períodos: evitar períodos ruins para certas disciplinas
                    if disciplina.tipo == "pesada":
                        # Matérias pesadas preferencialmente de manhã
                        periodos.sort(key=lambda p: 0 if p <= 3 else 1 if p <= 5 else 2)
                    elif disciplina.tipo == "pratica":
                        # Práticas não no primeiro período
                        periodos.sort(key=lambda p: 1 if p == 1 else 0)
                    
                    for periodo in periodos:
                        # Pular se horário já está ocupado
                        if self.horario_esta_preenchido(aulas, turma_nome, dia, periodo):
                            continue
                        
                        # Encontrar professor disponível REALMENTE
                        professor = self.encontrar_professor_disponivel_real(
                            disciplina.nome, grupo_turma, aulas, 
                            dia, periodo, segmento, turma_nome
                        )
                        
                        if professor:
                            # Verificar se disciplina já foi dada hoje (limitar repetição)
                            aulas_hoje = [
                                a for a in aulas 
                                if a.turma == turma_nome and 
                                a.dia == dia and 
                                a.disciplina == disciplina.nome
                            ]
                            
                            # Limitar: máximo 2 aulas da mesma disciplina por dia
                            if len(aulas_hoje) >= 2:
                                continue
                            
                            # Se disciplina pesada, evitar mais de 1 por dia
                            if disciplina.tipo == "pesada" and len(aulas_hoje) >= 1:
                                continue
                            
                            # TODAS AS CONDIÇÕES ATENDIDAS! Criar aula
                            nova_aula = Aula(
                                turma=turma_nome,
                                disciplina=disciplina.nome,
                                professor=professor.nome,
                                dia=dia,
                                horario=periodo,
                                segmento=segmento
                            )
                            aulas.append(nova_aula)
                            aulas_alocadas_turma += 1
                            alocado = True
                            break
                    
                    if alocado:
                        break
                
                # Se não conseguiu alocar, adicionar à lista de não alocadas
                if not alocado:
                    aulas_nao_alocadas.append(disciplina.nome)
            
            # Relatório da turma
            necessarias, _ = self.calcular_necessidades_turma(turma_nome, grupo_turma)
            
            if aulas_nao_alocadas:
                st.warning(f"⚠️ Turma {turma_nome}: {aulas_alocadas_turma}/{necessarias} aulas")
                st.write(f"   Não alocadas: {', '.join(set(aulas_nao_alocadas))}")
            else:
                st.success(f"✅ Turma {turma_nome}: {aulas_alocadas_turma}/{necessarias} aulas")
        
        # FASE 4: Diagnóstico final
        total_necessario = 0
        for turma in turmas_validas:
            necessarias, _ = self.calcular_necessidades_turma(turma.nome, turma.grupo)
            total_necessario += necessarias
        
        total_alocado = len(aulas)
        
        st.subheader("📊 RELATÓRIO FINAL DA GERAÇÃO")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Aulas Necessárias", total_necessario)
        with col2:
            st.metric("Aulas Alocadas", total_alocado)
        with col3:
            percentual = (total_alocado / total_necessario * 100) if total_necessario > 0 else 0
            st.metric("Completude", f"{percentual:.1f}%")
        
        if total_alocado < total_necessario:
            st.warning(f"⚠️ Faltam {total_necessario - total_alocado} aulas!")
            st.write("**Possíveis causas:**")
            st.write("1. Professores insuficientes para algumas disciplinas")
            st.write("2. Conflitos de horário REAL não resolvíveis")
            st.write("3. Limites de professores atingidos")
            st.write("4. Horários indisponíveis bloqueando alocações")
        
        # Verificar conflitos residuais
        conflitos = 0
        for i, aula1 in enumerate(aulas):
            for aula2 in aulas[i+1:]:
                if (aula1.professor == aula2.professor and 
                    aula1.dia == aula2.dia):
                    seg1 = self.obter_segmento_turma(aula1.turma)
                    seg2 = self.obter_segmento_turma(aula2.turma)
                    
                    inicio1, fim1, _, _ = self.obter_horario_real_intervalos(seg1, aula1.horario)
                    inicio2, fim2, _, _ = self.obter_horario_real_intervalos(seg2, aula2.horario)
                    
                    if self.horarios_colidem(inicio1, fim1, inicio2, fim2):
                        conflitos += 1
        
        if conflitos > 0:
            st.error(f"❌ ATENÇÃO: {conflitos} conflitos de horário REAL detectados!")
        else:
            st.success("✅ Nenhum conflito de horário REAL!")
        
        return aulas
        
    
    
    
    
    
   ''' def gerar_grade(self):
        """
        Gera grade completa respeitando TODAS as regras
        Usa backtracking quando encontra conflitos
        """
        aulas = []
        max_iteracoes = 10000
        iteracao = 0
        
        # FASE 1: Preparar lista de alocações necessárias
        alocacoes_necessarias = []
        
        for turma in self.turmas:
            turma_nome = turma.nome
            segmento = self.obter_segmento_turma(turma_nome)
            grupo_turma = turma.grupo if hasattr(turma, 'grupo') else "A"
            
            # Obter disciplinas desta turma
            disciplinas_turma = []
            for disc in self.disciplinas:
                if turma_nome in disc.turmas:
                    disc_grupo = disc.grupo if hasattr(disc, 'grupo') else "A"
                    if disc_grupo == grupo_turma:
                        # Adicionar uma entrada para cada aula necessária
                        for aula_num in range(disc.carga_semanal):
                            alocacoes_necessarias.append({
                                'turma': turma_nome,
                                'disciplina': disc,
                                'segmento': segmento,
                                'grupo': grupo_turma,
                                'aula_num': aula_num + 1,
                                'tipo': disc.tipo
                            })
        
        # Embaralhar para distribuição aleatória
        random.shuffle(alocacoes_necessarias)
        
        # FASE 2: Tentar alocar cada aula
        for alocacao in alocacoes_necessarias:
            turma_nome = alocacao['turma']
            disciplina = alocacao['disciplina']
            segmento = alocacao['segmento']
            grupo_turma = alocacao['grupo']
            tipo_disciplina = alocacao['tipo']
            
            # Encontrar professores disponíveis
            professores_candidatos = []
            for prof in self.professores:
                if disciplina.nome in prof.disciplinas:
                    prof_grupo = prof.grupo if hasattr(prof, 'grupo') else "A"
                    if prof_grupo in [grupo_turma, "AMBOS"]:
                        # Verificar se professor não atingiu limite
                        if not self.professor_atingiu_limite(aulas, prof):
                            professores_candidatos.append(prof)
            
            if not professores_candidatos:
                self.regras_violadas.append(f"Sem professor para {disciplina.nome} (Turma {turma_nome})")
                continue
            
            # Ordenar professores por carga atual (menos carregados primeiro)
            professores_candidatos.sort(key=lambda p: len(
                [a for a in aulas if a.professor == p.nome]
            ))
            
            # Períodos ideais para esta disciplina
            periodos_ideais = self.distribuir_periodos_ideais(segmento, tipo_disciplina)
            
            # Tentar alocar
            alocado = False
            tentativas_professor = 0
            
            for professor in professores_candidatos:
                if alocado:
                    break
                
                # Dias disponíveis do professor
                dias_disponiveis = professor.disponibilidade if hasattr(professor, 'disponibilidade') else self.dias_semana
                
                # Tentar dias em ordem preferencial (segunda a sexta)
                for dia in self.dias_semana:
                    if dia not in dias_disponiveis:
                        continue
                    
                    # Verificar horário indisponível específico
                    if hasattr(professor, 'horarios_indisponiveis'):
                        # Tentar períodos ideais primeiro
                        for periodo in periodos_ideais:
                            if f"{dia}_{periodo}" in professor.horarios_indisponiveis:
                                continue
                            
                            # REGRA: Turma livre neste horário?
                            if not self.turma_tem_horario_livre(aulas, turma_nome, dia, periodo):
                                continue
                            
                            # REGRA: Disciplina já dada hoje?
                            if self.disciplina_ja_dada_hoje(aulas, turma_nome, dia, disciplina.nome):
                                continue
                            
                            # REGRA CRÍTICA: Professor disponível no horário REAL?
                            if not self.professor_disponivel_horario_real(
                                aulas, professor.nome, dia, segmento, periodo
                            ):
                                continue
                            
                            # REGRA: Evitar aulas pesadas em períodos ruins
                            if tipo_disciplina == "pesada" and segmento == "EM" and periodo > 5:
                                continue  # Evitar matemática no 6º-7º período
                            
                            # REGRA: Evitar práticas no 1º período
                            if tipo_disciplina == "pratica" and periodo == 1:
                                continue
                            
                            # TODAS AS REGRAS ATENDIDAS! Criar aula
                            nova_aula = Aula(
                                turma=turma_nome,
                                disciplina=disciplina.nome,
                                professor=professor.nome,
                                dia=dia,
                                horario=periodo,
                                segmento=segmento
                            )
                            aulas.append(nova_aula)
                            alocado = True
                            break
                        
                        if alocado:
                            break
                    
                    # Se não encontrou nos horários ideais, tentar outros
                    if not alocado:
                        # Períodos disponíveis para esta turma
                        if segmento == "EM":
                            todos_periodos = list(range(1, 8))
                        else:
                            todos_periodos = list(range(1, 6))
                        
                        for periodo in todos_periodos:
                            if f"{dia}_{periodo}" in getattr(professor, 'horarios_indisponiveis', []):
                                continue
                            
                            if not self.turma_tem_horario_livre(aulas, turma_nome, dia, periodo):
                                continue
                            
                            if self.disciplina_ja_dada_hoje(aulas, turma_nome, dia, disciplina.nome):
                                continue
                            
                            if not self.professor_disponivel_horario_real(
                                aulas, professor.nome, dia, segmento, periodo
                            ):
                                continue
                            
                            # Criar aula
                            nova_aula = Aula(
                                turma=turma_nome,
                                disciplina=disciplina.nome,
                                professor=professor.nome,
                                dia=dia,
                                horario=periodo,
                                segmento=segmento
                            )
                            aulas.append(nova_aula)
                            alocado = True
                            break
                    
                    if alocado:
                        break
                
                tentativas_professor += 1
            
            # Se não alocou após tentar todos professores
            if not alocado:
                self.regras_violadas.append(
                    f"Não alocado: {disciplina.nome} - {turma_nome}"
                )
                self.tentativas_falhas += 1
        
        # FASE 3: Otimização final - remover conflitos residuais
        aulas = self.otimizar_grade(aulas)
        
        # Relatório
        if self.regras_violadas:
            print(f"⚠️ Regras violadas: {len(self.regras_violadas)}")
            for violacao in self.regras_violadas[:5]:
                print(f"  - {violacao}")
        
        return aulas
    '''
    # ============================================
    # FASE 3: OTIMIZAÇÃO
    # ============================================
    
    def otimizar_grade(self, aulas):
        """Otimiza a grade final, removendo conflitos residuais"""
        aulas_otimizadas = aulas.copy()
        melhorias = 0
        
        # Verificar e corrigir conflitos de professor
        for i, aula in enumerate(aulas_otimizadas):
            for j, outra_aula in enumerate(aulas_otimizadas):
                if i >= j:
                    continue
                
                # Se mesmo professor e mesmo dia
                if (aula.professor == outra_aula.professor and 
                    aula.dia == outra_aula.dia):
                    
                    # Obter horários REAIS
                    seg1 = self.obter_segmento_turma(aula.turma)
                    inicio1, fim1, _, _ = self.obter_horario_real_intervalos(seg1, aula.horario)
                    
                    seg2 = self.obter_segmento_turma(outra_aula.turma)
                    inicio2, fim2, _, _ = self.obter_horario_real_intervalos(seg2, outra_aula.horario)
                    
                    # Se há conflito REAL
                    if self.horarios_colidem(inicio1, fim1, inicio2, fim2):
                        # Tentar mover uma das aulas
                        if self.tentar_mover_aula(aulas_otimizadas, i):
                            melhorias += 1
                            break
        
        if melhorias > 0:
            print(f"✅ {melhorias} conflitos corrigidos na otimização")
        
        return aulas_otimizadas
    
    def tentar_mover_aula(self, aulas, indice_aula):
        """Tenta mover uma aula para resolver conflito"""
        aula = aulas[indice_aula]
        turma_nome = aula.turma
        segmento = self.obter_segmento_turma(turma_nome)
        
        # Períodos disponíveis
        if segmento == "EM":
            periodos = list(range(1, 8))
        else:
            periodos = list(range(1, 6))
        
        # Tentar outros períodos no mesmo dia
        for novo_periodo in periodos:
            if novo_periodo == aula.horario:
                continue
            
            # Verificar se período está livre
            periodo_livre = True
            for a in aulas:
                if (a.turma == turma_nome and 
                    a.dia == aula.dia and 
                    a.horario == novo_periodo):
                    periodo_livre = False
                    break
            
            if periodo_livre:
                # Verificar professor disponível
                if self.professor_disponivel_horario_real(
                    [a for j, a in enumerate(aulas) if j != indice_aula],
                    aula.professor,
                    aula.dia,
                    segmento,
                    novo_periodo
                ):
                    # Mover aula
                    aulas[indice_aula].horario = novo_periodo
                    return True
        
        return False
    
    # ============================================
    # MÉTODO COMPATÍVEL (para substituição direta)
    # ============================================
    
    @classmethod
    def substituir_original(cls):
        """Método para substituir a classe original no import"""
        return cls

# Classe wrapper para compatibilidade
class SimpleGradeHoraria(SimpleGradeHorariaFinal):
    """Wrapper para compatibilidade com código existente"""
    pass