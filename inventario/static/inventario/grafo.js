/* Camadas calculadas no servidor; foco e hover percorrem o mesmo fluxo j → i. */
document.addEventListener("DOMContentLoaded", () => {
  const host = document.getElementById("dependency-graph");
  if (!host) return;
  const data = JSON.parse(document.getElementById("graph-data").textContent);
  if (!data.nos?.length) return;
  const namespace = "http://www.w3.org/2000/svg";
  const node = (name,attributes,text) => {
    const e = document.createElementNS(namespace,name);
    Object.entries(attributes).forEach(([key,value]) => e.setAttribute(key,String(value)));
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const svg = node("svg", {viewBox:`0 0 ${data.largura} ${data.altura}`,class:"dependency-svg",role:"group","aria-label":"Grafo de risco: setas do fornecedor para o dependente"});
  const defs = node("defs",{});
  const marker = node("marker", {id:"risk-arrow",viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:5,markerHeight:5,orient:"auto-start-reverse"});
  marker.append(node("path",{d:"M0 0L10 5L0 10Z",fill:"context-stroke"}));
  defs.append(marker); svg.append(defs);
  const positions = new Map(data.nos.map(n => [n.id,n]));
  const edgeElements = [];
  const nodeElements = new Map();
  data.arestas.forEach(edge => {
    const a = positions.get(edge.origem), b = positions.get(edge.destino);
    const path = node("path", {d:`M${a.x} ${a.y+33} C${a.x} ${a.y+85},${b.x} ${b.y-85},${b.x} ${b.y-33}`,class:"graph-edge","stroke-width":edge.espessura,"marker-end":"url(#risk-arrow)"});
    path.append(node("title",{},`${edge.origem} → ${edge.destino}, peso ${edge.peso}`));
    svg.append(path); edgeElements.push([edge,path]);
  });
  const status = document.getElementById("graph-status");
  const highlight = id => {
    const reached = new Set([id]);
    const queue = [id];
    while (queue.length) {
      const current = queue.shift();
      data.arestas.filter(e => e.origem === current).forEach(e => {
        if (!reached.has(e.destino)) { reached.add(e.destino); queue.push(e.destino); }
      });
    }
    nodeElements.forEach((e,key) => e.classList.toggle("inflamed",reached.has(key)));
    edgeElements.forEach(([edge,e]) => e.classList.toggle("inflamed",reached.has(edge.origem)));
    status.textContent = `${id} alcança ${reached.size-1} outro(s) ativo(s) pelos vínculos exibidos. A quantidade não mede o risco: consulte os pesos e x.`;
  };
  const clear = () => {
    nodeElements.forEach(e => e.classList.remove("inflamed"));
    edgeElements.forEach(([,e]) => e.classList.remove("inflamed"));
  };
  data.nos.forEach(n => {
    const link = node("a", {href:`/ativos/${encodeURIComponent(n.id)}/`,class:`graph-node ${n.faixa}`,tabindex:0,"aria-label":`${n.nome}, ${n.id}, risco efetivo ${n.efetivo.toFixed(2)}; abrir ficha`});
    link.append(node("rect",{x:n.x-93,y:n.y-33,width:186,height:66,rx:7}));
    link.append(node("text",{x:n.x,y:n.y-6,"text-anchor":"middle"},n.id));
    link.append(node("text",{x:n.x,y:n.y+13,"text-anchor":"middle",class:"node-detail"},`x ${n.efetivo.toFixed(2)} · índice ${n.indice.toFixed(1)}`));
    link.addEventListener("pointerenter",() => highlight(n.id));
    link.addEventListener("focus",() => highlight(n.id));
    link.addEventListener("pointerleave",clear);
    link.addEventListener("blur",clear);
    link.addEventListener("keydown",event => { if (event.key === "Enter") location.assign(link.getAttribute("href")); });
    svg.append(link); nodeElements.set(n.id,link);
  });
  host.replaceChildren(svg);
});
