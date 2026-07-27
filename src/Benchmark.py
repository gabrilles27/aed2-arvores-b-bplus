import BTree
import BplusTree
import time
import tracemalloc
import random
import shutil
import os
import gc
import csv

# Configurações do Experimento
ARQUIVO_ORIGINAL = 'open4goods-isbn-dataset.csv'
ARQUIVO_TEMP = 'temp_dataset.csv'
REPETICOES = 10
GRAUS_PARA_TESTAR = [10, 50, 100, 200]
QTD_INSERCOES_TESTE = 1000

# Fixando a semente para garantir chaves idênticas em todos os testes
random.seed(42)
CHAVES_TESTE = [random.randint(9780000000000, 9789999999999) for _ in range(QTD_INSERCOES_TESTE)]

def executar_bateria():
    resultados = []
    
    for grau_maximo in GRAUS_PARA_TESTAR:
        # Ajuste matemático para as árvores terem capacidades comparáveis
        grau_t_btree = grau_maximo // 2 
        order_bplus = grau_maximo
        
        for tipo_arvore in ["B", "B+"]:
            for rep in range(1, REPETICOES + 1):
                print(f"Executando {tipo_arvore} | Grau Máximo: {grau_maximo} | Repetição: {rep}/{REPETICOES}")
                
                # 1. Isolar o ambiente (Cópia limpa do CSV)
                shutil.copyfile(ARQUIVO_ORIGINAL, ARQUIVO_TEMP)
                
                # 2. Medir Construção (Tempo e Memória)
                gc.collect()
                tracemalloc.start()
                t0 = time.perf_counter()
                
                if tipo_arvore == "B":
                    arvore = BTree.BTree(grau_t_btree)
                    with open(ARQUIVO_TEMP, 'r', encoding='utf-8') as f:
                        f.readline()
                        for linha in f:
                            id_str = linha.split(',', 1)[0].replace('"', '')
                            if id_str.isdigit():
                                arvore.insert((int(id_str), 0)) # Offset dummy para o teste de ram
                else:
                    arvore = BplusTree.BplusTree(order_bplus)
                    with open(ARQUIVO_TEMP, 'r', encoding='utf-8') as f:
                        f.readline()
                        for linha in f:
                            id_str = linha.split(',', 1)[0].replace('"', '')
                            if id_str.isdigit():
                                arvore.insert(int(id_str), 0)

                t1 = time.perf_counter()
                _, pico_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                tempo_construcao = t1 - t0
                mem_construcao_mb = pico_mem / (1024 * 1024)
                
                # 3. Medir Inserção em Lote (Apenas na memória, sem I/O para isolar a estrutura)
                t_insert_inicio = time.perf_counter()
                for chave in CHAVES_TESTE:
                    if tipo_arvore == "B":
                        arvore.insert((chave, 999))
                    else:
                        arvore.insert(chave, 999)
                tempo_insercao = time.perf_counter() - t_insert_inicio
                
                # 4. Medir Busca em Lote
                t_busca_inicio = time.perf_counter()
                for chave in CHAVES_TESTE:
                    if tipo_arvore == "B":
                        arvore.search(arvore.root, chave)
                    else:
                        arvore.search_offset(chave)
                tempo_busca = time.perf_counter() - t_busca_inicio

                # 5. Medir Deleção em Lote (Deletando as chaves recém-inseridas)
                t_delete_inicio = time.perf_counter()
                for chave in CHAVES_TESTE:
                    if tipo_arvore == "B":
                        arvore.delete(arvore.root, (chave,))
                    else:
                        # B+ precisa da chave e do offset inserido para o match perfeito na deleção
                        arvore.delete(chave, 999)
                tempo_delecao = time.perf_counter() - t_delete_inicio
                
                # Guardar resultados
                resultados.append({
                    "Repeticao": rep,
                    "Tipo": tipo_arvore,
                    "Grau_Maximo": grau_maximo,
                    "Tempo_Construcao_s": tempo_construcao,
                    "Memoria_Pico_MB": mem_construcao_mb,
                    "Tempo_Insercao_1k_s": tempo_insercao,
                    "Tempo_Busca_1k_s": tempo_busca,
                    "Tempo_Delecao_1k_s": tempo_delecao
                })
                
                # Limpeza
                del arvore
                os.remove(ARQUIVO_TEMP)
                
    return resultados

if __name__ == "__main__":
    dados = executar_bateria()
    
    # Exportar para CSV para análise em ferramentas de dados
    with open('resultados_benchmark.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=dados[0].keys())
        writer.writeheader()
        writer.writerows(dados)
        
    print("\nBenchmark concluído! Resultados salvos em 'resultados_benchmark.csv'.")