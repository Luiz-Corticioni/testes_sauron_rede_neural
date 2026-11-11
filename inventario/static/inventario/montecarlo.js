"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const painel = document.getElementById("mc-painel");
  if (!painel) return;
  const porId = id => document.getElementById(id);
  const parametros = porId("mc-parametros"), laboratorio = porId("simulacao-montecarlo");
  const status = porId("mc-status"), saida = laboratorio.querySelector("#resultado-simulacao");
  const selecao = porId("mc-selecao");
  const moeda = v => new Intl.NumberFormat("pt-BR", {style:"currency", currency:"BRL", maximumFractionDigits:0}).format(v);
  const percentual = v => new Intl.NumberFormat("pt-BR", {style:"percent", maximumFractionDigits:1}).format(v);
  const numero = v => new Intl.NumberFormat("pt-BR").format(v);
  const contexto = porId("mc-contexto"), aplicarContexto = porId("mc-contexto-aplicar");
  const resultadoContexto = porId("mc-contexto-resultado");
  let faixaContexto = null;
  contexto.addEventListener("input", () => {
    faixaContexto = null;
    aplicarContexto.disabled = true;
    resultadoContexto.textContent = "Valores alterados; estime novamente antes de aplicar.";
  });
  contexto.addEventListener("submit", e => {
    e.preventDefault();
    faixaContexto = null;
    aplicarContexto.disabled = true;
    if (!contexto.reportValidity()) return;
    const campos = new FormData(contexto), valor = nome => Number(campos.get(nome));
    const hora = valor("custo_hora"), recuperacao = valor("recuperacao");
    const horas = ["horas_min", "horas_moda", "horas_max"].map(valor);
    const faixa = horas.map(h => h * hora + recuperacao);
    if (![hora, recuperacao, ...horas, ...faixa].every(Number.isFinite) ||
        !(horas[0] < horas[1] && horas[1] < horas[2]) ||
        !(faixa[0] < faixa[1] && faixa[1] < faixa[2]) || faixa[2] > 1e15) {
      resultadoContexto.textContent = "Informe custo por hora maior que zero, durações mínima < mais provável < máxima e valores dentro dos limites.";
      return;
    }
    faixaContexto = faixa;
    resultadoContexto.textContent = `Por incidente: mínimo ${moeda(faixa[0])}; mais provável ${moeda(faixa[1])}; máximo ${moeda(faixa[2])}. Confira as premissas antes de aplicar.`;
    aplicarContexto.disabled = false;
  });
  aplicarContexto.addEventListener("click", () => {
    if (!faixaContexto) return;
    ["A_min", "A_moda", "A_max"].forEach((nome, i) => { parametros.elements[nome].value = faixaContexto[i]; });
    resultadoContexto.textContent += " Faixa aplicada à disponibilidade para a simulação atual.";
    agendar(true);
  });
  let geracao = 0, temporizador, controlador;
  const svgNo = (nome, atributos = {}, texto) => {
    const no = document.createElementNS("http://www.w3.org/2000/svg", nome);
    Object.entries(atributos).forEach(([k, v]) => no.setAttribute(k, String(v)));
    if (texto !== undefined) no.textContent = texto;
    return no;
  };
  const tabela = (id, linhas) => {
    const fragmento = document.createDocumentFragment();
    linhas.forEach(linha => {
      const tr = document.createElement("tr");
      linha.forEach((valor, i) => {
        const celula = document.createElement(i === 0 ? "th" : "td");
        if (i === 0) celula.scope = "row";
        celula.textContent = valor;
        tr.append(celula);
      });
      fragmento.append(tr);
    });
    porId(id).replaceChildren(fragmento);
  };
  const quadro = (rotulo, maxY, textoY, rotulosX) => {
    const svg = svgNo("svg", {viewBox:"0 0 960 360", role:"img", "aria-label":rotulo});
    svg.append(svgNo("title", {}, rotulo));
    const x = i => 140 + i / Math.max(1, rotulosX.length-1) * 780;
    const y = v => 292 - (v / (maxY || 1)) * 250;
    for (let i=0; i<=4; i++) {
      const valor = maxY*i/4;
      svg.append(svgNo("line", {x1:140, y1:y(valor), x2:920, y2:y(valor), class:"mc-grade"}));
      svg.append(svgNo("text", {x:130, y:y(valor)+4, "text-anchor":"end"}, textoY(valor)));
    }
    rotulosX.forEach((texto, i) => svg.append(svgNo("text", {x:x(i), y:320, "text-anchor":"middle"}, texto)));
    return {svg, x, y};
  };
  const limpar = () => {
    for (const id of ["mc-distribuicao", "mc-excedencia", "mc-comparacao", "mc-contribuicoes", "mc-excedencia-tabela", "mc-fontes"]) porId(id).replaceChildren();
    for (const id of ["mc-ganho", "mc-hipotese", "mc-escopo"]) porId(id).textContent = "";
    for (const id of ["mc-kpi-media", "mc-kpi-p95", "mc-kpi-perda", "mc-kpi-reducao"]) porId(id).textContent = "—";
    saida.textContent = "";
  };
  const desenhar = r => {
    if (r.horizonte_dias !== 30) throw new Error("Resultado incompatível com o horizonte de 30 dias. Atualize a página.");
    if (!r.disponivel) {
      for (const id of ["mc-kpi-media", "mc-kpi-p95", "mc-kpi-perda", "mc-kpi-reducao"]) porId(id).textContent = "—";
      for (const id of ["mc-distribuicao", "mc-excedencia", "mc-comparacao", "mc-contribuicoes", "mc-excedencia-tabela", "mc-fontes"]) porId(id).replaceChildren();
      porId("mc-ganho").textContent = "";
      porId("mc-frase").textContent = "Dados insuficientes para calcular perdas em 30 dias.";
      status.textContent = `${r.aviso} ${r.pendencias_total} vínculo(s) pendente(s).`;
      saida.textContent = r.pendencias.map(p => `${p.ativo} · ${p.cve}: ${p.motivo}`).join("\n");
      if (r.pendencias_limitadas) saida.textContent += "\nAté 100 pendências exibidas; o total considera todas.";
      status.dataset.erro = "1";
      return;
    }
    if (r.quantidade_incidencias === 0) {
      limpar();
      porId("mc-frase").textContent = "Não há incidências elegíveis para esta análise.";
      status.textContent = "Cadastre e revise os vínculos do inventário. Ausência de registros não demonstra ausência de risco.";
      status.dataset.erro = "1";
      return;
    }
    const a = r.antes, d = r.depois;
    porId("mc-kpi-media").textContent = moeda(a.media);
    porId("mc-kpi-p95").textContent = moeda(a.P95);
    porId("mc-kpi-perda").textContent = percentual(a.probabilidade_perda);
    porId("mc-kpi-reducao").textContent = moeda(r.ganho_media);
    const campos = ["media", "P50", "P90", "P95"];
    const {svg, x, y} = quadro("Comparação de perdas em 30 dias: média, mediana, P90 e P95. Consulte a tabela com os mesmos valores.", Math.max(1, ...campos.map(c => a[c])), moeda, ["Média", "Mediana", "P90", "P95"]);
    campos.forEach((campo,i) => {
      for (const [valor, deslocamento, cor] of [[a[campo],-18,"#e85d5d"],[d[campo],2,"#62c4a1"]]) {
        const barra = svgNo("rect", {x:x(i)+deslocamento, y:y(valor), width:16, height:Math.max(0,y(0)-y(valor)), fill:cor});
        barra.append(svgNo("title", {}, `${campo}: ${moeda(valor)} em 30 dias`));
        svg.append(barra);
      }
    });
    porId("mc-distribuicao").replaceChildren(svg);
    const maxPerda = Math.max(1, ...r.excedencia.map(p => p.perda));
    const q = quadro("Frequência simulada em 30 dias de ultrapassar cada perda: cenário atual e após correções. Valores na tabela de excedência.", 1, percentual, Array.from({length:5},(_,i) => moeda(maxPerda*i/4)));
    const xPerda = valor => 140 + valor/maxPerda*780;
    for (const [campo, classe] of [["probabilidade", "mc-linha"], ["probabilidade_depois", "mc-linha-depois"]]) {
      const d = r.excedencia.map((p,i) => `${i ? "L" : "M"}${xPerda(p.perda)},${q.y(p[campo])}`).join(" ");
      q.svg.append(svgNo("path", {d, class:classe}));
    }
    porId("mc-excedencia").replaceChildren(q.svg);
    porId("mc-frase").textContent = `Nos cenários hipotéticos de 30 dias, a média é ${moeda(a.media)}, a mediana é ${moeda(a.P50)} e o P95 é ${moeda(a.P95)}. Uma mediana zero pode coexistir com perdas elevadas em outros cenários.`;
    tabela("mc-comparacao", [["Mediana em 30 dias", moeda(a.P50), moeda(d.P50)], ["Perda média em 30 dias", moeda(a.media), moeda(d.media)],
      ["P90 dos cenários de 30 dias", moeda(a.P90), moeda(d.P90)], ["P5", moeda(a.P5), moeda(d.P5)],
      ["P95", moeda(a.P95), moeda(d.P95)], ["P99", moeda(a.P99), moeda(d.P99)], ["Cenários com alguma perda", percentual(a.probabilidade_perda), percentual(d.probabilidade_perda)]]);
    porId("mc-ganho").textContent = `Redução estimada da perda média em 30 dias: ${moeda(r.ganho_media)}.`;
    tabela("mc-contribuicoes", r.contribuicoes.map(c => [c.cve, moeda(c.media_atribuida), moeda(c.ganho_correcao)]));
    tabela("mc-excedencia-tabela", r.excedencia.map(p => [moeda(p.perda), percentual(p.probabilidade), percentual(p.probabilidade_depois)]));
    tabela("mc-fontes", r.entradas.map(e => [e.ativo, e.cve, percentual(e.epss), e.origem_epss, e.epss_data || "—", percentual(e.probabilidade_cenario_30d), e.impacto_estimado ? "estimado por CVSS" : "vetor CVSS 3.x"]));
    porId("mc-hipotese").textContent = r.hipotese_epss;
    porId("mc-escopo").textContent = r.escopo;
    saida.textContent = `SIMULAÇÃO SEM GRAVAÇÃO\nPerda média: ${moeda(a.media)} → ${moeda(d.media)}\nRedução: ${moeda(r.ganho_media)}`;
    status.textContent = `${numero(r.n)} cenários hipotéticos de 30 dias · seed ${r.seed} · ${numero(r.quantidade_ativos)} ativos · ${numero(r.quantidade_incidencias)} vínculos. Custos e fatores são hipóteses, sem garantia de ocorrência ou perda. Valores arredondados ao real.`;
    status.dataset.erro = "0";
  };
  const ler = () => {
    if (!parametros.reportValidity()) throw new Error("Confira os parâmetros destacados.");
    const campos = new FormData(parametros), valor = nome => Number(campos.get(nome));
    const custos = Object.fromEntries(["C","I","A"].map(dim => [dim, ["min","moda","max"].map(s => valor(`${dim}_${s}`))]));
    if (Object.values(custos).some(([a,m,b]) => !(a < m && m < b))) throw new Error("Cada faixa de custo exige mínimo < mais provável < máximo.");
    return {custos, n:valor("n"), seed:valor("seed"), teto:campos.get("teto") === "" ? null : valor("teto"),
      exposicao_internet:valor("exposicao_internet"), exposicao_interna:valor("exposicao_interna"),
      cves_corrigidas:[...selecao.querySelectorAll("input:checked")].map(c => c.value),
      incidencias_corrigidas:laboratorio.elements.incidencias.value.split(",").map(v => v.trim()).filter(Boolean)};
  };
  const executar = async atual => {
    try {
      const dados = ler();
      controlador = new AbortController();
      painel.setAttribute("aria-busy", "true");
      status.textContent = "Recalculando os cenários…";
      const r = await SauronHTTP.json(laboratorio.action, {method:"POST", signal:controlador.signal,
        headers:{"Content-Type":"application/json", "X-CSRFToken":laboratorio.querySelector("[name=csrfmiddlewaretoken]").value}, body:JSON.stringify(dados)});
      if (atual === geracao) desenhar(r);
    } catch (erro) {
      if (atual !== geracao || erro.name === "AbortError") return;
      status.textContent = `Não foi possível atualizar: ${erro.message} Confira os parâmetros e tente novamente; não há resultado atualizado.`;
      if (erro.reautenticacao) {
        const link = document.createElement("a");
        link.href = "/mfa/";
        link.textContent = " Confirmar MFA";
        status.append(link);
      }
      status.dataset.erro = "1";
    } finally {
      if (atual === geracao) painel.setAttribute("aria-busy", "false");
    }
  };
  const agendar = (imediato=false) => {
    clearTimeout(temporizador);
    controlador?.abort();
    const atual = ++geracao;
    limpar();
    porId("mc-frase").textContent = "Aguardando cálculo dos cenários de 30 dias.";
    status.textContent = "Parâmetros alterados; aguardando recálculo…";
    temporizador = setTimeout(() => executar(atual), imediato ? 0 : 450);
  };
  parametros.addEventListener("input", () => agendar());
  parametros.addEventListener("submit", e => {e.preventDefault(); agendar(true);});
  laboratorio.addEventListener("submit", e => {e.preventDefault(); agendar(true);});
  laboratorio.elements.incidencias.addEventListener("input", () => agendar());
  selecao.addEventListener("change", () => agendar());
  laboratorio.querySelector("#reset-simulation").addEventListener("click", () => {
    laboratorio.elements.incidencias.value = "";
    selecao.querySelectorAll("input").forEach(c => {c.checked=false;});
    agendar(true);
  });
  agendar(true);
});
