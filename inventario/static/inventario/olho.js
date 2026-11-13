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
    }
  };
  eyes.forEach(eye => setEye(eye, original.get(eye)));
  window.SauronEye = {
    atualizar(indices, simulation = true) {
      const index = indices.length ? indices.reduce((a,b) => a+b,0) / indices.length : 0;
      eyes.filter(eye => !eye.classList.contains("eye-small")).forEach(eye => setEye(eye,index));
      document.querySelectorAll("[data-global-index]").forEach(e => e.textContent = format(index));
      document.querySelectorAll("[data-eye-caption]").forEach(e => {
        e.textContent = simulation ? "Média dos índices · simulação sem gravação" : "Média dos índices · cenário atual";
      });
    }
  };
});
