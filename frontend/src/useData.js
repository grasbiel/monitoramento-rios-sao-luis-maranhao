import { useEffect, useMemo, useState } from "react";

const saudeDe = (conf) => (conf >= 60 ? "good" : conf >= 40 ? "mid" : "bad");
const media = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null);

// Carrega o JSON gerado pelo Python (public/dashboard-data.json)
export function useData() {
  const [raw, setRaw] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    fetch("dashboard-data.json")
      .then((r) => {
        if (!r.ok) throw new Error("Falha ao carregar dados");
        return r.json();
      })
      .then(setRaw)
      .catch((e) => setErro(e.message));
  }, []);

  return { raw, erro };
}

// Recalcula todos os agregados a partir das amostras filtradas
export function agregar(raw, anosSel, riosSel) {
  if (!raw) return null;
  const L = raw.limites;
  const samples = raw.samples.filter(
    (s) => anosSel.has(s.ano) && riosSel.has(s.rio)
  );
  const total = samples.length;

  const conforme = (s) => {
    if (s.ph != null && !(s.ph >= L.phMin && s.ph <= L.phMax)) return false;
    if (s.od != null && s.od < L.odMin) return false;
    if (s.turb != null && s.turb > L.turbMax) return false;
    return true;
  };
  const conformes = samples.filter(conforme).length;
  const conformidade = total ? +((conformes / total) * 100).toFixed(1) : 0;

  // por rio
  const porRio = {};
  for (const s of samples) (porRio[s.rio] ||= []).push(s);
  let rios = Object.entries(porRio).map(([nome, g]) => {
    const conf = +((g.filter(conforme).length / g.length) * 100).toFixed(1);
    return {
      nome,
      n: g.length,
      conf,
      od: round(media(g.filter((x) => x.od != null).map((x) => x.od)), 2),
      turb: round(media(g.filter((x) => x.turb != null).map((x) => x.turb)), 1),
      ph: round(media(g.filter((x) => x.ph != null).map((x) => x.ph)), 2),
      saude: saudeDe(conf),
    };
  });
  rios.sort((a, b) => b.conf - a.conf);

  // por parâmetro
  const bloco = (key, ok) => {
    const validos = samples.filter((s) => s[key] != null);
    const c = validos.filter((s) => ok(s[key])).length;
    return { conforme: c, naoConforme: validos.length - c, semDado: total - validos.length };
  };
  const phB = bloco("ph", (v) => v >= L.phMin && v <= L.phMax);
  const odB = bloco("od", (v) => v >= L.odMin);
  const tbB = bloco("turb", (v) => v <= L.turbMax);
  const viol = { pH: phB.naoConforme, OD: odB.naoConforme, Turbidez: tbB.naoConforme };
  const piorParam = Object.keys(viol).reduce((a, b) => (viol[a] >= viol[b] ? a : b));
  const parametros = [
    { nome: "pH", ...phB, limite: "6,0 – 9,0", vilao: piorParam === "pH" },
    { nome: "Oxigênio Dissolvido", curto: "OD", ...odB, limite: "≥ 5,0 mg/L", vilao: piorParam === "OD" },
    { nome: "Turbidez", ...tbB, limite: "≤ 100 NTU", vilao: piorParam === "Turbidez" },
  ];

  // por ano
  const porAno = {};
  for (const s of samples) (porAno[s.ano] ||= []).push(s);
  const anos = Object.entries(porAno)
    .map(([ano, g]) => ({
      ano: String(ano),
      conf: Math.round((g.filter(conforme).length / g.length) * 100),
      n: g.length,
      od: round(media(g.filter((x) => x.od != null).map((x) => x.od)), 2),
    }))
    .sort((a, b) => a.ano.localeCompare(b.ano));

  // geo (normaliza lat/lon reais para 0–1)
  const b = raw.bounds;
  const dlon = b.lonMax - b.lonMin || 1;
  const dlat = b.latMax - b.latMin || 1;
  const saudePorRio = Object.fromEntries(rios.map((r) => [r.nome, r.saude]));
  const geo = Object.entries(porRio)
    .map(([nome, g]) => {
      const pts = g.filter((s) => s.lat != null && s.lon != null);
      if (!pts.length) return null;
      const x = (media(pts.map((p) => p.lon)) - b.lonMin) / dlon;
      const y = (b.latMax - media(pts.map((p) => p.lat))) / dlat;
      return { nome, n: g.length, x: +x.toFixed(3), y: +y.toFixed(3), saude: saudePorRio[nome] || "mid" };
    })
    .filter(Boolean);

  // crítico + vilão
  const critico = rios.length ? rios.reduce((a, b) => (a.conf <= b.conf ? a : b)) : null;
  const vilaoReprovas = viol[piorParam];
  const vilaoMap = { pH: "pH", OD: "Oxigênio Dissolvido", Turbidez: "Turbidez" };

  const meta = {
    ...raw.meta,
    amostras: total,
    rios: rios.length,
    conformidade,
    reprovadas: total - conformes,
    criticoNome: critico ? `Rio ${critico.nome}` : "—",
    criticoConf: critico ? critico.conf : 0,
    vilao: vilaoMap[piorParam],
    vilaoReprovas,
    vilaoPct: total ? Math.round((vilaoReprovas / total) * 100) : 0,
  };

  return { meta, rios, parametros, anos, geo };
}

function round(v, dec) {
  if (v == null || Number.isNaN(v)) return null;
  return +v.toFixed(dec);
}
