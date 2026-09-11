"""Interface compartilhada entre a versão completa (app.py) e a pública
(app_publico.py).

Mantém um ponto único de verdade para os contatos dos gestores e para o card de
detalhes do município: se os telefones ficassem duplicados nos dois aplicativos,
uma atualização em um deles passaria despercebida no outro.
"""

# Mapeamento Oficial de Contatos e Cores dos Gestores
GESTOR_INFO = {
    'BRUNA': {
        'nome': 'Bruna Borini',
        'fone': '(27) 99987-0011',
        'wa_link': 'https://wa.me/5527999870011',
        'regiao': 'Norte / Noroeste / Vitória',
        'cor': '#FC8DCD',
        'borda': '#be185d',
    },
    'ALESSANDRA': {
        'nome': 'Alessandra Suriano',
        'fone': '(27) 99590-9556',
        'wa_link': 'https://wa.me/5527995909556',
        'regiao': 'Centro-Oeste / Metropolitana',
        'cor': '#DABDFF',
        'borda': '#6b21a8',
    },
    'AMANDA': {
        'nome': 'Amanda Passine',
        'fone': '(27) 99850-1040',
        'wa_link': 'https://wa.me/5527998501040',
        'regiao': 'Sul / Caparaó / Serrana',
        'cor': '#BDE6FF',
        'borda': '#0284c7',
    },
    'PABLO': {
        'nome': 'Pablo Andrade',
        'fone': '(27) 99590-4584',
        'wa_link': 'https://wa.me/5527995904584',
        'regiao': 'Litoral Sul / Serra / Litoral Norte',
        'cor': '#BDFFCC',
        'borda': '#15803d',
    },
}

# Bloco CSS usado pelos dois aplicativos.
# Adaptação ao tema claro/escuro sem detectar o tema: o Streamlit 1.63 não
# publica variáveis CSS de tema, e st.context.theme só se atualiza no rerun
# seguinte à troca — usá-la deixaria o texto com a cor antiga até o próximo
# clique. Por isso nada aqui fixa cor de texto: o texto herda a cor que o
# Streamlit aplica e os painéis usam cinza translúcido, que escurece sobre fundo
# claro e clareia sobre fundo escuro. Os acentos têm contraste >= 3:1 sobre os
# dois fundos reais do Streamlit (#ffffff e #0e1117).
CSS_BASE = """
<style>
    :root {
        --painel-bg: rgba(128, 128, 128, 0.09);
        --painel-borda: rgba(128, 128, 128, 0.30);
        --linha: rgba(128, 128, 128, 0.22);
        --acento-pj: #3b82f6;
        --acento-pf: #059669;
        --acento-total: #8b5cf6;
    }
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: inherit;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: inherit;
        opacity: 0.72;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: var(--painel-bg);
        border: 1px solid var(--painel-borda);
        border-radius: 12px;
        padding: 1.1rem;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.12);
    }
    .kpi-value {
        font-size: 1.9rem;
        font-weight: 700;
        color: inherit;
        margin: 0.3rem 0;
    }
    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: inherit;
        opacity: 0.72;
    }
    .kpi-delta {
        font-size: 0.8rem;
        color: var(--acento-pf);
        font-weight: 600;
    }
</style>
"""


def fmt_int(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def fmt_float(n, dec=1):
    try:
        parts = f"{float(n):.{dec}f}".split(".")
        inteiro = f"{int(parts[0]):,}".replace(",", ".")
        return f"{inteiro},{parts[1]}"
    except Exception:
        return str(n)


def html_block(html):
    """Compacta HTML multilinha em uma única linha para o st.markdown.

    O renderizador Markdown do Streamlit encerra o bloco HTML na primeira linha
    em branco; as linhas indentadas seguintes passam a ser tratadas como bloco
    de código e aparecem como código-fonte na tela. Removendo quebras de linha e
    indentação, todo o trecho permanece um único bloco HTML.
    """
    return "".join(linha.strip() for linha in str(html).splitlines())


def hex_rgba(cor_hex, alfa):
    """Converte '#RRGGBB' em rgba() — usado para tingir painéis com a cor do
    gestor sem fixar um fundo opaco, que quebraria no tema escuro."""
    h = str(cor_hex).lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alfa})"


def info_gestor(chave, nome_alternativo='Não informado'):
    """Dados do gestor, com um registro neutro para chaves desconhecidas."""
    return GESTOR_INFO.get(str(chave).upper(), {
        'nome': nome_alternativo,
        'fone': '-',
        'wa_link': '',
        'regiao': '',
        'cor': '#94a3b8',
        'borda': '#475569',
    })


