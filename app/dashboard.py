import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime
import os
import time

#Configuração da página
st.set_page_config(
    page_title="Plataforma de Gestão de Qualidade - E-commerce",
    page_icon="📊",
    layout="wide"
)

#Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'database', 'qualidade.duckdb')

@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH)

conn = get_connection()

#Título Principal
st.title("📊 Plataforma de Gestão de Qualidade | E-commerce")
st.markdown("Monitoramento de devoluções, ofensores e indicadores operacionais.")

#Sidebar de Filtros Globais
st.sidebar.header("🔍 Filtros Globais")
try:
    responsaveis = ["TODOS"] + [r[0] for r in conn.execute("SELECT DISTINCT RESPONSÁVEL FROM fact_devolucoes ORDER BY 1").fetchall()]
    resp_selecionado = st.sidebar.selectbox("Responsável", responsaveis)
except Exception:
    resp_selecionado = "TODOS"

#Indicador de Última Atualização
st.sidebar.markdown("---")
try:
    data_modificacao = os.path.getmtime(DB_PATH)
    ultima_atualizacao = datetime.fromtimestamp(data_modificacao).strftime('%d/%m/%Y às %H:%M')
    st.sidebar.caption("🕒 **Última atualização dos dados:**")
    st.sidebar.caption(f"{ultima_atualizacao}")
except Exception:
    pass

#Construção da Query Base com Filtro
query_base = "SELECT * FROM fact_devolucoes WHERE 1=1"
if resp_selecionado != "TODOS":
    query_base += f" AND RESPONSÁVEL = '{resp_selecionado}'"

df_view = conn.execute(query_base).df()

if df_view.empty:
    st.warning("Nenhum dado encontrado para o filtro selecionado.")
