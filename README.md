# benchmark_ia

Este repositório reúne benchmarks práticos de IA, com foco em medir
comportamento real, custo operacional e reprodutibilidade no hardware
testado.

O objetivo não é manter apenas um experimento isolado. A ideia é ter
uma base organizada para vários benchmarks, cada um com seu próprio
escopo, documentação, artefatos e critérios de avaliação.

## Estrutura

- [benchmarks/browser_computer_use/README.md](benchmarks/browser_computer_use/README.md)
  Benchmark de modelos para browser/computer use, com aplicação
  controlada, harness local, resultados consolidados e suites externas
  planejadas.

## Convenção do repositório

Cada benchmark deve ficar em um diretório próprio dentro de
`benchmarks/`.

Todo benchmark nasce com o mínimo de `bootstrap`:

- `README.md`
- `AGENTS.md`
- `HANDOFF.md`
- plano de benchmark

Quando o benchmark chega ao estágio `pronto para campanha`, ele também
deve ter:

- `PLAYBOOK.md`
- estratégia de artefatos
- contrato de comparação
- código e testes do benchmark

Quando o benchmark chega ao estágio `consolidado`, ele também deve ter:

- resultados consolidados

Isso permite evoluir benchmarks diferentes sem misturar contexto,
decisões ou métricas.

## Como contribuir

As regras de contribuição do repositório estão em
[CONTRIBUTING.md](CONTRIBUTING.md).

Esse documento explica:

- quais perguntas precisam ser feitas antes de criar ou alterar um
  benchmark;
- como declarar se o benchmark é `host-local` ou comparável entre
  hosts;
- como escrever o contrato de comparação;
- o que os testes devem responder;
- o que uma campanha de benchmark precisa entregar no resultado final;
- quando um benchmark já precisa ter `PLAYBOOK.md`.

## Benchmark ativo

Hoje, o benchmark mais avançado neste repositório é:

- [browser_computer_use](benchmarks/browser_computer_use/README.md)

Ele mede modelos locais para uso autônomo de navegador, com foco em:

- taxa de sucesso real;
- confiabilidade;
- latência;
- uso de VRAM/RAM;
- comportamento agentic em tarefas multi-etapas.

Esse benchmark já possui playbook reproduzível em
[benchmarks/browser_computer_use/PLAYBOOK.md](benchmarks/browser_computer_use/PLAYBOOK.md).

## Continuidade

O estado mais recente do repositório-mãe está em
[HANDOFF.md](HANDOFF.md).

Para trabalho dentro de um benchmark específico, consulte também o
`HANDOFF.md` local do respectivo benchmark.
