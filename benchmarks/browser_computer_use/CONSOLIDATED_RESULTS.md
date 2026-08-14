# Consolidated Results

Ultima atualizacao: 2026-08-10

## Atualizacao pos-correcoes de 2026-08-10

Nota metodologica posterior, adicionada em sexta-feira, 14 de agosto de
2026:

- a amostra `3/5` registrada neste documento continua valida como
  leitura historica do que foi medido;
- ela antecede o formato canonico atual de campanha com manifesto,
  metadados de auditoria completos e consolidacao deterministica;
- por isso, deve ser tratada como `legado`, e nao como o formato
  canonico reproduzivel que passa a ser exigido daqui em diante pelo
  [PLAYBOOK.md](PLAYBOOK.md).

Nesta segunda-feira, 10 de agosto de 2026, o harness foi corrigido e
as tarefas `t4` e `t5` foram repetidas em `Q4` e `BF16 offload` sem
alterar prompts, resolucao, tarefas ou demais condicoes do benchmark.

### O que mudou no harness antes do rerun

- artefatos deixaram de sobrescrever runs anteriores;
- o runner passou a separar:
  - `task_success`;
  - `semantic_success`;
  - `protocol_error`;
  - `executor_error`;
  - `model_error`;
- o adapter do Fara passou a aceitar:
  - JSON em `<tool_call>`;
  - formato oficial com `<function=computer_use>`;
  - `message.tool_calls` estruturado;
  - variante observada `key` com `text="ArrowDown Enter"`;
- a base automatizada ficou em
  `PYTHONPATH=src .\\.venv\\Scripts\\python -m pytest -q` =
  `26 passed`.

### Reruns preservados

- BF16 offload:
  - `artifacts/runs/t4-pending-highest/endpoint-run-bf16fix2-20260810-t4`
  - `artifacts/runs/t5-customer-recent-order/endpoint-run-bf16fix2-20260810-t5`
- Q4:
  - `artifacts/runs/t4-pending-highest/endpoint-run-q4fix-20260810-t4`
  - `artifacts/runs/t5-customer-recent-order/endpoint-run-q4fix-20260810-t5`

### Resultado objetivo desses reruns

- BF16 offload `t4`:
  - chegou ao filtro correto
    `/orders?status=Concluido&q=`;
  - terminou `25` passos sem resposta final;
  - `protocol_errors=18`.
- BF16 offload `t5`:
  - chegou a `/orders/10489`;
  - terminou `25` passos sem resposta final;
  - `protocol_errors=22`.
- Q4 `t4`:
  - chegou a `/orders?status=Concluido&q=&page=2`;
  - terminou `25` passos sem resposta final;
  - `protocol_errors=2`.
- Q4 `t5`:
  - chegou a `/orders/10491`;
  - terminou `25` passos sem resposta final;
  - `protocol_errors=15`.

### Leitura atualizada

- as correcoes reduziram bastante o ruido estrutural do harness;
- em especial, o `Q4` agora mostra trajetorias que chegam ao estado
  praticamente correto com pouco erro de protocolo residual;
- o gargalo dominante passou a ser encerramento agentic:
  o modelo frequentemente chega ao lugar certo, mas nao conclui com
  `terminate` + `answer`;
- isso enfraquece ainda mais a leitura de que o principal problema seja
  apenas interacao inicial com dropdown ou parse bruto do primeiro
  `<tool_call>`.

## Escopo desta consolidacao

Esta consolidacao resume apenas o que ja foi medido de forma objetiva
no host atual para a Fase 6:

- `microsoft/Fara1.5-4B` em rota official/native local;
- `microsoft/Fara1.5-4B` quantizado;
- `microsoft/Fara1.5-4B` com offload;
- `microsoft/Fara-7B` native/BF16;
- `microsoft/Fara-7B` GGUF `Q4_K_M`;
- `microsoft/Fara-7B` GGUF `Q5_K_M`.

Nao inclui ainda Suite B externa publica nem Suite C autenticada.

## Leitura rapida das tarefas citadas nos resultados

Os relatorios tecnicos usam os IDs internos do harness. Em linguagem
mais direta:

- `t4-pending-highest`:
  filtrar a lista de pedidos por um status especifico e descobrir qual
  pedido tem o maior valor dentro desse subconjunto.
