"""Núcleo estático do mapa: malha do IBGE, metadados dos municípios e a
atribuição de gestores.

Separado de data_loader.py de propósito. Este módulo não conhece o Google
Sheets nem os dados de PF/PJ, e por isso pode ser publicado junto da versão
pública do aplicativo. Tudo o que envolve a planilha fica em data_loader.py,
usado apenas pela versão completa.
"""

import os
import re
import json
import unicodedata
import pandas as pd


def normalize_text(text: str) -> str:
    """Remove acentos, pontuações e converte para minúsculas para matching resiliente."""
    if not isinstance(text, str):
        text = str(text) if pd.notna(text) else ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.strip().lower()

# Mapeamento oficial dos Gestores.
# Fica no código, não na planilha: a versão pública precisa saber o gestor de
# cada município sem baixar nada do Google Sheets, que traz os dados de PF/PJ.
GESTORES_MAP = {
    'BRUNA': [
        'Água Doce do Norte', 'Ecoporanga', 'Barra de São Francisco', 'Vila Pavão',
        'Mucurici', 'Ponto Belo', 'Montanha', 'Boa Esperança', 'Pinheiros',
        'Pedro Canário', 'Conceição da Barra', 'São Mateus', 'Jaguaré',
        'Nova Venécia', 'Sooretama', 'Soretama', 'Linhares', 'Vitória', 'Rio Bananal'
    ],
    'ALESSANDRA': [
        'Mantenópolis', 'Alto Rio Novo', 'Águia Branca', 'Pancas',
        'São Domingos do Norte', 'São Gabriel da Palha', 'Gabriel da Palha', 'Vila Valério',
        'Governador Lindenberg', 'Marilândia', 'Colatina', 'Baixo Guandu',
        'Laranja da Terra', 'Itaguaçu', 'São Roque do Canaã', 'Santa Teresa',
        'Itarana', 'Santa Maria de Jetibá', 'Santa Maria de Itibá', 'Santa Leopoldina',
        'Cariacica', 'Viana', 'Vila Velha'
    ],
    'AMANDA': [
        'Afonso Cláudio', 'Brejetuba', 'Ibatiba', 'Ibitirama', 'Irupi', 'Iúna',
        'Muniz Freire', 'Conceição do Castelo', 'Venda Nova do Imigrante',
        'Domingos Martins', 'Marechal Floriano', 'Alfredo Chaves', 'Vargem Alta',
        'Castelo', 'Iconha', 'Coia', 'Rio Novo do Sul', 'Atílio Vivacqua', 'Atílio Vivácqua',
        'Cachoeiro de Itapemirim', 'Jerônimo Monteiro', 'Muqui', 'Mimoso do Sul',
        'Apiacá', 'Bom Jesus do Norte', 'São José do Calçado', 'Guaçuí',
        'Alegre', 'Divino de São Lourenço', 'Domingo de São Lourenço',
        'Dores do Rio Preto', 'Domingo do Rio Preto'
    ],
    'PABLO': [
        'Aracruz', 'João Neiva', 'Ibiraçu', 'Fundão',
        'Serra', 'Guarapari', 'Anchieta', 'Piúma',
        'Itapemirim', 'Marataízes', 'Presidente Kennedy'
    ]
}

MUNI_PARA_GESTOR = {}
for gestor, mlist in GESTORES_MAP.items():
    for mname in mlist:
        MUNI_PARA_GESTOR[normalize_text(mname)] = gestor

# Alias específicos
MUNI_PARA_GESTOR['soretama'] = 'BRUNA'
MUNI_PARA_GESTOR['gabriel da palha'] = 'ALESSANDRA'
MUNI_PARA_GESTOR['santa maria de itiba'] = 'ALESSANDRA'
MUNI_PARA_GESTOR['coia'] = 'AMANDA'
MUNI_PARA_GESTOR['domingo de sao lourenco'] = 'AMANDA'
MUNI_PARA_GESTOR['domingo do rio preto'] = 'AMANDA'

