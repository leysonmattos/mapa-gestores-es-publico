from pathlib import Path

import folium
from folium import plugins
import branca.colormap as cm
from jinja2 import Template
from branca.element import MacroElement
import pandas as pd
from shapely.geometry import box, mapping, shape
from shapely.ops import polylabel, unary_union

from src.base_municipios import normalize_text
from src.ui_comum import GESTOR_INFO

PASTA_SRC = Path(__file__).resolve().parent


class MapaOrganico(MacroElement):
    """Interface do mapa no estilo dos mapas de apuração de eleição.

    Fundo escuro só com os municípios do ES, uma mira no centro que seleciona
    o município embaixo dela enquanto o mapa é arrastado, um painel inferior
    com os dados do município e controles discretos (legenda, busca, zoom,
    voltar ao estado inteiro).

    O comportamento e a aparência ficam em mapa_organico.js e
    mapa_organico.css, embutidos no HTML para que o mapa exportado continue
    funcionando sozinho, sem servidor.
    """

    _template = Template("""
        {% macro header(this, kwargs) %}
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap">
            <style>{{ this.css }}</style>
        {% endmacro %}
        {% macro script(this, kwargs) %}
            {{ this.js }}
            iniciarMapaOrganico({{ this._parent.get_name() }}, {{ this.config | tojson }});
        {% endmacro %}
    """)

    def __init__(self, config: dict):
        super().__init__()
        self._name = "MapaOrganico"
        self.config = config
        self.css = (PASTA_SRC / 'mapa_organico.css').read_text(encoding='utf-8')
        self.js = (PASTA_SRC / 'mapa_organico.js').read_text(encoding='utf-8')


class TelaCheiaEmIframe(MacroElement):
    """Faz o botão de tela cheia funcionar dentro do iframe do Streamlit.

    O mapa é renderizado num iframe de altura fixa. O controle do Leaflet usa a
    Fullscreen API quando ela existe e, quando não, aplica um "pseudo
    fullscreen" com position:fixed — que dentro de um iframe preenche só o
    iframe. No celular isso fazia o botão parecer não funcionar: o iOS não expõe
    a Fullscreen API fora de vídeo, e expandir para 100% de um quadro de 680px
    não muda quase nada.

    Aqui o pseudo fullscreen é usado em todas as plataformas e, junto dele, o
    próprio iframe é esticado para cobrir a janela da página que o contém.

    O estado fica marcado no dataset do iframe, não numa variável do script.
    Clicar num município faz o st_folium devolver o dado e o Streamlit
    reexecutar a página, o que remonta o mapa do zero — mas o elemento iframe
    sobrevive. Sem essa marca, o mapa recém-criado nasceria no tamanho normal
    dentro de um quadro ainda esticado, que era a tela embaralhada relatada.
    """

    _template = Template("""
        {% macro script(this, kwargs) %}
            setTimeout(function () {
                var mapObj = {{ this._parent.get_name() }};

                var quadro = null;
                try { quadro = window.frameElement; } catch (e) { quadro = null; }
                if (!quadro) { return; }

                var paginaPai = quadro.ownerDocument;

                function esticar() {
                    quadro.style.position = 'fixed';
                    quadro.style.top = '0';
                    quadro.style.left = '0';
                    quadro.style.width = '100vw';
                    quadro.style.maxWidth = '100vw';
                    quadro.style.height = '100vh';
                    quadro.style.zIndex = '2147483647';
                    quadro.dataset.telaCheia = '1';
                    try { paginaPai.body.style.overflow = 'hidden'; } catch (e) { }
                    setTimeout(function () { mapObj.invalidateSize(); }, 80);
                }

                function encolher() {
                    var anterior = quadro.dataset.estiloOriginal;
                    if (anterior) {
                        quadro.setAttribute('style', anterior);
                    } else {
                        quadro.removeAttribute('style');
                    }
                    delete quadro.dataset.telaCheia;
                    delete quadro.dataset.estiloOriginal;
                    try { paginaPai.body.style.overflow = ''; } catch (e) { }
                    setTimeout(function () { mapObj.invalidateSize(); }, 80);
                }

                mapObj.on('enterFullscreen', function () {
                    if (quadro.dataset.telaCheia !== '1') {
                        quadro.dataset.estiloOriginal = quadro.getAttribute('style') || '';
                    }
                    esticar();
                });

                mapObj.on('exitFullscreen', encolher);

                // Retoma a tela cheia depois de uma reexecução do Streamlit.
                // O clique passa pelo próprio controle do plugin, para que o
                // estado interno dele e o ícone do botão fiquem coerentes.
                // O setTimeout aninhado garante que isso rode depois que os
                // demais elementos do mapa já registraram seus ouvintes.
                if (quadro.dataset.telaCheia === '1') {
                    setTimeout(function () {
                        var botao = mapObj.getContainer().querySelector('.leaflet-control-zoom-fullscreen');
                        if (botao) { botao.click(); }
                    }, 0);
                }
            }, 0);
        {% endmacro %}
    """)

    def __init__(self):
        super().__init__()
        self._name = "TelaCheiaEmIframe"


