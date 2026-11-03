"""Métodos numéricos com exemplos e explicação do resultado."""

from inventario.matematica.euler import Derivador, FuncaoMatematica, Integrador
from inventario.cli_menus.comum import Cor, menu_seguro
from inventario.cli_menus.guias import GUIAS


class EulerMenu:
    @menu_seguro()
    def menu_euler(self):
        opcoes = [
            ("1", "Avaliar f(x)"),
            ("2", "Derivada central"),
            ("3", "Derivada segunda"),
            ("4", "Integral de Simpson"),
            ("5", "Guia de notação e exemplos"),
            ("6", "Tendência e risco-dia"),
            ("7", "Integral por trapézios"),
            ("8", "Grafo: alcance, ciclos e cenário por camada"),
        ]
        while True:
            op = self._submenu("MODO EULER", opcoes)
            if op == "0":
                return
            if op == "5":
                self.saida(GUIAS["MODO EULER"])
            elif op == "6":
                self.historico_risco_terminal()
            elif op == "8":
                from inventario.cli_menus.relacoes import analisar
                analisar(self)
            elif op in {"1", "2", "3", "4", "7"}:
                self._calcular_euler(op)
            else:
                self._falha("Opção inválida. Escolha de 1 a 8, ? ou 0.")
            self._pausa()

    def _calcular_euler(self, opcao):
        self.saida("Expressão: só o lado direito, ex. x^2 + 2*x. Use ponto decimal.")
        funcao = FuncaoMatematica(self._texto("Expressão"))
        self.saida(f"Tipo sugerido (heurística): {funcao.identificar_tipo()}")
        if opcao in {"1", "2", "3"}:
            x = self._decimal("Ponto x")
            if opcao == "1":
                valor = funcao.avaliar(x)
                metodo = f"Substituição de x por {x}: f({x}) = {valor}."
            else:
                h = self._decimal("Passo h > 0", padrao=1e-5 if opcao == "2" else 1e-4)
                if h <= 0:
                    raise ValueError("O passo h deve ser positivo.")
                anterior, central, posterior = [funcao.avaliar(p) for p in (x - h, x, x + h)]
                if opcao == "2":
                    valor = Derivador.central(funcao.avaliar, x, h)
                    metodo = f"[f(x+h)-f(x-h)]/(2h), h={h}; amostras {posterior:g} e {anterior:g}."
                else:
                    valor = Derivador.segunda(funcao.avaliar, x, h)
                    metodo = f"[f(x+h)-2*f(x)+f(x-h)]/h², h={h}; f(x)={central:g}."
        else:
            a, b = self._decimal("Limite a"), self._decimal("Limite b")
            n = self._inteiro("Subintervalos n (par para Simpson)", 2, 100000, 100)
            while opcao == "4" and n % 2:
                self._falha("Simpson exige n par: 2, 4, 6, ..., 100000.")
                n = self._inteiro("Subintervalos pares", 2, 100000, 100)
            h = (b - a) / n
            if opcao == "4":
                valor = Integrador.simpson(funcao.avaliar, a, b, n)
                metodo = f"h/3 * [f(a)+4*f1+2*f2+...+4*f(n-1)+f(b)]; h={h:g}, n={n}."
            else:
                valor = Integrador.trapezios(funcao.avaliar, a, b, n)
                metodo = f"h * [(f(a)+f(b))/2 + soma dos pontos internos]; h={h:g}, n={n}."
            if a > b:
                self.saida("Limites invertidos: a integral muda de sinal.")
        self.saida(f'Resultado: {Cor.destaque(f"{valor:.10g}")}')
        self.saida("Como foi calculado: " + metodo)
        if opcao != "1":
            self.saida(
                "Aproximação numérica; use função suave no intervalo e compare outros passos."
            )
