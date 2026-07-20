import BplusTree, time, tracemalloc, random

def criar_arvore_bplus_indices(path, grau):
    arvoreplus = BplusTree.BplusTree(grau)
    with open(path, 'r', encoding='utf-8') as f:
        f.readline()  # pula o cabeçalho
        while True:
            offset = f.tell()
            linha = f.readline()
            if not linha: break

            id_str = linha.split(',', 1)[0].replace('"', '')
            if not id_str.isdigit(): continue

            # B+ usa parâmetros separados (Chave, Valor)
            arvoreplus.insert(int(id_str), offset)
    return arvoreplus


def buscar_no_disco(arquivo, offset):
    arquivo.seek(offset)
    return arquivo.readline()


def inserir_novo_registro(arvore, path, id_novo, linha_completa, tipo_arvore="B"):
    #faz a gravação no disco sem contar o tempo
    with open(path, 'a', encoding='utf-8') as f:
        f.seek(0, 2)
        novo_offset = f.tell()
        f.write(linha_completa + "\n")

        #inicia o cronômetro apenas para a Árvore
    inicio_arvore = time.perf_counter()

    if tipo_arvore == "B":
        arvore.insert((id_novo, novo_offset))
    elif tipo_arvore == "B+":
        arvore.insert(id_novo, novo_offset)

    fim_arvore = time.perf_counter()
    tempo_insercao = fim_arvore - inicio_arvore

    #retorna o offset e o tempo da operação na estrutura
    return novo_offset, tempo_insercao


