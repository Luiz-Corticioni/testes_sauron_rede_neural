document.addEventListener('DOMContentLoaded', () => {
  const dialogo = document.getElementById('comandos');
  const abrir = document.getElementById('comandos-abrir');
  if (!dialogo || typeof dialogo.showModal !== 'function') return;
  const campo = document.getElementById('comandos-busca');
  const lista = document.getElementById('comandos-lista');
  const status = document.getElementById('comandos-resultado');
  // Reaproveita apenas links que o servidor já autorizou no menu.
  const itens = [...document.querySelectorAll('#navegacao-links a')].map(link => ({
    nome: link.querySelector('b')?.textContent.trim() || link.textContent.trim(),
    descricao: link.querySelector('small')?.textContent.trim() || '', href: link.getAttribute('href')
  }));
  const ativos = itens.find(item => item.nome === 'Ativos');
  const atualizar = () => {
    const termo = campo.value.trim().toLocaleLowerCase('pt-BR');
    const encontrados = itens.filter(item => `${item.nome} ${item.descricao}`.toLocaleLowerCase('pt-BR').includes(termo));
    const resultados = encontrados.map(item => {
      const li = document.createElement('li'), link = document.createElement('a'), desc = document.createElement('small');
      link.href = item.href; link.textContent = item.nome; desc.textContent = item.descricao; link.append(desc); li.append(link); return li;
    });
    if (ativos && termo) {
      const li = document.createElement('li'), link = document.createElement('a');
      link.href = `${ativos.href}?${new URLSearchParams({q: campo.value.trim()})}`;
      link.textContent = 'Buscar este termo no inventário de ativos'; li.append(link); resultados.push(li);
    }
    lista.replaceChildren(...resultados);
    status.textContent = `${encontrados.length} seção(ões) encontrada(s).`;
  };
  const mostrar = () => { campo.value = ''; atualizar(); dialogo.showModal(); campo.focus(); };
  abrir.hidden = false; abrir.addEventListener('click', mostrar); campo.addEventListener('input', atualizar);
  document.addEventListener('keydown', evento => {
    if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'k' && !dialogo.open) {
      evento.preventDefault(); mostrar();
    }
  });
});
