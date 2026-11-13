/* Navegação móvel com foco contido, Escape e restauração do foco. */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const main = document.getElementById("conteudo");
  const mobile = matchMedia("(max-width:820px)");
  const closeButton = document.querySelector(".drawer-close");
  const opened = () => document.body.classList.contains("sidebar-open");
  const closeMenu = (restore = true) => {
    document.body.classList.remove("sidebar-open");
    toggle.setAttribute("aria-expanded", "false");
    main.inert = false;
    sidebar.inert = mobile.matches;
    if (restore && mobile.matches) toggle.focus();
  };
  sidebar.inert = mobile.matches;
  toggle.addEventListener("click", () => {
    if (opened()) return closeMenu();
    sidebar.inert = false;
    document.body.classList.add("sidebar-open");
    toggle.setAttribute("aria-expanded", "true");
    main.inert = true;
    closeButton.focus();
  });
  document.querySelector(".sidebar-overlay").addEventListener("click", () => closeMenu());
  closeButton.addEventListener("click", () => closeMenu());
  document.querySelectorAll(".sidebar nav a").forEach(link => {
    link.addEventListener("click", () => closeMenu(false));
    if (link.pathname === location.pathname) {
      link.setAttribute("aria-current", "page");
      link.classList.add("active");
    }
  });
  mobile.addEventListener("change", () => closeMenu(false));
  document.addEventListener("keydown", event => {
    if (!opened()) return;
    if (event.key === "Escape") closeMenu();
    if (event.key !== "Tab") return;
    const items = [...sidebar.querySelectorAll("a[href]:not([hidden]),button:not([disabled]),input:not([disabled]):not([type=hidden])")];
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
  document.querySelectorAll(".table-wrap,.graph-scroll").forEach(element => {
    element.tabIndex = 0;
    element.setAttribute("role", "region");
    element.setAttribute("aria-label", element.getAttribute("aria-label") || "Tabela com rolagem");
  });
  const consultarSaude = async () => {
    const chave = "sauron:saude:v1", agora = Date.now();
    try {
      const anterior = JSON.parse(sessionStorage.getItem(chave));
      if (anterior?.status === "ok" && agora-anterior.em >= 0 && agora-anterior.em < 60000) return anterior;
    } catch { /* Armazenamento indisponível: consulta normalmente. */ }
    const response = await fetch("/api/saude/", {credentials:"same-origin", cache:"no-store"});
    if (response.status === 429) throw Object.assign(new Error("Verificação limitada"), {limitado:true});
    if (!response.ok) throw new Error("Saúde indisponível");
    const data = await response.json();
    if (data.status === "ok") {
      try { sessionStorage.setItem(chave, JSON.stringify({status:"ok", em:agora})); } catch { /* Opcional. */ }
    }
    return data;
  };
  consultarSaude()
    .then(data => {
      if (data.status !== "ok") throw new Error("Saúde indisponível");
      document.getElementById("service-label").textContent = "Serviço respondeu";
      document.getElementById("service-detail").textContent = "Resposta obtida há menos de 1 minuto";
      document.getElementById("service-state").textContent = "resposta recente";
      document.getElementById("service-eye").setAttribute("aria-label", "Serviço respondeu ao teste de saúde");
    }).catch(erro => {
      if (erro.limitado) {
        document.getElementById("service-label").textContent = "Verificação limitada";
        document.getElementById("service-detail").textContent = "Aguarde antes de verificar novamente";
        document.getElementById("service-state").textContent = "verificação pendente";
        document.getElementById("service-eye").setAttribute("aria-label", "Verificação limitada; disponibilidade não confirmada");
        return;
      }
      document.getElementById("service-label").textContent = "Serviço sem resposta";
      document.getElementById("service-detail").textContent = "Recarregue para tentar novamente";
      document.getElementById("service-state").textContent = "sem resposta";
      const eye = document.getElementById("service-eye");
      eye.classList.add("offline");
      eye.setAttribute("aria-label", "Teste de saúde sem resposta");
    });
});
