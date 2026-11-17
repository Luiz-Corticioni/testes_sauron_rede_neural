const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const runtime={setTimeout,clearTimeout,setInterval,clearInterval,performance};
vm.createContext(runtime);
for(const nome of ['d3-dispatch','d3-quadtree','d3-timer','d3-force'])
 vm.runInContext(fs.readFileSync(`inventario/static/inventario/vendor/d3/${nome}.min.js`,'utf8'),runtime);
const exemplo=[{id:'A',x:0,y:0},{id:'B',x:100,y:100}];
runtime.d3.forceSimulation(exemplo).force('carga',runtime.d3.forceManyBody()).stop().tick(20);
assert.ok(exemplo.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
class Elemento {
 constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.events={};this.value='';this.hidden=false;this.classes=new Set();this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)};}
 setAttribute(k,v){this.attrs[k]=String(v)} getAttribute(k){return this.attrs[k]} append(...x){this.children.push(...x)} replaceChildren(...x){this.children=x}
 addEventListener(k,f){this.events[k]=f}
}
const ids=['dependency-graph','graph-status','graph-details','graph-controls','graph-search','graph-type','graph-severity','graph-zoom-in','graph-zoom-out','graph-reset'];
const elementos=Object.fromEntries(ids.map(k=>[k,new Elemento('div')]));
const dados={largura:760,altura:760,nos:[{id:'A',nome:'Cisco',x:380,y:380,faixa:'alto',efetivo:10,indice:50,criticidade:4,tipo:'4',tipo_nome:'Switch',maior_cvss:10,cves:[{id:'CVE-2023-20198',cvss:10}],total_cves:1},{id:'B',nome:'Servidor',x:380,y:150,faixa:'baixo',efetivo:2,indice:3,criticidade:2,tipo:'1',tipo_nome:'Servidor',maior_cvss:null,cves:[],total_cves:0}],arestas:[{origem:'A',destino:'B',peso:.2,espessura:2}]};
elementos['graph-data']={textContent:JSON.stringify(dados)};
const document={getElementById:id=>elementos[id],createElementNS:(_,tag)=>new Elemento(tag),createElement:tag=>new Elemento(tag),addEventListener:(nome,fn)=>{if(nome==='DOMContentLoaded')fn()}};
vm.runInNewContext(fs.readFileSync('inventario/static/inventario/grafo.js','utf8'),{document,window:{},JSON,Object,Map,Set,Math,String,encodeURIComponent});
const svg=elementos['dependency-graph'].children[0], links=svg.children.filter(e=>e.tag==='a');
assert.ok(svg.children.find(e=>e.classes.has('fluxo-critico')));
links[0].events.click({preventDefault(){}});assert.match(elementos['graph-details'].children[2].textContent,/CVE-2023-20198/);
elementos['graph-type'].value='1';elementos['graph-type'].events.change();assert.ok(links[0].classes.has('graph-filtered'));assert.ok(!links[1].classes.has('graph-filtered'));
elementos['graph-zoom-in'].events.click();assert.notEqual(svg.attrs.viewBox,'0 0 760 760');elementos['graph-reset'].events.click();assert.equal(svg.attrs.viewBox,'0 0 760 760');
console.log('OK: detalhes, filtro, alcance crítico e zoom do grafo.');
