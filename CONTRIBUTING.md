# Contribuindo para `benchmark_ia`

Este repositório existe para produzir benchmarks de IA que sejam:

- úteis;
- reproduzíveis;
- comparáveis;
- auditáveis.

Contribuir aqui não é só adicionar código. É ajudar o repositório a
responder perguntas objetivas sobre comportamento real de modelos.

## Escopo declarado do benchmark

Antes de começar, declare em qual classe o benchmark se encaixa:

- `host-local`:
  o benchmark responde perguntas válidas principalmente para o hardware
  e software daquele host;
- `comparável entre hosts`:
  o benchmark foi desenhado para permitir comparação entre máquinas
  diferentes, com protocolo e controle suficientes para isso.

Não trate benchmark `host-local` como se ele fosse automaticamente
comparável entre GPUs ou entre máquinas.

## Antes de começar

Antes de abrir um benchmark novo ou alterar um benchmark existente,
responda estas perguntas:

1. Qual pergunta concreta este benchmark quer responder?
2. Quem vai usar essa resposta para tomar decisão?
3. O benchmark mede comportamento real ou apenas proxy acadêmico?
4. O ambiente de teste é reproduzível?
5. O critério de sucesso é verificável automaticamente?
6. As falhas poderão ser classificadas depois?
7. O custo de hardware e tempo de execução será registrado?
8. O teste está isolando a variável certa ou misturando várias coisas?

Se essas perguntas ainda não estiverem claras, o benchmark ainda não
está pronto para virar campanha formal.

## Estágios de maturidade

Nem todo benchmark nasce pronto para campanha consolidada. Use estes
estágios:

1. `bootstrap`:
   pergunta, escopo, `README.md`, `AGENTS.md`, `HANDOFF.md` e plano
   inicial.
2. `instrumentado`:
   harness, executor, critérios de sucesso, métricas e testes básicos.
3. `pronto para campanha`:
   playbook reproduzível, contrato de comparação, estratégia de
   artefatos e procedimento de consolidação.
4. `consolidado`:
   campanha executada, artefatos preservados e leitura prática
   registrada em documento de resultados.

Não exija documento de resultados consolidados de um benchmark que
ainda está em `bootstrap` ou apenas `instrumentado`.

## O que uma contribuição deve entregar

Uma contribuição útil para este repositório normalmente cai em uma
destas classes:

- criação de um benchmark novo em `benchmarks/<nome>/`;
- melhoria de documentação, plano, handoff ou resultados;
- melhoria de harness, executor, adaptador ou coleta de métricas;
- adição de testes automatizados;
- nova campanha de benchmark com artefatos e consolidação.

## Estrutura mínima para benchmark novo

Cada benchmark novo deve nascer em `bootstrap` com, no mínimo:

- `README.md`
- `AGENTS.md`
- `HANDOFF.md`
- plano de benchmark
- definição inicial de métricas
- critério inicial de sucesso

Ao chegar em `pronto para campanha`, o benchmark também deve ter:

- `PLAYBOOK.md`
- estratégia de artefatos
- política de repetição
- contrato de comparação
- inventário de ambiente, quando aplicável

Ao chegar em `consolidado`, o benchmark também deve ter:

- documento de resultados consolidados

## Precedência de regras

As regras da raiz definem o padrão mínimo do repositório.

As regras do benchmark local definem a metodologia específica, o fluxo
operacional e o playbook daquele benchmark.

Dentro do escopo de um benchmark específico, a documentação local
prevalece sobre a raiz quando for mais específica.

Se uma exceção local deixar de ser excepcional e passar a ser política
útil para outros benchmarks, ela deve ser promovida para a
documentação da raiz.

## Contrato de comparação

Sempre que uma contribuição criar, repetir ou ampliar uma comparação,
deixe explícito o que fica fixo e o que pode variar.

No mínimo, registre:

- versão da suite, tarefas e dataset;
- revisão exata do benchmark:
  `git SHA`, `task_snapshot_hash` e `seed_data_hash`, quando houver;
- estado inicial, mecanismo de reset e fixtures usados;
- checkpoint exato do modelo;
- runtime exato;
- modo de execução exato:
  `native`, `quantized`, `offload` ou equivalente;
