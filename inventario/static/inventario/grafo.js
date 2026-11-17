/* Distribuição em anéis é visual; foco e hover seguem os vínculos j → i. */
document.addEventListener("DOMContentLoaded", () => {
  const host = document.getElementById("dependency-graph");
  if (!host) return;
  const data = JSON.parse(document.getElementById("graph-data").textContent);
  if (!data.nos?.length) return;
  // O layout é apenas apresentação, com custo limitado pela janela de 60 nós.
  const d3 = typeof window !== 'undefined' ? window.d3 : null;
  if (d3?.forceSimulation) {
    const links = data.arestas.map(e => ({source:e.origem,target:e.destino}));
    const simulacao = d3.forceSimulation(data.nos)
      .force('ligacoes', d3.forceLink(links).id(n=>n.id).distance(250).strength(.25))
      .force('repulsao', d3.forceManyBody().strength(-800))
      .force('colisao', d3.forceCollide(105))
      .force('horizontal', d3.forceX(data.largura/2).strength(.04))
      .force('vertical', d3.forceY(data.altura/2).strength(.04))
      .force('centro', d3.forceCenter(data.largura/2, data.altura/2)).stop();
    simulacao.tick(120);
    data.nos.forEach(n=>{n.x=Math.max(110,Math.min(data.largura-110,n.x));n.y=Math.max(60,Math.min(data.altura-60,n.y));});
  }
  const namespace = "http://www.w3.org/2000/svg";
  const node = (name,attributes,text) => {
    const e = document.createElementNS(namespace,name);
    Object.entries(attributes).forEach(([key,value]) => e.setAttribute(key,String(value)));
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const densidade = data.nos.length > 49 ? "dense-xl" : data.nos.length > 25 ? "dense" : data.nos.length > 9 ? "medium" : "";
  const svg = node("svg", {viewBox:`0 0 ${data.largura} ${data.altura}`,class:`dependency-svg ${densidade}`,role:"group","aria-label":"Grafo de risco: setas do fornecedor para o dependente"});
  const defs = node("defs",{});
  const marker = node("marker", {id:"risk-arrow",viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:5,markerHeight:5,orient:"auto-start-reverse"});
  marker.append(node("path",{d:"M0 0L10 5L0 10Z",fill:"context-stroke"}));
  defs.append(marker); svg.append(defs);
  const positions = new Map(data.nos.map(n => [n.id,n]));
  const edgeElements = [];
  const nodeElements = new Map();
  const escala = n => n.criticidade ? .8 + n.criticidade*.05 : 1;
  const criticos = new Set(data.nos.filter(n => n.maior_cvss != null && n.maior_cvss >= 9).map(n=>n.id));
  const filaCritica = [...criticos];
  while (filaCritica.length) {
    const atual = filaCritica.shift();
    data.arestas.filter(e=>e.origem===atual).forEach(e=>{if(!criticos.has(e.destino)){criticos.add(e.destino);filaCritica.push(e.destino);}});
  }
  data.arestas.forEach(edge => {
    const a = positions.get(edge.origem), b = positions.get(edge.destino);
    const dx = b.x-a.x, dy = b.y-a.y;
    const bordaA = Math.min(93*escala(a)/(Math.abs(dx)||1e-9), 33*escala(a)/(Math.abs(dy)||1e-9));
    const bordaB = Math.min(93*escala(b)/(Math.abs(dx)||1e-9), 33*escala(b)/(Math.abs(dy)||1e-9));
    const x1=a.x+dx*bordaA, y1=a.y+dy*bordaA, x2=b.x-dx*bordaB, y2=b.y-dy*bordaB;
    const path = node("path", {d:`M${x1} ${y1} L${x2} ${y2}`,class:"graph-edge","stroke-width":edge.espessura,"marker-end":"url(#risk-arrow)"});
    if (criticos.has(edge.origem)) path.classList.add('fluxo-critico');
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
    nodeElements.forEach((e,key) => {e.classList.toggle("inflamed",reached.has(key));e.classList.toggle('graph-muted',!reached.has(key));});
    edgeElements.forEach(([edge,e]) => {e.classList.toggle("inflamed",reached.has(edge.origem));e.classList.toggle('graph-muted',!reached.has(edge.origem));});
    status.textContent = `${id} alcança ${reached.size-1} outro(s) ativo(s) pelos vínculos exibidos. A quantidade não mede o risco: consulte os pesos e x.`;
  };
  const clear = () => {
    nodeElements.forEach(e => {e.classList.remove("inflamed");e.classList.remove('graph-muted');});
    edgeElements.forEach(([,e]) => {e.classList.remove("inflamed");e.classList.remove('graph-muted');});
  };
  const detalhes = document.getElementById('graph-details');
  data.nos.forEach(n => {
    const link = node("a", {href:`/ativos/${encodeURIComponent(n.id)}/`,class:`graph-node ${n.faixa}`,tabindex:0,"aria-label":`${n.nome}, ${n.id}, risco efetivo ${n.efetivo.toFixed(2)}; selecionar detalhes`});
    link.append(node("title",{},`${n.nome} · ${n.id}`));
    link.append(node("rect",{x:n.x-93*escala(n),y:n.y-33*escala(n),width:186*escala(n),height:66*escala(n),rx:7}));
    link.append(node("text",{x:n.x,y:n.y-6,"text-anchor":"middle"},n.id));
    link.append(node("text",{x:n.x,y:n.y+13,"text-anchor":"middle",class:"node-detail"},`x ${n.efetivo.toFixed(2)} · índice ${n.indice.toFixed(1)}`));
    link.addEventListener("pointerenter",() => highlight(n.id));
    link.addEventListener("focus",() => highlight(n.id));
    link.addEventListener("pointerleave",clear);
    link.addEventListener("blur",clear);
    if (detalhes) link.addEventListener('click', evento=>{
      evento.preventDefault(); detalhes.hidden=false;
      const titulo=document.createElement('h3'), resumo=document.createElement('p'), lista=document.createElement('p'), acao=document.createElement('a');
      titulo.textContent=`${n.nome} · ${n.id}`;
      resumo.textContent=`${n.tipo_nome || 'Tipo não informado'} · criticidade declarada ${n.criticidade || '—'} · índice ${n.indice.toFixed(1)}/100 · risco x ${n.efetivo.toFixed(2)}`;
      lista.textContent=n.cves?.length ? `Incidências consideradas (${n.total_cves}; até 3 exibidas): ${n.cves.map(v=>`${v.id} (CVSS ${v.cvss})`).join(', ')}.` : 'Sem incidências consideradas neste recorte; isso não comprova segurança.';
      acao.href=link.getAttribute('href');acao.textContent='Abrir ficha do ativo';
      detalhes.replaceChildren(titulo,resumo,lista,acao);
      highlight(n.id);
    });
    svg.append(link); nodeElements.set(n.id,link);
  });
  host.replaceChildren(svg);
  const controles=document.getElementById('graph-controls');
  if (!controles) return;
  controles.hidden=false;
  const busca=document.getElementById('graph-search'), tipo=document.getElementById('graph-type'), severidade=document.getElementById('graph-severity');
  const filtrar=()=>{
    const termo=busca.value.trim().toLocaleLowerCase('pt-BR'), escolhidos=new Set();
    data.nos.forEach(n=>{
      const cvss=n.maior_cvss;
      const faixa=!severidade.value || (severidade.value==='sem' ? cvss == null : cvss != null &&
        (severidade.value==='critica' ? cvss>=9 : severidade.value==='alta' ? cvss>=7 && cvss<9 : cvss<7));
      const visivel=(!termo || `${n.id} ${n.nome}`.toLocaleLowerCase('pt-BR').includes(termo)) && (!tipo.value || tipo.value===n.tipo) && faixa;
      if(visivel) escolhidos.add(n.id);
      nodeElements.get(n.id).classList.toggle('graph-filtered',!visivel);
    });
    edgeElements.forEach(([e,el])=>el.classList.toggle('graph-filtered',!escolhidos.has(e.origem)||!escolhidos.has(e.destino)));
    status.textContent=`${escolhidos.size} de ${data.nos.length} ativos na janela correspondem aos filtros. A tabela abaixo mantém todos os vínculos exibidos.`;
  };
  busca.addEventListener('input',filtrar);tipo.addEventListener('change',filtrar);severidade.addEventListener('change',filtrar);
  let zoom=1, x=0, y=0;
  const atualizarVisao=()=>svg.setAttribute('viewBox',`${x} ${y} ${data.largura/zoom} ${data.altura/zoom}`);
  const alterarZoom=fator=>{const anterior=zoom;zoom=Math.max(1,Math.min(4,zoom*fator));x+=(data.largura/anterior-data.largura/zoom)/2;y+=(data.altura/anterior-data.altura/zoom)/2;atualizarVisao();};
  document.getElementById('graph-zoom-in').addEventListener('click',()=>alterarZoom(1.3));
  document.getElementById('graph-zoom-out').addEventListener('click',()=>alterarZoom(1/1.3));
  document.getElementById('graph-reset').addEventListener('click',()=>{zoom=1;x=0;y=0;busca.value=tipo.value=severidade.value='';atualizarVisao();filtrar();});
  let arrasto=null;
  svg.addEventListener('pointerdown',e=>{if(e.target!==svg)return;arrasto={x:e.clientX,y:e.clientY};svg.setPointerCapture(e.pointerId);});
  svg.addEventListener('pointermove',e=>{if(!arrasto)return;const rect=svg.getBoundingClientRect();x-=(e.clientX-arrasto.x)*data.largura/zoom/rect.width;y-=(e.clientY-arrasto.y)*data.altura/zoom/rect.height;arrasto={x:e.clientX,y:e.clientY};atualizarVisao();});
  svg.addEventListener('pointerup',()=>{arrasto=null;});svg.addEventListener('pointercancel',()=>{arrasto=null;});
});
