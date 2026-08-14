# AGENTS

## Objetivo

Este repositório existe para reunir benchmarks de IA em uma estrutura
única, organizada e comparável.

Cada benchmark deve ser tratado como um subprojeto autocontido, com sua
própria documentação, handoff, código, artefatos e resultados.

## Leitura obrigatória

Antes de iniciar qualquer trabalho no repositório-mãe, leia:

1. [HANDOFF.md](HANDOFF.md)
2. [README.md](README.md)

Se o trabalho for dentro de um benchmark específico, leia também o
`AGENTS.md` e o `HANDOFF.md` daquele diretório antes de editar qualquer
arquivo.

## Regra de organização

- não misturar documentação global com documentação interna de um
  benchmark;
- não assumir que regras, métricas ou artefatos de um benchmark valem
  para outro;
- manter cada benchmark sob `benchmarks/<nome>/`;
- preservar continuidade local via `HANDOFF.md` dentro de cada
  benchmark.

## Benchmark atual mais avançado

O benchmark mais desenvolvido neste repositório, no momento, é:

- [benchmarks/browser_computer_use](benchmarks/browser_computer_use/README.md)

Se a tarefa cair nesse benchmark, siga as instruções locais dele.
