# 🗺️ Mapa de Gestores — CREF22/ES

Versão **pública** do mapa do CREF22/ES: mostra qual gestor responde por cada um
dos 78 municípios do Espírito Santo, os dados oficiais do IBGE e o contato
direto de cada gestor.

## 🔒 O que esta versão NÃO contém

Este repositório é público de propósito e foi montado para não carregar nenhum
dado restrito. Ele **não** inclui:

- Quantidades de academias (PJ) e de profissionais (PF), nem rankings ou
  percentuais derivados;
- O endereço da planilha oficial no Google Sheets, que é a fonte desses números;
- Os arquivos `.xlsx` com a base de dados.

A omissão não é apenas visual: o GeoJSON embarcado na página é filtrado por
`filtrar_geojson_publico()` antes de ser enviado ao navegador, de modo que os
valores de PF/PJ não aparecem nem no código-fonte da página.

A versão completa, com todos esses dados, vive em um repositório privado e é
publicada como um aplicativo separado, de acesso restrito.

## 📁 Estrutura

```
├── data/
│   ├── es_municipios.geojson   # Malha oficial IBGE dos 78 municípios
│   └── municipios_es.json      # Metadados oficiais (população, área, região)
├── src/
│   ├── base_municipios.py      # Malha, metadados e atribuição de gestores
│   ├── map_generator.py        # Mapa interativo (Folium)
│   └── ui_comum.py             # Contatos dos gestores e card do município
├── app_publico.py              # Aplicativo Streamlit
└── requirements.txt
```

Os arquivos acima são sincronizados a partir do repositório principal por
`sincronizar_publico.py` — edite-os lá, não aqui, para as duas versões não
divergirem.

## 🛠️ Rodar localmente

```powershell
pip install -r requirements.txt
python -m streamlit run app_publico.py
```

Não há configuração nem credenciais: todos os dados vêm dos arquivos estáticos
em `data/`, sem acesso à rede.
