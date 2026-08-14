# Benchmark Plan

Ultima atualizacao: 2026-08-14

## Objetivo

Executar um benchmark local, reproduzivel e comparavel para descobrir
qual modelo open-weight pequeno entrega o melhor equilibrio entre:

- taxa de sucesso real;
- confiabilidade;
- latencia;
- uso de VRAM/RAM;
- estabilidade em tarefas longas;
- custo operacional no hardware atual.

## Estrategia geral

O benchmark sera implementado em camadas, nesta ordem:

1. detectar o ambiente real da maquina;
2. selecionar modelos e runtimes viaveis;
3. construir uma aplicacao local de teste;
4. construir o harness de execucao;
5. instrumentar metricas e monitoramento;
6. integrar um modelo primeiro;
7. validar ponta a ponta;
8. expandir para os demais modelos;
9. executar campanhas comparativas;
10. gerar relatorios e recomendacao final.

Isso evita perder tempo baixando modelos ou construindo integracoes
prematuras antes de confirmar viabilidade no hardware.

## Regra de reproducao em outro hardware

O benchmark deve poder ser repetido em outra VGA, mas a repeticao tem
que preservar metodo e nao copiar conclusoes.

Isso significa:

- repetir tarefas, prompts, resolucao e criterios de validacao;
- repetir o mesmo estado inicial deterministico e o mesmo reset de
  dados da Suite A;
- manter o mesmo checkpoint, a mesma quantizacao exata, o mesmo runtime
  e a mesma politica de offload entre hosts para a comparacao que esta
  sendo feita;
- medir novamente VRAM, RAM, driver, CUDA, runtime e estabilidade;
- classificar novamente cada modelo em `official/native`, `quantized`,
  `offload` ou `inviavel`;
- gerar consolidacao propria por host;
- declarar quando a comparacao cruzada vale apenas para a Suite A
  controlada e quando tambem inclui Suites B e C.

Em outras palavras:

- o protocolo experimental deve ser reproduzivel;
- os resultados precisam ser recalculados para cada GPU.

## Suites de teste

O benchmark nao sera baseado em uma unica origem de teste.

Ele sera dividido em suites separadas, com resultados reportados em
secoes distintas:

### Suite A - Controlada

Ambiente:

- aplicacao web local ou self-hosted, criada para benchmark.

Objetivo:

- medir os modelos em ambiente reproduzivel;
- comparar modelos com justica;
- validar a infraestrutura do harness;
- isolar qualidade do modelo de variaveis externas.

Validacao:

- por estado interno da aplicacao;
- por URL final esperada;
- por dados criados/alterados corretamente;
- por seletores e conteudo esperado no estado final.

### Suite B - Externa publica

Ambiente:

- URLs externas reais, publicas e relativamente estaveis;
- sem uso de credenciais reais;
- sem acao irreversivel;
- sem dependencia de dados privados.

Objetivo:

- medir robustez fora do ambiente controlado;
- expor os modelos a interfaces mais complexas e menos previsiveis;
- avaliar grounding visual e navegacao em sites reais.

Validacao:

- por URL final;
- por titulo da pagina;
- por presenca de texto ou elemento esperado;
- por evidencia observavel do estado final, nunca apenas pela resposta
  textual do modelo.

### Suite C - Externa autenticada e sensivel

Ambiente:

- portais reais com autenticacao e fluxo critico, como classe de teste
  similar a e-CAC;
- somente com conta de teste, ambiente de homologacao ou escopo
  estritamente limitado e seguro;
- nunca com credenciais pessoais reais do usuario em benchmark
  autonomo.

Objetivo:

- medir capacidade de login, navegacao autenticada e resiliencia em UI
  complexa de alta friccao;
- validar se o modelo consegue lidar com portais reais mais proximos de
  uso profissional.

Validacao:

- por conclusao de um objetivo seguro e reversivel;
- por chegada a uma pagina autenticada esperada;
- por presenca de elementos exclusivos do estado logado;
- por logout limpo ao final, quando aplicavel.

Restricoes:

- nao executar acoes fiscais, cadastrais, financeiras ou juridicamente
  relevantes;
- nao protocolar, transmitir, assinar, pagar, alterar cadastro ou
  confirmar operacoes reais;
- usar apenas tarefas de navegacao segura, observacao e acesso
  controlado.

## Caso especifico: e-CAC como classe de teste externa

Um teste do tipo e-CAC entra na Suite C, nao na Suite A.

Isso significa que ele sera tratado como teste de realismo e nao como
fonte unica de verdade do benchmark.

Para esse tipo de portal, o benchmark deve separar claramente:

