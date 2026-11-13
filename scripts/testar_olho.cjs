/* Preserva a leitura do índice e o estado de dados indisponíveis, sem animação contínua. */
const assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
function olho(disponivel, pequeno=false){
 const titulo={textContent:"original"};
 return {dataset:{index:"50",disponivel},classList:{contains:n=>n === "eye-small" && pequeno},
   style:{setProperty(){}},querySelector:()=>titulo,titulo};
}
const ativo=olho("true"), ausente=olho("false"), pequeno=olho("false",true), indice={textContent:""}, legenda={textContent:""};
const document={addEventListener:(e,f)=>{if(e === "DOMContentLoaded")f();},querySelectorAll:q=>({
 "[data-eye]":[ativo,ausente,pequeno],"[data-global-index]":[indice],"[data-eye-caption]":[legenda],
}[q]||[])};
const window={}; vm.runInNewContext(fs.readFileSync("inventario/static/inventario/olho.js","utf8"),{document,window,Number,Math,Map});
assert.equal(ativo.dataset.band,"alto");
assert.match(ativo.titulo.textContent,/50/);
assert.equal(ausente.dataset.band,"indisponivel");
assert.equal(ausente.titulo.textContent,"original");
window.SauronEye.atualizar([20,40],true);
assert.equal(indice.textContent,"30"); assert.match(legenda.textContent,/simulação/);
assert.equal(ausente.dataset.band,"indisponivel");
console.log("OK: olho estático, índice existente, simulação e estado indisponível.");
