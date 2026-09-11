import json
import folium
from folium import plugins
import branca.colormap as cm
from jinja2 import Template
from branca.element import MacroElement
import pandas as pd
from src.base_municipios import normalize_text

class DockedMuniAndLegendControl(MacroElement):
    """
    Controle Leaflet unificado no canto inferior direito:
    1. Painel de Detalhes do Município Clicado (posicionado ACIMA da tabela de gestores).
    2. Tabela de Gestores / Regiões (posicionada ABAIXO).
    """
    _template = Template("""
        {% macro script(this, kwargs) %}
            var mapObj = {{ this._parent.get_name() }};
            // Na versão pública o card omite tudo de PF/PJ, mostrando só
            // identificação do município, dados do IBGE e contato do gestor.
            var modoPublico = {{ this.modo_publico | tojson }};
            
            // Controle único no canto inferior direito contendo, nesta ordem:
            //   1. o card de detalhes do município clicado (em cima);
            //   2. a tabela de Gestores / Regiões (embaixo).
            // Os dois ficam no MESMO container porque o Leaflet insere controles de
            // cantos "bottom" com insertBefore(corner.firstChild), ou seja, o último
            // controle adicionado apareceria por cima. Um container só torna a
            // ordem explícita e independente desse comportamento.
            var dockControl = L.control({position: 'bottomright'});
            dockControl.onAdd = function (map) {
                var wrapper = L.DomUtil.create('div', 'leaflet-dock-bottomright');

                var detail = L.DomUtil.create('div', 'leaflet-muni-card-fixed', wrapper);
                detail.id = 'leaflet-muni-details-card';
                detail.style.display = 'none';

                var legend = L.DomUtil.create('div', 'leaflet-legend-gestores', wrapper);
                legend.innerHTML = {{ this.legend_html | tojson }};

                L.DomEvent.disableClickPropagation(wrapper);
                L.DomEvent.disableScrollPropagation(wrapper);
                return wrapper;
            };
            dockControl.addTo(mapObj);

            // Função global para fechar o card do município
            window.closeMuniDetailCard = function() {
                var card = document.getElementById('leaflet-muni-details-card');
                if (card) {
                    card.style.display = 'none';
                }
            };

            var gestorMeta = {
                'BRUNA': { nome: 'Bruna Borini', fone: '(27) 99987-0011', wa: '5527999870011', cor: '#FC8DCD', borda: '#831843', bg: '#fce7f3' },
                'ALESSANDRA': { nome: 'Alessandra Suriano', fone: '(27) 99590-9556', wa: '5527995909556', cor: '#DABDFF', borda: '#4c1d95', bg: '#f3e8ff' },
                'AMANDA': { nome: 'Amanda Passine', fone: '(27) 99850-1040', wa: '5527998501040', cor: '#BDE6FF', borda: '#0369a1', bg: '#e0f2fe' },
                'PABLO': { nome: 'Pablo Andrade', fone: '(27) 99590-4584', wa: '5527995904584', cor: '#BDFFCC', borda: '#15803d', bg: '#dcfce7' }
            };

            function formatInt(num) {
                if (!num && num !== 0) return '0';
                return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".");
            }

            function formatFloat(num, dec) {
                if (!num && num !== 0) return '0';
                var parts = Number(num).toFixed(dec || 1).split('.');
                parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".");
                return parts.join(',');
            }

            function bindMuniClickEvents() {
                mapObj.eachLayer(function(layer) {
                    if (layer.feature && layer.feature.properties && !layer._hasMuniDetailBound) {
                        layer._hasMuniDetailBound = true;
                        layer.on('click', function(e) {
                            var props = e.target.feature.properties;
                            var card = document.getElementById('leaflet-muni-details-card');
                            if (!card) return;

                            var gKey = (props.gestor || '').toUpperCase();
                            var gInfo = gestorMeta[gKey] || { nome: props.gestor || 'Não informado', fone: '-', wa: '', cor: '#94a3b8', borda: '#475569', bg: '#f1f5f9' };

                            var html = `
                                <div style="position: relative; padding: 2px;">
                                    <button onclick="window.closeMuniDetailCard()" title="Fechar" style="position: absolute; top: -2px; right: -2px; background: none; border: none; font-size: 18px; font-weight: bold; color: #64748b; cursor: pointer; line-height: 1; padding: 2px 6px; z-index: 10;">&times;</button>
                                    
                                    <div style="font-size: 13px; font-weight: 800; color: #0f172a; margin-bottom: 6px; padding-right: 22px; display: flex; align-items: center; justify-content: space-between;">
                                        <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">📍 ${props.municipio || props.name || ''}</span>
                                        <span style="font-size: 10px; font-weight: 600; color: #64748b; background: #e2e8f0; padding: 1px 5px; border-radius: 4px; white-space: nowrap;">${props.cod_ibge ? 'IBGE ' + props.cod_ibge : ''}</span>
                                    </div>

                                    <table style="width: 100%; border-collapse: separate; border-spacing: 0 2px; font-size: 11.5px;">
                                        <tr style="background: ${gInfo.bg};">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">👤 Gestor(a)</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: ${gInfo.borda}; border-radius: 0 4px 4px 0; font-size: 11.5px;">
                                                <span style="display: inline-block; width: 8px; height: 8px; background: ${gInfo.cor}; border-radius: 2px; margin-right: 4px; border: 1px solid ${gInfo.borda};"></span>
                                                ${gKey}
                                            </td>
                                        </tr>
                                        <tr style="background: rgba(241, 245, 249, 0.85);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">👥 População</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #0f172a; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatInt(props.populacao)} hab</td>
                                        </tr>
                                        <tr style="background: rgba(255, 255, 255, 0.95);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">📐 Área</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #0f172a; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatFloat(props.area_km2, 1)} km²</td>
                                        </tr>
                                        <tr style="background: rgba(241, 245, 249, 0.85);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🧭 Densidade</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #0f172a; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatFloat(props.densidade, 2)} hab/km²</td>
                                        </tr>
                                        ${modoPublico ? '' : `
                                        <tr style="background: rgba(255, 255, 255, 0.95);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🏢 PJ Academias</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #2563eb; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatInt(props.pj_academias)}</td>
                                        </tr>
                                        <tr style="background: rgba(241, 245, 249, 0.85);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🏆 Ranking PJ</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #0f172a; border-radius: 0 4px 4px 0; font-size: 11.5px;">${props.ranking_pj}º</td>
                                        </tr>
                                        <tr style="background: rgba(255, 255, 255, 0.95);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🏋️ Profissionais PF</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #059669; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatInt(props.pf_profissionais)}</td>
                                        </tr>
                                        <tr style="background: rgba(241, 245, 249, 0.85);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🏆 Ranking PF</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #0f172a; border-radius: 0 4px 4px 0; font-size: 11.5px;">${props.ranking_pf}º</td>
                                        </tr>
                                        <tr style="background: rgba(255, 255, 255, 0.95);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">📈 Total (PF+PJ)</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 700; color: #7c3aed; border-radius: 0 4px 4px 0; font-size: 11.5px;">${formatInt(props.total)}</td>
                                        </tr>
                                        `}
                                        <tr style="background: rgba(241, 245, 249, 0.85);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🗺️ Microrregião</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 600; color: #0369a1; border-radius: 0 4px 4px 0; font-size: 11px;">${props.microrregiao || '-'}</td>
                                        </tr>
                                        <tr style="background: rgba(255, 255, 255, 0.95);">
                                            <th style="padding: 3.5px 8px; text-align: left; font-weight: 600; color: #1e293b; border-radius: 4px 0 0 4px; font-size: 11px;">🌐 Mesorregião</th>
                                            <td style="padding: 3.5px 8px; text-align: right; font-weight: 600; color: #0369a1; border-radius: 0 4px 4px 0; font-size: 11px;">${props.mesorregiao || '-'}</td>
                                        </tr>
                                    </table>

                                    ${gInfo.wa ? `
                                    <div style="margin-top: 6px;">
                                        <div style="font-size: 11px; font-weight: 700; color: #1e293b; margin-bottom: 3px;">${gInfo.nome} &nbsp;•&nbsp; <span style="font-weight: 600; color: #475569;">📞 ${gInfo.fone}</span></div>
                                        <a href="https://wa.me/${gInfo.wa}" target="_blank" style="display: flex; align-items: center; justify-content: center; gap: 5px; background: #25D366; color: #ffffff !important; text-decoration: none; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; box-shadow: 0 2px 4px rgba(37,211,102,0.3);">
                                            💬 Chamar no WhatsApp
                                        </a>
                                    </div>
                                    ` : ''}
                                </div>
                            `;

                            card.innerHTML = html;
                            card.style.display = 'block';
                        });
                    }
                });
            }

            setTimeout(bindMuniClickEvents, 100);
            mapObj.on('layeradd', function() {
                setTimeout(bindMuniClickEvents, 50);
            });
        {% endmacro %}
    """)

    def __init__(self, legend_html: str, modo_publico: bool = False):
        super().__init__()
        self._name = "DockedMuniAndLegendControl"
        self.legend_html = legend_html
        self.modo_publico = modo_publico