else:
    
    #KPIs Executivos
    total_ocorrencias = len(df_view['NFD'].unique())
    total_itens = df_view['QTD'].sum()
    valor_total = df_view['DEVOLUÇÃO'].sum()
    ticket_medio = valor_total / total_ocorrencias if total_ocorrencias > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Ocorrências (NFDs)", f"{total_ocorrencias:,.0f}")
    col2.metric("💰 Valor Total Devolvido", f"R$ {valor_total:,.2f}")
    col3.metric("📋 Itens Devolvidos", f"{total_itens:,.0f}")
    col4.metric("📊 Ticket Médio da Devolução", f"R$ {ticket_medio:,.2f}")

    st.markdown("---")

    #Visão Gráfica: Top Ofensores por Motivo e Responsável
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("⚠️ Top Motivos de Devolução (Valor R$)")
        df_motivo = df_view.groupby('Motivo')['DEVOLUÇÃO'].sum().reset_index().sort_values(by='DEVOLUÇÃO', ascending=False).head(10)
        fig_motivo = px.bar(df_motivo, x='DEVOLUÇÃO', y='Motivo', orientation='h', text_auto='.2s', color='DEVOLUÇÃO', color_continuous_scale='Reds')
        fig_motivo.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_motivo, use_container_width=True)

    with col_r:
        st.subheader("👥 Impacto por Responsável (%)")
        df_resp = df_view.groupby('RESPONSÁVEL')['DEVOLUÇÃO'].sum().reset_index()
        fig_resp = px.pie(df_resp, names='RESPONSÁVEL', values='DEVOLUÇÃO', hole=0.4)
        st.plotly_chart(fig_resp, use_container_width=True)

    st.markdown("---")

    #Análise por Linha de Produto e Fabricante
    col_l2, col_r2 = st.columns(2)
    
    with col_l2:
        st.subheader("🏭 Devoluções por Linha de Produto")
        df_linha = df_view.groupby('LINHA')['DEVOLUÇÃO'].sum().reset_index().sort_values(by='DEVOLUÇÃO', ascending=False)
        fig_linha = px.bar(df_linha, x='LINHA', y='DEVOLUÇÃO', text_auto='.2s', color='DEVOLUÇÃO', color_continuous_scale='Blues')
        st.plotly_chart(fig_linha, use_container_width=True)

    with col_r2:
        st.subheader("🏢 Top Fabricantes Ofensores")
        df_fab = df_view.groupby('FABRICANTE')['DEVOLUÇÃO'].sum().reset_index().sort_values(by='DEVOLUÇÃO', ascending=False).head(10)
        fig_fab = px.bar(df_fab, x='DEVOLUÇÃO', y='FABRICANTE', orientation='h', text_auto='.2s', color='DEVOLUÇÃO', color_continuous_scale='Purples')
        fig_fab.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_fab, use_container_width=True)

    st.markdown("---")

    #Tabela de Detalhamento / Dados Brutos Tratados
    st.subheader("🔍 Detalhamento Analítico das Ocorrências")
    st.dataframe(df_view[['DT_DEV', 'NFD', 'RESPONSÁVEL', 'Motivo', 'SubMotivo', 'FABRICANTE', 'DESCRIÇÃO', 'DEVOLUÇÃO']], use_container_width=True)
    
    st.markdown("---")
    st.header("🎯 Inteligência e Priorização")

    col_matriz, col_pareto = st.columns(2)

    with col_matriz:
        st.subheader("📍 Matriz Frequência x Impacto (Por SubMotivo)")
        df_matriz = df_view.groupby('SubMotivo').agg(
            Frequencia=('NFD', 'nunique'),
            Impacto=('DEVOLUÇÃO', 'sum')
        ).reset_index()
        
        df_matriz = df_matriz[df_matriz['SubMotivo'] != 'NÃO CLASSIFICADO']

        if not df_matriz.empty:
            media_freq = df_matriz['Frequencia'].median()
            media_impacto = df_matriz['Impacto'].median()

            fig_matriz = px.scatter(
                df_matriz, x='Frequencia', y='Impacto', text='SubMotivo',
                size='Impacto', color='Impacto', color_continuous_scale='Turbo',
                title="Quadrantes de Prioridade"
            )
            fig_matriz.add_hline(y=media_impacto, line_dash="dash", line_color="red")
            fig_matriz.add_vline(x=media_freq, line_dash="dash", line_color="red")
            fig_matriz.update_traces(textposition='top center')
            st.plotly_chart(fig_matriz, use_container_width=True)
            st.caption("Eixo superior direito = CRÍTICO (Alta frequência e Alto impacto).")

    with col_pareto:
        st.subheader("📈 Curva de Pareto (Ofensores)")
        dimensao_pareto = st.selectbox("Analisar Pareto por:", ['FABRICANTE', 'Transportadora', 'Falha'])
        
        df_pareto = df_view.groupby(dimensao_pareto)['DEVOLUÇÃO'].sum().reset_index()
        df_pareto = df_pareto.sort_values(by='DEVOLUÇÃO', ascending=False)
        df_pareto['% Acumulado'] = (df_pareto['DEVOLUÇÃO'].cumsum() / df_pareto['DEVOLUÇÃO'].sum()) * 100
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(go.Bar(x=df_pareto[dimensao_pareto], y=df_pareto['DEVOLUÇÃO'], name="Impacto R$"), secondary_y=False)
        fig_pareto.add_trace(go.Scatter(x=df_pareto[dimensao_pareto], y=df_pareto['% Acumulado'], name="% Acumulado", mode="lines+markers", line=dict(color="red")), secondary_y=True)
        
        fig_pareto.update_layout(showlegend=False)
        fig_pareto.update_yaxes(title_text="Impacto Financeiro (R$)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="% Acumulado", range=[0, 105], secondary_y=True)
        st.plotly_chart(fig_pareto, use_container_width=True)

    st.markdown("---")
    
    #Módulo de Qualidade dos Dados
    st.header("🚨 Saúde e Qualidade dos Dados")
    col_dq1, col_dq2 = st.columns(2)
    
    with col_dq1:
        st.error("Registros Não Classificados")
        nao_classificados = df_view[df_view['Motivo'] == 'NÃO CLASSIFICADO']
        qtd_nc = len(nao_classificados)
        valor_nc = nao_classificados['DEVOLUÇÃO'].sum()
        st.metric("Ocorrências sem Classificação", f"{qtd_nc} casos", f"R$ {valor_nc:,.2f} impactados", delta_color="inverse")
        
    with col_dq2:
        st.warning("Inconsistência de Chave (NFD)")
        inconsistencias = df_view.groupby('NFD').agg(Qtd_Responsaveis=('RESPONSÁVEL', 'nunique')).reset_index()
        nfd_problematicas = inconsistencias[inconsistencias['Qtd_Responsaveis'] > 1]
        st.metric("NFDs com Conflito de Informação", f"{len(nfd_problematicas)} identificadas")
        if not nfd_problematicas.empty:
            st.write("Exemplo de NFD conflitante:", nfd_problematicas['NFD'].iloc[0])
            
    
    # MÓDULO DE PLANOS DE AÇÃO
    
    st.markdown("---")
    st.header("📋 Planos de Ação e Gestão Corretiva")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_planos_acao (
            id_acao INTEGER PRIMARY KEY,
            data_criacao DATE,
            problema VARCHAR,
            responsavel VARCHAR,
            acao_corretiva VARCHAR,
            prazo DATE,
            prioridade VARCHAR,
            status VARCHAR
        );
    """)

    tab_lista, tab_novo = st.tabs(["📂 Acompanhar Planos", "➕ Nova Ação Corretiva"])

    with tab_lista:
        df_acoes = conn.execute("SELECT * FROM fact_planos_acao ORDER BY id_acao DESC").df()
        
        if df_acoes.empty:
            st.info("Nenhum plano de ação cadastrado no momento. Utilize a aba ao lado para criar o primeiro.")
        else:
            #Tratamento de Datas e Cálculo de SLA / Dias em Aberto
            df_acoes['prazo_dt'] = pd.to_datetime(df_acoes['prazo']).dt.date
            df_acoes['data_criacao_dt'] = pd.to_datetime(df_acoes['data_criacao']).dt.date
            
            df_acoes['Dias Restantes'] = df_acoes['prazo_dt'].apply(lambda x: (x - date.today()).days)
            
            #(Idade da Ação)
            def get_dias_aberto(row):
                if row['status'] == 'Concluído':
                    return "Finalizado"
                return f"{(date.today() - row['data_criacao_dt']).days} dias"
            
            df_acoes['Dias em Aberto'] = df_acoes.apply(get_dias_aberto, axis=1)
            
            def get_status_sla(row):
                if row['status'] == 'Concluído':
                    return '✅ Concluído'
                elif row['Dias Restantes'] < 0:
                    return '🔴 Atrasado'
                elif row['Dias Restantes'] <= 3:
                    return '🟡 Atenção'
                else:
                    return '🟢 No Prazo'

            df_acoes['SLA'] = df_acoes.apply(get_status_sla, axis=1)
            
            #Formatando para exibição visual DD/MM/YYYY
            df_acoes['Criada em'] = pd.to_datetime(df_acoes['data_criacao']).dt.strftime('%d/%m/%Y')
            df_acoes['Prazo'] = pd.to_datetime(df_acoes['prazo']).dt.strftime('%d/%m/%Y')

            
            # NOVO: GRÁFICOS ANALÍTICOS DE PLANOS DE AÇÃO
            
            st.markdown("### 📊 Visão Geral da Gestão Corretiva")
            col_ga1, col_ga2, col_ga3 = st.columns(3)
            
            with col_ga1:
                #Gráfico 1 Distribuição por Status
                df_status = df_acoes['status'].value_counts().reset_index()
                df_status.columns = ['Status', 'Quantidade']
                fig_status = px.pie(df_status, names='Status', values='Quantidade', hole=0.4, title="Ações por Status")
                st.plotly_chart(fig_status, use_container_width=True)

            with col_ga2:
                #Gráfico 2 Carga por Responsável
                df_resp_acao = df_acoes['responsavel'].value_counts().reset_index()
                df_resp_acao.columns = ['Responsável', 'Quantidade']
                fig_resp = px.bar(df_resp_acao, x='Quantidade', y='Responsável', orientation='h', title="Carga por Responsável", text_auto=True)
                fig_resp.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_resp, use_container_width=True)
                
            with col_ga3:
                #Gráfico 3 Termômetro de SLA
                df_sla = df_acoes['SLA'].value_counts().reset_index()
                df_sla.columns = ['SLA', 'Quantidade']
                #Mapeamento fixo de cores para padronizar a urgência
                cores_sla = {
                    '✅ Concluído': '#28a745', # Verde sucesso
                    '🟢 No Prazo': '#17a2b8',  # Azul/Verde seguro
                    '🟡 Atenção': '#ffc107',   # Amarelo alerta
                    '🔴 Atrasado': '#dc3545'   # Vermelho perigo
                }
                fig_sla = px.pie(df_sla, names='SLA', values='Quantidade', hole=0.4, title="Termômetro de Prazos (SLA)", color='SLA', color_discrete_map=cores_sla)
                st.plotly_chart(fig_sla, use_container_width=True)
            
            st.markdown("---")
            # ==========================================
            
            st.markdown("### 📋 Listagem de Ações")
            colunas_exibicao = ['id_acao', 'Criada em', 'Dias em Aberto', 'problema', 'responsavel', 'acao_corretiva', 'Prazo', 'prioridade', 'status', 'SLA']
            st.dataframe(df_acoes[colunas_exibicao], use_container_width=True, hide_index=True)

            #SUB-MÓDULO EDITAR / EXCLUIR AÇÕES
            st.markdown("### ⚙️ Gerenciar Ações")
            with st.expander("Clique aqui para Atualizar Status ou Excluir uma Ação"):
                lista_ids = df_acoes['id_acao'].tolist()
                acao_selecionada = st.selectbox("Selecione o ID da Ação:", lista_ids)
                
                if acao_selecionada is not None:
                    #Carrega os dados da ação selecionada
                    acao_data = df_acoes[df_acoes['id_acao'] == acao_selecionada].iloc[0]
                    
                    col_ed1, col_ed2, col_ed3 = st.columns(3)
                    with col_ed1:
                        lista_status = ["Aberto", "Em Andamento", "Aguardando Evidência", "Concluído"]
                        idx_status = lista_status.index(acao_data['status']) if acao_data['status'] in lista_status else 0
                        novo_status = st.selectbox("Atualizar Status", lista_status, index=idx_status)
                    with col_ed2:
                        novo_prazo = st.date_input("Prorrogar/Ajustar Prazo", value=acao_data['prazo_dt'], format="DD/MM/YYYY")
                    with col_ed3:
                        st.write("") # Espaçamento
                        st.write("")
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾 Salvar", use_container_width=True):
                                conn.execute(f"UPDATE fact_planos_acao SET status = '{novo_status}', prazo = '{novo_prazo}' WHERE id_acao = {acao_selecionada}")
                                st.toast("✅ Ação atualizada com sucesso!", icon="✅")
                                time.sleep(1) 
                                st.rerun()
                        with col_btn2:
                            if st.button("🗑️ Excluir", type="primary", use_container_width=True):
                                conn.execute(f"DELETE FROM fact_planos_acao WHERE id_acao = {acao_selecionada}")
                                st.toast("🗑️ Ação excluída permanentemente!", icon="🚨")
                                time.sleep(1)
                                st.rerun()

    with tab_novo:
        st.subheader("Registrar Nova Ação Corretiva")
        # Add limpeza com clear_on_submit=True
        with st.form("form_plano_acao", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                problema_rel = st.text_input("Problema / Ofensor Identificado")
                responsavel_acao = st.text_input("Responsável pela Ação (Ex: João - Logística)")
                prioridade_acao = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            with col_f2:
                prazo_acao = st.date_input("Prazo Limite (SLA)", format="DD/MM/YYYY")
                status_acao = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Evidência", "Concluído"])
            
            acao_corretiva = st.text_area("Descrição da Ação Corretiva / Preventiva")
            
            submitted = st.form_submit_button("Salvar Plano de Ação")
            if submitted:
                if problema_rel and responsavel_acao and acao_corretiva:
                    max_id_query = conn.execute("SELECT COALESCE(MAX(id_acao), 0) FROM fact_planos_acao").fetchone()[0]
                    novo_id = max_id_query + 1
                    hoje = date.today().isoformat()
                    
                    conn.execute(f"""
                        INSERT INTO fact_planos_acao VALUES (
                            {novo_id}, '{hoje}', '{problema_rel}', '{responsavel_acao}', 
                            '{acao_corretiva}', '{prazo_acao}', '{prioridade_acao}', '{status_acao}'
                        )
                    """)
                    
                    #Notificação flutuante temporária
                    st.toast("Ação registrada com sucesso!", icon="✅")
                    time.sleep(1.5) 
                    st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")