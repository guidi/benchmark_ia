# AGENTS

## Objetivo

Este diretorio contem o benchmark de browser/computer use do
repositório [benchmark_ia](../../README.md).

Este benchmark existe para construir uma base local, reproduzivel e
mensuravel de modelos open-weight para browser/computer use, com foco
em taxa de sucesso real, estabilidade e uso de recursos no hardware
desta maquina.

## Arquivos que todo agente deve ler primeiro

Antes de iniciar qualquer trabalho, leia nesta ordem:

1. [../../HANDOFF.md](../../HANDOFF.md)
2. [../../AGENTS.md](../../AGENTS.md)
3. [HANDOFF.md](HANDOFF.md)
4. [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md)
5. [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)
6. [PLAYBOOK.md](PLAYBOOK.md)
7. [ENVIRONMENT_INVENTORY.md](ENVIRONMENT_INVENTORY.md)
8. [MODEL_RESEARCH.md](MODEL_RESEARCH.md)
9. [EXTERNAL_TEST_SUITES.md](EXTERNAL_TEST_SUITES.md)
10. [README.md](README.md)
11. [browser_agent_local_benchmark.md](browser_agent_local_benchmark.md)

## Regra obrigatoria de handoff

O arquivo de continuidade deste projeto e:

- [HANDOFF.md](HANDOFF.md)

Todo agente deve:

- consultar o `HANDOFF.md` antes de tomar decisoes;
- atualizar o `HANDOFF.md` ao parar o trabalho;
- registrar no handoff o que foi feito, o que nao foi feito, onde o
  trabalho parou e qual e o proximo passo recomendado;
- manter o handoff aderente ao estado real do repositorio.

Nao encerrar uma sessao deixando contexto relevante apenas na conversa.

## Diretrizes de execucao

- Nao assumir hardware, VRAM, compatibilidade ou viabilidade de modelos
  sem medir.
- Nao baixar modelos grandes antes de verificar espaco em disco,
  memoria, runtime e compatibilidade.
- Nao integrar varios modelos ao mesmo tempo no inicio.
- Integrar um modelo primeiro, validar ponta a ponta, e so depois
  expandir.
- Privilegiar benchmark reproduzivel, nao demos manuais.
- Ao repetir campanha ou comparacao publicada, seguir o `PLAYBOOK.md`
  antes de abrir variacoes novas.
- Validar sucesso por estado interno da aplicacao sempre que possivel,
  nao apenas pela afirmacao do modelo.
- Registrar metricas e artefatos de execucao desde cedo.

## Ordem recomendada de trabalho

1. Inspecionar hardware e software reais da maquina.
2. Registrar o ambiente detectado em artefato do projeto.
3. Pesquisar documentacao oficial atual dos modelos prioritarios.
4. Definir runtimes e quantizacoes iniciais viaveis.
5. Criar ambiente isolado do projeto.
6. Criar a aplicacao local de benchmark.
7. Implementar o harness.
8. Implementar coleta de metricas e monitoramento.
9. Integrar um modelo primeiro.
10. Validar o fluxo ponta a ponta.
11. Integrar os demais modelos.
12. Rodar benchmarks comparativos e gerar relatorios.

## Criterio de qualidade

O objetivo nao e mostrar que um modelo consegue clicar uma vez.

O objetivo e responder de forma objetiva:

> qual modelo local realmente consegue operar um browser de maneira
> autonoma, consistente e mensuravel neste computador?
