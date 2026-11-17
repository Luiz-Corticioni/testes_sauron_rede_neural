const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
class Elemento {
  constructor(nome='') { this.nome=nome; this.children=[]; this.events={}; this.hidden=false; this.value=''; this.open=false; }
  addEventListener(tipo, fn) { this.events[tipo]=fn; }
  append(...elementos) { this.children.push(...elementos); }
  replaceChildren(...elementos) { this.children=elementos; }
  showModal() { this.open=true; }
  focus() { this.focado=true; }
}
const ids=Object.fromEntries(['comandos','comandos-abrir','comandos-busca','comandos-lista','comandos-resultado'].map(k=>[k,new Elemento(k)]));
const link=(nome,href)=>({querySelector:seletor=>seletor==='b'?{textContent:nome}:{textContent:'Descrição'},getAttribute:()=>href});
const document={events:{},getElementById:id=>ids[id],createElement:()=>new Elemento(),
  querySelectorAll:()=>[link('Ativos','/ativos/'),link('Guia','/guia/')],
  addEventListener(tipo,fn){this.events[tipo]=fn; if(tipo==='DOMContentLoaded')fn();}};
vm.runInNewContext(fs.readFileSync('inventario/static/inventario/comandos.js','utf8'),{document,URLSearchParams});
ids['comandos-abrir'].events.click();
assert.ok(ids.comandos.open && ids['comandos-busca'].focado);
ids['comandos-busca'].value='servidor & teste'; ids['comandos-busca'].events.input();
assert.equal(ids['comandos-lista'].children.length,1);
assert.equal(ids['comandos-lista'].children[0].children[0].href,'/ativos/?q=servidor+%26+teste');
assert.ok(!JSON.stringify(ids['comandos-lista'].children).includes('/admin/'));
console.log('OK: paleta usa links autorizados e codifica a busca.');
