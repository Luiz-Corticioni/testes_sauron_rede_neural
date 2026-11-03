/* Barras vetoriais locais. Números e rótulos permanecem acessíveis. */
document.addEventListener("DOMContentLoaded", () => {
  const host = document.getElementById("riskChart");
  const raw = document.getElementById("risk-data");
  if (!host || !raw) return;
  const data = JSON.parse(raw.textContent);
  if (!data.ids_ativos?.length) return;
  const namespace = "http://www.w3.org/2000/svg";
  const node = (name, attrs, text) => {
    const element = document.createElementNS(namespace,name);
    Object.entries(attrs).forEach(([key,value]) => element.setAttribute(key,String(value)));
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const records = data.ids_ativos.slice(0,20);
  const max = Math.max(1,...data.risco_efetivo,...data.risco_proprio);
  const svg = node("svg", {viewBox:`0 0 650 ${60+records.length*64}`, class:"risk-chart", role:"img", "aria-label":"Risco próprio em cinza e risco efetivo em carmesim, por ativo"});
  svg.append(node("rect", {x:0,y:7,width:10,height:10,class:"bar-own"}),node("text", {x:17,y:17,class:"chart-muted"},"Próprio b"));
  svg.append(node("rect", {x:126,y:7,width:10,height:10,class:"bar-effective"}),node("text", {x:143,y:17,class:"chart-muted"},"Efetivo x"));
  records.forEach((id,i) => {
    const y = 51+i*64;
    const b = data.risco_proprio[i], x = data.risco_efetivo[i];
    const group = node("g", {});
    group.append(node("title", {},`${id}: risco próprio ${b}; risco efetivo ${x}`));
    group.append(node("text", {x:0,y:y+18},id));
    group.append(node("rect", {x:99,y:y,width:b/max*390,height:9,rx:2,class:"bar-own"}));
    group.append(node("rect", {x:99,y:y+14,width:x/max*390,height:9,rx:2,class:"bar-effective"}));
    group.append(node("text", {x:505,y:y+18},`${b.toFixed(1)} → ${x.toFixed(1)}`));
    svg.append(group);
  });
  host.replaceChildren(svg);
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Ler valores do gráfico";
  const list = document.createElement("ul");
  records.forEach((id,i) => { const li = document.createElement("li"); li.textContent = `${id}: b ${data.risco_proprio[i]}, x ${data.risco_efetivo[i]}`; list.append(li); });
  details.append(summary,list); host.append(details);
  if (data.ids_ativos.length > 20) { const note = document.createElement("p"); note.className = "muted"; note.textContent = "Gráfico dos primeiros 20 ativos. Consulte o JSON para todos os resultados."; host.append(note); }
});
