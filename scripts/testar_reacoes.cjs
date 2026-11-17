const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
function rodar(reduzido){
 const numero={dataset:{contagem:'31'},textContent:'31'}, quadros=[];
 const document={querySelector:()=>null,querySelectorAll:()=>[numero],addEventListener:(e,f)=>f()};
 const window={matchMedia:()=>({matches:reduzido}),requestAnimationFrame:fn=>quadros.push(fn)};
 vm.runInNewContext(fs.readFileSync('inventario/static/inventario/reacoes.js','utf8'),{document,window,performance:{now:()=>100},Number,Math});
 return {numero,quadros,window};
}
const normal=rodar(false); assert.equal(normal.quadros.length,1); normal.quadros[0](700); assert.equal(normal.numero.textContent,'31');
const reduzido=rodar(true); assert.equal(reduzido.quadros.length,0); assert.equal(reduzido.numero.textContent,'31');
const valor={textContent:'10'}; reduzido.window.SauronContar(valor,22.6,1,10); assert.equal(valor.textContent,'22,6');
console.log('OK: contadores preservam resultado e respeitam movimento reduzido.');
