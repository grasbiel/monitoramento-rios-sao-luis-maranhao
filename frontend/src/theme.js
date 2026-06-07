// Tokens semânticos e helpers — espelham window.WQT do handoff de design.
export const T = {
  ink: "#13242f",
  ink2: "#52646f",
  ink3: "#8c9aa3",
  hair: "#e3e9ee",
  hair2: "#eef2f5",
  paper: "#ffffff",
  paper2: "#f6f9fb",
  navy: "#16344a",
  blue: "#1f6f9e",
  blueMid: "#3f93c4",
  blueLt: "#e9f2f8",
  blueLt2: "#d6e7f1",
  green: "#2f9e6f",
  greenLt: "#e4f4ec",
  red: "#cd4a3a",
  redLt: "#f8e6e2",
  amber: "#d9963f",
  amberLt: "#f8eedb",
  gray: "#aab4bc",
  grayLt: "#eef1f3",
};

export const saude = (s) => (s === "good" ? T.green : s === "bad" ? T.red : T.amber);
export const saudeLt = (s) => (s === "good" ? T.greenLt : s === "bad" ? T.redLt : T.amberLt);
export const saudeLabel = (s) => (s === "good" ? "Conforme" : s === "bad" ? "Crítico" : "Atenção");

// Formatação pt-BR (vírgula decimal); null/undefined -> "—"
export const fmt = (v, dec = 0) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toFixed(dec).replace(".", ",");
};
