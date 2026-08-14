# Handoff

Ultima atualizacao: 2026-08-14

## Estado atual do repositorio

Este repositório já está estruturado para hospedar múltiplos benchmarks
de IA.

Documentação global adicional já criada:

- [CONTRIBUTING.md](CONTRIBUTING.md)

Benchmark atualmente mais avançado:

- [benchmarks/browser_computer_use](benchmarks/browser_computer_use/README.md)

Esse benchmark já possui:

- documentação principal;
- `AGENTS.md` local;
- `HANDOFF.md` local;
- `PLAYBOOK.md` local;
- manifesto-base de campanha;
- plano;
- resultados consolidados;
- inventário de ambiente;
- código, scripts, testes e artefatos.

## Convenção vigente

Cada benchmark deve evoluir dentro do seu próprio diretório em
`benchmarks/`, mantendo:

- contexto técnico local;
- handoff local;
- playbook local quando estiver pronto para campanha;
- resultados locais;
- links internos apontando para sua própria árvore.

As regras da raiz definem o padrão mínimo do repositório.

As regras do benchmark local definem a metodologia específica e
prevalecem dentro do seu próprio escopo quando forem mais específicas.

## Próximo passo recomendado

- continuar o trabalho diretamente em
  [benchmarks/browser_computer_use](benchmarks/browser_computer_use/README.md)
  quando o objetivo for browser/computer use;
- criar novos benchmarks em diretórios irmãos, seguindo a mesma
  convenção estrutural.
- usar [CONTRIBUTING.md](CONTRIBUTING.md) como referência para novas
  contribuições, especialmente ao definir escopo `host-local` ou
  comparável entre hosts, contrato de comparação, playbook reproduzível
  e o que os testes devem responder.
- no benchmark `browser_computer_use`, seguir o playbook guiado por
  manifesto de campanha e consolidação determinística, em vez de
  consolidação apenas manual.
