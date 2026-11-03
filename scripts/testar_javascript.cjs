/* Testes opcionais com Node, sem bibliotecas externas. Não é dependência da aplicação. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const raiz = path.resolve(__dirname, '..');
const ler = nome => fs.readFileSync(path.join(raiz,'inventario','static','inventario',nome),'utf8');

async function saude({anterior, status=200, falha=false, armazenamento=true}={}) {
  const elementos = new Map();
  let chamadas = 0, salvo;
  const elemento = id => {
    if (!elementos.has(id)) elementos.set(id, {textContent:'', addEventListener(){}, setAttribute(){},
      classList:{valores:new Set(),add(v){this.valores.add(v)},remove(){},contains(){return false}}});
    return elementos.get(id);
  };
  const contexto = {Date, JSON, Error, Object,
    document:{body:elemento('body'),getElementById:elemento,querySelector:elemento,querySelectorAll:()=>[],
      addEventListener(evento, callback){if(evento==='DOMContentLoaded') callback()}},
    matchMedia:()=>({matches:false,addEventListener(){}}),
    sessionStorage:{getItem(){if(!armazenamento) throw new Error('Indisponível');return anterior ? JSON.stringify(anterior):null},
      setItem(k,v){if(!armazenamento) throw new Error('Indisponível');salvo=JSON.parse(v)}},
    fetch:async()=>{chamadas++;if(falha)throw new Error('Sem rede');return {status,ok:status===200,json:async()=>({status:'ok'})}}};
  vm.runInNewContext(ler('shell.js'),contexto);
  await new Promise(resolve=>setImmediate(resolve));
  return {chamadas,salvo,label:elemento('service-label').textContent,offline:elemento('service-eye').classList.valores.has('offline')};
}

async function http(resposta) {
  const contexto={window:{},URL,document:{},fetch:async()=>resposta};
  vm.runInNewContext(ler('http.js'),contexto);
  return contexto.window.SauronHTTP.json('/api/montecarlo/');
}

async function main() {
  const a = await saude();
  assert.equal(a.chamadas,1);assert.equal(a.label,'Serviço respondeu');assert.equal(a.salvo.status,'ok');
  assert.equal((await saude({anterior:{status:'ok',em:Date.now()}})).chamadas,0);
  assert.equal((await saude({anterior:{status:'ok',em:Date.now()-61000}})).chamadas,1);
  assert.equal((await saude({anterior:{status:'ok',em:Date.now()+60000}})).chamadas,1);
  const limitado = await saude({status:429});
  assert.equal(limitado.label,'Verificação limitada');assert.equal(limitado.offline,false);
  assert.equal((await saude({falha:true})).offline,true);
  assert.equal((await saude({armazenamento:false})).label,'Serviço respondeu');
  const resposta = (url,tipo,extra={})=>({redirected:true,url,status:200,ok:true,headers:{get:()=>tipo},json:async()=>({horizonte_dias:30}),...extra});
  assert.equal((await http(resposta('http://localhost/api/montecarlo/','application/json',{redirected:false}))).horizonte_dias,30);
  await assert.rejects(http(resposta('http://localhost/mfa/','text/html')),e=>e.reautenticacao===true);
  await assert.rejects(http(resposta('http://localhost/entrar/','text/html')),/sessão expirou/);
  await assert.rejects(http(resposta('http://localhost/api/montecarlo/','application/json',{redirected:false,status:400,ok:false,json:async()=>({erro:'Inválido'})})),/Inválido/);
  await assert.rejects(http(resposta('http://localhost/api/montecarlo/','text/html',{redirected:false,status:500})),/servidor respondeu 500/);
  console.log('12 cenários JavaScript aprovados: sete de saúde/cache e cinco de HTTP/autenticação.');
}
main().catch(erro=>{console.error(erro);process.exitCode=1});
