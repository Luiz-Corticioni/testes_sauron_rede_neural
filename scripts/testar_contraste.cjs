const assert = require('node:assert/strict'), fs = require('node:fs');
function luminosidade(hex) {
  const componentes = hex.match(/\w\w/g).map(v => parseInt(v,16)/255).map(v => v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
  return .2126*componentes[0] + .7152*componentes[1] + .0722*componentes[2];
}
const tokens=fs.readFileSync('inventario/static/inventario/tokens.css','utf8');
const estilos=fs.readFileSync('inventario/static/inventario/sentinela.css','utf8');
const osso=tokens.match(/--osso:#([\da-f]{6})/i)[1];
const pares=[...estilos.matchAll(/\.heat-(?:low|high)\{background:#([\da-f]{6});color:#([\da-f]{6})\}/gi)].map(m=>[m[2],m[1]]);
assert.equal(pares.length,2);
for (const [texto,fundo] of [[osso,'191411'],...pares]) {
  const [a,b]=[luminosidade(texto),luminosidade(fundo)].sort((x,y)=>y-x);
  const contraste=(a+.05)/(b+.05);
  assert.ok(contraste>=4.5, `Contraste insuficiente: ${texto}/${fundo}: ${contraste.toFixed(2)}:1`);
  console.log(`#${texto} sobre #${fundo}: ${contraste.toFixed(2)}:1`);
}