class TelaCheiaEmIframe(MacroElement):
    """Faz o botão de tela cheia funcionar dentro do iframe do Streamlit.

    O mapa é renderizado num iframe de altura fixa. O controle do Leaflet usa a
    Fullscreen API quando ela existe e, quando não, aplica um "pseudo
    fullscreen" com position:fixed — que dentro de um iframe preenche só o
    iframe. No celular isso fazia o botão parecer não funcionar: o iOS não expõe
    a Fullscreen API fora de vídeo, e expandir para 100% de um quadro de 680px
    não muda quase nada.

    Aqui o pseudo fullscreen é usado em todas as plataformas e, junto dele, o
    próprio iframe é esticado para cobrir a janela da página que o contém. Fora
    de um iframe o controle padrão já basta e nada é alterado.
    """

    _template = Template("""
        {% macro script(this, kwargs) %}
            (function () {
                var mapObj = {{ this._parent.get_name() }};

                var quadro = null;
                try { quadro = window.frameElement; } catch (e) { quadro = null; }
                if (!quadro) { return; }

                var estiloAnterior = quadro.getAttribute('style');
                var paginaPai = quadro.ownerDocument;
                var overflowAnterior = null;

                mapObj.on('enterFullscreen', function () {
                    estiloAnterior = quadro.getAttribute('style');
                    quadro.style.position = 'fixed';
                    quadro.style.top = '0';
                    quadro.style.left = '0';
                    quadro.style.width = '100vw';
                    quadro.style.maxWidth = '100vw';
                    quadro.style.height = '100vh';
                    quadro.style.zIndex = '2147483647';
                    try {
                        overflowAnterior = paginaPai.body.style.overflow;
                        paginaPai.body.style.overflow = 'hidden';
                    } catch (e) { /* página pai inacessível: só o iframe expande */ }
                    setTimeout(function () { mapObj.invalidateSize(); }, 80);
                });

                mapObj.on('exitFullscreen', function () {
                    if (estiloAnterior === null) {
                        quadro.removeAttribute('style');
                    } else {
                        quadro.setAttribute('style', estiloAnterior);
                    }
                    try {
                        if (overflowAnterior !== null) {
                            paginaPai.body.style.overflow = overflowAnterior;
                        }
                    } catch (e) { /* idem */ }
                    setTimeout(function () { mapObj.invalidateSize(); }, 80);
                });
            })();
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

def filtrar_geojson_publico(geojson: dict) -> dict:
    """Devolve uma cópia do GeoJSON sem as propriedades de PF/PJ."""
    features = []
    for feature in geojson.get('features', []):
        props = {k: v for k, v in feature.get('properties', {}).items()
                 if k not in CAMPOS_RESTRITOS}
        features.append({**feature, 'properties': props})
    return {**geojson, 'features': features}


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
        Gera um mapa interativo e coroplético do Espírito Santo com popups e tooltips ricos.
        """
        dados_geojson = (filtrar_geojson_publico(self.geojson_data)
                         if modo_publico else self.geojson_data)

        # Centro do Espírito Santo
        center_lat = -19.65
        center_lon = -40.60
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles=None,
            control_scale=True,
            prefer_canvas=True
        )

        # Adicionar camadas extras de mapa base para o usuário alternar
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            name='OpenStreetMap Padrão'
        ).add_to(m)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            attr='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            name='Esri Topográfico'
        ).add_to(m)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            name='Esri Satélite'
        ).add_to(m)

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
        
        # Criar colormap contínuo apenas para interpolação de cores em memória (sem adicionar ao mapa)
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

        # Função de estilo para cada município
        def style_function(feature):
            muni_norm = normalize_text(feature['properties'].get('municipio', ''))
            
            # Verificar Grupo 1 (#FC8DCD)
            if highlight_active and group1_active and (muni_norm in norm_group1 or any(h in muni_norm for h in norm_group1 if len(h) > 5)):
                return {
                    'fillColor': GROUP_1_COLOR,
                    'color': '#831843',
                    'weight': 1.8,
                    'fillOpacity': 0.88,
                    'dashArray': ''
                }
            # Verificar Grupo 2 (#DABDFF)
            elif highlight_active and group2_active and (muni_norm in norm_group2 or any(h in muni_norm for h in norm_group2 if len(h) > 5)):
                return {
                    'fillColor': GROUP_2_COLOR,
                    'color': '#4c1d95',
                    'weight': 1.8,
                    'fillOpacity': 0.88,
                    'dashArray': ''
                }
            # Verificar Grupo 3 (#BDE6FF)
            elif highlight_active and group3_active and (muni_norm in norm_group3 or any(h in muni_norm for h in norm_group3 if len(h) > 5)):
                return {
                    'fillColor': GROUP_3_COLOR,
                    'color': '#0369a1',
                    'weight': 1.8,
                    'fillOpacity': 0.88,
                    'dashArray': ''
                }
            # Verificar Grupo 4 (#BDFFCC)
            elif highlight_active and group4_active and (muni_norm in norm_group4 or any(h in muni_norm for h in norm_group4 if len(h) > 5)):
                return {
                    'fillColor': GROUP_4_COLOR,
                    'color': '#15803d',
                    'weight': 1.8,
                    'fillOpacity': 0.88,
                    'dashArray': ''
                }
            else:
                if modo_publico:
                    # Sem coroplético na versão pública: ela não expõe métricas de PF/PJ.
                    fill_color = '#e2e8f0'
                else:
                    val = feature['properties'].get(field_name, 0)
                    fill_color = colormap(float(val)) if val is not None else '#e2e8f0'
                return {
                    'fillColor': fill_color,
                    'color': '#334155',
                    'weight': 1.0,
                    'fillOpacity': 0.68,
                    'dashArray': '1, 1'
                }

        # Função de destaque ao passar o mouse
        def highlight_function(feature):
            return {
                'fillColor': '#fef08a',
                'color': '#000000',
                'weight': 3,
                'fillOpacity': 0.95,
                'dashArray': ''
            }

        # Injetar CSS customizado para garantir visibilidade com retângulo branco translúcido (10% transparência)
        custom_css = """
        <style>
            /* Container do Popup com Retângulo Branco Translúcido (10% transparência / 90% opacidade) */
            .leaflet-popup-content-wrapper {
                background: rgba(255, 255, 255, 0.90) !important;
                backdrop-filter: blur(8px) !important;
                -webkit-backdrop-filter: blur(8px) !important;
                border: 2px solid rgba(15, 23, 42, 0.15) !important;
                border-radius: 12px !important;
                box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.35), 0 5px 15px rgba(0, 0, 0, 0.15) !important;
                padding: 10px 12px !important;
            }
            .leaflet-popup-tip {
                background: rgba(255, 255, 255, 0.90) !important;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25) !important;
            }
            .leaflet-popup-content {
                margin: 6px 8px !important;
                min-width: 270px !important;
                max-width: 380px !important;
                line-height: 1.4 !important;
            }
            .leaflet-popup-content table {
                width: 100% !important;
                border-collapse: separate !important;
                border-spacing: 0 3px !important;
                background: transparent !important;
            }
            .leaflet-popup-content tr {
                background-color: rgba(241, 245, 249, 0.8) !important;
                border-radius: 6px !important;
                transition: background-color 0.15s ease;
            }
            .leaflet-popup-content tr:nth-child(even) {
                background-color: rgba(255, 255, 255, 0.95) !important;
            }
            .leaflet-popup-content th {
                padding: 5px 10px !important;
                font-size: 12px !important;
                font-weight: 600 !important;
                color: #1e293b !important;
                text-align: left !important;
                white-space: nowrap !important;
                border-radius: 4px 0 0 4px !important;
            }
            .leaflet-popup-content td {
                padding: 5px 10px !important;
                font-size: 12.5px !important;
                font-weight: 700 !important;
                color: #0369a1 !important;
                text-align: right !important;
                white-space: nowrap !important;
                border-radius: 0 4px 4px 0 !important;
            }
            .leaflet-popup-close-button {
                color: #475569 !important;
                padding: 6px !important;
                font-size: 16px !important;
            }
            .leaflet-popup-close-button:hover {
                color: #0f172a !important;
            }

            /* Pilha fixa do canto inferior direito: card do município acima, gestores abaixo */
            .leaflet-dock-bottomright {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-end !important;
                gap: 8px !important;
                margin: 0 25px 25px 0 !important;
                pointer-events: auto !important;
            }

            /* Container de Detalhes do Município (Canto Inferior Direito - Acima dos Gestores) */
            .leaflet-muni-card-fixed {
                background: rgba(255, 255, 255, 0.96) !important;
                backdrop-filter: blur(8px) !important;
                -webkit-backdrop-filter: blur(8px) !important;
                padding: 10px 14px !important;
                border-radius: 12px !important;
                border: 1.5px solid rgba(15, 23, 42, 0.18) !important;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.25), 0 8px 10px -6px rgba(0,0,0,0.15) !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                font-size: 12px !important;
                color: #1e293b !important;
                min-width: 340px !important;
                max-width: 370px !important;
                max-height: 400px !important;
                overflow-y: auto !important;
                margin: 0 !important;
                pointer-events: auto !important;
                z-index: 1000 !important;
                transition: all 0.2s ease-in-out !important;
            }

            /* Container da Tabela de Gestores / Regiões (Exibido em modo normal e modo Tela Cheia) */
            .leaflet-legend-gestores {
                background: rgba(255, 255, 255, 0.96) !important;
                backdrop-filter: blur(8px) !important;
                -webkit-backdrop-filter: blur(8px) !important;
                padding: 12px 16px !important;
                border-radius: 12px !important;
                border: 1.5px solid rgba(15, 23, 42, 0.18) !important;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.25), 0 8px 10px -6px rgba(0,0,0,0.15) !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                font-size: 12px !important;
                color: #1e293b !important;
                min-width: 340px !important;
                max-width: 370px !important;
                margin: 0 !important;
                pointer-events: auto !important;
                z-index: 1000 !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }

            /* Em telas estreitas a atribuição dos tiles ocupava quatro linhas
               sobre o mapa. Reduzida, não ocultada: creditar a fonte dos tiles
               é exigência de licença do OpenStreetMap e do Esri. */
            @media (max-width: 640px) {
                .leaflet-control-attribution {
                    font-size: 9px !important;
                    line-height: 1.3 !important;
                    padding: 1px 4px !important;
                }
            }

            /* Ocultar completamente qualquer popup padrão sobre o mapa */
            .leaflet-popup, .leaflet-popup-pane, .leaflet-popup-content-wrapper, .leaflet-popup-tip-container {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            /* Ocultar completamente qualquer barra de legenda gradiente residual ou SVG de colormap */
            .legend, .caption, svg.legend, div.legend, .leaflet-control-container .legend, 
            .leaflet-top .legend, .leaflet-bottom .legend, g.legend, svg.leaflet-control,
            .folium-map svg.legend, svg[class*="legend"], svg[class*="caption"],
            .leaflet-control-layers-base label input[type="radio"] {
                /* regras de visualização */
            }
            .legend, .caption, svg.legend, div.legend, g.legend, svg.leaflet-control {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                height: 0 !important;
                width: 0 !important;
                pointer-events: none !important;
            }
        </style>
        """
        m.get_root().header.add_child(folium.Element(custom_css))

        # Criar Camada GeoJson com Tooltips Interativos
        geojson_layer = folium.GeoJson(
            dados_geojson,
            name='Municípios do ES',
            style_function=style_function,
            highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(
                fields=(['municipio', 'gestor'] if modo_publico
                        else ['municipio', 'pj_academias', 'pf_profissionais', 'total']),
                aliases=(['📍 Município:', '👤 Gestor(a):'] if modo_publico
                         else ['📍 Município:', '🏢 PJ Academias:', '🏋️ Profissionais PF:', '📊 Total (PF+PJ):']),
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #0f172a;
                    color: #ffffff;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 8px 12px;
                    border-radius: 8px;
                    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
                    border: 1px solid #334155;
                    line-height: 1.5;
                """
            )
        )
        geojson_layer.add_to(m)

        # Adicionar controle de camadas
        folium.LayerControl(position='topright', collapsed=False).add_to(m)

        # Adicionar botão de Tela Cheia
        # force_pseudo_fullscreen deixa o comportamento igual em toda
        # plataforma, inclusive no iOS, que não oferece a Fullscreen API.
        # TelaCheiaEmIframe cuida de expandir o iframe do Streamlit junto.
        plugins.Fullscreen(
            position='topleft',
            title='Expandir para Tela Cheia',
            title_cancel='Sair da Tela Cheia',
            force_separate_button=True,
            force_pseudo_fullscreen=True
        ).add_to(m)
        m.add_child(TelaCheiaEmIframe())

        # Adicionar MiniMapa no canto inferior esquerdo
        plugins.MiniMap(
            tile_layer='OpenStreetMap',
            position='bottomleft',
            width=120,
            height=120,
            zoom_animation=True,
            toggle_display=True
        ).add_to(m)

        if highlight_active:
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

            b_stats = stats_by_gestor.get('BRUNA', {'pj': 0, 'pf': 0, 'munis': 18})
            al_stats = stats_by_gestor.get('ALESSANDRA', {'pj': 0, 'pf': 0, 'munis': 21})
            am_stats = stats_by_gestor.get('AMANDA', {'pj': 0, 'pf': 0, 'munis': 28})
            p_stats = stats_by_gestor.get('PABLO', {'pj': 0, 'pf': 0, 'munis': 11})

            # Uma linha por gestor. Na versão pública os selos de PJ/PF saem,
            # restando apenas a cor, o nome e a quantidade de municípios.
            gestores_legenda = [
                ('BRUNA', GROUP_1_COLOR, '#831843', group1_active, 18),
                ('ALESSANDRA', GROUP_2_COLOR, '#4c1d95', group2_active, 21),
                ('AMANDA', GROUP_3_COLOR, '#0369a1', group3_active, 28),
                ('PABLO', GROUP_4_COLOR, '#15803d', group4_active, 11),
            ]
            ativos = [g for g in gestores_legenda if g[3]]

            linhas = []
            for i, (nome, cor, borda, _, munis_padrao) in enumerate(ativos):
                st_g = stats_by_gestor.get(nome, {'pj': 0, 'pf': 0, 'munis': munis_padrao})
                separador = '' if i == len(ativos) - 1 else ' border-bottom: 1px solid rgba(241, 245, 249, 0.9);'
                if modo_publico:
                    selos = ''
                else:
                    selos = (
                        '<div style="display: flex; gap: 6px;">'
                        f'<span style="background: rgba(37, 99, 235, 0.12); color: #1d4ed8; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 11.5px; white-space: nowrap;">🏢 {st_g["pj"]} PJ</span>'
                        f'<span style="background: rgba(5, 150, 105, 0.12); color: #047857; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 11.5px; white-space: nowrap;">🏋️ {st_g["pf"]} PF</span>'
                        '</div>'
                    )
                linhas.append(
                    f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0;{separador}">'
                    '<div style="display: flex; align-items: center; gap: 8px;">'
                    f'<span style="display: inline-block; width: 14px; height: 14px; background-color: {cor}; border-radius: 3px; border: 1px solid {borda};"></span>'
                    f'<span style="font-weight: 700; color: #0f172a; font-size: 12.5px;">{nome} '
                    f'<span style="font-size: 11px; font-weight: 500; color: #64748b; white-space: nowrap;">({st_g["munis"]} munis)</span></span>'
                    '</div>'
                    f'{selos}</div>'
                )

            titulo_direita = '' if modo_publico else '<span style="font-size: 11px; color: #64748b; font-weight: 600;">Totais ES</span>'
            card_content = (
                '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 6px;">'
                '<span style="font-weight: 800; font-size: 12px; color: #0f172a; text-transform: uppercase; letter-spacing: 0.05em;">📍 GESTORES / REGIÕES</span>'
                f'{titulo_direita}</div>' + ''.join(linhas)
            )
            legend_control = DockedMuniAndLegendControl(card_content, modo_publico=modo_publico)
            m.add_child(legend_control)

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
