"""
Gera o JSON consumido pelo painel React (Direção B — Operational Panel).

Lê data/processed/dados_tratados_tcc.csv e deriva os agregados no mesmo
formato do `window.WQ` do handoff de design:
  meta · rios[] · parametros[] · anos[] · geo[]

Regra de conformidade (CONAMA 357/2005): uma amostra é conforme quando
atende SIMULTANEAMENTE a pH ∈ [6, 9], OD ≥ 5,0 mg/L e turbidez ≤ 100 NTU.

Saída: frontend/public/dashboard-data.json
"""
import json
import os
import unicodedata

import numpy as np
import pandas as pd

CAMINHO_CSV = "data/processed/dados_tratados_tcc.csv"
CAMINHO_SAIDA = "frontend/public/dashboard-data.json"

# Limites CONAMA 357/2005
PH_MIN, PH_MAX = 6.0, 9.0
OD_MIN = 5.0
TURB_MAX = 100.0


def titulo_rio(nome: str) -> str:
    """RIO JAGUAREMA -> Jaguarema ; RIO DOS CACHORROS -> Dos Cachorros."""
    if not isinstance(nome, str):
        return "Desconhecido"
    txt = nome.strip().upper()
    if txt.startswith("RIO "):
        txt = txt[4:]
    return txt.title()


def saude_de(conf: float) -> str:
    if conf >= 60:
        return "good"
    if conf >= 40:
        return "mid"
    return "bad"


