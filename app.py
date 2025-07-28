import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io

# Configurando a página
st.set_page_config(
    page_title="Analisador de Datasets Pro",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Funções Auxiliares ---

# << CORREÇÃO 2: Lógica de conversão de data mais inteligente e menos agressiva >>
@st.cache_data
def load_dados(arquivo, separador, aba):
    """
    Função para carregar dados de um arquivo Excel ou CSV, tentando converter datas de forma inteligente.
    """
    try:
        if arquivo.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(arquivo, sheet_name=aba)
        elif arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo, sep=separador)
        else:
            st.error("Formato de arquivo não suportado. Use .xlsx ou .csv.")
            return None

        # Tenta converter colunas para data de forma mais segura
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    # Tenta a conversão em uma cópia temporária
                    temp_col = pd.to_datetime(df[col], errors='coerce')
                    # Só efetiva a conversão se mais de 50% dos valores não-nulos foram convertidos com sucesso
                    # Isso evita converter colunas que são primariamente texto.
                    if temp_col.notna().sum() / df[col].notna().sum() > 0.5:
                        
                        df[col] = temp_col.dt.normalize()
                except Exception:
                    # Se qualquer outro erro ocorrer, apenas ignora a conversão para esta coluna
                    pass
        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return None


def capturar_info(df):
    buffer = io.StringIO()
    df.info(buf=buffer)
    return buffer.getvalue()

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Barra Lateral (Sidebar) ---
st.sidebar.title("Configurações")
st.sidebar.write("Faça o upload do seu dataset e ajuste os parâmetros abaixo.")

arquivo = st.sidebar.file_uploader("Carregar arquivo (.csv ou .xlsx)", type=["xlsx", "csv", "xls"])

df = None
if arquivo:
    st.sidebar.header("Parâmetros de Importação")
    aba = None
    separador = ","

    if arquivo.name.endswith(('.xls', '.xlsx')):
        try:
            excel_file = pd.ExcelFile(arquivo)
            abas_disponiveis = excel_file.sheet_names
            aba = st.sidebar.selectbox("Selecione a aba (para Excel)", options=abas_disponiveis)
        except Exception as e:
            st.sidebar.error(f"Não foi possível ler as abas: {e}")
    else: # .csv
        separador = st.sidebar.selectbox("Selecione o separador (para CSV)", options=[",", ";", "\t", "|"])

    with st.spinner("Carregando e processando os dados..."):
        df = load_dados(arquivo, separador, aba)
else:
    st.sidebar.info("Aguardando o upload de um arquivo.")

# --- Painel Principal ---
st.title("✨ Analisador de Datasets Pro")
st.markdown("Uma ferramenta aprimorada para análise exploratória de dados. Por **Streamy**.")

