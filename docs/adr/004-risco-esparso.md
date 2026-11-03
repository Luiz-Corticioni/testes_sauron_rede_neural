# 004 — Núcleo esparso e custo de apresentação

M, A e exposição são CSR; I-A usa fatoração LU esparsa. Matrizes até 300 nós preservam
diagnósticos densos; acima disso numero_condicao é null até diagnóstico explícito.
Norma infinito < 1 certifica estabilidade; potência fornece estimativa do raio. Nos
demais casos usa ARPACK, recusando modelos cuja estimativa não converge.
Resultados mantêm chaves e sequência de linhas. Matrizes grandes só se materializam
no to_dict/export: a representação densa pode custar O(n²) e não faz parte da meta
de 100 ms do núcleo. A listagem completa de prioridades também custa O(n*m).
Benchmark de referência: 5000 nós, 4999 arestas, uma vulnerabilidade, sem serialização.
CI admite margem 10x e imprime o tempo; isso não promete 100 ms em qualquer topologia.
