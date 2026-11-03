"use strict";

// Respostas de login/erro podem ser HTML. Nunca tratá-las como JSON cegamente.
window.SauronHTTP = {
  async json(url, options = {}) {
    const {acceptedStatuses = [], ...fetchOptions} = options;
    const response = await fetch(url, {credentials: "same-origin", ...fetchOptions});
    if (response.redirected && new URL(response.url).pathname === "/entrar/") {
      throw new Error("Sua sessão expirou. Entre novamente para continuar.");
    }
    if (response.redirected && new URL(response.url).pathname === "/mfa/") {
      const erro = new Error("Confirme novamente seu segundo fator em /mfa/ e refaça a operação.");
      erro.reautenticacao = true;
      throw erro;
    }
    const type = response.headers.get("content-type") || "";
    if (!type.includes("application/json")) {
      throw new Error(`O servidor respondeu ${response.status}. Consulte o diagnóstico do servidor.`);
    }
    const data = await response.json();
    if (!response.ok && !acceptedStatuses.includes(response.status)) throw new Error(data.erro || `Operação indisponível (${response.status}).`);
    return data;
  },
  csrf() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  }
};
