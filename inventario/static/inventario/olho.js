/* SVG original e atmosfera decorativa. Nenhuma imagem ou fonte externa. */
document.addEventListener("DOMContentLoaded", () => {
  const eyes = [...document.querySelectorAll("[data-eye]")];
  const original = new Map(eyes.map(eye => [eye, Number(eye.dataset.index) || 0]));
  const format = n => n.toLocaleString("pt-BR", {maximumFractionDigits:1});
  const setEye = (eye, index) => {
    if (!eye.classList.contains("eye-small") && eye.dataset.disponivel === "false") {
      eye.dataset.band = "indisponivel";
      return;
    }
    index = Math.min(100, Math.max(0, Number(index) || 0));
    eye.style.setProperty("--risco", String(index / 100));
    eye.dataset.band = ["baixo","medio","alto","critico"][Math.min(3, Math.floor(index / 25))];
    if (!eye.classList.contains("eye-small")) {
      eye.querySelector("title").textContent = `Índice global: média ${format(index)} de 100`;
      if (document.body) document.body.dataset.riscoFaixa = eye.dataset.band;
    }
  };
  eyes.forEach(eye => setEye(eye, original.get(eye)));
  const hero = document.querySelector?.(".visao-geral .hero");
  const esfera = hero?.querySelector(".astrolabio");
  const movimento = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  if (hero && esfera && window.requestAnimationFrame) {
    let quadro = 0, posicao = [0, 0];
    const desenhar = () => { esfera.style.transform = `translate3d(${posicao[0]}px, ${posicao[1]}px, 0)`; quadro = 0; };
    hero.addEventListener("pointermove", evento => {
      if (movimento?.matches || window.SauronEfeitos?.reduzidos() || evento.pointerType === "touch") return;
      const area = hero.getBoundingClientRect();
      posicao = [((evento.clientX-area.left)/area.width-.5)*8, ((evento.clientY-area.top)/area.height-.5)*8];
      if (!quadro) quadro = window.requestAnimationFrame(desenhar);
    });
    hero.addEventListener("pointerleave", () => { posicao = [0, 0]; if (!quadro) quadro = window.requestAnimationFrame(desenhar); });
    movimento?.addEventListener?.('change', evento => {
      if (evento.matches) { posicao = [0, 0]; if (!quadro) quadro = window.requestAnimationFrame(desenhar); }
    });
    document.addEventListener('sauron:efeitos', () => {
      if (window.SauronEfeitos?.reduzidos()) { posicao = [0, 0]; if (!quadro) quadro = window.requestAnimationFrame(desenhar); }
    });
  }
  window.SauronEye = {
    atualizar(indices, simulation = true) {
      const index = indices.length ? indices.reduce((a,b) => a+b,0) / indices.length : 0;
      eyes.filter(eye => !eye.classList.contains("eye-small")).forEach(eye => setEye(eye,index));
      document.querySelectorAll("[data-global-index]").forEach(e => {
        const anterior = Number(e.textContent.replace(',', '.'));
        if (window.SauronContar) window.SauronContar(e, index, 1, Number.isFinite(anterior) ? anterior : index);
        else e.textContent = format(index);
      });
      document.querySelectorAll("[data-eye-caption]").forEach(e => {
        e.textContent = simulation ? "Média dos índices · simulação sem gravação" : "Média dos índices · cenário atual";
      });
    }
  };
});
