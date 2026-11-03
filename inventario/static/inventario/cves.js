"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("cve-search-form");
  const output = document.getElementById("cve-search-results");
  const searchStatus = document.getElementById("cve-search-status");
  const submit = document.getElementById("cve-search-button");
  if (form) form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    searchStatus.textContent = "Consultando a NVD…";
    output.replaceChildren();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);
    try {
      const data = await SauronHTTP.json(form.action, {
        method: "POST", signal: controller.signal,
        headers: {"Content-Type": "application/json", "X-CSRFToken": SauronHTTP.csrf()},
        body: JSON.stringify({termo: document.getElementById("cve-search").value,
                              forcar: document.getElementById("cve-force").checked})
      });
      searchStatus.textContent = `${data.resultados.length} de ${data.total} resultados · ${data.origem} · consulta: ${new Date(data.consultado_em).toLocaleString("pt-BR")}${data.truncado ? " · exibição limitada a 20; refine sua busca" : ""}. ${data.aviso}`;
      data.resultados.forEach(item => {
        const card = document.createElement("article");
        card.className = "panel cve-result";
        const title = document.createElement("h3"); title.textContent = item.id;
        const description = document.createElement("p"); description.textContent = item.descricao;
        const score = document.createElement("p");
        score.textContent = item.cvss.score === null ? "CVSS não informado" : `CVSS ${item.cvss.versao}: ${item.cvss.score} · fonte: ${item.cvss.fonte}`;
        const vector = document.createElement("code"); vector.textContent = item.cvss.vetor || "Sem vetor";
        const check = document.createElement("p");
        check.textContent = item.cvss.score_recalculado === null ? item.cvss.aviso : `Recálculo local: ${item.cvss.score_recalculado} · ${item.cvss.consistente ? "confere com a fonte" : "divergência: revisar"}. ${item.cvss.aviso}`;
        const link = document.createElement("a"); link.textContent = "Ver registro na NVD";
        link.href = item.url; link.target = "_blank"; link.rel = "noopener noreferrer";
        card.append(title, description, score, vector, check, link);
        const comparison = item.comparacao_cvss;
        if (comparison) {
          const notes = document.createElement("p");
          const fmt = value => value === null ? "não disponível" : value.toLocaleString("pt-BR", {minimumFractionDigits:1, maximumFractionDigits:1});
          notes.textContent = `3.1 local: ${fmt(comparison.local31.nota)} · 4.0 na NVD: ${fmt(comparison.nvd40.nota)} · diferença 4.0 − 3.1: ${fmt(comparison.diferenca_40_menos_31)}${comparison.diferenca_40_menos_31 === null ? "" : " pontos"}.`;
          card.append(notes);
        }
        if (form.dataset.compararUrl) {
          const compare = document.createElement("a");
          compare.textContent = "Comparar notas e conferir publicadores";
          compare.href = `${form.dataset.compararUrl}?cve=${encodeURIComponent(item.id)}`;
          card.append(compare);
        }
        if (form.dataset.cadastrarUrl) {
          const create = document.createElement("a");
          create.className = "button secondary";
          create.textContent = form.dataset.ativo ? "Revisar e vincular ao ativo" : "Revisar cadastro";
          create.href = `${form.dataset.cadastrarUrl}?cve=${encodeURIComponent(item.id)}`;
          card.append(create);
        }
        output.append(card);
      });
    } catch (error) {
      searchStatus.textContent = error.name === "AbortError" ? "A consulta demorou demais. Tente novamente; as sugestões locais continuam disponíveis." : error.message;
    } finally { clearTimeout(timeout); submit.disabled = false; }
  });
  const button = document.getElementById("load-kev");
  const status = document.getElementById("kev-status");
  const list = document.getElementById("kev-list");
  if (!button) return;
  button.addEventListener("click", async () => {
    status.textContent = "Lendo o catálogo local…";
    button.disabled = true;
    try {
      const data = await SauronHTTP.json("/api/cves/kev/?limite=15");
      status.textContent = `${data.quantidade} registros · origem: ${data.origem}`;
      list.replaceChildren();
      data.vulnerabilidades.forEach((item, i) => {
        const article = document.createElement("article");
        article.className = "panel kev-card";
        const number = document.createElement("span");
        number.textContent = String(i + 1).padStart(2, "0");
        const details = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = item.cveID;
        const description = document.createElement("p");
        description.textContent = item.vulnerabilityName;
        const source = document.createElement("small");
        source.textContent = `${item.vendorProject} · ${item.product} · ${item.dateAdded}`;
        details.append(title, description, source);
        article.append(number, details);
        list.append(article);
      });
    } catch (error) {
      status.textContent = `Não foi possível consultar: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
});