# ==========================================
# EXECUÇÃO E COLETA DE MÉTRICAS - ÁRVORE B+
# ==========================================
if __name__ == "__main__":
    path = 'open4goods-isbn-dataset.csv'
    grau = 100

    print("--- INICIANDO BENCHMARK: ÁRVORE B+ ---")

    tracemalloc.start()
    inicio_carga = time.perf_counter()

    arvore = criar_arvore_bplus_indices(path, grau)

    fim_carga = time.perf_counter()
    _, pico_memoria = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tempo_carga = fim_carga - inicio_carga
    memoria_mb = pico_memoria / (1024 * 1024)

    print(f"[MÉTRICA] Tempo de Construção: {tempo_carga:.2f} segundos")
    print(f"[MÉTRICA] Pico de Memória RAM (Espaço): {memoria_mb:.2f} MB")

    # Variável para a memória do menu
    ultimo_isbn_manipulado = None
    isbn_conhecido_base = 9781141136599  # Um ISBN que sabemos que existe no CSV

    while True:
        print("\n" + "=" * 40)
        print("--- MENU DE EXPERIMENTOS ---")
        opcao = int(input('''
            1 - INSERIR ÚNICO REGISTRO (Automático)
            2 - INSERIR N REGISTROS (Lote Automático)
            3 - REMOVER ÚNICO REGISTRO
            4 - REMOVER INTERVALO
            5 - BUSCAR ÚNICO REGISTRO
            6 - BUSCAR INTERVALO
            0 - SAIR DO PROGRAMA\n
            OPÇÃO: '''))

        match opcao:
            case 1:
                print("\n--- INSERIR ÚNICO REGISTRO ---")
                isbn_novo = random.randint(9780000000000, 9789999999999)
                ultimo_isbn_manipulado = isbn_novo

                linha_nova = f'"{isbn_novo}","Livro Gerado Automaticamente","0000000000000","1","50.00","0.1","BRL","http://link",,,,,,,,'

                print(f"Gerando e inserindo o ISBN: {isbn_novo}")

                # ATENÇÃO: Recebe o tempo retornado pela função
                offset_gerado, tempo_exato = inserir_novo_registro(arvore, path, isbn_novo, linha_nova,
                                                                   tipo_arvore="B+")

                print(f"[MÉTRICA] Tempo de Inserção (APENAS NA ÁRVORE): {tempo_exato:.6f} segundos")

            case 2:
                print("\n--- INSERIR N REGISTROS ---")
                n = int(input("Quantos registros simulados deseja inserir? (ex: 1000): "))

                isbn_base = random.randint(9780000000000, 9789999999000)
                ultimo_isbn_manipulado = isbn_base

                print(f"Iniciando inserção de {n} registros a partir do ISBN {isbn_base}...")

                tempo_total_arvore = 0.0  # Variável para somar os tempos isolados

                for i in range(n):
                    isbn_atual = isbn_base + i
                    linha_mock = f'"{isbn_atual}","Livro Lote {i}","000","0","0","0","BRL","",,,,,,,,'

                    # Acumula apenas o tempo de manipulação da estrutura de dados
                    _, tempo_parcial = inserir_novo_registro(arvore, path, isbn_atual, linha_mock,
                                                             tipo_arvore="B+")
                    tempo_total_arvore += tempo_parcial

                print(
                    f"[MÉTRICA] Tempo Total de Inserção de {n} registros (APENAS NA ÁRVORE): {tempo_total_arvore:.6f} segundos")
                print(f"[MÉTRICA] Tempo Médio por registro na árvore: {tempo_total_arvore / n:.6f} segundos")

            case 3:
                print("\n--- REMOVER ÚNICO REGISTRO ---")
                sugestao = ultimo_isbn_manipulado if ultimo_isbn_manipulado else isbn_conhecido_base

                entrada = input(f"Digite o ISBN para deletar (Enter para usar {sugestao}): ")
                isbn_remover = int(entrada) if entrada.strip() else sugestao

                print(f"Tentando deletar o ISBN: {isbn_remover}")

                inicio_delete = time.perf_counter()

                offset_para_deletar = arvore.search_offset(isbn_remover)

                if offset_para_deletar is not None:
                    arvore.delete(isbn_remover, offset_para_deletar)
                    fim_delete = time.perf_counter()
                    print(f"[MÉTRICA] Tempo de Deleção Lógica: {fim_delete - inicio_delete:.6f} segundos")
                else:
                    print("Registro não encontrado para deleção.")

            case 4:
                print("\n--- REMOVER INTERVALO ---")
                sugestao_inicio = ultimo_isbn_manipulado if ultimo_isbn_manipulado else isbn_conhecido_base
                sugestao_fim = sugestao_inicio + 100

                entrada_inicio = input(f"ISBN inicial (Enter para usar {sugestao_inicio}): ")
                isbn_inicio = int(entrada_inicio) if entrada_inicio.strip() else sugestao_inicio

                entrada_fim = input(f"ISBN final (Enter para usar {sugestao_fim}): ")
                isbn_fim = int(entrada_fim) if entrada_fim.strip() else sugestao_fim

                print(f"Deletando intervalo de {isbn_inicio} a {isbn_fim}...")

                inicio_delete_range = time.perf_counter()
                for isbn in range(isbn_inicio, isbn_fim + 1):
                    # Mesmo processo: busca offset, depois deleta[cite: 4]
                    off = arvore.search_offset(isbn)
                    if off is not None:
                        arvore.delete(isbn, off)
                fim_delete_range = time.perf_counter()

                print(f"[MÉTRICA] Tempo de Deleção em Lote: {fim_delete_range - inicio_delete_range:.6f} segundos")

            case 5:
                print("\n--- BUSCAR ÚNICO REGISTRO ---")
                sugestao = ultimo_isbn_manipulado if ultimo_isbn_manipulado else isbn_conhecido_base

                entrada = input(f"Digite o ISBN para buscar (Enter para procurar {sugestao}): ")
                isbn_procurado = int(entrada) if entrada.strip() else sugestao

                print(f"Buscando: {isbn_procurado}")
                inicio_busca = time.perf_counter()

                # Na B+, usamos search_offset diretamente sem precisar passar a raiz[cite: 4]
                offset_encontrado = arvore.search_offset(isbn_procurado)

                if offset_encontrado is not None:
                    with open(path, "r", encoding="utf-8") as arquivo_csv:
                        registro = buscar_no_disco(arquivo_csv, offset_encontrado)

                    fim_busca = time.perf_counter()
                    print(f"[MÉTRICA] Tempo de Busca Pontual: {fim_busca - inicio_busca:.6f} segundos")
                    print(f"Registro encontrado:\n{registro.strip()}")
                else:
                    fim_busca = time.perf_counter()
                    print(f"[MÉTRICA] Tempo de Busca (Falha): {fim_busca - inicio_busca:.6f} segundos")
                    print("Registro não encontrado na estrutura da árvore.")

            case 6:
                print("\n--- BUSCAR INTERVALO (RANGE QUERY) ---")
                print("Para uma comparação justa, escolha um cenário padronizado:")
                print("1 - Cenário Curto  (Aprox. 1.000 números de amplitude)")
                print("2 - Cenário Médio  (Aprox. 1 milhão de números de amplitude)")
                print("3 - Cenário Massivo(Varredura de prefixos inteiros - Milhões de registros)")

                escolha_cenario = input("\nEscolha o cenário (1/2/3): ")

                if escolha_cenario == '1':
                    isbn_inicio = 9781141136000
                    isbn_fim = 9781141137000
                elif escolha_cenario == '2':
                    isbn_inicio = 9781141000000
                    isbn_fim = 9781142000000
                elif escolha_cenario == '3':
                    isbn_inicio = 9780862000000
                    isbn_fim = 9781862000000


                print(f"\nIniciando busca do intervalo: {isbn_inicio} ATÉ {isbn_fim}...")

                inicio_range = time.perf_counter()

                lista_offsets = arvore.range_search(isbn_inicio, isbn_fim)

                fim_range = time.perf_counter()

                print(f"[MÉTRICA] Tempo da Busca em Intervalo: {fim_range - inicio_range:.6f} segundos")
                print(f"Total de registros encontrados no intervalo: {len(lista_offsets)}")

                if lista_offsets:
                    mostrar = input("Deseja imprimir os 5 primeiros resultados? (s/n): ")
                    if mostrar.lower() == 's':
                        with open(path, "r", encoding="utf-8") as arquivo_csv:
                            for off in lista_offsets[:5]:
                                print(buscar_no_disco(arquivo_csv, off).strip())

            case 0:
                print("Encerrando a sessão de testes...")
                break

            case _:
                print("Opção inválida.")