- teste de acesso;
- teste de navegacao autenticada;
- teste de consulta segura;
- tarefas proibidas.

Exemplo de tarefas permitidas para um portal dessa classe:

- acessar a pagina inicial publica;
- iniciar fluxo de autenticacao;
- concluir login em conta de teste apropriada;
- chegar a pagina inicial autenticada esperada;
- localizar uma area especifica sem confirmar nenhuma operacao;
- encerrar sessao com logout.

Exemplos de tarefas proibidas:

- enviar declaracoes;
- emitir documentos reais com efeito pratico;
- alterar dados cadastrais;
- assinar ou protocolar requerimentos;
- consultar ou expor dados reais sensiveis fora de ambiente autorizado.

## Fases e entregaveis

## Fase 1 - Inventario do ambiente

Objetivo:

Medir a maquina real antes de qualquer decisao tecnica relevante.

Entregaveis:

- artefato com CPU, RAM, GPU, VRAM, driver NVIDIA, CUDA, sistema
  operacional e espaco em disco;
- registro de versoes de Python, Node, Playwright e dependencias
  criticas;
- avaliacao inicial de viabilidade para modelos 7B a 14B.

Como vou executar:

- coletar dados do sistema por comandos locais;
- registrar os dados em arquivo versionado;
- usar esse inventario para decidir limites realistas de quantizacao,
  contexto e runtime.

Criterio de saida:

- existe um artefato confiavel descrevendo o ambiente;
- ja e possivel decidir o teto de memoria e a faixa inicial de modelos.

## Fase 2 - Pesquisa tecnica dos modelos

Objetivo:

Escolher checkpoints, runtimes e quantizacoes iniciais sem adivinhacao.

Entregaveis:

- matriz comparativa por modelo;
- checkpoint candidato por modelo;
- runtime recomendado por modelo;
- quantizacao inicial proposta;
- riscos conhecidos de compatibilidade.

Como vou executar:

- consultar a documentacao oficial atual de cada modelo prioritario;
- registrar formato, licenca, memoria estimada, dependencia de vision
  encoder e recomendacao de inferencia;
- descartar configuracoes inviaveis para a GPU atual antes do download.

Criterio de saida:

- existe uma shortlist objetiva do que vale integrar primeiro.

## Fase 3 - Aplicacao local de benchmark

Objetivo:

Criar a base controlada e reproduzivel da Suite A.

Entregaveis:

- aplicacao web local com rotas, tabelas, formularios, filtros, modal,
  busca, paginacao, scroll e estados de erro/sucesso;
- mecanismo de reset para estado inicial deterministico;
- validadores internos de sucesso por tarefa.

Como vou executar:

- construir um site local simples com dados fake e sem dependencias
  externas;
- incluir identificadores internos para validacao automatica do harness;
- garantir que esses identificadores nao sejam expostos ao modelo.

Criterio de saida:

- todas as tarefas podem ser executadas manualmente no browser;
- o estado inicial pode ser resetado antes de cada run;
- cada tarefa tem criterio de sucesso verificavel por codigo.

## Fase 4 - Harness de execucao

Objetivo:

Implementar o loop browser -> screenshot -> modelo -> acao -> validacao.

Entregaveis:

- controlador de browser baseado em Playwright;
- capturador de screenshots com resolucao fixa;
- executor de acoes normalizadas;
- loop de execucao de tarefa;
- logs estruturados por passo.

Como vou executar:

- padronizar o contrato de acao para `click`, `type`, `scroll`,
  `keypress`, `wait`, `navigate`, `back`, `mouse_move`, `answer` e
  possiveis variantes necessarias;
- suportar tambem acoes visuais por coordenadas quando o modelo nao
  depender de seletores;
- definir limites de passos, timeout por tarefa e regras de falha;
- salvar screenshot antes e depois de cada acao relevante;
- persistir historico em `actions.jsonl`.

Criterio de saida:

- o harness consegue executar uma tarefa de teste com um agente mock;
- as evidencias da execucao sao reconstituiveis pelos logs.

Restricao arquitetural:

- o agente nao deve receber token interno, task id interno nem acesso
  direto aos endpoints internos de reset, validacao ou catalogo privado.

## Fase 5 - Metricas e monitoramento

Objetivo:

Medir recurso, latencia e qualidade sem depender de observacao manual.

Entregaveis:

- coletor de tempo por etapa do loop;
- coletor de RAM do processo;
- coletor de GPU/VRAM por `nvidia-smi` ou NVML;
- schema de `metrics.json`;
- schema de `metadata.json`.

Como vou executar:

- amostrar GPU periodicamente durante toda a run;
- registrar picos e medias de uso;
- separar, quando possivel, latencia de screenshot, preprocessamento,
  inferencia, execucao da acao e carregamento da pagina;
