/* SVG original e atmosfera decorativa. Nenhuma imagem ou fonte externa. */
document.addEventListener("DOMContentLoaded", () => {
  const motion = matchMedia("(prefers-reduced-motion:reduce)");
  const eyes = [...document.querySelectorAll("[data-eye]")];
  const original = new Map(eyes.map(eye => [eye, Number(eye.dataset.index) || 0]));
  const format = n => n.toLocaleString("pt-BR", {maximumFractionDigits:1});
  const setEye = (eye, index) => {
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
  const animations = eyes.flatMap(eye => [...eye.querySelectorAll("[data-eye-animation]")]);
  const canvas = document.getElementById("embers");
  const context = canvas?.getContext("2d");
  let request = null, previous = 0, smilStarted = false;
  let width = 0, height = 145;
  const particles = Array.from({length:36}, () => ({x:Math.random(), y:Math.random(), speed:.015 + Math.random() * .02, size:.5 + Math.random()}));
  const resize = () => {
    if (!context) return;
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = width * ratio; canvas.height = height * ratio;
    context.setTransform(ratio,0,0,ratio,0,0);
  };
  const frame = timestamp => {
    if (document.hidden || motion.matches) return;
    request = requestAnimationFrame(frame);
    if (timestamp - previous < 1000/30) return;
    const delta = Math.min((timestamp-previous)/1000,.1);
    previous = timestamp;
    context.clearRect(0,0,width,height);
    context.fillStyle = "#ff4d2e";
    particles.forEach(p => {
      p.y -= p.speed * delta;
      if (p.y < 0) { p.y = 1; p.x = Math.random(); }
      context.globalAlpha = p.y * .4;
      context.beginPath(); context.arc(p.x * width,p.y * height,p.size,0,Math.PI*2); context.fill();
    });
  };
  const synchronize = () => {
    const active = !document.hidden && !motion.matches;
    document.body.classList.toggle("page-hidden", document.hidden);
    if (active && !smilStarted) {
      animations.forEach(a => { if (!a.closest(".eye-small")) a.beginElement(); });
      smilStarted = true;
    }
    eyes.forEach(eye => active ? eye.unpauseAnimations() : eye.pauseAnimations());
    if (request !== null) cancelAnimationFrame(request);
    request = null;
    if (context && active) { previous = performance.now(); request = requestAnimationFrame(frame); }
    if (context && !active) context.clearRect(0,0,width,height);
  };
  resize(); synchronize();
  motion.addEventListener("change", synchronize);
  document.addEventListener("visibilitychange", synchronize);
  window.addEventListener("resize", resize, {passive:true});
});