def gestor_do_municipio(nome_municipio):
    """Gestor responsável por um município, tolerante a variações de grafia."""
    norm = normalize_text(nome_municipio)
    if norm in MUNI_PARA_GESTOR:
        return MUNI_PARA_GESTOR[norm]
    for k, v in MUNI_PARA_GESTOR.items():
        if len(k) > 4 and (k in norm or norm in k):
            return v
    return 'OUTROS'


class BaseMunicipios:
    """Carrega a malha oficial e os metadados dos 78 municípios do ES."""

    def __init__(self, geojson_path="data/es_municipios.geojson", metadata_path="data/municipios_es.json"):
        self.geojson_path = geojson_path
        self.metadata_path = metadata_path
        self.municipios_df = None
        self.raw_geojson = None
        self._load_reference_data()

    def _load_reference_data(self):
        """Carrega dados oficiais de referência do IBGE para os 78 municípios do ES."""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.municipios_df = pd.DataFrame(data)
            self.municipios_df['Codigo_IBGE'] = self.municipios_df['Codigo_IBGE'].astype(str)
            self.municipios_df['nome_norm'] = self.municipios_df['Municipio'].apply(normalize_text)
        else:
            raise FileNotFoundError(f"Arquivo de metadados não encontrado em: {self.metadata_path}")

        if os.path.exists(self.geojson_path):
            with open(self.geojson_path, 'r', encoding='utf-8') as f:
                self.raw_geojson = json.load(f)
        else:
            raise FileNotFoundError(f"Arquivo GeoJSON não encontrado em: {self.geojson_path}")

    def carregar_base_publica(self) -> pd.DataFrame:
        """Base da versão pública: identificação, dados do IBGE e gestor.

        Não acessa o Google Sheets nem devolve colunas de PF/PJ — a versão
        pública não deve sequer carregar esses números na memória. Tudo vem do
        metadados oficial em data/municipios_es.json e do mapa de gestores,
        ambos estáticos.
        """
        df = self.municipios_df.drop(columns=['nome_norm'], errors='ignore').copy()
        df['Gestor'] = df['Municipio'].apply(gestor_do_municipio)
        return df.sort_values('Municipio').reset_index(drop=True)

    def get_enriched_geojson(self, df_processed: pd.DataFrame) -> dict:
        """
        Retorna o GeoJSON com todas as propriedades e métricas calculadas embutidas em cada polígono.
        """
        geojson_copy = json.loads(json.dumps(self.raw_geojson))
        data_lookup = df_processed.set_index('Codigo_IBGE').to_dict(orient='index')

        for feature in geojson_copy['features']:
            cod = str(feature['properties'].get('codarea', ''))
            if cod in data_lookup:
                info = data_lookup[cod]
                feature['properties'].update({
                    'name': info.get('Municipio', ''),
                    'municipio': info.get('Municipio', ''),
                    'gestor': info.get('Gestor', ''),
                    'cod_ibge': cod,
                    'pj_academias': int(info.get('Quantidade de PJ de Academias', 0)),
                    'pf_profissionais': int(info.get('Quantidade de Profissionais PF', 0)),
                    'total': int(info.get('Total (PF + PJ)', 0)),
                    'ranking_pj': int(info.get('Ranking_PJ', 0)),
                    'ranking_pf': int(info.get('Ranking_PF', 0)),
                    'perc_pj': float(info.get('Perc_PJ', 0)),
                    'perc_pf': float(info.get('Perc_PF', 0)),
                    'microrregiao': info.get('Microrregiao', ''),
                    'mesorregiao': info.get('Mesorregiao', ''),
                    'populacao': int(info.get('Populacao_IBGE_2022', 0)),
                    'area_km2': float(info.get('Area_km2', 0.0)),
                    'densidade': float(info.get('Densidade_Demografica', 0.0))
                })
            else:
                feature['properties'].update({
                    'gestor': '',
                    'pj_academias': 0,
                    'pf_profissionais': 0,
                    'total': 0,
                    'ranking_pj': 0,
                    'ranking_pf': 0,
                    'perc_pj': 0.0,
                    'perc_pf': 0.0,
                    'populacao': 0,
                    'area_km2': 0.0,
                    'densidade': 0.0
                })

        return geojson_copy
