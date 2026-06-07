import { useMemo, useState } from "react";
import { T, saude as saudeCor, fmt } from "./theme";
import { useData, agregar } from "./useData";
import { Trend, MiniMap } from "./components/Charts";
import { KpiCard, ParamCard, RiverMatrix, Pill } from "./components/Pieces";

const TABS = ["Visão geral", "Conformidade", "Evolução temporal", "Mapa"];

function Drop() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill={T.blue}>
      <path d="M12 2.5C12 2.5 5 10 5 15a7 7 0 0 0 14 0c0-5-7-12.5-7-12.5z" />
    </svg>
  );
}

function CardHead({ title, micro }) {
  return (
    <div className="flex justify-between items-center" style={{ padding: "16px 18px 12px", gap: 10 }}>
      <span style={{ fontSize: 14.5, fontWeight: 700, letterSpacing: "-0.01em" }}>{title}</span>
      {micro && <span className="micro">{micro}</span>}
    </div>
  );
}

export default function App() {
  const { raw, erro } = useData();
  const [tab, setTab] = useState(0);

  // estado de filtros
  const todosAnos = useMemo(() => (raw ? [...new Set(raw.samples.map((s) => s.ano))].sort() : []), [raw]);
  const todosRios = useMemo(
    () => (raw ? raw.rios.map((r) => r.nome) : []),
    [raw]
  );
  const [anosSel, setAnosSel] = useState(null);
  const [riosSel, setRiosSel] = useState(null);

  const anosAtivos = anosSel ?? new Set(todosAnos);
  const riosAtivos = riosSel ?? new Set(todosRios);

  const D = useMemo(
    () => (raw ? agregar(raw, anosAtivos, riosAtivos) : null),
    [raw, anosAtivos, riosAtivos]
  );

  if (erro) return <Centro>Erro ao carregar dados: {erro}. Rode <code className="mx-1 font-mono">python gerar_dados_painel.py</code>.</Centro>;
  if (!raw || !D) return <Centro>Carregando painel…</Centro>;

  const toggle = (set, val, all, cur) => {
    const base = new Set(cur ?? all);
    base.has(val) ? base.delete(val) : base.add(val);
    set(base);
  };

  const m = D.meta;

  return (
    <div className="min-h-full" style={{ background: T.paper2 }}>
      {/* TOP BAR */}
      <div className="bg-paper border-b border-hair" style={{ padding: "0 26px" }}>
        <div className="flex items-center justify-between" style={{ padding: "16px 0 14px" }}>
          <div className="flex items-center" style={{ gap: 11 }}>
            <Drop />
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em" }}>Monitoramento Hídrico</div>
              <div className="micro">Qualidade da água · São Luís — MA</div>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="op-btn">{raw.meta.periodo} <span style={{ color: T.ink3 }}>▾</span></div>
            <button className="op-btn pri" onClick={() => window.print()}>Exportar relatório</button>
          </div>
        </div>
        <div className="flex" style={{ gap: 26 }}>
          {TABS.map((t, i) => (
            <div key={t} className={"op-tab" + (i === tab ? " on" : "")} onClick={() => setTab(i)}>{t}</div>
          ))}
        </div>
      </div>

      {/* BODY */}
      <div className="grid items-start" style={{ gridTemplateColumns: "256px 1fr", gap: 22, padding: "22px 26px 28px" }}>
        {/* SIDEBAR */}
        <div className="flex flex-col" style={{ gap: 16 }}>
          <div className="card">
            <div style={{ padding: "15px 16px 12px", borderBottom: `1px solid ${T.hair2}` }}>
              <span style={{ fontSize: 14.5, fontWeight: 700 }}>Filtros</span>
            </div>
            <div style={{ padding: "14px 16px" }}>
              <div className="micro" style={{ marginBottom: 10 }}>Período</div>
              <div className="flex flex-wrap" style={{ gap: 7 }}>
                {todosAnos.map((a) => (
                  <span
                    key={a}
                    className={"op-chip " + (anosAtivos.has(a) ? "on" : "off")}
                    onClick={() => toggle(setAnosSel, a, todosAnos, anosSel)}
                  >
                    {a}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ padding: "4px 16px 16px" }}>
              <div className="micro" style={{ marginBottom: 8 }}>Rios monitorados</div>
              {raw.rios.map((r) => {
                const on = riosAtivos.has(r.nome);
                return (
                  <div key={r.nome} className="op-rio" onClick={() => toggle(setRiosSel, r.nome, todosRios, riosSel)}>
                    <span
                      className="flex items-center justify-center"
                      style={{
                        width: 16, height: 16, borderRadius: 4,
                        border: `1.5px solid ${saudeCor(r.saude)}`,
                        background: on ? saudeCor(r.saude) : "transparent",
                      }}
                    >
                      {on && (
                        <svg width="9" height="9" viewBox="0 0 10 10" fill="none" stroke="#fff" strokeWidth="2"><path d="M2 5l2 2 4-5" /></svg>
                      )}
                    </span>
                    <span className="flex-1" style={{ fontSize: 13.5, fontWeight: 500, opacity: on ? 1 : 0.5 }}>{r.nome}</span>
                    <span className="font-mono" style={{ fontSize: 11.5, fontWeight: 600, color: saudeCor(r.saude) }}>{fmt(r.conf, 0)}%</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card" style={{ padding: "15px 16px", background: T.navy, border: "none" }}>
            <div className="micro" style={{ color: T.blueMid }}>Referência</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", marginTop: 6 }}>CONAMA 357/2005</div>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 8, lineHeight: 1.5 }}>
              pH 6–9 · OD ≥ 5 mg/L · Turbidez ≤ 100 NTU
            </div>
          </div>
        </div>

        {/* MAIN */}
        <div className="flex flex-col" style={{ gap: 16 }}>
          {/* KPIs — visíveis em todas as abas */}
          <div className="flex" style={{ gap: 14 }}>
            <KpiCard label="Amostras" value={String(m.amostras)} accent={T.blue} delta={`${m.rios} rios · ${raw.meta.periodo}`} />
            <KpiCard label="Conformidade" value={fmt(m.conformidade, 1)} sub="%" tone={T.red} accent={T.red} delta={`${fmt(100 - m.conformidade, 1)}% reprovam em ≥1 padrão`} />
            <KpiCard label="Rio crítico" value={m.criticoNome.replace("Rio ", "")} accent={T.red} delta={`${fmt(m.criticoConf, 1)}% conforme`} />
            <KpiCard label="Parâmetro vilão" value={m.vilao === "Oxigênio Dissolvido" ? "OD" : m.vilao} accent={T.amber} delta={`${m.vilaoReprovas} reprovas · ${m.vilaoPct}% do total`} />
          </div>

          {tab === 0 && <VisaoGeral D={D} />}
          {tab === 1 && <Conformidade D={D} />}
          {tab === 2 && <Evolucao D={D} />}
          {tab === 3 && <Mapa D={D} />}
        </div>
      </div>
    </div>
  );
}

// ── VISÃO GERAL ──────────────────────────────────────────────────
function VisaoGeral({ D }) {
  return (
    <>
      <div className="grid" style={{ gridTemplateColumns: "1fr 280px", gap: 16 }}>
        <RiverMatrix rios={D.rios} />
        <ParamPanel parametros={D.parametros} />
      </div>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="card">
          <CardHead title="Conformidade por ano" micro={`média ${fmt(D.meta.conformidade, 1)}%`} />
          <div style={{ padding: "0 18px 18px" }}><Trend anos={D.anos} media={D.meta.conformidade} /></div>
        </div>
        <div className="card">
          <CardHead title="Distribuição espacial" micro="nº de amostras por ponto" />
          <div style={{ padding: "0 18px 18px" }}><MiniMap geo={D.geo} /></div>
        </div>
      </div>
    </>
  );
}

// ── CONFORMIDADE ─────────────────────────────────────────────────
function Conformidade({ D }) {
  return (
    <div className="grid" style={{ gridTemplateColumns: "320px 1fr", gap: 16 }}>
      <ParamPanel parametros={D.parametros} />
      <RiverMatrix rios={D.rios} />
    </div>
  );
}

// ── EVOLUÇÃO TEMPORAL ────────────────────────────────────────────
function Evolucao({ D }) {
  return (
    <>
      <div className="card">
        <CardHead title="Conformidade por ano" micro={`média ${fmt(D.meta.conformidade, 1)}%`} />
        <div style={{ padding: "0 18px 18px" }}><Trend anos={D.anos} media={D.meta.conformidade} /></div>
      </div>
      <div className="card">
        <CardHead title="Detalhamento anual" micro="conformidade · amostras · OD médio" />
        <div style={{ padding: "0 18px 16px" }}>
          <div className="grid micro" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10, padding: "0 0 10px", borderBottom: `1px solid ${T.hair}` }}>
            {["Ano", "Conformidade", "Amostras", "OD médio"].map((h, i) => (
              <span key={h} style={{ textAlign: i ? "right" : "left" }}>{h}</span>
            ))}
          </div>
          {D.anos.map((a) => (
            <div key={a.ano} className="op-row grid items-center" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10, padding: "10px 6px", margin: "0 -6px", borderBottom: `1px solid ${T.hair2}`, borderRadius: 6 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>{a.ano}</span>
              <span className="num text-right font-mono" style={{ fontSize: 13, fontWeight: 700, color: a.conf >= 50 ? T.green : a.conf >= 40 ? T.amber : T.red }}>{a.conf}%</span>
              <span className="num text-right" style={{ fontSize: 13, color: T.ink2 }}>{a.n}</span>
              <span className="num text-right" style={{ fontSize: 13, color: a.od != null && a.od < 5 ? T.red : T.ink2 }}>{fmt(a.od, 2)}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ── MAPA ─────────────────────────────────────────────────────────
function Mapa({ D }) {
  return (
    <div className="card">
      <CardHead title="Distribuição espacial dos pontos" micro="cor = saúde · tamanho = nº de amostras" />
      <div style={{ padding: "0 18px 18px" }}>
        <MiniMap geo={D.geo} />
        <div className="flex" style={{ gap: 18, marginTop: 14 }}>
          {[["Conforme (≥60%)", T.green], ["Atenção (40–60%)", T.amber], ["Crítico (<40%)", T.red]].map(([l, c]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: c }} />
              <span style={{ fontSize: 12, color: T.ink2 }}>{l}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ParamPanel({ parametros }) {
  return (
    <div className="card">
      <CardHead title="Por parâmetro" />
      <div style={{ padding: "0 18px 16px" }}>
        {parametros.map((p) => <ParamCard key={p.nome} p={p} />)}
        <div className="flex" style={{ gap: 14, marginTop: 14 }}>
          {[["Conf.", T.green], ["Não", T.red], ["S/dado", T.gray]].map(([l, col]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span style={{ width: 9, height: 9, borderRadius: 2, background: col }} />
              <span style={{ fontSize: 11.5, color: T.ink2 }}>{l}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Centro({ children }) {
  return <div className="flex items-center justify-center min-h-screen text-ink2 text-sm px-6 text-center">{children}</div>;
}
