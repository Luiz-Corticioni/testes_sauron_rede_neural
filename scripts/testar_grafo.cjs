const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Elemento {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.children = []; this.events = {}; this.classList = {toggle(){}, remove(){}}; }
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return this.attrs[k]; }
  append(...itens) { this.children.push(...itens); }
  replaceChildren(...itens) { this.children = itens; }
  addEventListener(nome, fn) { this.events[nome] = fn; }
}
const host = new Elemento('div'), status = new Elemento('p');
const dados = {largura: 760, altura: 760, nos: [
  {id:'A', nome:'Fornecedor', x:380, y:380, faixa:'baixo', efetivo:1, indice:2},
  {id:'B', nome:'Dependente', x:380, y:150, faixa:'alto', efetivo:2, indice:3},
], arestas:[{origem:'A', destino:'B', peso:.2, espessura:2.6}]};
const elementos = {'dependency-graph':host, 'graph-data':{textContent:JSON.stringify(dados)}, 'graph-status':status};
const document = {getElementById:id=>elementos[id], createElementNS:(_,tag)=>new Elemento(tag),
  addEventListener:(nome, fn)=>{if(nome==='DOMContentLoaded') fn();}};
vm.runInNewContext(fs.readFileSync('inventario/static/inventario/grafo.js','utf8'), {document, JSON, Object, Map, Set, Math, String, encodeURIComponent});
const svg=host.children[0];
assert.equal(svg.tag,'svg');
const aresta=svg.children.find(e=>e.attrs.class==='graph-edge');
assert.equal(aresta.attrs.d,'M380 347 L380 183');
assert.equal(aresta.attrs['marker-end'],'url(#risk-arrow)');
const origem=svg.children.find(e=>e.attrs.href==='/ativos/A/');
origem.events.focus();
assert.match(status.textContent, /alcança 1 outro/);
assert.match(origem.attrs['aria-label'], /Fornecedor/);
console.log('Grafo: direção, acessibilidade e alcance verificados.');
