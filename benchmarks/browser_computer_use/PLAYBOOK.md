# Playbook Reproduzível

## Objetivo

Este playbook descreve como reproduzir o benchmark
`browser_computer_use` no estado atual do repositório, com foco em:

- preparar o ambiente;
- validar o harness;
- executar a campanha canônica mínima da Suite A;
- preservar artefatos auditáveis;
- consolidar resultados com comando determinístico.

No estado atual, este playbook cobre de forma confiável a `Suite A`
controlada. Suites B e C devem seguir as mesmas regras, mas não fazem
parte da campanha canônica mínima deste playbook.

## Escopo declarado

Leitura principal deste benchmark hoje:

- `host-local` para a campanha consolidada neste host;
- `comparável entre hosts` apenas se o mesmo playbook for repetido com
  o mesmo manifesto de campanha, o mesmo contrato de comparação e sem
  reaproveitar métricas do host anterior.

## Campanha canônica mínima

A campanha canônica mínima deste benchmark, a partir de sexta-feira,
14 de agosto de 2026, é:

- suite:
  `suite-a-controlled-v1`;
- tarefas:
  `t1-product-navigation`,
  `t2-create-customer`,
  `t3-open-order`,
  `t4-pending-highest`,
  `t5-customer-recent-order`;
- repetições por tarefa:
  `1`;
- manifesto-base:
  `campaigns/suite_a_controlled_v1.template.yaml`;
- consolidação determinística:
  `cua-bench consolidate-campaign`.

Leituras históricas anteriores a este playbook, como a amostra `3/5`
publicada em 10 de agosto de 2026, devem ser tratadas como `legado`.
Elas continuam úteis como evidência histórica, mas não são o formato
canônico reproduzível daqui em diante porque antecedem a captura
obrigatória dos campos de auditoria atuais.

## Contrato de comparação

Antes de comparar modelos, checkpoints, quantizações ou rotas de
execução, manter fixo:

- a mesma Suite A controlada;
- o mesmo manifesto de campanha;
- o mesmo código do harness, executor e adaptador;
- o mesmo critério de validação;
- o mesmo estado inicial determinístico e o mesmo reset;
- a mesma geração determinística de tarefas a partir do seed data;
- a mesma resolução e viewport;
- o mesmo limite de passos por tarefa;
- o mesmo prompt e o mesmo protocolo;
- a mesma política de repetição;
- a mesma forma de gravar artefatos.

Registrar explicitamente o que varia:

- checkpoint exato;
- runtime exato e versão do runtime;
- classe de execução:
  `official/native`, `quantized`, `offload` ou `inviável`;
- quantização exata, quando existir;
- política de offload, quando existir;
- hardware e software do host.

Cada run real deve preservar em `metadata.json`, no mínimo:

- `suite`
- `suite_version`
- `campaign_id`
- `model_checkpoint`
- `execution_class`
- `quantization`
- `runtime`
- `runtime_version`
- `offload_policy`
- `endpoint_base_url`
- `endpoint_contract`
- `benchmark_git_sha`
- `benchmark_git_dirty`
- `benchmark_git_diff_hash`, quando houver alteracoes locais
- `task_snapshot_hash`
- `seed_data_hash`
- `environment_inventory_path`
- `environment_inventory_hash`

No fluxo canônico deste benchmark:

- runs de campanha com `git` sujo não devem ser consolidadas;
- a consolidação rejeita campanhas que misturem `benchmark_git_sha`,
  `task_snapshot_hash`, `seed_data_hash` ou
  `environment_inventory_hash` diferentes;
- a consolidação também valida `campaign_id`, `model_checkpoint`,
  `execution_class`, `runtime`, `runtime_version`,
  `endpoint_contract`, `endpoint_base_url`, `quantization` e
  `offload_policy` contra o manifesto.

## Pré-requisitos

Parta sempre da raiz deste benchmark:

```text
benchmarks/browser_computer_use
```

Pré-requisitos:

- Windows com Python `3.10+`;
- Google Chrome disponível para Playwright;
- dependências Python do benchmark instaladas;
- para rotas locais de modelo:
  endpoint multimodal compatível com o contrato deste benchmark;
- para rotas em WSL:
  ambiente Linux capaz de executar os scripts de `scripts/`.

## Contrato exato do endpoint

Para este benchmark, `compatível com OpenAI` não significa apenas ter o
mesmo caminho HTTP.

O endpoint precisa suportar, de forma funcional:

- `POST /v1/chat/completions`;
- mensagens multimodais com imagem e texto no mesmo request;
- resposta textual contendo um único `tool_call` válido;
- pelo menos uma das variantes aceitas pelo adaptador atual:
  - JSON em `<tool_call>...</tool_call>`;
  - formato oficial com `<function=computer_use>`;
  - `message.tool_calls` estruturado;
- ações de `computer_use` com coordenadas coerentes;
- finalização válida com `action=terminate` e `answer=...`.

Se o endpoint não cumprir isso, a falha pode ser de protocolo e não do
modelo. Não promova a rota para campanha real antes de validar esse
contrato em smoke e em run controlada.

## Preparação do ambiente

No PowerShell, a partir da raiz deste benchmark:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements-base.txt
.\.venv\Scripts\python -m playwright install chrome
$env:PYTHONPATH = "src"
```

## Validação mínima antes de campanha

Rodar nesta ordem:

1. inventário do ambiente:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli inventory
```

O arquivo gerado em `artifacts/environment-inventory.json` deve ser o
mesmo referenciado depois nas runs da campanha.

2. smoke do navegador:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli browser-smoke --channel chrome
```

3. smoke da aplicação controlada:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli controlled-smoke --task-id t1-product-navigation --run-id smoke-t1
```

4. suíte automatizada:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Se qualquer etapa falhar, não promover o host nem o modelo para campanha
comparativa.

## Subida da aplicação controlada

Para inspeção manual ou integração externa:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli serve-controlled-app --host 127.0.0.1 --port 8000
```

O runner de benchmark já sobe uma instância gerenciada da aplicação
quando usa `controlled-smoke` e `controlled-endpoint-run`.

## Subida de endpoint de modelo

### Opção A: endpoint já existente

Se já houver um endpoint funcional, registrar:

- URL base;
- modelo servido;
- checkpoint exato;
- runtime e versão;
- classe de execução;
- quantização ou política de offload;
- contrato suportado.

### Opção B: servidor local por `transformers`

Em WSL ou ambiente Linux compatível, a partir da raiz deste benchmark:

```bash
MODEL_NAME="microsoft/Fara1.5-4B" \
SERVER_PORT="8001" \
SERVER_BITS="4" \
bash scripts/launch_transformers_server.sh
```

Observações:

- `SERVER_BITS` vazio tende à rota mais próxima de `native`, se ela
  couber;
- `SERVER_BITS="4"` representa rota quantizada `4-bit`;
- se for necessário ativar uma `venv` Linux específica, definir
  `VENV_DIR` explicitamente antes de chamar o script;
- não publicar comparação só porque o servidor subiu:
  a rota precisa funcionar no benchmark real.

## Execução da campanha canônica mínima

Copie o manifesto-base:

```powershell
Copy-Item campaigns\suite_a_controlled_v1.template.yaml campaigns\suite_a_controlled_v1.yaml
```

Execute exatamente as 5 tarefas da campanha canônica mínima.

Exemplo de run quantizada para `t4`:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli controlled-endpoint-run `
  --task-id t4-pending-highest `
  --endpoint-url http://127.0.0.1:8001 `
  --model microsoft/Fara1.5-4B `
  --campaign-id suite-a-controlled-v1-q4 `
  --suite-version suite-a-controlled-v1 `
  --model-checkpoint microsoft/Fara1.5-4B `
  --execution-class quantized `
  --quantization bitsandbytes-4bit `
  --offload-policy none `
  --runtime-label openai-compatible-endpoint `
  --runtime-version transformers `
  --endpoint-contract openai-chat-completions-multimodal-computer-use `
  --environment-inventory artifacts/environment-inventory.json `
  --max-history-messages 8 `
  --request-timeout-seconds 240 `
  --run-id fara15-q4-t4-r1
```

Exemplo de run com offload para `t5`:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli controlled-endpoint-run `
  --task-id t5-customer-recent-order `
  --endpoint-url http://127.0.0.1:8001 `
  --model microsoft/Fara1.5-4B `
  --campaign-id suite-a-controlled-v1-bf16offload `
  --suite-version suite-a-controlled-v1 `
  --model-checkpoint microsoft/Fara1.5-4B `
  --execution-class offload `
  --runtime-label openai-compatible-endpoint `
  --runtime-version transformers `
  --offload-policy device_map=auto `
  --endpoint-contract openai-chat-completions-multimodal-computer-use `
  --environment-inventory artifacts/environment-inventory.json `
  --max-history-messages 8 `
  --request-timeout-seconds 240 `
  --run-id fara15-bf16offload-t5-r1
