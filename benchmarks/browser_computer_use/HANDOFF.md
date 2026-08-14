# Handoff

Ultima atualizacao: 2026-08-14

## Revisao adversarial curta de 2026-08-14

Escopo revisado nesta passada:

- `README.md`
- `PLAYBOOK.md`
- `HANDOFF.md`
- `src/benchmark_cua/benchmark/runner.py`
- `src/benchmark_cua/reporting/campaign.py`
- `src/benchmark_cua/site/scenarios.py`
- `tests/test_controlled_app.py`
- `tests/test_reporting.py`

Leitura objetiva:

- ainda restam dois findings materiais de comparabilidade no contrato
  canonico do `PLAYBOOK`;
- a consolidacao trata campos opcionais da rota como curinga quando o
  manifesto deixa valor em branco, o que enfraquece a garantia de que
  `quantization` e `offload_policy` realmente batem com a rota
  declarada;
- a consolidacao tambem nao revalida o hash do
  `environment-inventory.json` no momento da leitura, entao um arquivo
  de inventario alterado depois dos runs pode mudar a consolidacao
  "deterministica" sem erro.

Proximo passo recomendado:

- endurecer `src/benchmark_cua/reporting/campaign.py` para distinguir
  `campo omitido` de `campo explicitamente nulo` no manifesto;
- recomputar o hash do inventario carregado durante a consolidacao e
  falhar se ele divergir de `environment_inventory_hash`;
- adicionar testes cobrindo esses dois casos antes de publicar nova
  campanha canonica.

## Escopo deste benchmark

Este diretorio contem o benchmark de `browser_computer_use` dentro do
repositorio [benchmark_ia](../../README.md).

O foco aqui e comparar modelos locais para uso autonomo de navegador,
com prioridade para:

- taxa de sucesso real;
- confiabilidade;
- latencia;
- uso de VRAM/RAM;
- estabilidade em tarefas multi-etapas.

## Estado atual

Este benchmark esta funcional e organizado em torno destes artefatos
principais:

- [README.md](README.md)
- [PLAYBOOK.md](PLAYBOOK.md)
- [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md)
- [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)
- [ENVIRONMENT_INVENTORY.md](ENVIRONMENT_INVENTORY.md)
- [MODEL_RESEARCH.md](MODEL_RESEARCH.md)
- [EXTERNAL_TEST_SUITES.md](EXTERNAL_TEST_SUITES.md)
- [AGENTS.md](AGENTS.md)

Codigo e execucao:

- `src/`
- `tests/`
- `scripts/`
- `artifacts/`

## Leitura atual confiavel

Para entender o estado tecnico real deste benchmark, usar nesta ordem:

1. [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md)
2. [PLAYBOOK.md](PLAYBOOK.md)
3. [README.md](README.md)
4. [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)
5. [ENVIRONMENT_INVENTORY.md](ENVIRONMENT_INVENTORY.md)
6. [MODEL_RESEARCH.md](MODEL_RESEARCH.md)

Este `HANDOFF.md` nao deve ser tratado como historico completo de tudo
o que ja aconteceu. Ele deve refletir apenas o estado operacional atual
e o proximo passo recomendado.

## Resultado consolidado ate agora

Leitura objetiva da Fase 6:

- `Fara1.5-4B` quantized:
  - funcional na Suite A;
  - `3/5` tarefas concluidas com sucesso na amostra historica de
    2026-08-10.
- `Fara1.5-4B` offload:
  - funcional na Suite A;
  - `3/5` tarefas concluidas com sucesso na amostra historica de
    2026-08-10;
  - custo operacional maior que o quantized.
- `Fara1.5-4B` official/native local:
  - nao funcional neste host na rota testada.
- `Fara-7B` native/BF16:
  - inviavel em 8 GB de VRAM para a rota local direta.
- `Fara-7B` GGUF `Q4_K_M`:
  - carregou e respondeu em probe;
  - falhou funcionalmente no benchmark real.
- `Fara-7B` GGUF `Q5_K_M`:
  - nao foi validado funcionalmente para campanha real.

O ponto central da leitura atual e:

- o baseline funcional principal neste host e o
  `Fara1.5-4B quantized`;
- o baseline funcional secundario e o
  `Fara1.5-4B offload`;
- a proxima expansao natural do benchmark e sair da Suite A controlada
  para a Suite B externa publica.

Leitura metodologica adicional:

- a amostra `3/5` publicada em 2026-08-10 permanece como evidencia
  historica util;
- a partir de 2026-08-14, a campanha canonica reproduzivel deste
  benchmark passa a ser a campanha dirigida por manifesto descrita em
  [PLAYBOOK.md](PLAYBOOK.md);
- novas campanhas nao devem mais ser publicadas sem manifesto,
  metadados de auditoria e consolidacao deterministica.

## Estado do repositorio dentro de benchmark_ia

Este benchmark ja foi reorganizado para funcionar como subprojeto
nativo de `benchmark_ia`.

Regras atuais:

- a documentacao global fica na raiz do repositorio;
- a documentacao tecnica e operacional deste benchmark fica aqui;
- o procedimento reproduzivel deste benchmark fica em `PLAYBOOK.md`;
- links internos devem apontar para esta arvore com caminhos relativos;
- novas decisoes deste benchmark devem ser registradas neste handoff
  local, nao no handoff da raiz.

## O que fazer a seguir

Proximo passo recomendado:

1. iniciar a Suite B externa publica;
2. usar `Fara1.5-4B` quantized como baseline principal;
3. usar `Fara1.5-4B` offload como baseline secundario;
4. manter separadas as leituras `quantized`, `offload`,
   `official/native` e `inviavel`;
5. deixar a Suite C autenticada apenas para a etapa final read-only.

## Notas operacionais

- o estado do hardware medido para este benchmark esta em
  [ENVIRONMENT_INVENTORY.md](ENVIRONMENT_INVENTORY.md);
- o benchmark principal continua sendo a Suite A controlada;
- comparacoes entre GPUs exigem repetir o protocolo com o mesmo
  checkpoint, a mesma quantizacao, o mesmo runtime e o mesmo estado
  inicial deterministico;
- o benchmark agora possui `PLAYBOOK.md` para execucao reproduzivel e
  contrato de comparacao;
- o CLI agora aceita campos de auditoria para `suite_version`,
  `campaign_id`, `execution_class`, `runtime_version`,
  `offload_policy`, `endpoint_contract` e `model_checkpoint`;
- a consolidacao deterministica por manifesto agora e feita por
  `cua-bench consolidate-campaign`;
- a base automatizada no estado atual do repositorio esta em
  `38 passed`;
- a Suite A agora gera tarefas de forma deterministica a partir do seed
  data, eliminando variacao aleatoria entre resets da campanha;
- o script `scripts/launch_transformers_server.sh` foi ajustado para
  localizar `transformers_openai_server.py` por caminho relativo e usar
  `VENV_DIR` apenas quando essa variavel for definida explicitamente;
- a reorganizacao documental para `benchmark_ia` passou por revisao
  adversarial e voltou sem findings materiais remanescentes nesse
  escopo.
