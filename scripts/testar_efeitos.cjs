const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function executar(preferencia,sistema) {
  const eventos={},acoes={},armazenamento={valor:preferencia, getItem(){return this.valor},setItem(_,v){this.valor=v}};
  const botao={hidden:true,atributos:{},setAttribute(k,v){this.atributos[k]=v},addEventListener(k,f){acoes[k]=f}};
  const document={documentElement:{dataset:{}},addEventListener(k,f){eventos[k]=f},getElementById:()=>botao,dispatchEvent(){}};
  const window={matchMedia:()=>({matches:sistema})};
  vm.runInNewContext(fs.readFileSync('inventario/static/inventario/efeitos.js','utf8'),{document,window,localStorage:armazenamento,Event:class {}});
  eventos.DOMContentLoaded();
  return {document,window,botao,acoes,armazenamento};
}
const normal=executar('0',false);
assert.equal(normal.window.SauronEfeitos.reduzidos(),false);
normal.acoes.click();
assert.equal(normal.botao.atributos['aria-pressed'],'true');
assert.equal(normal.document.documentElement.dataset.efeitos,'reduzidos');
assert.equal(normal.armazenamento.valor,'1');
const sistema=executar('0',true);
assert.equal(sistema.window.SauronEfeitos.reduzidos(),true);
console.log('OK: preferência local e preferência do sistema são respeitadas.');