- quantização, offload e parâmetros relevantes;
- prompt, protocolo e adaptador usados;
- resolução, viewport e demais condições de interface;
- hardware e software relevantes;
- política de repetição:
  número de runs, critérios de retry e critérios de descarte;
- critério de validação:
  `task_success`, `semantic_success`, `protocol_error`,
  `executor_error` e `model_error`, quando aplicável.

Sem esse contrato, a comparação não deve ser tratada como leitura
confiável.

## Perguntas que todo benchmark deve responder

Todo benchmark neste repositório deve tentar responder, de forma
explícita, perguntas como:

1. O modelo consegue concluir a tarefa correta?
2. Ele conclui de forma válida, ou apenas chega perto?
3. Ele repete esse resultado de forma consistente?
4. Quanto tempo leva?
5. Quanto de VRAM, RAM e CPU/GPU consome?
6. Quando falha, a falha parece ser do modelo, do protocolo, do
   executor ou do ambiente?
7. O benchmark é `host-local` ou comparável entre hosts?
8. Se for comparável entre hosts, o resultado continua parecido quando
   o hardware muda?
9. O custo operacional compensa o ganho de qualidade?

## O que os testes devem responder

Os testes de um benchmark não devem existir só para “passar”.
Eles devem responder pelo menos uma destas coisas:

- o ambiente sobe e reseta corretamente;
- o reset é determinístico e restaura o mesmo estado inicial;
- fixtures, dados de teste e seeds permanecem estáveis entre execuções;
- o harness executa ações do jeito esperado;
- o critério de validação distingue sucesso de quase-sucesso;
- o adaptador interpreta corretamente a saída do modelo;
- o executor interage com a interface sem corromper a tarefa;
- os artefatos são preservados sem sobrescrever execuções anteriores;
- as métricas registradas batem com o que a campanha precisa analisar;
- drift do ambiente ou da suite é detectado antes de contaminar uma
  comparação;
- regressões já corrigidas continuam cobertas.

## O que uma campanha de benchmark deve responder

Quando alguém roda uma campanha real, o resultado final deve permitir
responder claramente:

1. Qual modelo foi testado?
2. Em que configuração ele foi testado?
3. Em qual hardware?
4. Em quais tarefas?
5. Quantas vezes?
6. Com qual taxa de sucesso?
7. Com qual custo operacional?
8. Com quais falhas dominantes?
9. Qual leitura prática sai disso?
10. Qual é o próximo passo recomendado?
11. Em qual playbook essa campanha pode ser reproduzida?

Se a campanha não consegue responder isso, ela ainda não está
consolidada.

## Regras práticas de contribuição

- não misture benchmark novo com mudanças grandes não relacionadas;
- não altere prompts, tarefas, resolução e hardware no meio de uma
  comparação sem registrar isso;
- não publique comparação sem contrato explícito do que ficou fixo e do
  que pôde variar;
- não trate “carregou o modelo” como sinônimo de “benchmark funcional”;
- não trate “respondeu um comando” como sinônimo de “agente funcional”;
- não trate benchmark `host-local` como resultado universal;
- ao preparar benchmark `pronto para campanha`, crie ou atualize o
  `PLAYBOOK.md` reproduzível correspondente;
- não deixe contexto importante só na conversa;
- atualize o `HANDOFF.md` correspondente ao encerrar o trabalho.

## Onde registrar cada tipo de mudança

- contexto global do repositório:
  `HANDOFF.md` da raiz
- contexto técnico de benchmark específico:
  `HANDOFF.md` local do benchmark
- regra operacional do benchmark:
  `AGENTS.md` local
- procedimento reproduzível de execução:
  `PLAYBOOK.md`
- leitura humana principal:
  `README.md`
- decisão metodológica:
  plano do benchmark
- resultado consolidado:
  documento de resultados do benchmark

## Fluxo recomendado

1. Ler `README.md`, `AGENTS.md` e `HANDOFF.md` relevantes.
2. Confirmar a pergunta que o trabalho quer responder.
3. Definir o escopo da mudança.
4. Fazer a mudança com artefatos e testes adequados.
5. Atualizar documentação e handoff.
6. Deixar claro o que foi feito, o que não foi feito e o próximo passo.
