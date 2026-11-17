/* Feedback visual não cria nem altera dados; mensagens reais continuam no HTML. */
document.addEventListener('DOMContentLoaded', () => {
  const reduzido = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const mensagem = document.querySelector('.message.ativo-criado');
  if (mensagem) {
    mensagem.classList.add('toast-visivel');
    const fechar = document.createElement('button');
    fechar.type = 'button'; fechar.textContent = 'Fechar';
    fechar.addEventListener('click', () => mensagem.remove());
    mensagem.append(fechar);
    document.querySelector('.page-heading h1')?.classList.add('ativo-vinculado');
  }
  const animar = (elemento, fim, casas=0, de=0) => {
    if (!Number.isFinite(fim)) return;
    if (reduzido || !window.requestAnimationFrame) { elemento.textContent = fim.toLocaleString('pt-BR',{maximumFractionDigits:casas}); return; }
    const inicio = performance.now(), duracao = 600;
    const quadro = agora => {
      const progresso = Math.min(1, Math.max(0, (agora - inicio) / duracao));
      const valor = de + (fim-de) * (1 - Math.pow(1-progresso, 3));
      elemento.textContent = valor.toLocaleString('pt-BR',{maximumFractionDigits:casas});
      if (progresso < 1) window.requestAnimationFrame(quadro);
    };
    window.requestAnimationFrame(quadro);
  };
  window.SauronContar = animar;
  document.querySelectorAll('[data-contagem]').forEach(elemento => {
    const fim = Number(elemento.dataset.contagem);
    if (Number.isSafeInteger(fim) && fim > 0) animar(elemento, fim);
  });
});