def card_municipio(linha, incluir_pf_pj=True):
    """HTML do card de detalhes de um município.

    incluir_pf_pj=False remove o bloco de atuação profissional — é o que a
    versão pública exibe, restrita a identificação, dados do IBGE e contato do
    gestor responsável.
    """
    m_nome = linha['Municipio']
    m_ibge = linha['Codigo_IBGE']
    m_micro = linha.get('Microrregiao', '')
    m_meso = linha.get('Mesorregiao', '')

    g_key = str(linha.get('Gestor', 'OUTROS')).upper()
    g_info = info_gestor(g_key, linha.get('Gestor', 'Não informado'))

    m_pop_str = fmt_int(int(linha.get('Populacao_IBGE_2022', 0)))
    m_area_str = fmt_float(float(linha.get('Area_km2', 0.0)), 1)
    m_dens_str = fmt_float(float(linha.get('Densidade_Demografica', 0.0)), 2)

    if g_info['wa_link']:
        botao_whatsapp = f"""
            <a href="{g_info['wa_link']}" target="_blank" style="display: flex; align-items: center; justify-content: center; gap: 8px; background-color: #25D366; color: #ffffff !important; text-decoration: none; padding: 0.5rem 0.8rem; border-radius: 8px; font-size: 0.85rem; font-weight: 700; box-shadow: 0 2px 4px rgba(37,211,102,0.3); transition: all 0.2s ease;">
                <span style="font-size: 1.1rem;">💬</span> Chamar no WhatsApp
            </a>
        """
    else:
        botao_whatsapp = ''

    if incluir_pf_pj:
        m_pj = int(linha['Quantidade de PJ de Academias'])
        m_pf = int(linha['Quantidade de Profissionais PF'])
        m_total = int(linha['Total (PF + PJ)'])
        bloco_atuacao = f"""
            <div style="background: var(--painel-bg); border: 1px solid var(--painel-borda); border-radius: 10px; padding: 0.8rem;">
                <div style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: inherit; opacity: 0.75; margin-bottom: 0.45rem;">🏢 ATUAÇÃO PROFISSIONAL &amp; ACADEMIAS</div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0; border-bottom: 1px solid var(--linha);">
                    <div>
                        <div style="color: inherit; font-weight: 700; font-size: 0.88rem;">🏢 PJ Academias:</div>
                        <div style="font-size: 0.72rem; color: inherit; opacity: 0.70;">{int(linha['Ranking_PJ'])}º no ES • {fmt_float(float(linha.get('Perc_PJ', 0.0)), 2)}% do ES</div>
                    </div>
                    <span style="font-size: 1.15rem; font-weight: 800; color: var(--acento-pj);">{fmt_int(m_pj)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0; border-bottom: 1px solid var(--linha);">
                    <div>
                        <div style="color: inherit; font-weight: 700; font-size: 0.88rem;">🏋️ Profissionais PF:</div>
                        <div style="font-size: 0.72rem; color: inherit; opacity: 0.70;">{int(linha['Ranking_PF'])}º no ES • {fmt_float(float(linha.get('Perc_PF', 0.0)), 2)}% do ES</div>
                    </div>
                    <span style="font-size: 1.15rem; font-weight: 800; color: var(--acento-pf);">{fmt_int(m_pf)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0;">
                    <div>
                        <div style="color: inherit; font-weight: 700; font-size: 0.88rem;">📈 Total (PF + PJ):</div>
                        <div style="font-size: 0.72rem; color: inherit; opacity: 0.70;">{int(linha.get('Ranking_Total', 0))}º no ES</div>
                    </div>
                    <span style="font-size: 1.15rem; font-weight: 800; color: var(--acento-total);">{fmt_int(m_total)}</span>
                </div>
            </div>
        """
        margem_ibge = '0.85rem'
    else:
        bloco_atuacao = ''
        margem_ibge = '0'

    return f"""
    <div style="background: var(--painel-bg); border: 1.5px solid var(--painel-borda); border-radius: 12px; padding: 1.1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.06); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="border-bottom: 2px solid var(--linha); padding-bottom: 0.7rem; margin-bottom: 0.8rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                <div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: inherit; line-height: 1.2;">📍 {m_nome}</div>
                    <div style="font-size: 0.8rem; color: inherit; opacity: 0.70; margin-top: 0.2rem;">{m_micro} • {m_meso}</div>
                </div>
                <span style="background: var(--painel-bg); color: inherit; font-size: 0.72rem; font-weight: 700; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--painel-borda); white-space: nowrap;">Cód. {m_ibge}</span>
            </div>
        </div>
        <div style="background: {hex_rgba(g_info['cor'], 0.20)}; border: 1.5px solid {hex_rgba(g_info['cor'], 0.75)}; border-radius: 10px; padding: 0.8rem; margin-bottom: 0.85rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                <span style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: inherit; opacity: 0.75;">👤 GESTOR(A) RESPONSÁVEL</span>
                <span style="font-size: 0.72rem; background: {g_info['cor']}; color: #0f172a; padding: 1px 7px; border-radius: 4px; font-weight: 800; border: 1px solid {hex_rgba(g_info['cor'], 0.9)};">{g_key}</span>
            </div>
            <div style="font-size: 1.08rem; font-weight: 800; color: inherit; margin-bottom: 0.15rem;">{g_info['nome']}</div>
            <div style="font-size: 0.78rem; color: inherit; opacity: 0.75; margin-bottom: 0.25rem; font-weight: 600;">🗂️ Região: {g_info.get('regiao') or '-'}</div>
            <div style="font-size: 0.82rem; color: inherit; margin-bottom: 0.6rem; font-weight: 600;">📞 {g_info['fone']}</div>
            {botao_whatsapp}
        </div>
        <div style="background: var(--painel-bg); border: 1px solid var(--painel-borda); border-radius: 10px; padding: 0.8rem; margin-bottom: {margem_ibge};">
            <div style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: inherit; opacity: 0.75; margin-bottom: 0.45rem;">📊 DADOS OFICIAIS IBGE (CENSO 2022)</div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0; border-bottom: 1px solid var(--linha); font-size: 0.85rem;">
                <span style="color: inherit; opacity: 0.75; font-weight: 600;">👥 População:</span>
                <span style="font-weight: 800; color: inherit;">{m_pop_str} hab</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0; border-bottom: 1px solid var(--linha); font-size: 0.85rem;">
                <span style="color: inherit; opacity: 0.75; font-weight: 600;">📐 Área Territorial:</span>
                <span style="font-weight: 800; color: inherit;">{m_area_str} km²</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0; font-size: 0.85rem;">
                <span style="color: inherit; opacity: 0.75; font-weight: 600;">🧭 Densidade:</span>
                <span style="font-weight: 800; color: inherit;">{m_dens_str} hab/km²</span>
            </div>
        </div>
        {bloco_atuacao}
    </div>
    """
