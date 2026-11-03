"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[data-autocomplete-cve]").forEach((input, index) => {
    const wrap = document.createElement("div");
    wrap.className = "autocomplete-wrap";
    input.replaceWith(wrap);
    wrap.append(input);
    const list = document.createElement("div");
    list.id = `cve-suggestions-${index}`;
    list.className = "autocomplete-list";
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-label", "Sugestões de CVEs");
    list.hidden = true;
    const message = document.createElement("small");
    message.className = "autocomplete-status";
    message.id = `${list.id}-status`;
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");
    wrap.append(list, message);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", list.id);
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-describedby", [input.getAttribute("aria-describedby"), message.id].filter(Boolean).join(" "));
    input.autocomplete = "off";
    let timer, controller, sequence = 0, selected = -1, results = [];

    function close() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      selected = -1;
    }

    function choose(i) {
      if (!results[i]) return;
      sequence += 1;
      clearTimeout(timer);
      controller?.abort();
      input.value = results[i].id;
      close();
      message.textContent = `${input.value} selecionada. Confirme os dados antes de cadastrar.`;
      input.dispatchEvent(new Event("change", {bubbles: true}));
      input.dispatchEvent(new CustomEvent("sauron:cve-selecionada", {bubbles: true, detail: results[i]}));
      input.focus();
    }

    input.addEventListener("input", () => {
      clearTimeout(timer);
      controller?.abort();
      const current = ++sequence;
      close();
      const term = input.value.trim();
      if (term.length < 2) { message.textContent = "Digite ao menos dois caracteres para ver sugestões."; return; }
      timer = setTimeout(async () => {
        controller = new AbortController();
        message.textContent = "Buscando no catálogo local…";
        try {
          const data = await SauronHTTP.json(`/api/cves/sugestoes/?q=${encodeURIComponent(term)}`, {signal: controller.signal});
          if (current !== sequence) return;
          results = data.sugestoes;
          list.replaceChildren();
          results.forEach((item, i) => {
            const option = document.createElement("button");
            option.type = "button";
            option.id = `${list.id}-${i}`;
            option.setAttribute("role", "option");
            option.setAttribute("aria-selected", "false");
            option.tabIndex = -1;
            const title = document.createElement("strong");
            title.textContent = item.id;
            const description = document.createElement("span");
            description.textContent = item.titulo || item.descricao || "Sem descrição";
            const source = document.createElement("small");
            source.textContent = `${item.origem} · ${item.correspondencia}`;
            option.append(title, description, source);
            option.addEventListener("mousedown", event => event.preventDefault());
            option.addEventListener("click", () => choose(i));
            list.append(option);
          });
          list.hidden = results.length === 0;
          input.setAttribute("aria-expanded", String(results.length > 0));
          message.textContent = results.length ? `${results.length} sugestões. Use ↑/↓ e Enter, ou clique para selecionar.` : "Sem sugestões locais. Consulte a NVD por identificador ou nome de produto.";
        } catch (error) {
          if (error.name !== "AbortError" && current === sequence) message.textContent = error.message;
        }
      }, 250);
    });
    input.addEventListener("keydown", event => {
      if (event.key === "Escape") { sequence += 1; controller?.abort(); close(); return; }
      if (list.hidden) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        selected = selected < 0 ? (event.key === "ArrowDown" ? 0 : results.length - 1) :
          (selected + (event.key === "ArrowDown" ? 1 : -1) + results.length) % results.length;
        [...list.children].forEach((el, i) => el.setAttribute("aria-selected", String(i === selected)));
        input.setAttribute("aria-activedescendant", `${list.id}-${selected}`);
        list.children[selected].scrollIntoView({block: "nearest"});
      } else if (event.key === "Enter" && selected >= 0) { event.preventDefault(); choose(selected); }
    });
    input.addEventListener("blur", () => { sequence += 1; clearTimeout(timer); controller?.abort(); close(); });
  });
});