COLOR_PALETTES = {
    'Azul e Verde (YlGnBu)': ['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494'],
    'Tons de Azul (Blues)': ['#eff3ff', '#bdd7e7', '#6baed6', '#3182bd', '#08519c'],
    'Viridis (Moderno)': ['#fde725', '#5ec962', '#21918c', '#3b528b', '#440154'],
    'Laranja e Vermelho (OrRd)': ['#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000'],
    'Roxo e Rosa (BuPu)': ['#edf8fb', '#b3cde3', '#8c96c6', '#8856a7', '#810f7c'],
    'Esmeralda e Menta (Greens)': ['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c']
}

# Grupos de Municípios com Cores Personalizadas
GROUP_1_MUNICIPIOS = [
    'Água Doce do Norte', 'Ecoporanga', 'Barra de São Francisco', 'Vila Pavão',
    'Mucurici', 'Ponto Belo', 'Montanha', 'Boa Esperança', 'Pinheiros',
    'Pedro Canário', 'Conceição da Barra', 'São Mateus', 'Jaguaré',
    'Nova Venécia', 'Sooretama', 'Soretama', 'Linhares', 'Vitória', 'Rio Bananal'
]
GROUP_1_COLOR = "#FC8DCD"

GROUP_2_MUNICIPIOS = [
    'Mantenópolis', 'Alto Rio Novo', 'Águia Branca', 'Pancas',
    'São Domingos do Norte', 'São Gabriel da Palha', 'Gabriel da Palha', 'Vila Valério',
    'Governador Lindenberg', 'Marilândia', 'Colatina', 'Baixo Guandu',
    'Laranja da Terra', 'Itaguaçu', 'São Roque do Canaã', 'Santa Teresa',
    'Itarana', 'Santa Maria de Jetibá', 'Santa Maria de Itibá', 'Santa Leopoldina',
    'Cariacica', 'Viana', 'Vila Velha'
]
GROUP_2_COLOR = "#DABDFF"

GROUP_3_MUNICIPIOS = [
    'Afonso Cláudio', 'Brejetuba', 'Ibatiba', 'Ibitirama', 'Irupi', 'Iúna',
    'Muniz Freire', 'Conceição do Castelo', 'Venda Nova do Imigrante',
    'Domingos Martins', 'Marechal Floriano', 'Alfredo Chaves', 'Vargem Alta',
    'Castelo', 'Iconha', 'Coia', 'Rio Novo do Sul', 'Atílio Vivacqua', 'Atílio Vivácqua',
    'Cachoeiro de Itapemirim', 'Jerônimo Monteiro', 'Muqui', 'Mimoso do Sul',
    'Apiacá', 'Bom Jesus do Norte', 'São José do Calçado', 'Guaçuí',
    'Alegre', 'Divino de São Lourenço', 'Domingo de São Lourenço',
    'Dores do Rio Preto', 'Domingo do Rio Preto'
]
GROUP_3_COLOR = "#BDE6FF"

GROUP_4_MUNICIPIOS = [
    'Aracruz', 'João Neiva', 'Ibiraçu', 'Fundão',
    'Serra', 'Guarapari', 'Anchieta', 'Piúma',
    'Itapemirim', 'Marataízes', 'Presidente Kennedy'
]
GROUP_4_COLOR = "#BDFFCC"

# Compatibilidade retroativa
DEFAULT_HIGHLIGHT_MUNICIPIOS = GROUP_1_MUNICIPIOS
HIGHLIGHT_COLOR = GROUP_1_COLOR

METRIC_LABELS = {
    'Quantidade de PJ de Academias': {
        'field': 'pj_academias',
        'title': 'Quantidade de PJ de Academias',
        'unit': 'unidades PJ',
        'badge_color': '#2563eb'
    },
    'Quantidade de Profissionais PF': {
        'field': 'pf_profissionais',
        'title': 'Quantidade de Profissionais PF',
        'unit': 'profissionais',
        'badge_color': '#059669'
    },
    'Total (PF + PJ)': {
        'field': 'total',
        'title': 'Total de Atuação (PF + PJ)',
        'unit': 'total',
        'badge_color': '#7c3aed'
    }
}

