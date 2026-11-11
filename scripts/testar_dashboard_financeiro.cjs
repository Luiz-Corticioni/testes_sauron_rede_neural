"use strict";
// Exercita os eventos reais do painel sem navegador, rede ou dados de clientes.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const {TextDecoder, TextEncoder} = require("node:util");
const elementos = new Map();
function no(id) {
  if (!elementos.has(id)) {
    const eventos = {};
    elementos.set(id, {id, eventos, textContent:"", disabled:false, dataset:{}, value:"",
      elements:{}, addEventListener: (evento, fn) => { eventos[evento] = fn; },
      reportValidity: () => true, replaceChildren: () => {}, append: () => {},
      setAttribute: () => {}, querySelectorAll: () => [], querySelector: seletor => no(id + seletor)});
  }
  return elementos.get(id);
}
const parametros = no("mc-parametros"), laboratorio = no("simulacao-montecarlo"), contexto = no("mc-contexto");
parametros.elements = {A_min:{value:""}, A_moda:{value:""}, A_max:{value:""}};
parametros.dados = {C_min:"1", C_moda:"2", C_max:"3", I_min:"1", I_moda:"2", I_max:"3",
  A_min:"1", A_moda:"2", A_max:"3", n:"100", seed:"42", teto:"", exposicao_internet:"1", exposicao_interna:"1"};
laboratorio.elements = {incidencias:no("incidencias")};
contexto.dados = {custo_hora:"1000", recuperacao:"2000", horas_min:"4", horas_moda:"8", horas_max:"24"};
let temporizador, resposta, contador = 0;
const ambiente = {
  document: {addEventListener: (evento, fn) => { if (evento === "DOMContentLoaded") fn(); }, getElementById:no,
    createElement: () => no(`criado-${contador++}`), createElementNS: () => no(`criado-${contador++}`),
    createDocumentFragment: () => no(`criado-${contador++}`)},
  FormData: class { constructor(form) { this.form = form; } get(chave) { return this.form.dados[chave]; } },
  Intl, Number, Object, Math, String, Array, TextEncoder, TextDecoder,
  setTimeout: fn => { temporizador = fn; return 1; }, clearTimeout: () => {}, AbortController: class {abort() {}},
  SauronHTTP: {json: async () => resposta},
};
vm.runInNewContext(fs.readFileSync("inventario/static/inventario/montecarlo.js", "utf8"), ambiente);
const submeter = () => contexto.eventos.submit({preventDefault(){}});
submeter();
assert.equal(no("mc-contexto-aplicar").disabled, false);
assert.match(no("mc-contexto-resultado").textContent, /6\.000/);
assert.match(no("mc-contexto-resultado").textContent, /10\.000/);
assert.match(no("mc-contexto-resultado").textContent, /26\.000/);
no("mc-contexto-aplicar").eventos.click();
assert.deepEqual([parametros.elements.A_min.value,parametros.elements.A_moda.value,parametros.elements.A_max.value], [6000,10000,26000]);
contexto.dados.horas_max = "7";
contexto.eventos.input();
assert.equal(no("mc-contexto-aplicar").disabled, true);
submeter();
assert.equal(no("mc-contexto-aplicar").disabled, true);
assert.match(no("mc-contexto-resultado").textContent, /mínima/);
no("mc-contexto-aplicar").eventos.click();
assert.deepEqual([parametros.elements.A_min.value,parametros.elements.A_moda.value,parametros.elements.A_max.value], [6000,10000,26000]);
contexto.dados = {custo_hora:"1000000000000000",recuperacao:"0",horas_min:"1",horas_moda:"2",horas_max:"3"};
submeter();
assert.equal(no("mc-contexto-aplicar").disabled, true);
(async () => {
  const resumo = {media:12000, P5:0, P50:0, P90:10000, P95:20000, P99:40000, probabilidade_perda:.2};
  resposta = {horizonte_dias:30, disponivel:true, antes:resumo, depois:resumo, ganho_media:1000,
    excedencia:[{perda:0, probabilidade:.2, probabilidade_depois:.1}], contribuicoes:[], entradas:[],
    hipotese_epss:"hipótese", escopo:"escopo", n:100, seed:42, quantidade_ativos:1, quantidade_incidencias:1};
  await temporizador();
  assert.match(no("mc-kpi-media").textContent, /12\.000/);
  assert.match(no("mc-kpi-p95").textContent, /20\.000/);
  assert.match(no("mc-kpi-perda").textContent, /20%/);
  resposta = {...resposta, quantidade_incidencias:0};
  parametros.eventos.submit({preventDefault(){}});
  await temporizador();
  assert.equal(no("mc-kpi-media").textContent, "—");
  assert.match(no("mc-status").textContent, /não demonstra ausência de risco/);
  resposta = {horizonte_dias:30, disponivel:false, aviso:"EPSS ausente", pendencias_total:1,
    pendencias:[{ativo:"A", cve:"CVE", motivo:"sem observação"}], pendencias_limitadas:false};
  parametros.eventos.submit({preventDefault(){}});
  await temporizador();
  assert.equal(no("mc-kpi-media").textContent, "—");
  assert.match(no("mc-status").textContent, /EPSS ausente/);
  console.log("OK: cálculo, aplicação explícita, limites, resumo, inventário vazio e EPSS ausente.");
})().catch(erro => { console.error(erro); process.exitCode = 1; });
