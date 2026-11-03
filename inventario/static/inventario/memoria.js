/* Força da memória, curva exponencial do domínio e tabela de amostras. */
document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("memory-choice");
  if (!select) return;
  const memories = JSON.parse(document.getElementById("memory-data").textContent);
  const host = document.getElementById("memory-chart");
  const namespace = "http://www.w3.org/2000/svg";
  const element = (tag,attrs,text) => {
    const e = document.createElementNS(namespace,tag);
    Object.entries(attrs).forEach(([k,v]) => e.setAttribute(k,String(v)));
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const draw = () => {
    const m = memories.find(item => String(item.id) === select.value);
    if (!m) return;
    const end = Math.max(1,m.pontos[m.pontos.length-1][0]);
    const svg = element("svg",{viewBox:"0 0 660 255",class:"risk-chart",role:"img","aria-label":`Decaimento da memória ${m.id}; dias desde o reforço e força de 0 a 1`});
    svg.append(element("path",{d:"M55 20V205H630",stroke:"#68778a",fill:"none"}));
    [0,.25,.5,.75,1].forEach(value => svg.append(element("text",{x:12,y:210-value*180,class:"chart-muted"},String(value))));
    const points = m.pontos.map(([day,force]) => `${55+day/end*570},${205-force*180}`).join(" ");
    svg.append(element("polyline",{points,fill:"none",stroke:"#ff4d2e","stroke-width":2.5}));
    svg.append(element("text",{x:55,y:238,class:"chart-muted"},"0 dias"),element("text",{x:580,y:238,class:"chart-muted"},`${end} dias`));
    const details = document.createElement("details"), summary = document.createElement("summary"), list = document.createElement("ul");
    summary.textContent = "Ler amostras da curva";
    m.pontos.forEach(([day,force]) => { const item = document.createElement("li"); item.textContent = `Dia ${day}: força ${force.toFixed(4)}`; list.append(item); });
    details.append(summary,list); host.replaceChildren(svg,details);
    document.getElementById("memory-status").textContent = `Memória ${m.id}, idade ${m.idade.toFixed(1)} dias; força atual ${m.forca_atual.toFixed(3)}. A curva é uma projeção sem novo reforço.`;
  };
  select.addEventListener("change",draw); draw();
});