# Propriedades de PF/PJ removidas do GeoJSON na versão pública. Ocultá-las
# apenas no card não bastaria: o GeoJSON é embarcado na página e qualquer
# visitante leria os valores pelo código-fonte.
CAMPOS_RESTRITOS = (
    'pj_academias', 'pf_profissionais', 'total',
    'ranking_pj', 'ranking_pf', 'perc_pj', 'perc_pf', 'razao_pf_pj',
)

# Vitória: o rótulo da capital tem prioridade sobre os vizinhos maiores
# (Serra, Vila Velha, Cariacica) quando os nomes não cabem lado a lado.
CODIGO_CAPITAL = '3205309'


def filtrar_geojson_publico(geojson: dict) -> dict:
    """Devolve uma cópia do GeoJSON sem as propriedades de PF/PJ."""
    features = []
    for feature in geojson.get('features', []):
        props = {k: v for k, v in feature.get('properties', {}).items()
                 if k not in CAMPOS_RESTRITOS}
        features.append({**feature, 'properties': props})
    return {**geojson, 'features': features}


def _arredondar(coords, casas=5):
    if isinstance(coords, (int, float)):
        return round(coords, casas)
    return [_arredondar(c, casas) for c in coords]


def _maior_poligono(geometria):
    if geometria.geom_type == 'MultiPolygon':
        return max(geometria.geoms, key=lambda g: g.area)
    return geometria


_CACHE_CARTOGRAFIA = {}


def cartografia_es(geojson: dict) -> dict:
    """Contorno do ES, limites para enquadrar o estado e o ponto de rótulo de
    cada município.

    O contorno e os limites usam só o continente: o município de Vitória
    inclui as ilhas de Trindade e Martim Vaz, a ~1.100 km da costa, que
    estenderiam os limites até o meio do Atlântico e encolheriam o estado na
    tela. O ponto de rótulo (polylabel) fica sempre dentro do polígono, ao
    contrário do centro do retângulo envolvente, que cai fora em municípios
    recortados; o mapa também se centraliza nele ao clicar.

    O cálculo leva ~70 ms e a geometria de cada código IBGE não muda durante
    a execução, então o resultado fica em cache — o Streamlit recria o mapa a
    cada interação na barra lateral.
    """
    chave = tuple(str(f['properties'].get('codarea', '')) for f in geojson['features'])
    if chave in _CACHE_CARTOGRAFIA:
        return _CACHE_CARTOGRAFIA[chave]

    geometrias = [shape(f['geometry']) for f in geojson['features']]
    uniao = unary_union(geometrias)
    partes = list(uniao.geoms) if uniao.geom_type == 'MultiPolygon' else [uniao]
    continente = max(partes, key=lambda g: g.area)
    janela = box(*continente.bounds).buffer(0.3)
    contorno = unary_union([p for p in partes if p.intersects(janela)]).boundary

    rotulos = {}
    for cod, geo in zip(chave, geometrias):
        partes_mun = list(geo.geoms) if geo.geom_type == 'MultiPolygon' else [geo]
        perto = [p for p in partes_mun if p.intersects(janela)] or partes_mun
        ponto = polylabel(max(perto, key=lambda g: g.area), tolerance=0.001)
        rotulos[cod] = [round(ponto.y, 5), round(ponto.x, 5)]

    oeste, sul, leste, norte = continente.bounds
    geo_contorno = mapping(contorno)
    resultado = {
        'contorno': {'type': geo_contorno['type'],
                     'coordinates': _arredondar(geo_contorno['coordinates'])},
        'limites': [[sul, oeste], [norte, leste]],
        'centro': [(sul + norte) / 2, (oeste + leste) / 2],
        'rotulos': rotulos,
    }
    _CACHE_CARTOGRAFIA[chave] = resultado
    return resultado