if df is not None:
    st.success(f"Dataset **'{arquivo.name}'** carregado com **{df.shape[0]} linhas** e **{df.shape[1]} colunas**.")

    colunas_numericas = df.select_dtypes(include=['number']).columns.tolist()
    # << CORREÇÃO 2: A detecção de data agora funciona corretamente após a carga segura >>
    colunas_datetime = df.select_dtypes(include=['datetime64[ns]', 'datetime', 'date']).columns.tolist()
    colunas_categoricas = df.select_dtypes(exclude=['number', 'datetime64[ns]', 'datetime', 'date']).columns.tolist()

    tab_overview, tab_missing, tab_univariate, tab_bivariate, tab_correlation, tab_download = st.tabs([
        " Visão Geral ",
        " Dados Faltantes ",
        " Análise Univariada ",
        " Análise Bivariada ",
        " Correlação ",
        " 📥 Download "
    ])

    with tab_overview:
        st.header("Visão Geral do Dataset")
        st.subheader("Amostra dos Dados")
        st.dataframe(df.head())

        st.subheader("Informações Gerais")
        st.text(f"Dimensões: {df.shape[0]} linhas e {df.shape[1]} colunas.")
        st.write(f"- Numéricas: {len(colunas_numericas)} | Categóricas: {len(colunas_categoricas)} | Datas: {len(colunas_datetime)}")

        st.subheader("Detalhes das Colunas (.info)")
        st.text(capturar_info(df))

        st.subheader("Estatísticas Descritivas (.describe)")
        # << CORREÇÃO 1: Removido o argumento 'datetime_is_numeric=True' para compatibilidade >>
        st.dataframe(df.describe(include='all'))

    with tab_missing:
        st.header("Análise de Valores Nulos (NaN)")
        dados_nulos = df.isnull().sum().to_frame('Contagem')
        dados_nulos['Percentual (%)'] = (df.isnull().sum() / len(df) * 100).round(2)
        st.dataframe(dados_nulos[dados_nulos['Contagem'] > 0])
        if df.isnull().sum().sum() > 0:
            st.subheader("Heatmap de Valores Nulos")
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.heatmap(df.isnull(), cbar=False, yticklabels=False, cmap='viridis', ax=ax)
            st.pyplot(fig)
        else:
            st.success("Ótima notícia! Não há valores nulos no seu dataset.")

    with tab_univariate:
        st.header("Análise de Coluna Individual (Univariada)")
        coluna_selecionada = st.selectbox("Selecione uma coluna para analisar:", df.columns)

        if coluna_selecionada:
            st.subheader(f"Análise da Coluna: '{coluna_selecionada}'")

            if coluna_selecionada in colunas_numericas:
                st.write("Esta é uma coluna **numérica**.")
                fig_hist, ax_hist = plt.subplots(1, 2, figsize=(15, 5))
                sns.histplot(df[coluna_selecionada], kde=True, ax=ax_hist[0])
                ax_hist[0].set_title(f'Histograma de {coluna_selecionada}')
                sns.boxplot(x=df[coluna_selecionada], ax=ax_hist[1])
                ax_hist[1].set_title(f'Box Plot de {coluna_selecionada}')
                st.pyplot(fig_hist)

            elif coluna_selecionada in colunas_datetime:
                st.write("Esta é uma coluna de **data**.")
                contagem_data = df[coluna_selecionada].value_counts().sort_index()
                st.line_chart(contagem_data)
                st.write("O gráfico acima mostra a contagem de ocorrências por data.")

            else: # Categórica
                st.write("Esta é uma coluna **categórica/objeto**.")
                contagem = df[coluna_selecionada].value_counts()

                if len(contagem) > 20:
                    ver_todos = st.checkbox(f"A coluna tem {len(contagem)} categorias. Mostrar todas?", value=False)
                    if not ver_todos:
                        st.info("Mostrando as 20 categorias mais frequentes.")
                        contagem = contagem.head(20)

                fig_bar, ax_bar = plt.subplots()
                sns.barplot(y=contagem.index.astype(str), x=contagem.values, orient='h', ax=ax_bar)
                ax_bar.set_title(f'Frequência em {coluna_selecionada}')
                st.pyplot(fig_bar)

    with tab_bivariate:
        st.header("Análise de Relação entre Duas Colunas (Bivariada)")
        if len(colunas_numericas) < 2:
            st.warning("São necessárias pelo menos duas colunas numéricas para esta análise.")
        else:
            st.subheader("Gráfico de Dispersão (Scatter Plot)")
            col1, col2 = st.columns(2)
            eixo_x = col1.selectbox("Eixo X", colunas_numericas, key='x_scatter')
            eixo_y = col2.selectbox("Eixo Y", colunas_numericas, index=min(1, len(colunas_numericas)-1), key='y_scatter')

            fig, ax = plt.subplots(figsize=(10, 6))
            sns.scatterplot(data=df, x=eixo_x, y=eixo_y, ax=ax)
            st.pyplot(fig)

    with tab_correlation:
        st.header("Análise de Correlação entre Colunas Numéricas")
        if len(colunas_numericas) < 2:
            st.warning("São necessárias pelo menos duas colunas numéricas para a correlação.")
        else:
            paleta_cores = st.selectbox("Escolha a paleta de cores:", ["coolwarm", "viridis", "plasma", "inferno", "magma", "cividis"])
            st.subheader(f"Heatmap de Correlação (Paleta: {paleta_cores})")

            matriz_corr = df[colunas_numericas].corr()
            fig, ax = plt.subplots(figsize=(14, 10))
            sns.heatmap(matriz_corr, annot=True, fmt=".2f", cmap=paleta_cores, linewidths=.5, ax=ax)
            st.pyplot(fig)

    with tab_download:
        st.header("Download do Dataset")
        st.write("Faça o download dos dados atualmente carregados como um arquivo CSV.")
        csv = convert_df_to_csv(df)
        st.download_button(
            label="📥 Baixar dados como CSV",
            data=csv,
            file_name=f'dataset_analisado.csv',
            mime='text/csv',
        )

else:
    st.info("Para começar, faça o upload de um dataset usando o painel à esquerda.")
    st.image("https://streamlit.io/images/brand/share-social-twitter.png", caption="Streamlit: A forma mais rápida de criar apps de dados.", use_container_width=True)