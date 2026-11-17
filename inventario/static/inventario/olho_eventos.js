/* Apenas criações registradas depois de abrir o painel; não identifica exploração. */
document.addEventListener('DOMContentLoaded', () => {
  const origem = document.getElementById('eye-cursor');
  const aviso = document.getElementById('eye-event');
  const olho = document.querySelector('.visao-geral .astrolabio');
  if (!origem || !aviso) return;
  let cursor = JSON.parse(origem.textContent), timer;
  const consultar = async () => {
    if (!document.hidden) {
      try {
        const resposta = await fetch(`/api/olho/eventos/?cursor=${encodeURIComponent(cursor)}`, {cache:'no-store'});
        if (resposta.ok) {
          const dados = await resposta.json();
          cursor = dados.cursor;
          if (dados.eventos.length) {
            const evento = dados.eventos[0];
            const link = document.createElement('a');
            link.href = evento.url;
            link.textContent = `${evento.ativo} · ${evento.cve}`;
            aviso.replaceChildren(document.createTextNode(`${dados.eventos.length} incidência(s) crítica(s) cadastrada(s); não indica exploração. Exemplo: `), link);
            if (olho) {
              olho.classList.add('despertar');
              window.setTimeout(() => olho.classList.remove('despertar'), 2000);
            }
          }
        }
      } catch (_) { /* A próxima tentativa não transforma falha de rede em alerta. */ }
    }
    timer = window.setTimeout(consultar, 60000);
  };
  timer = window.setTimeout(consultar, 60000);
  window.addEventListener('pagehide', () => window.clearTimeout(timer), {once:true});
});
