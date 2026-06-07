# Painel de Qualidade da Água — Frontend (React)

Reconstrução da **Direção B — Operational Panel** do handoff de design, em
**React + Vite + Tailwind**. Consome o JSON gerado pelo pipeline Python.

## Fluxo de dados

```
data/raw/dados_brutos.xlsx
        │  (processamento_dados.py)
        ▼
data/processed/dados_tratados_tcc.csv
        │  (gerar_dados_painel.py)
        ▼
frontend/public/dashboard-data.json   ← consumido pelo React
```

Sempre que os dados mudarem, regenere o JSON a partir da raiz do projeto:

```bash
python processamento_dados.py      # (se o CSV mudou)
python gerar_dados_painel.py       # gera frontend/public/dashboard-data.json
```

## Rodar localmente

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Build de produção

```bash
npm run build      # gera frontend/dist/
npm run preview    # serve o build localmente
```

## Estrutura

| Arquivo | Papel |
|---|---|
| `src/theme.js` | Tokens de cor/tipografia + helpers (`saude`, `fmt`) — espelha `window.WQT`. |
| `src/useData.js` | Carrega o JSON e **recalcula os agregados** (meta, rios, parâmetros, anos, geo) a partir das amostras filtradas. |
| `src/App.jsx` | Top bar, tabs, sidebar de filtros (ano/rio) e as 4 visões. |
| `src/components/Charts.jsx` | Gráficos SVG: linha anual (`Trend`) e mapa esquemático (`MiniMap`). |
| `src/components/Pieces.jsx` | `KpiCard`, `ParamCard`, `RiverMatrix`, `Pill`. |

## Filtros

Os chips de **período** e a lista de **rios** filtram de verdade: as amostras
selecionadas são reagregadas no cliente (`agregar()` em `useData.js`), e todos os
KPIs, tabelas e gráficos recalculam.

## Regra de conformidade (CONAMA 357/2005)

Uma amostra é **conforme** quando atende simultaneamente a `pH ∈ [6, 9]`,
`OD ≥ 5,0 mg/L` e `turbidez ≤ 100 NTU`. Valores `0`/ausentes são tratados como
"sem dado" e não reprovam.
