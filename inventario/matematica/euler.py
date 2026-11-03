"""Métodos numéricos puros, com limites de tamanho, custo e tempo."""

from __future__ import annotations

import ast
from collections.abc import Callable
import math
import operator
import time

FUNCOES = {
    "sin": math.sin,
    "sen": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "ln": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
}
CONSTANTES = {"pi": math.pi, "e": math.e}
NOS_PERMITIDOS = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)
TEMPO_MAXIMO = 0.5
MAXIMO_INTERVALOS = 100_000


class ConstantesFloat(ast.NodeTransformer):
    """Evita que Python tente construir inteiros de tamanho arbitrário."""

    def visit_Constant(self, no):
        if isinstance(no.value, bool) or not isinstance(no.value, (int, float)):
            raise ValueError("Use apenas constantes numéricas reais.")
        try:
            valor = float(no.value)
        except OverflowError as erro:
            raise ValueError("Constante numérica grande demais.") from erro
        if not math.isfinite(valor):
            raise ValueError("Constantes precisam ser finitas.")
        return ast.copy_location(ast.Constant(value=valor), no)


def validar_arvore(arvore):
    pilha = [(arvore, 0)]
    while pilha:
        no, profundidade = pilha.pop()
        if profundidade > 20:
            raise ValueError("A expressão ultrapassa a profundidade máxima de 20.")
        if not isinstance(no, NOS_PERMITIDOS):
            raise ValueError(f"Elemento não permitido: {type(no).__name__}")
        if isinstance(no, ast.Name) and no.id not in {"x", *FUNCOES, *CONSTANTES}:
            raise ValueError(f"Nome não permitido: {no.id}")
        if isinstance(no, ast.Call):
            if not isinstance(no.func, ast.Name) or no.func.id not in FUNCOES:
                raise ValueError("Use apenas as funções matemáticas do menu.")
            maximo = 2 if no.func.id in {"log", "ln"} else 1
            if no.keywords or not 1 <= len(no.args) <= maximo:
                raise ValueError("Quantidade de argumentos inválida.")
        pilha.extend((filho, profundidade + 1) for filho in ast.iter_child_nodes(no))


def verificar_tempo(prazo):
    if time.monotonic() >= prazo:
        raise ValueError("Tempo máximo de cálculo excedido; reduza o número de intervalos.")


def finito(valor):
    try:
        numero = float(valor)
    except (TypeError, OverflowError) as erro:
        raise ValueError("O resultado deve ser um número real finito.") from erro
    if not math.isfinite(numero):
        raise ValueError("O resultado deve ser um número real finito.")
    return numero


class FuncaoMatematica:
    def __init__(self, expressao: str):
        if not isinstance(expressao, str) or len(expressao) > 200:
            raise ValueError("A expressão deve ter no máximo 200 caracteres.")
        self.expressao = expressao.strip().replace("^", "**")
        try:
            arvore = ast.parse(self.expressao, mode="eval")
            validar_arvore(arvore)
            arvore = ConstantesFloat().visit(arvore)
            self._arvore = arvore.body
        except (SyntaxError, RecursionError) as erro:
            raise ValueError("Expressão inválida ou complexa demais.") from erro

    def avaliar(self, x: float) -> float:
        ambiente={"x":finito(x), **CONSTANTES}
        operadores={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
                    ast.Div:operator.truediv,ast.Pow:operator.pow,ast.Mod:operator.mod}
        def interpretar(no):
            if isinstance(no,ast.Constant):
                return no.value
            if isinstance(no,ast.Name):
                return ambiente.get(no.id,FUNCOES.get(no.id))
            if isinstance(no,ast.UnaryOp):
                valor=interpretar(no.operand)
                return finito(-valor if isinstance(no.op,ast.USub) else +valor)
            if isinstance(no,ast.BinOp):
                return finito(operadores[type(no.op)](interpretar(no.left),interpretar(no.right)))
            if isinstance(no,ast.Call):
                return finito(FUNCOES[no.func.id](*(interpretar(arg) for arg in no.args)))
            raise ValueError("Nó não permitido.")
        try:
            return finito(interpretar(self._arvore))
        except (OverflowError,ZeroDivisionError,TypeError,RecursionError) as erro:
            raise ValueError("Operação fora do domínio dos reais finitos.") from erro

    def identificar_tipo(self) -> str:
        texto = self.expressao.lower()
        if any(nome in texto for nome in ("sin", "sen", "cos", "tan")):
            return "Trigonométrica"
        if "exp" in texto or "e**" in texto:
            return "Exponencial"
        if "log" in texto or "ln" in texto:
            return "Logarítmica"
        if "sqrt" in texto or "**0.5" in texto:
            return "Radical"
        if "/" in texto:
            return "Racional ou quociente"
        return "Polinomial ou algébrica" if "x" in texto else "Constante"


