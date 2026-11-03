
from math import e
from pathlib import Path
from unittest import TestCase
from inventario.matematica import euler


class M5(TestCase):
    def test_sem_compile_eval(self):
        import ast
        arvore=ast.parse(Path(euler.__file__).read_text(encoding="utf-8"))
        proibidas=[n.func.id for n in ast.walk(arvore) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id in ("eval","compile")]
        self.assertEqual(proibidas,[])

    def test_edo_euler_e_rk4(self):
        for metodo,tolerancia in ((euler.metodo_euler,.02),(euler.rk4,1e-8)):
            resultado=metodo(lambda t,y:y,1.0,0,1,100)
            self.assertAlmostEqual(resultado["estados"][-1],e,delta=tolerancia)
        self.assertAlmostEqual(euler.FuncaoMatematica("sin(pi/2)+x^2").avaliar(3),10)

