const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const timers = [], aviso = {replaceChildren(...itens){this.itens=itens;}}, classes = new Set();
const olho = {classList:{add:c=>classes.add(c), remove:c=>classes.delete(c)}};
const document = {hidden:false, getElementById:id=>id === 'eye-cursor' ? {textContent:'"cursor"'} : aviso,
  querySelector:()=>olho, createElement:()=>({}), createTextNode:text=>({text}),
  addEventListener:(nome, fn)=>{if(nome === 'DOMContentLoaded') fn();}};
const window = {setTimeout:(fn, ms)=>{timers.push({fn,ms}); return timers.length;}, clearTimeout(){}, addEventListener(){}};
const fetch = async url=>{assert.match(url,/cursor=cursor/);return {ok:true,json:async()=>({cursor:'proximo', eventos:[{ativo:'A',cve:'CVE-2024-3400',url:'/ativos/A/'}]})};};
vm.runInNewContext(fs.readFileSync('inventario/static/inventario/olho_eventos.js','utf8'),{document,window,fetch,JSON,encodeURIComponent});
assert.equal(timers[0].ms,60000);
timers[0].fn().then(()=>{assert.match(aviso.itens[0].text,/não indica exploração/);assert.equal(aviso.itens[1].href,'/ativos/A/');assert.ok(classes.has('despertar'));console.log('OK: aviso crítico somente a partir de evento recebido.');}).catch(e=>{console.error(e);process.exitCode=1;});