class ESMapGenerator:
    def __init__(self, geojson_data: dict, df_data: pd.DataFrame):
        self.geojson_data = geojson_data
        self.df_data = df_data

    def create_map(
        self,
        metric_name: str = 'Quantidade de PJ de Academias',
        palette_name: str = 'Azul e Verde (YlGnBu)',
        base_layer: str = 'OpenStreetMap',
        highlight_active: bool = True,
        group1_active: bool = True,
        group2_active: bool = True,
        group3_active: bool = True,
        group4_active: bool = True,
        show_colorbar: bool = False,
        modo_publico: bool = False
    ) -> folium.Map:
        """
        Gera o mapa interativo do Espírito Santo: municípios coloridos pelo
        gestor responsável, sobre fundo escuro, com mira e painel de detalhes.
        """
        dados_geojson = (filtrar_geojson_publico(self.geojson_data)
                         if modo_publico else self.geojson_data)
        cartografia = cartografia_es(dados_geojson)

        # Sem tiles: o fundo é a cor do próprio contêiner, e só o ES aparece.
        # zoomSnap fracionário deixa o enquadramento e o zoom mais suaves.
        m = folium.Map(
            location=cartografia['centro'],
            zoom_start=7,
            tiles=None,
            zoom_control=False,
            attribution_control=False,
            max_zoom=12,
            zoom_snap=0.25,
            zoom_delta=0.5,
            wheel_px_per_zoom_level=90
        )

        # Obter configuração da métrica
        metric_info = METRIC_LABELS.get(metric_name, METRIC_LABELS['Quantidade de PJ de Academias'])
        field_name = metric_info['field']

        # Calcular valores mín e máx para a escala de cores.
        # Na versão pública o campo da métrica já foi removido do GeoJSON, então
        # a lista fica zerada — o coroplético não é usado ali de todo modo.
        values = []
        for feature in dados_geojson['features']:
            val = feature['properties'].get(field_name, 0)
            values.append(float(val or 0))

        min_val = min(values) if values else 0
        max_val = max(values) if values else 1
        if min_val == max_val:
            max_val = min_val + 1

        colors = COLOR_PALETTES.get(palette_name, COLOR_PALETTES['Azul e Verde (YlGnBu)'])

        # Colormap contínuo usado só para calcular a cor dos municípios de
        # gestores desmarcados.
        colormap = cm.LinearColormap(
            colors=colors,
            vmin=min_val,
            vmax=max_val
        )

        # Conjunto normalizado de municípios do Grupo 1 (#FC8DCD)
        norm_group1 = {normalize_text(h) for h in GROUP_1_MUNICIPIOS}
        if 'soretama' in norm_group1:
            norm_group1.add('sooretama')

        # Conjunto normalizado de municípios do Grupo 2 (#DABDFF)
        norm_group2 = {normalize_text(h) for h in GROUP_2_MUNICIPIOS}
        if 'gabriel da palha' in norm_group2:
            norm_group2.add('sao gabriel da palha')
        if 'santa maria de itiba' in norm_group2:
            norm_group2.add('santa maria de jetiba')

        # Conjunto normalizado de municípios do Grupo 3 (#BDE6FF)
        norm_group3 = {normalize_text(h) for h in GROUP_3_MUNICIPIOS}
        if 'coia' in norm_group3:
            norm_group3.add('iconha')
        if 'domingo de sao lourenco' in norm_group3:
            norm_group3.add('divino de sao lourenco')
        if 'domingo do rio preto' in norm_group3:
            norm_group3.add('dores do rio preto')

        # Conjunto normalizado de municípios do Grupo 4 (#BDFFCC)
        norm_group4 = {normalize_text(h) for h in GROUP_4_MUNICIPIOS}

        grupos = [
            (group1_active, norm_group1, GROUP_1_COLOR),
            (group2_active, norm_group2, GROUP_2_COLOR),
            (group3_active, norm_group3, GROUP_3_COLOR),
            (group4_active, norm_group4, GROUP_4_COLOR),
        ]

        def cor_do_municipio(props):
            muni_norm = normalize_text(props.get('municipio', ''))
            for ativo, conjunto, cor in grupos:
                if highlight_active and ativo and (
                        muni_norm in conjunto
                        or any(h in muni_norm for h in conjunto if len(h) > 5)):
                    return cor
            if modo_publico:
                # Sem coroplético na versão pública: ela não expõe métricas de PF/PJ.
                return '#e2e8f0'
            val = props.get(field_name, 0)
            return colormap(float(val)) if val is not None else '#e2e8f0'

        # Cópia das feições com a cor já resolvida e o ponto de rótulo: o
        # GeoJSON recebido não é alterado.
        feicoes = []
        for feature in dados_geojson['features']:
            props = dict(feature['properties'])
            props['cor'] = cor_do_municipio(props)
            props['rotulo'] = cartografia['rotulos'].get(str(props.get('codarea', '')))
            feicoes.append({**feature, 'properties': props})

        # Totais dinâmicos por Gestor
        stats_by_gestor = {}
        if self.df_data is not None and 'Gestor' in self.df_data.columns:
            for g in ['BRUNA', 'ALESSANDRA', 'AMANDA', 'PABLO']:
                sub = self.df_data[self.df_data['Gestor'] == g]
                tem_pf_pj = 'Quantidade de PJ de Academias' in sub.columns
                stats_by_gestor[g] = {
                    'pj': int(sub['Quantidade de PJ de Academias'].sum()) if tem_pf_pj else 0,
                    'pf': int(sub['Quantidade de Profissionais PF'].sum()) if tem_pf_pj else 0,
                    'munis': len(sub)
                }
        else:
            stats_by_gestor = {
                'BRUNA': {'pj': 474, 'pf': 4301, 'munis': 18},
                'ALESSANDRA': {'pj': 601, 'pf': 4300, 'munis': 21},
                'AMANDA': {'pj': 278, 'pf': 2038, 'munis': 28},
                'PABLO': {'pj': 417, 'pf': 3351, 'munis': 11}
            }

        # Uma linha por gestor ativo, usada na legenda e no resumo do estado.
        # Na versão pública os totais de PJ/PF ficam de fora.
        gestores_legenda = [
            ('BRUNA', GROUP_1_COLOR, group1_active, 18),
            ('ALESSANDRA', GROUP_2_COLOR, group2_active, 21),
            ('AMANDA', GROUP_3_COLOR, group3_active, 28),
            ('PABLO', GROUP_4_COLOR, group4_active, 11),
        ]
        legenda = []
        if highlight_active:
            for chave, cor, ativo, munis_padrao in gestores_legenda:
                if not ativo:
                    continue
                st_g = stats_by_gestor.get(chave, {'pj': 0, 'pf': 0, 'munis': munis_padrao})
                item = {
                    'chave': chave,
                    'nome': GESTOR_INFO.get(chave, {}).get('nome', chave),
                    'cor': cor,
                    'municipios': st_g['munis'],
                }
                if not modo_publico:
                    item['pj'] = st_g['pj']
                    item['pf'] = st_g['pf']
                legenda.append(item)

        # Escala do coroplético, só quando algum município fica sem a cor de
        # gestor (gestor desmarcado na barra lateral).
        algum_inativo = not highlight_active or not all(g[0] for g in grupos)
        escala = None
        if algum_inativo and not modo_publico:
            escala = {
                'titulo': metric_info['title'],
                'cores': colors,
                'min': min_val,
                'max': max_val,
            }

        # Tela cheia: o botão é movido para a pilha de controles da direita
        # pelo mapa_organico.js. force_pseudo_fullscreen deixa o comportamento
        # igual em toda plataforma, inclusive no iOS, que não oferece a
        # Fullscreen API. TelaCheiaEmIframe cuida de expandir o iframe do
        # Streamlit junto.
        plugins.Fullscreen(
            position='topleft',
            title='Expandir para Tela Cheia',
            title_cancel='Sair da Tela Cheia',
            force_separate_button=True,
            force_pseudo_fullscreen=True
        ).add_to(m)
        m.add_child(TelaCheiaEmIframe())

        m.add_child(MapaOrganico({
            'municipios': {'type': 'FeatureCollection', 'features': feicoes},
            'contorno': cartografia['contorno'],
            'limites': cartografia['limites'],
            'capital': CODIGO_CAPITAL,
            'gestores': {
                chave: {k: info[k] for k in ('nome', 'fone', 'wa_link', 'regiao', 'cor', 'borda')}
                for chave, info in GESTOR_INFO.items()
            },
            'legenda': legenda,
            'escala': escala,
            'modoPublico': modo_publico,
        }))

        return m

    def save_html(
        self,
        output_path: str = 'mapa_es_interativo.html',
        metric_name: str = 'Quantidade de PJ de Academias',
        palette_name: str = 'Azul e Verde (YlGnBu)',
        highlight_active: bool = True,
        group1_active: bool = True,
        group2_active: bool = True,
        group3_active: bool = True,
        group4_active: bool = True,
        show_colorbar: bool = False,
        modo_publico: bool = False
    ):
        """Salva o mapa em formato HTML autônomo."""
        m = self.create_map(
            metric_name=metric_name,
            palette_name=palette_name,
            highlight_active=highlight_active,
            group1_active=group1_active,
            group2_active=group2_active,
            group3_active=group3_active,
            group4_active=group4_active,
            show_colorbar=show_colorbar,
            modo_publico=modo_publico
        )
        m.save(output_path)
        print(f"Mapa salvo com sucesso em: {output_path}")
        return output_path
