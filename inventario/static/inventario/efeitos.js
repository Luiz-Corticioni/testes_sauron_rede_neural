/* Preferência local ao navegador; a configuração do sistema continua prevalecendo. */
(() => {
  const chave = 'sauron-reduzir-efeitos';
  let reduzido = false;
  try { reduzido = localStorage.getItem(chave) === '1'; } catch (_) { /* Armazenamento opcional. */ }
  const sistema = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  const aplicar = () => { document.documentElement.dataset.efeitos = reduzido ? 'reduzidos' : 'normais'; };
  aplicar();
  window.SauronEfeitos = { reduzidos: () => reduzido || !!sistema?.matches };
  document.addEventListener('DOMContentLoaded', () => {
    const botao = document.getElementById('efeitos-toggle');
    if (!botao) return;
    const atualizar = () => { botao.setAttribute('aria-pressed', String(reduzido)); };
    botao.hidden = false; atualizar();
    botao.addEventListener('click', () => {
      reduzido = !reduzido; aplicar(); atualizar();
      try { localStorage.setItem(chave, reduzido ? '1' : '0'); } catch (_) { /* Mantém a preferência nesta página. */ }
      document.dispatchEvent(new Event('sauron:efeitos'));
    });
  });
})();
