"use client";

import Plotly from "plotly.js-basic-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import type { P2PResponse } from "@/lib/types";

const Plot = createPlotlyComponent(Plotly);

interface Props {
  result: P2PResponse;
}

export default function ProfileChart({ result }: Props) {
  const { profile, horizons, flags } = result;
  if (!profile || profile.length === 0) return null;

  const distances = profile.map((p) => p.d / 1000);
  const terrainB = profile.map((p) => p.terrain_bulge);
  const los = profile.map((p) => p.los);
  const fu = profile.map((p) => p.fresnel_upper);
  const fl = profile.map((p) => p.fresnel_lower);
  const f60 = profile.map((p) => p.fresnel_60);

  const terrainTrace = {
    x: distances,
    y: terrainB,
    name: "Terrain (earth-curved)",
    type: "scatter" as const,
    fill: "tozeroy" as const,
    fillcolor: "rgba(92, 64, 42, 0.55)",
    line: { color: "#8B5A2B", width: 2 },
    hovertemplate: "%{x:.2f} km<br>%{y:.0f} m<extra></extra>",
  };

  const fresnelZone = {
    x: [...distances, ...distances.slice().reverse()],
    y: [...fu, ...fl.slice().reverse()],
    name: "Fresnel F1",
    type: "scatter" as const,
    fill: "toself" as const,
    fillcolor: "rgba(255, 200, 0, 0.12)",
    line: { color: "rgba(255, 200, 0, 0.5)", width: 1 },
    hoverinfo: "skip" as const,
  };

  const f60Trace = {
    x: distances,
    y: f60,
    name: "0.6 F1",
    type: "scatter" as const,
    line: { color: "rgba(255, 200, 0, 0.8)", width: 1, dash: "dot" as const },
    hoverinfo: "skip" as const,
  };

  const losTrace = {
    x: distances,
    y: los,
    name: "LOS",
    type: "scatter" as const,
    line: { color: "#3b82f6", width: 2, dash: "dash" as const },
    hoverinfo: "skip" as const,
  };

  const obstructX: number[] = [];
  const obstructYtop: number[] = [];
  const obstructYbottom: number[] = [];
  profile.forEach((p) => {
    if (p.violates_f1) {
      obstructX.push(p.d / 1000);
      obstructYtop.push(Math.min(p.terrain_bulge, p.fresnel_upper));
      obstructYbottom.push(p.fresnel_lower);
    }
  });

  const traces: Plotly.Data[] = [fresnelZone, f60Trace, losTrace, terrainTrace];

  if (obstructX.length > 1) {
    traces.push({
      x: [...obstructX, ...obstructX.slice().reverse()],
      y: [...obstructYtop, ...obstructYbottom.slice().reverse()],
      name: "Fresnel violation",
      type: "scatter" as const,
      fill: "toself" as const,
      fillcolor: "rgba(239, 68, 68, 0.45)",
      line: { color: "rgba(239, 68, 68, 0.85)", width: 1 },
      hoverinfo: "skip" as const,
    });
  }

  const shapes: Partial<Plotly.Shape>[] = (horizons || []).map((h) => ({
    type: "line" as const,
    x0: h.d_m / 1000,
    x1: h.d_m / 1000,
    yref: "paper" as const,
    y0: 0,
    y1: 1,
    line: { color: "#f59e0b", width: 1.5, dash: "dot" as const },
  }));

  const annotations: Partial<Plotly.Annotations>[] = (horizons || []).map(
    (h, i) => ({
      x: h.d_m / 1000,
      y: 1,
      yref: "paper" as const,
      text: h.role === "tx_horizon" ? "TX horizon" : "RX horizon",
      showarrow: false,
      font: { size: 10, color: "#f59e0b" },
      yshift: -4,
      xshift: i % 2 === 0 ? 30 : -30,
    })
  );

  let flagLabel = "";
  let flagClass = "";
  if (flags?.los_blocked) {
    flagLabel = "LOS blocked";
    flagClass = "text-red-400";
  } else if (flags?.fresnel_60_violated) {
    flagLabel = "0.6 F1 violated";
    flagClass = "text-yellow-400";
  } else if (flags?.fresnel_f1_violated) {
    flagLabel = "F1 grazed";
    flagClass = "text-yellow-400";
  } else {
    flagLabel = "F1 clear";
    flagClass = "text-green-400";
  }

  return (
    <div>
      <Plot
        data={traces}
        layout={{
          margin: { t: 20, r: 20, b: 36, l: 52 },
          xaxis: { title: { text: "Distance (km)" }, gridcolor: "#333" },
          yaxis: { title: { text: "Elevation (m)" }, gridcolor: "#333" },
          legend: { orientation: "h", y: -0.22, font: { size: 10 } },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { color: "#ddd", size: 11 },
          shapes,
          annotations,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
      />
      <div className={`text-xs mt-1 font-medium ${flagClass}`}>{flagLabel}</div>
    </div>
  );
}
