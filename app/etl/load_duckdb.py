import duckdb
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'database', 'qualidade.duckdb')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'devolucoes')

def carregar_duckdb():
    print("Conectando ao DuckDB...")
    conn = duckdb.connect(DB_PATH)
    
    #Busca o arquivo parquet processado
    arquivos = [f for f in os.listdir(PROCESSED_DIR) if f.endswith('.parquet')]
    if not arquivos:
        print("Nenhum arquivo parquet encontrado.")
        return
    
    parquet_path = os.path.join(PROCESSED_DIR, arquivos[0])
    
    #Cria ou substitui a tabela fato no DuckDB usando o Parquet diretamente
    conn.execute(f"""
        CREATE OR REPLACE TABLE fact_devolucoes AS 
        SELECT * FROM read_parquet('{parquet_path}');
    """)
    
    #Validação rápida da carga
    total_linhas = conn.execute("SELECT COUNT(*) FROM fact_devolucoes").fetchone()[0]
    total_valor = conn.execute("SELECT SUM(DEVOLUÇÃO) FROM fact_devolucoes").fetchone()[0]
    
    print(f"Sucesso! Tabela 'fact_devolucoes' criada no DuckDB.")
    print(f"Total de registros na tabela: {total_linhas}")
    print(f"Valor total de devoluções: R$ {total_valor:,.2f}")
    
    conn.close()

if __name__ == "__main__":
    carregar_duckdb()