- `t5-customer-recent-order`:
  encontrar uma cliente, abrir os pedidos dessa pessoa e identificar
  qual e o pedido mais recente.

Essas duas tarefas foram mantidas em destaque porque exigem mais do que
um clique isolado. Elas testam leitura de tabela, comparacao de dados,
manutencao de contexto e encerramento correto da tarefa.

## Ambiente consolidado

- data de referencia: 2026-08-10;
- host: Windows + WSL2;
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU;
- VRAM util detectada no host: 8188 MiB;
- restricao central do experimento: 8 GB de VRAM tornam inviavel
  assumir BF16 nativo para checkpoints acima desse envelope.

## Matriz final da Fase 6

| Modelo / rota | Runtime | Classe | Evidencia real | Classificacao consolidada |
| --- | --- | --- | --- | --- |
| `Fara1.5-4B` official/native local | `vllm 0.26.0` em WSL2 | official/native precision | carga BF16 avancou, mas a inicializacao falhou em CUDA/FlashAttention | nao funcional neste host |
| `Fara1.5-4B` quantized | `transformers + bitsandbytes 4-bit` | quantized | Suite A real com 5 tarefas, 3 sucessos e 2 falhas funcionais | funcional |
| `Fara1.5-4B` offload | `transformers` BF16 com `device_map="auto"` | offload | Suite A real com 5 tarefas, 3 sucessos e 2 falhas funcionais | funcional |
| `Fara-7B` native/BF16 | checkpoint official | official/native precision | checkpoint official de 15.46 GB frente a 8 GB de VRAM | inviavel em 8 GB |
| `Fara-7B` GGUF `Q4_K_M` | `llama.cpp` Vulkan | quantized | visao + `<tool_call>` em probe; falha funcional em benchmark real `t1` | nao funcional no benchmark real |
| `Fara-7B` GGUF `Q5_K_M` | `llama.cpp` Vulkan | quantized | probe multimodal gerou `<tool_call>` malformado | nao funcionalmente validado |

## Evidencias por rota

### 1. Fara1.5-4B official/native local

- stack medida: `vllm 0.26.0` no WSL2 com `uv --torch-backend=auto`;
- houve carga real de pesos BF16;
- a rota falhou no runtime CUDA/FlashAttention do host;
- conclusao: a rota official/native local nao esta operacional neste
  ambiente e nao pode ser tratada como benchmark funcional.

### 2. Fara1.5-4B quantized

Runs reais consolidadas da Suite A:

| Tarefa | Resultado | Steps | Duracao (s) | Pico VRAM (MB) |
| --- | --- | ---: | ---: | ---: |
| `t1-product-navigation` | sucesso | 3 | 27.347 | 6921.07 |
| `t2-create-customer` | sucesso | 8 | 94.675 | 6971.55 |
| `t3-open-order` | sucesso | 5 | 65.000 | 6850.11 |
| `t4-pending-highest` (`T4`: filtrar pedidos e achar o maior valor) | falha funcional | 25 | 358.129 | 6997.39 |
| `t5-customer-recent-order` (`T5`: achar o pedido mais recente de uma cliente) | falha funcional | 25 | 533.653 | 7410.02 |

Consolidacao:

- taxa de sucesso medida nesta amostra: `3/5 = 60%`;
- a rota e operacional e consegue concluir fluxos reais;
- ainda perde consistencia em tarefas mais longas ou de leitura mais
  exigente.

### 3. Fara1.5-4B offload

Runs reais consolidadas da Suite A:

| Tarefa | Resultado | Steps | Duracao (s) | Pico VRAM (MB) |
| --- | --- | ---: | ---: | ---: |
| `t1-product-navigation` | sucesso | 3 | 162.792 | 7927.50 |
| `t2-create-customer` | sucesso | 9 | 614.924 | 8101.00 |
| `t3-open-order` | sucesso | 5 | 350.898 | 8112.02 |
| `t4-pending-highest` (`T4`: filtrar pedidos e achar o maior valor) | falha funcional | 25 | 1233.641 | 8153.14 |
| `t5-customer-recent-order` (`T5`: achar o pedido mais recente de uma cliente) | falha funcional | 17 | 1109.974 | 8116.51 |

Consolidacao:

- taxa de sucesso medida nesta amostra: `3/5 = 60%`;
- a rota e funcional no benchmark real;
- o custo operacional e alto: duracoes muito maiores e VRAM sempre no
  limite do host;
- a Fase 6.1 nao mostrou ganho funcional sobre o `Q4` nas duas tarefas
  em que a rota quantizada havia falhado;
- deve ser tratada como classe separada, nao como equivalente a
  precision native.

### 4. Fara-7B native/BF16

- armazenamento official reportado: `15.46 GB`;
- host medido: `8188 MiB` de VRAM;
- conclusao: manter como `inviavel em 8 GB` para a rota local direta.

### 5. Fara-7B GGUF Q4_K_M

Evidencias:

- carregou em `llama.cpp` Vulkan;
- exigiu tuning de sobrevivencia:
  - `ctx-size=1024`;
  - `image-min-tokens=64`;
  - `image-max-tokens=256`;
- nessa configuracao, houve probe com visao + `<tool_call>` funcional;
- tambem houve resposta correta em chamada OpenAI-compatible simples;
- no benchmark real `t1-product-navigation`:
  - `success=false`;
  - `steps_executed=25`;
  - `duration_seconds=948.433`;
  - `peak_vram_mb=8048.94`;
  - `final_url=/`.

Consolidacao:

- esta rota nao deve ser considerada funcional para browser/computer
  use neste host;
- o fato de carregar e emitir uma acao isolada nao se converteu em
  desempenho real no harness.

### 6. Fara-7B GGUF Q5_K_M

Evidencias:

- carregou em `llama.cpp` Vulkan no probe multimodal minimo;
- o primeiro `<tool_call>` retornou malformado e com esquema
  incompativel com o harness;
- nao avancou para benchmark real.

Consolidacao:

- nao ha validacao funcional suficiente para considera-lo operacional;
- por ora, a rota fica abaixo do limiar minimo para promocao a campanha
  real.

## Leitura consolidada

### Melhor rota funcional atual

A melhor rota funcional atual para seguir benchmark neste host e:

- `Fara1.5-4B` quantized, quando o objetivo for melhor compromisso
  entre viabilidade, custo e tempo;
- `Fara1.5-4B` offload, quando o objetivo for testar confiabilidade em
  troca de latencia muito pior e VRAM no teto.

### O que a Fase 6.1 mostrou

- nas tarefas `t4` e `t5`, o `BF16 offload` nao recuperou as falhas do
  `Q4`;
- neste recorte controlado, `Q4` e `BF16 offload` terminaram ambos com
  `3/5`;
- isso enfraquece a hipotese de que a diferenca observada ate aqui seja
  explicada principalmente por quantizacao;
- o gargalo atual parece estar mais ligado a capacidade agentic do
  modelo nessa faixa de tarefa do que apenas a representacao dos pesos.

### O que nao pode ser confundido

- `offload` nao e `native`;
- `carregar modelo` nao e `benchmark funcional`;
- `emitir um <tool_call>` em probe unico nao basta para aprovar agente;
- `GGUF` e `checkpoint official` devem continuar separados na matriz.

## Recomendacao consolidada

1. Manter `Fara1.5-4B` quantized como baseline principal da campanha.
2. Manter `Fara1.5-4B` offload como baseline secundaria de
   confiabilidade, explicitamente marcada como `offload`.
3. Marcar `Fara-7B` native/BF16 como inviavel neste host.
4. Marcar `Fara-7B` GGUF `Q4_K_M` como nao funcional no benchmark real
   deste host.
5. Manter `Fara-7B` GGUF `Q5_K_M` como nao funcionalmente validado.
6. Levar `Fara1.5-4B` quantized e `Fara1.5-4B` offload para a
   Suite B externa publica.
7. Adiar novo investimento em `Fara-7B` GGUF ate surgir uma hipotese
   tecnica mais forte.

## Proximo passo recomendado

Com a Fase 6 consolidada, o proximo passo recomendado e:

1. usar `Fara1.5-4B` quantized como baseline primaria da Suite B;
2. usar `Fara1.5-4B` offload como baseline secundaria da Suite B;
3. manter a comparacao `Q4` versus `offload` separada na leitura dos
   resultados;
4. iniciar a campanha externa publica mantendo a Suite C para o final.