class Derivador:
    @staticmethod
    def validar_passo(x, h, ordem):
        denominador = 2*h if ordem == 1 else h*h
        if (h <= 0 or x+h == x or x-h == x or not math.isfinite(x+h)
                or not math.isfinite(x-h) or not math.isfinite(denominador) or denominador == 0):
            raise ValueError("Passo h sem resolução numérica para este x; ajuste h ou reescale os valores.")

    @staticmethod
    def central(funcao: Callable, x: float, h: float = 1e-5) -> float:
        x, h = finito(x), finito(h)
        Derivador.validar_passo(x, h, 1)
        return finito((funcao(x + h) - funcao(x - h)) / (2 * h))

    @staticmethod
    def segunda(funcao: Callable, x: float, h: float = 1e-4) -> float:
        x, h = finito(x), finito(h)
        Derivador.validar_passo(x, h, 2)
        return finito((funcao(x + h) - 2 * funcao(x) + funcao(x - h)) / (h * h))


class Integrador:
    @staticmethod
    def validar(a, b, n, par=False):
        if isinstance(n, bool) or not isinstance(n, int) or not 0 < n <= MAXIMO_INTERVALOS:
            raise ValueError("n deve ser inteiro positivo, no máximo 100000.")
        if par and n % 2:
            raise ValueError("Na Regra de Simpson, n deve ser par.")
        return finito(a), finito(b), time.monotonic() + TEMPO_MAXIMO

    @staticmethod
    def simpson(funcao: Callable, a: float, b: float, n: int = 100) -> float:
        a, b, prazo = Integrador.validar(a, b, n, par=True)
        h = (b - a) / n
        soma = finito(funcao(a)) + finito(funcao(b))
        for i in range(1, n):
            verificar_tempo(prazo)
            soma += (4 if i % 2 else 2) * finito(funcao(a + i * h))
        verificar_tempo(prazo)
        return finito(soma * h / 3)

    @staticmethod
    def trapezios(funcao: Callable, a: float, b: float, n: int = 100) -> float:
        a, b, prazo = Integrador.validar(a, b, n)
        h = (b - a) / n
        soma = (finito(funcao(a)) + finito(funcao(b))) / 2
        for i in range(1, n):
            verificar_tempo(prazo)
            soma += finito(funcao(a + i * h))
        verificar_tempo(prazo)
        return finito(soma * h)

def integrar_edo(funcao,y0,t0,t1,passos,metodo):
    """Integra dy/dt=f(t,y); tempos em unidade definida pelo chamador, sem extrapolar."""
    import numpy as np
    if type(passos) is not int or not 1<=passos<=MAXIMO_INTERVALOS:
        raise ValueError("Quantidade de passos inválida.")
    t0,t1=finito(t0),finito(t1)
    if t1<=t0 or metodo not in ("euler","rk4"):
        raise ValueError("Intervalo ou método inválido.")
    try:
        y=np.asarray(y0,dtype=float)
    except (TypeError,ValueError,OverflowError) as erro:
        raise ValueError("Estado inicial inválido.") from erro
    if not y.size or not np.all(np.isfinite(y)) or y.size*passos>2000000:
        raise ValueError("Estado não finito ou limite de trabalho excedido.")
    h=(t1-t0)/passos
    tempos=np.linspace(t0,t1,passos+1)
    estados=[y.copy()]
    def derivada(t,valor):
        d=np.asarray(funcao(t,valor),dtype=float)
        if d.shape!=y.shape or not np.all(np.isfinite(d)):
            raise ValueError("Derivada com forma ou valores inválidos.")
        return d
    for t in tempos[:-1]:
        try:
            k1=derivada(t,y)
            if metodo=="euler":
                y=y+h*k1
            else:
                k2=derivada(t+h/2,y+h*k1/2)
                k3=derivada(t+h/2,y+h*k2/2)
                k4=derivada(t+h,y+h*k3)
                y=y+h*(k1+2*k2+2*k3+k4)/6
        except (OverflowError,ZeroDivisionError,TypeError,FloatingPointError) as erro:
            raise ValueError("EDO fora do domínio numérico.") from erro
        if not np.all(np.isfinite(y)):
            raise ValueError("Integração não finita; reduza o passo.")
        estados.append(y.copy())
    return {"tempos":tempos.tolist(),"estados":np.asarray(estados).tolist()}


def metodo_euler(funcao,y0,t0=0,t1=1,passos=100):
    """Euler explícito para EDO, erro global de ordem O(h)."""
    return integrar_edo(funcao,y0,t0,t1,passos,"euler")


def rk4(funcao,y0,t0=0,t1=1,passos=100):
    """Runge-Kutta clássico de quarta ordem para EDO."""
    return integrar_edo(funcao,y0,t0,t1,passos,"rk4")
