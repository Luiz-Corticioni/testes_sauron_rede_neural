/* Busca local somente entre links já renderizados com as permissões da sessão. */
document.addEventListener("DOMContentLoaded", () => {
  const campo = document.getElementById("buscar-menu");
  const navegacao = document.getElementById("navegacao-links");
  const resultado = document.getElementById("resultado-menu");
  if (!campo || !navegacao || !resultado) return;
  const area = campo.closest(".nav-search");
  if (area) area.hidden = false;
  const normalizar = texto => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").trim();
  const grupos = [];
  for (const elemento of navegacao.children) {
    if (elemento.classList.contains("nav-label")) grupos.push({titulo: elemento, links: []});
    else if (elemento.tagName === "A" && grupos.length) grupos.at(-1).links.push(elemento);
  }
  const filtrar = () => {
    const busca = normalizar(campo.value);
    let encontrados = 0;
    for (const grupo of grupos) {
      let visiveis = 0;
      for (const link of grupo.links) {
        const visivel = !busca || normalizar(link.textContent).includes(busca);
        link.hidden = !visivel;
        if (visivel) visiveis++;
      }
      grupo.titulo.hidden = visiveis === 0;
      encontrados += visiveis;
    }
    resultado.textContent = !busca ? "" : encontrados === 1 ? "1 seção encontrada." :
      encontrados ? `${encontrados} seções encontradas.` : "Nenhuma seção encontrada.";
  };
  campo.addEventListener("input", filtrar);
  filtrar();
});
