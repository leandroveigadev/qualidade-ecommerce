import pandas as pd
import yaml
import os

#Caminhos absolutos/relativos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, 'data', 'config', 'datasets.yaml')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'devolucoes')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'devolucoes')

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def processar_devolucoes():
    print("Iniciando ingestão de dados...")
    config = load_config()['datasets']['devolucoes']
    
    #Busca o arquivo de devoluções na pasta raw
    arquivos = [f for f in os.listdir(RAW_DIR) if f.endswith(('.xls', '.xlsx'))]
    if not arquivos:
        print("Nenhum arquivo encontrado em data/raw/devolucoes/")
        return
    
    arquivo_alvo = arquivos[0]
    caminho_arquivo = os.path.join(RAW_DIR, arquivo_alvo)
    print(f"Lendo arquivo: {arquivo_alvo}")
    
    #Leitura do Excel
    df = pd.read_excel(caminho_arquivo)
    total_linhas_originais = len(df)
    
    #Validação Estrutural
    colunas_faltantes = [col for col in config['colunas_obrigatorias'] if col not in df.columns]
    if colunas_faltantes:
        raise ValueError(f"Arquivo inválido. Faltam as colunas: {colunas_faltantes}")
    
    #Remoção da "Linha Técnica" (Onde NFD é nulo e é um agregador)
    df_clean = df.dropna(subset=['NFD']).copy()
    linhas_removidas = total_linhas_originais - len(df_clean)
    
    #Tratamento de Qualidade de Dados (Preenchendo nulos das classificações)
    for col in config['colunas_classificacao']:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna("NÃO CLASSIFICADO")
            
    #Salvando em Parquet para Alta Performance
    arquivo_saida = os.path.join(PROCESSED_DIR, arquivo_alvo.replace('.xls', '.parquet').replace('.xlsx', '.parquet'))
    df_clean.to_parquet(arquivo_saida, engine='pyarrow')
    
    print(f"Sucesso! {len(df_clean)} registros processados.")
    print(f"Linhas técnicas ignoradas: {linhas_removidas}")
    print(f"Arquivo salvo em: {arquivo_saida}")

if __name__ == "__main__":
    processar_devolucoes()