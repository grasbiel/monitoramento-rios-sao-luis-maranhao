import { T, saude as saudeCor, saudeLt, saudeLabel, fmt } from "../theme";

export function Pill({ s }) {
  return (
    <span
      className="font-bold uppercase whitespace-nowrap"
      style={{ fontSize: 11, letterSpacing: "0.03em", color: saudeCor(s), background: saudeLt(s), padding: "4px 9px", borderRadius: 6 }}
    >
      {saudeLabel(s)}
    </span>
  );
}

export function KpiCard({ label, value, sub, tone, accent, delta }) {
  return (
    <div className="card flex-1" style={{ padding: "16px 18px" }}>
      <div className="flex justify-between items-center" style={{ marginBottom: 14 }}>
        <span className="micro">{label}</span>
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: accent }} />
      </div>
      <div className="flex items-baseline gap-1">
        <span style={{ fontSize: value.length > 7 ? 26 : 32, fontWeight: 700, letterSpacing: "-0.03em", color: tone || T.ink, lineHeight: 1 }}>{value}</span>
        {sub && <span style={{ fontSize: 18, fontWeight: 600, color: tone || T.ink }}>{sub}</span>}
      </div>
      <div style={{ fontSize: 12.5, color: T.ink2, marginTop: 9 }}>{delta}</div>
    </div>
  );
}

export function ParamCard({ p }) {
  const total = p.conforme + p.naoConforme + p.semDado;
  const pct = total ? Math.round((p.conforme / total) * 100) : 0;
  const w = (v) => (total ? (v / total) * 100 : 0) + "%";
  return (
    <div style={{ padding: "14px 0", borderTop: `1px solid ${T.hair2}` }}>
      <div className="flex justify-between items-baseline" style={{ marginBottom: 9 }}>
        <span style={{ fontSize: 13.5, fontWeight: 700 }}>{p.curto || p.nome}</span>
        <span className="flex items-baseline gap-1.5">
          <span style={{ fontSize: 18, fontWeight: 700, color: p.vilao ? T.red : T.green, letterSpacing: "-0.02em" }}>{pct}%</span>
          <span style={{ fontSize: 11, color: T.ink3 }}>conf.</span>
        </span>
      </div>
      <div className="flex overflow-hidden" style={{ height: 8, borderRadius: 4, background: T.hair2 }}>
        <div style={{ width: w(p.conforme), background: T.green }} />
        <div style={{ width: w(p.naoConforme), background: T.red }} />
        <div style={{ width: w(p.semDado), background: T.gray }} />
      </div>
      <div className="micro" style={{ marginTop: 7 }}>{p.conforme} conf · {p.naoConforme} não · limite {p.limite}</div>
    </div>
  );
}

export function RiverMatrix({ rios }) {
  const cols = "1.4fr 0.7fr 0.7fr 0.7fr 1.5fr 0.9fr";
  return (
    <div className="card">
      <div className="flex justify-between items-center" style={{ padding: "16px 18px 12px", gap: 10 }}>
        <span style={{ fontSize: 14.5, fontWeight: 700, letterSpacing: "-0.01em" }}>Matriz por rio</span>
        <span className="micro">ordenado por conformidade</span>
      </div>
      <div style={{ padding: "0 18px 10px" }}>
        <div className="grid items-center" style={{ gridTemplateColumns: cols, gap: 10, padding: "0 0 10px", borderBottom: `1px solid ${T.hair}` }}>
          {["Rio", "OD", "Turb", "pH", "Conformidade", "Status"].map((h, i) => (
            <span key={h} className="micro" style={{ textAlign: i >= 1 && i <= 3 ? "right" : "left" }}>{h}</span>
          ))}
        </div>
        {rios.length === 0 && <div className="text-ink3 text-sm py-6 text-center">Sem dados para os filtros atuais.</div>}
        {rios.map((r) => {
          const c = saudeCor(r.saude);
          return (
            <div key={r.nome} className="op-row grid items-center" style={{ gridTemplateColumns: cols, gap: 10, padding: "11px 6px", margin: "0 -6px", borderBottom: `1px solid ${T.hair2}`, borderRadius: 6 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>{r.nome}</span>
              <span className="num text-right" style={{ fontSize: 13, fontWeight: 600, color: r.od != null && r.od < 5 ? T.red : T.ink }}>{fmt(r.od, 2)}</span>
              <span className="num text-right" style={{ fontSize: 13, color: r.turb != null && r.turb > 100 ? T.red : T.ink2 }}>{fmt(r.turb, 0)}</span>
              <span className="num text-right" style={{ fontSize: 13, color: T.ink2 }}>{fmt(r.ph, 1)}</span>
              <span className="flex items-center gap-2.5">
                <span className="flex-1 overflow-hidden" style={{ height: 6, background: T.hair2, borderRadius: 3 }}>
                  <span className="block h-full" style={{ width: r.conf + "%", background: c, borderRadius: 3 }} />
                </span>
                <span className="num font-mono font-bold text-right" style={{ fontSize: 11.5, color: c, minWidth: 34 }}>{fmt(r.conf, 0)}%</span>
              </span>
              <span className="justify-self-end"><Pill s={r.saude} /></span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