- usar `null` quando uma metrica nao puder ser obtida corretamente.

Criterio de saida:

- uma run completa ja produz metricas coerentes e brutas.

## Fase 6 - Primeira integracao de modelo

Objetivo:

Validar o benchmark ponta a ponta com um unico modelo antes de escalar.

Entregaveis:

- adapter de um modelo prioritario;
- rotina de warm-up;
- primeira execucao real completa em pelo menos uma tarefa.

Como vou executar:

- escolher o modelo com melhor relacao entre relevancia e viabilidade;
- implementar adapter com contrato comum para o harness;
- configurar prompt, formato de entrada visual e parsing de acao;
- rodar warm-up e ajustar limites de contexto e resolucao.

Status em 2026-08-10:

- adapter OpenAI-compatible para Fara ja implementado;
- `Fara1.5-4B` passou a ser o primeiro alvo real;
- stack oficial local em `vllm` foi testada no WSL2 e avancou ate carga
  dos pesos, mas falhou no runtime CUDA/FlashAttention deste host;
- rota quantizada local com `transformers + bitsandbytes 4-bit` foi
  integrada via endpoint local minimo;
- essa rota quantizada ja concluiu multiplas tarefas reais da Suite A;
- a rota `offload` em BF16 ja concluiu tres tarefas reais da Suite A;
- a rota `Fara-7B` GGUF `Q4_K_M` foi levada ate benchmark real com
  `llama.cpp`, mas falhou funcionalmente no `t1-product-navigation`;
- a rota `Fara-7B` GGUF `Q5_K_M` carregou em probe multimodal minimo,
  mas ainda nao entregou `<tool_call>` compativel com o harness.

Criterio de saida:

- o modelo completa ao menos parte do circuito real sem quebrar o
  harness;
- os artefatos de run sao gerados corretamente.

## Fase 7 - Validacao ponta a ponta

Objetivo:

Garantir que o benchmark mede o que deveria medir antes de comparar
varios modelos.

Entregaveis:

- execucoes de smoke test;
- lista de falhas de infraestrutura corrigidas;
- parametros padrao iniciais de campanha.

Como vou executar:

- rodar tarefas simples e depois multi-step;
- verificar se os validadores internos realmente detectam sucesso e
  falha;
- revisar se o modelo nao esta recebendo informacao privilegiada;
- ajustar timeouts, maximo de acoes e formato de evidencias.

Criterio de saida:

- o benchmark esta estavel o bastante para comparacao real.

## Fase 7B - Validacao externa

Objetivo:

Adicionar testes em URLs externas reais sem perder controle de escopo e
criterio de validacao.

Entregaveis:

- lista de URLs externas elegiveis;
- definicao das tarefas seguras por URL;
- validadores por URL e por tarefa;
- politica de retries, timeout e classificacao de erro externo.

Como vou executar:

- selecionar primeiro URLs publicas e estaveis para a Suite B;
- depois avaliar um portal autenticado de classe e-CAC para a Suite C,
  somente se houver conta de teste ou escopo seguro e autorizado;
- definir para cada tarefa um oraculo de sucesso observavel por codigo;
- registrar explicitamente o que e falha do modelo e o que e falha do
  site, rede ou autenticacao.

Criterio de saida:

- existe pelo menos uma tarefa externa publica bem definida;
- existe uma estrategia segura para portal autenticado, sem depender de
  improviso durante a execucao.

## Fase 8 - Expansao para outros modelos

Objetivo:

Adicionar os demais candidatos de forma comparavel.

Entregaveis:

- adapters adicionais;
- tabela de configuracoes por modelo;
- anotacoes de incompatibilidades ou concessoes tecnicas.

Como vou executar:

- manter o mesmo harness e o mesmo conjunto de tarefas;
- variar apenas o que for exigencia oficial do proprio modelo;
- documentar explicitamente qualquer diferenca que afete comparabilidade.

Criterio de saida:

- existem pelo menos dois modelos testaveis no mesmo benchmark.

## Fase 9 - Campanha de benchmark

Objetivo:

Executar comparacoes controladas com repetibilidade suficiente.

Entregaveis:

- runs organizadas por modelo e tarefa;
- resultados agregados em CSV e JSON;
- capturas e logs das execucoes relevantes.

Como vou executar:

- comecar com rodada exploratoria de 1 repeticao por combinacao;
- identificar modelos e tarefas promissoras ou problematicas;
- depois executar 3 repeticoes por combinacao selecionada;
- manter mesmo estado inicial, mesma resolucao e mesma configuracao de
  tarefa durante as comparacoes.

