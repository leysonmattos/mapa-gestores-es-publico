"""Versão pública do Mapa de Gestores CREF22/ES.

Mostra apenas a divisão de municípios por gestor, os dados oficiais do IBGE e o
contato de quem responde por cada região. Nada de PF/PJ: os dados de academias e
profissionais ficam restritos à versão completa (app.py).

A omissão não é só visual — ESMapGenerator(modo_publico=True) remove as
propriedades de PF/PJ do GeoJSON antes de embarcá-lo na página, de modo que os
valores não aparecem nem no código-fonte.
"""

import streamlit as st
from streamlit_folium import st_folium

from src.base_municipios import BaseMunicipios
from src.map_generator import ESMapGenerator
from src.ui_comum import (GESTOR_INFO, CSS_BASE, html_block, hex_rgba,
                          card_municipio)

st.set_page_config(
    page_title="Mapa de Gestores - CREF22/ES",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CSS_BASE, unsafe_allow_html=True)

loader = BaseMunicipios()


@st.cache_data(show_spinner="Carregando dados...")
def carregar_dados():
    """Base pública: IBGE + gestor, sem tocar no Google Sheets.

    A planilha só contém PF/PJ, que esta versão não exibe — não baixá-la evita
    trazer esses números para a memória e dispensa a dependência de rede.
    """
    return loader.carregar_base_publica()


# ==================== BARRA LATERAL ====================
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/4/43/Bandeira_do_Esp%C3%ADrito_Santo.svg",
        width=60
    )
    st.title("Mapa de Gestores - CREF22/ES")
    st.caption("Espírito Santo • 78 Municípios")

    st.markdown("---")
    st.subheader("👥 Gestores por Região")

    for chave, g in GESTOR_INFO.items():
        st.markdown(html_block(f"""
        <div style="background: {hex_rgba(g['cor'], 0.20)}; border: 1.5px solid {hex_rgba(g['cor'], 0.75)}; border-radius: 10px; padding: 0.7rem; margin-bottom: 0.6rem;">
            <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 0.2rem;">
                <span style="display: inline-block; width: 13px; height: 13px; background: {g['cor']}; border-radius: 3px; border: 1px solid {hex_rgba(g['cor'], 0.9)};"></span>
                <span style="font-weight: 800; font-size: 0.92rem; color: inherit;">{g['nome']}</span>
            </div>
            <div style="font-size: 0.74rem; color: inherit; opacity: 0.75; margin-bottom: 0.35rem;">🗂️ {g['regiao']}</div>
            <a href="{g['wa_link']}" target="_blank" style="display: flex; align-items: center; justify-content: center; gap: 6px; background-color: #25D366; color: #ffffff !important; text-decoration: none; padding: 0.32rem 0.6rem; border-radius: 6px; font-size: 0.76rem; font-weight: 700;">
                💬 {g['fone']}
            </a>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Clique em um município no mapa para ver o gestor responsável e os dados oficiais do IBGE.")

# ==================== DADOS ====================
df = carregar_dados()
geojson = loader.get_enriched_geojson(df)

# ==================== CABEÇALHO ====================
st.markdown('<div class="main-title">🗺️ Mapa de Gestores - CREF22/ES</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Encontre o <b>gestor responsável</b> pelo seu município e fale direto com ele</div>',
    unsafe_allow_html=True
)

col_mapa, col_detalhes = st.columns([3.1, 1.4])

with col_mapa:
    mapa = ESMapGenerator(geojson, df).create_map(modo_publico=True)
    st_folium(
        mapa,
        width=None,
        height=680,
        use_container_width=True,
        returned_objects=[],
        key="mapa_publico"
    )

with col_detalhes:
    st.subheader("🔍 Detalhes do Município")

    municipios = sorted(df['Municipio'].tolist())
    escolha = st.selectbox(
        "Selecione ou busque um município:",
        options=municipios,
        index=0,
        help="Escolha um município para ver o gestor responsável e os dados oficiais do IBGE."
    )

    linha = df[df['Municipio'] == escolha].iloc[0]
    st.markdown(html_block(card_municipio(linha, incluir_pf_pj=False)), unsafe_allow_html=True)
