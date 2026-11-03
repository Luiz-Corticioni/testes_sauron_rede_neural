document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("verify-audit");
  const output = document.getElementById("audit-result");
  button?.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const result = await SauronHTTP.json("/api/auditoria/verificar/", {acceptedStatuses: [409]});
      output.textContent = result.integra
        ? `Cadeia íntegra: ${result.verificados} registros verificados.`
        : `Integridade rompida no elo ${result.primeiro_elo_quebrado}.`;
    } catch (error) {
      output.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
});