Criterio de saida:

- existe volume suficiente de dados para comparar taxa de sucesso,
  tempo e uso de recurso com confianca pratica.

## Fase 10 - Relatorio final

Objetivo:

Responder qual modelo vale mais a pena neste hardware.

Entregaveis:

- `results/summary.md`;
- `results/results.csv`;
- `results/raw-results.json`;
- recomendacao final objetiva.

Como vou executar:

- agregar metricas por modelo, tarefa e quantizacao;
- destacar onde cada modelo falhou ou foi forte;
- classificar falhas por tipo, como erro de grounding, loop, acao
  alucinada ou perda de objetivo;
- apontar vencedor por confiabilidade, velocidade e equilibrio.

Criterio de saida:

- o relatorio responde claramente qual modelo e melhor, qual e mais
  rapido, qual e mais confiavel e se a GPU atual sustenta uso real.

## Metodologia de teste

## O que sera validado contra site local e o que sera validado contra
## URL externa

A Suite A sera validada contra a aplicacao local de benchmark.

A Suite B sera validada contra URLs externas publicas previamente
aprovadas.

A Suite C sera validada contra portais autenticados e sensiveis
somente quando houver:

- conta de teste ou ambiente apropriado;
- tarefa segura e reversivel;
- criterio objetivo de sucesso;
- escopo limitado para nao executar operacoes reais.

## Condicoes fixas

Sempre que possivel, vou manter fixos:

- resolucao de screenshot;
- estado inicial da aplicacao;
- conjunto de tarefas;
- limites de passos e timeout;
- politicas de logging;
- schema de metricas;
- processo de warm-up.

Isso evita comparacoes contaminadas por mudancas de ambiente.

## Execucao de cada teste

Cada run seguira o fluxo:

1. resetar a aplicacao de benchmark;
2. iniciar browser em estado limpo;
3. iniciar monitoramento de GPU/RAM;
4. carregar a tarefa;
5. capturar screenshot inicial;
6. executar o loop de inferencia e acao ate sucesso, falha ou timeout;
7. validar automaticamente o estado final;
8. salvar metricas, logs, screenshots e estado final;
9. encerrar browser e monitoramento;
10. consolidar resultado da run.

Para suites externas, a run tambem deve registrar:

- URL alvo exata;
- horario da execucao;
- eventuais erros de rede, captcha, indisponibilidade ou mudanca de UI;
- classificacao se a falha foi do modelo, da infraestrutura ou do site
  externo.

## Repeticoes

Plano de repeticao:

- fase exploratoria: 1 run por combinacao `modelo x tarefa`;
- fase comparativa: 3 runs por combinacao selecionada;
- quantizacao: ao menos 2 variantes para o melhor modelo viavel, se
  fizer sentido, por exemplo Q4 e Q5.

## Criterios de sucesso e falha

Sucesso:

- o validador interno da tarefa confirma que o objetivo foi alcancado.

Falha:

- timeout;
- excedeu maximo de acoes;
- acao invalida irrecuperavel;
- loop detectado;
- estado final nao atende o objetivo;
- erro de infraestrutura.

Para testes externos, acrescentar:

- falha de rede;
- mudanca inesperada de interface;
- bloqueio anti-automacao;
- indisponibilidade do servico;
- falha de autenticacao fora do controle do modelo.

## Como vou comparar os modelos

A ordem de decisao sera:

1. taxa de sucesso por tarefa;
2. consistencia entre repeticoes;
3. capacidade de recuperar erro;
4. numero de acoes e eficiencia;
5. tempo total e latencia media;
6. custo de VRAM/RAM e sinais de offload.

Velocidade so conta depois de confiabilidade minima aceitavel.

## Riscos tecnicos que vou controlar

- modelo nao cabe na VRAM em configuracao util;
- offload para RAM mascarando comparacoes;
- runtime incompativel com CUDA/driver;
- diferencas de arquitetura entre modelos afetando comparabilidade;
- benchmark vazando informacao privilegiada ao modelo;
- site de teste simples demais para discriminar qualidade real.

## Proximo passo imediato

A Fase 6.1 foi concluida.

Resultado pratico:

1. `t4-pending-highest` tambem falhou no `Fara1.5-4B` BF16 `offload`;
2. `t5-customer-recent-order` tambem falhou no `Fara1.5-4B` BF16
   `offload`;
3. nesse recorte controlado, `Q4` e `BF16 offload` terminaram ambos em
   `3/5`;
4. o proximo passo agora e promover `quantized` e `offload` para a
   Suite B externa publica;
5. manter a Suite C autenticada apenas para a fase final read-only.
