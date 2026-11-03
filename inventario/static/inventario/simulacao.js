/* Token do formulário (cookie CSRF HttpOnly). Simular não grava no banco. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("simulacao-risco");
  if (!form) return;
  const output = document.getElementById("resultado-simulacao");
  const button = form.querySelector('button[type="submit"]');
  const reset = document.getElementById("reset-simulation");
  const shortcuts = [...document.querySelectorAll("[data-simulate]")];
  const original = JSON.parse(document.getElementById("risk-data")?.textContent || "{}");
  let generation = 0;
  const disable = disabled => [button,...shortcuts].forEach(b => b.disabled = disabled);
  shortcuts.forEach(shortcut => shortcut.addEventListener("click", () => {
    form.elements.incidencias.value = shortcut.dataset.simulate;
    form.requestSubmit();
    output.focus();
  }));
  output.tabIndex = -1;
  reset.addEventListener("click", () => {
    generation += 1;
    window.SauronEye?.atualizar(original.indices || [],false);
    output.textContent = "Cenário atual restaurado. Nenhum cadastro foi alterado.";
    disable(false);
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const current = ++generation;
    disable(true);
    output.textContent = "Calculando a simulação…";
    try {
      const data = new FormData(form);
      const result = await SauronHTTP.json(form.action, {
        method:"POST", credentials:"same-origin",
        headers:{"Content-Type":"application/json", "X-CSRFToken":data.get("csrfmiddlewaretoken")},
        body:JSON.stringify({perfil:data.get("perfil"), incidencias_corrigidas:data.get("incidencias").split(",").map(id => id.trim()).filter(Boolean)})
      });
      if (current !== generation) return;
      const lines = result.antes.ids_ativos.map((id,i) => `${id}: ${result.antes.risco_efetivo[i]} → ${result.depois.risco_efetivo[i]}`);
      output.textContent = `SIMULAÇÃO SEM GRAVAÇÃO\nRedução total: ${result.ganho_total.toLocaleString("pt-BR", {maximumFractionDigits:2})}\n${lines.join("\n")}`;
      window.SauronEye?.atualizar(result.depois.indices || []);
    } catch (error) {
      if (current === generation) output.textContent = error.message || "Não foi possível calcular a simulação.";
    } finally {
      if (current === generation) disable(false);
    }
  });
});