def carregar() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_CSV)
    df["data"] = pd.to_datetime(df["data"], format="mixed", errors="coerce", dayfirst=True)
    df = df.dropna(subset=["data"])
    df["ano"] = df["data"].dt.year.astype(int)

    for col in ["ph", "od", "turbidez", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")

    df["rio_nome"] = df["rio"].apply(titulo_rio)
    return df


def conformidade_amostra(row) -> bool:
    """True se a amostra é conforme em TODOS os parâmetros com dado (0 = sem dado)."""
    ph, od, turb = row["ph"], row["od"], row["turbidez"]
    if pd.notna(ph) and ph > 0 and not (PH_MIN <= ph <= PH_MAX):
        return False
    if pd.notna(od) and od > 0 and od < OD_MIN:
        return False
    if pd.notna(turb) and turb > 0 and turb > TURB_MAX:
        return False
    return True


def calcular_meta(df: pd.DataFrame, rios: list) -> dict:
    total = len(df)
    conformes = int(df["_conforme"].sum())
    conformidade = round(conformes / total * 100, 1) if total else 0.0

    # rio mais crítico (menor conformidade)
    critico = min(rios, key=lambda r: r["conf"]) if rios else None

    # parâmetro vilão = mais não-conformidades
    viol = {
        "pH": int(((df["ph"] > 0) & ~df["ph"].between(PH_MIN, PH_MAX)).sum()),
        "Oxigênio Dissolvido": int(((df["od"] > 0) & (df["od"] < OD_MIN)).sum()),
        "Turbidez": int(((df["turbidez"] > 0) & (df["turbidez"] > TURB_MAX)).sum()),
    }
    vilao_nome = max(viol, key=viol.get)
    vilao_reprovas = viol[vilao_nome]

    return {
        "local": "Ilha de São Luís — Maranhão",
        "norma": "Resolução CONAMA 357/2005",
        "periodo": f"{int(df['ano'].min())} – {int(df['ano'].max())}",
        "amostras": total,
        "rios": df["rio_nome"].nunique(),
        "conformidade": conformidade,
        "reprovadas": total - conformes,
        "criticoNome": f"Rio {critico['nome']}" if critico else "—",
        "criticoConf": critico["conf"] if critico else 0.0,
        "vilao": vilao_nome,
        "vilaoReprovas": vilao_reprovas,
        "vilaoPct": round(vilao_reprovas / total * 100) if total else 0,
    }


def calcular_rios(df: pd.DataFrame) -> list:
    out = []
    for nome, g in df.groupby("rio_nome"):
        n = len(g)
        conf = round(g["_conforme"].sum() / n * 100, 1) if n else 0.0
        od_med = g.loc[g["od"] > 0, "od"].mean()
        turb_med = g.loc[g["turbidez"] > 0, "turbidez"].mean()
        ph_med = g.loc[g["ph"] > 0, "ph"].mean()
        out.append({
            "nome": nome,
            "n": n,
            "conf": conf,
            "od": round(float(od_med), 2) if pd.notna(od_med) else None,
            "turb": round(float(turb_med), 1) if pd.notna(turb_med) else None,
            "ph": round(float(ph_med), 2) if pd.notna(ph_med) else None,
            "saude": saude_de(conf),
        })
    return sorted(out, key=lambda r: r["conf"], reverse=True)


def calcular_parametros(df: pd.DataFrame) -> list:
    total = len(df)

    def bloco(serie, ok_func):
        sem = int((serie.isna() | (serie == 0)).sum())
        validos = serie[(serie.notna()) & (serie > 0)]
        conf = int(ok_func(validos).sum())
        nao = int(len(validos) - conf)
        return conf, nao, sem

    ph_c, ph_n, ph_s = bloco(df["ph"], lambda s: s.between(PH_MIN, PH_MAX))
    od_c, od_n, od_s = bloco(df["od"], lambda s: s >= OD_MIN)
    tb_c, tb_n, tb_s = bloco(df["turbidez"], lambda s: s <= TURB_MAX)

    viol = {"pH": ph_n, "OD": od_n, "Turbidez": tb_n}
    pior = max(viol, key=viol.get)

    return [
        {"nome": "pH", "conforme": ph_c, "naoConforme": ph_n, "semDado": ph_s,
         "limite": "6,0 – 9,0", "unidade": "", "vilao": pior == "pH"},
        {"nome": "Oxigênio Dissolvido", "curto": "OD", "conforme": od_c, "naoConforme": od_n,
         "semDado": od_s, "limite": "≥ 5,0 mg/L", "unidade": "mg/L", "vilao": pior == "OD"},
        {"nome": "Turbidez", "conforme": tb_c, "naoConforme": tb_n, "semDado": tb_s,
         "limite": "≤ 100 NTU", "unidade": "NTU", "vilao": pior == "Turbidez"},
    ]


def calcular_anos(df: pd.DataFrame) -> list:
    out = []
    for ano, g in df.groupby("ano"):
        n = len(g)
        conf = round(g["_conforme"].sum() / n * 100) if n else 0
        od_med = g.loc[g["od"] > 0, "od"].mean()
        out.append({
            "ano": str(int(ano)),
            "conf": conf,
            "n": n,
            "od": round(float(od_med), 2) if pd.notna(od_med) else None,
        })
    return sorted(out, key=lambda a: a["ano"])


def calcular_geo(df: pd.DataFrame, rios: list) -> list:
    """Normaliza lat/long reais para 0–1 (x=oeste→leste, y=norte→sul)."""
    saude_por_rio = {r["nome"]: r["saude"] for r in rios}
    coords = df.dropna(subset=["latitude", "longitude"])
    if coords.empty:
        return []

    lon_min, lon_max = coords["longitude"].min(), coords["longitude"].max()
    lat_min, lat_max = coords["latitude"].min(), coords["latitude"].max()
    dlon = (lon_max - lon_min) or 1
    dlat = (lat_max - lat_min) or 1

    out = []
    for nome, g in coords.groupby("rio_nome"):
        x = float((g["longitude"].mean() - lon_min) / dlon)   # oeste→leste
        y = float((lat_max - g["latitude"].mean()) / dlat)    # norte→sul
        out.append({
            "nome": nome,
            "n": len(g),
            "x": round(x, 3),
            "y": round(y, 3),
            "saude": saude_por_rio.get(nome, "mid"),
        })
    return out


def calcular_samples(df: pd.DataFrame) -> list:
    """Amostras individuais (enxutas) para o frontend recalcular agregados ao filtrar."""
    coords = df.dropna(subset=["latitude", "longitude"])
    lon_min, lon_max = coords["longitude"].min(), coords["longitude"].max()
    lat_min, lat_max = coords["latitude"].min(), coords["latitude"].max()

    def jnum(v, dec):
        return round(float(v), dec) if pd.notna(v) and v != 0 else None

    out = []
    for _, r in df.iterrows():
        out.append({
            "rio": r["rio_nome"],
            "ano": int(r["ano"]),
            "ph": jnum(r["ph"], 2),
            "od": jnum(r["od"], 2),
            "turb": jnum(r["turbidez"], 1),
            "lat": round(float(r["latitude"]), 6) if pd.notna(r["latitude"]) else None,
            "lon": round(float(r["longitude"]), 6) if pd.notna(r["longitude"]) else None,
        })
    return out, {
        "lonMin": float(lon_min), "lonMax": float(lon_max),
        "latMin": float(lat_min), "latMax": float(lat_max),
    }


def main():
    if not os.path.exists(CAMINHO_CSV):
        raise SystemExit(f"CSV não encontrado: {CAMINHO_CSV}. Rode processamento_dados.py antes.")

    df = carregar()
    df["_conforme"] = df.apply(conformidade_amostra, axis=1)

    rios = calcular_rios(df)
    samples, bounds = calcular_samples(df)
    payload = {
        "meta": calcular_meta(df, rios),
        "rios": rios,
        "parametros": calcular_parametros(df),
        "anos": calcular_anos(df),
        "geo": calcular_geo(df, rios),
        "samples": samples,
        "bounds": bounds,
        "limites": {"phMin": PH_MIN, "phMax": PH_MAX, "odMin": OD_MIN, "turbMax": TURB_MAX},
    }

    os.makedirs(os.path.dirname(CAMINHO_SAIDA), exist_ok=True)
    with open(CAMINHO_SAIDA, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

    print(f"✅ Painel de dados gerado: {CAMINHO_SAIDA}")
    print(f"   {payload['meta']['amostras']} amostras · {payload['meta']['rios']} rios "
          f"· conformidade {payload['meta']['conformidade']}%")


if __name__ == "__main__":
    main()