```

Repita o mesmo padrão para `t1`, `t2`, `t3`, `t4` e `t5`, sem trocar
prompt, resolução, tarefa, runtime ou endpoint no meio da campanha.

### Significado prático de T4 e T5

- `t4-pending-highest`:
  encontrar o pedido pendente de maior valor depois de aplicar o filtro
  correto e responder o identificador certo.
- `t5-customer-recent-order`:
  abrir os pedidos do cliente correto, identificar o pedido mais recente
  e encerrar a tarefa com a resposta válida.

Essas tarefas são úteis porque exigem visão, navegação, leitura de
dados e finalização correta de tarefa.

## Política de repetição

Para a campanha canônica mínima deste playbook:

- `1` run real por tarefa;
- `5` tarefas exatas:
  `t1`, `t2`, `t3`, `t4`, `t5`;
- `1` manifesto por rota comparada;
- `1` run de smoke antes da campanha;
- sem alterar prompt, resolução, tarefa, runtime ou endpoint no meio da
  série;
- sem reaproveitar run com artefato incompleto;
- sem sobrescrever `run_id` anterior:
  o runner cria sufixo numérico quando necessário.

Se a campanha usar `N > 1`, isso deve ser declarado antes do primeiro
run e refletido no manifesto.

## Artefatos obrigatórios por run

Cada run deve preservar, no mínimo:

- `metadata.json`
- `metrics.json`
- `actions.jsonl`
- `final-state.json`
- `gpu.csv`
- `screenshots/`

No estado atual, esses artefatos são gravados em:

```text
artifacts/runs/<task_id>/<run_id>/
```

Se um novo run usar o mesmo `run_id` solicitado, o runner deve criar um
novo diretório, como `run-id-2`, em vez de sobrescrever o anterior.

## Consolidação determinística

Depois de preencher o manifesto com os `artifact_dir` reais de cada
run, consolidar com:

```powershell
.\.venv\Scripts\python -m benchmark_cua.cli consolidate-campaign `
  --manifest campaigns\suite_a_controlled_v1.yaml `
  --output-dir results\suite_a_controlled_v1
```

O comando gera:

- `summary.json`
- `results.csv`
- `summary.md`

Esses arquivos passam a ser a base determinística da leitura pública da
campanha. Não consolidar resultado final apenas por inspeção manual de
Markdown.

Se qualquer run tiver:

- `campaign_id` divergente do manifesto;
- `model_checkpoint`, `runtime_version`, `endpoint_contract` ou
  `endpoint_base_url` divergentes da rota declarada;
- `benchmark_git_sha`, `task_snapshot_hash`, `seed_data_hash` ou
  `environment_inventory_hash` inconsistentes entre runs;
- `git` sujo quando `require_clean_worktree: true`;

a consolidação deve falhar.

## Classificação de resultado

Toda consolidação deve manter separadas estas leituras:

- `task_success`
- `semantic_success`
- `protocol_error`
- `executor_error`
- `model_error`

Também manter separadas estas classes de execução:

- `official/native`
- `quantized`
- `offload`
- `inviável`

Não tratar:

- modelo que apenas carregou como benchmark funcional;
- `semantic_success` como sinônimo automático de `task_success`;
- resposta ambígua de encerramento como sucesso válido.

## O que inspecionar quando houver falha

A ordem mínima de inspeção é:

1. `metadata.json`
2. `metrics.json`
3. `final-state.json`
4. `actions.jsonl`
5. screenshots do diretório `screenshots/`

Classificar a falha, quando possível, em categorias como:

- erro de grounding visual;
- interpretação incorreta de dados;
- perda do objetivo;
- loop;
- planejamento incorreto;
- ação válida com estratégia ruim;
- falha de recuperação;
- erro de protocolo;
- erro do executor;
- limitação do harness.

## Checklist de consolidação

Antes de atualizar `CONSOLIDATED_RESULTS.md`, confirmar:

1. o ambiente usado foi registrado;
2. o contrato de comparação foi mantido;
3. os artefatos estão íntegros e isolados por run;
4. a classe de execução está correta:
   `official/native`, `quantized`, `offload` ou `inviável`;
5. `task_success` e `semantic_success` não foram confundidos;
6. erros de protocolo, executor e modelo foram separados;
7. a consolidação final saiu do comando determinístico, não apenas de
   edição manual;
8. a leitura prática final está baseada em runs reais, não em probes.

## Atualização obrigatória de documentação

Ao encerrar uma campanha ou uma mudança metodológica:

- atualizar [HANDOFF.md](HANDOFF.md);
- atualizar [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md), se a
  leitura consolidada mudou;
- atualizar [README.md](README.md), se a leitura pública mudou;
- atualizar este `PLAYBOOK.md` se o procedimento reproduzível mudou.
