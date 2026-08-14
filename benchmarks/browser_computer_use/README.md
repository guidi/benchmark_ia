# Benchmark de Browser / Computer Use

Este benchmark faz parte do repositório
[benchmark_ia](../../README.md) e existe para medir, de forma
reproduzível, quais modelos open-weight pequenos entregam a melhor
experiência de browser/computer use neste hardware.

O benchmark prioriza resultado real em tarefas visuais e interativas,
não apenas throughput de tokens.

O documento-base deste benchmark é
[browser_agent_local_benchmark.md](browser_agent_local_benchmark.md).

A consolidação objetiva da Fase 6 deste benchmark está em
[CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md).

O estado operacional mais recente da continuidade do trabalho está em
[HANDOFF.md](HANDOFF.md).

O procedimento reproduzível de execução deste benchmark está em
[PLAYBOOK.md](PLAYBOOK.md).

## Atualização de 2026-08-12

Na quarta-feira, 12 de agosto de 2026, a análise mais recente ficou
focada no problema de encerramento de tarefa em `t4` e `t5`.

Leitura prática atual:

- o problema dominante deixou de ser apenas parse bruto do primeiro
  `<tool_call>` ou interação inicial com menu suspenso;
- em várias trajetórias o modelo chega ao estado correto, mas não
  respeita o protocolo oficial de finalização;
- o formato de término que continua sendo considerado válido é:
  `computer_use` com `action=terminate` e `answer=...`;
- continuam inválidas, por não serem variantes inequivocamente
  equivalentes ao formato oficial:
  - `arguments.answer` sem `action:"terminate"`;
  - `{"terminate": true}` sem `answer`.

A ampliação segura feita no adaptador nesta rodada foi aceitar
`pause_and_memorize_fact` como ação válida, pois ela faz parte do
schema oficial documentado do modelo.

Estado da base automatizada após essa rodada:

- `PYTHONPATH=src .\\.venv\\Scripts\\python -m pytest -q`
  - resultado mais recente no estado atual do repositório:
    `38 passed`.

## Objetivo

Comparar modelos locais pelo equilíbrio entre:

- inteligência;
- confiabilidade;
- latência;
- uso de GPU/RAM;
- estabilidade em tarefas longas.

Os testes devem avaliar, no mínimo:

- interpretação de screenshots;
- localização de elementos na interface;
- decisão da próxima ação;
- navegação multi-etapas;
- uso de mouse, teclado, scroll e formulários;
- recuperação após erro;
- taxa de sucesso;
- tempo total por tarefa;
- latência média por ação;
- consumo de VRAM e RAM;
- utilização da GPU.

## Para leigos em IA

Se você não trabalha com IA, a forma mais simples de entender este
projeto é a seguinte:

este benchmark tenta responder se um modelo local consegue agir como um
assistente digital diante de uma interface de navegador, e não apenas
conversar bem.

Hoje, a medição principal e mais controlada acontece na `Suite A`, que
usa uma aplicação local criada para o benchmark. Os testes em sites
externos existem como fase separada e não devem ser misturados com a
leitura principal dessa base controlada.

Em outras palavras, não basta o modelo "parecer inteligente" no chat.
Ele precisa:

- olhar a tela;
- entender o que está vendo;
- decidir o próximo passo;
- clicar, digitar, navegar e corrigir erros;
- chegar ao estado final certo e encerrar a tarefa de forma válida.

Uma boa analogia é pensar em um teste prático de direção:

- o chat do modelo seria parecido com a prova teórica;
- este benchmark é a prova prática;
- o que importa aqui não é só saber explicar o que fazer, mas conseguir
  fazer de verdade, passo a passo, sem se perder.

### O que estamos medindo, em linguagem simples

- `acerta a tarefa ou não`:
  o modelo realmente chegou ao resultado esperado?
- `acerta de forma válida`:
  além de chegar perto do resultado, ele concluiu a tarefa do jeito
  correto para o benchmark, sem erro de protocolo?
- `consistência`:
  ele acerta só uma vez por sorte ou consegue repetir?
- `capacidade de navegação`:
  ele sabe passar por várias telas sem perder o objetivo?
- `capacidade de leitura visual`:
  ele entende botões, tabelas, campos e mensagens na tela?
- `recuperação`:
  se clicar errado ou se confundir, ele consegue voltar ao caminho?
- `velocidade`:
  quanto tempo leva para concluir a tarefa?
- `custo de hardware`:
  quanta VRAM, RAM e tempo de máquina ele consome?

### O que não estamos medindo

- se o modelo escreve textos bonitos;
- se ele responde perguntas gerais de conhecimento;
- se ele tira nota alta em benchmark acadêmico sem usar navegador;
- se ele parece convincente mesmo quando erra.

O foco aqui é comportamento operacional real.

### Glossário rápido

- `modelo`:
  o "cérebro" que tenta resolver a tarefa.
- `open-weight`:
  um modelo cujos pesos podem ser baixados e executados localmente.
  Analogia: uma máquina que você pode trazer para dentro de casa, em vez
  de só alugar acesso remoto.
- `7B`, `9B` ou `4B`:
  uma forma abreviada de falar o tamanho aproximado do modelo em número
  de parâmetros, na casa dos bilhões.
  Em geral, números maiores indicam modelos maiores, mais pesados e
  mais caros de rodar.
  Analogia: como comparar motores de tamanhos diferentes.
- `prompt`:
  a instrução dada ao modelo.
  Analogia: como uma ordem de serviço.
- `screenshot`:
  a imagem da tela que o modelo recebe para enxergar o estado atual.
  Analogia: a visão do assistente naquele momento.
- `harness`:
  o sistema que organiza a prova, registra métricas e guarda
  evidências da execução.
  Analogia: a estrutura da prova como um todo.
- `executor`:
  a parte que realmente transforma a decisão do modelo em clique,
  digitação, scroll ou navegação.
  Analogia: a mão que executa o comando.
- `validação automática`:
  a checagem final que verifica se a tarefa terminou corretamente.
  Analogia: o corretor da prova prática.
- `ação`:
  um clique, uma digitação, um scroll, um `back` ou outra interação.
- `taxa de sucesso`:
  a porcentagem de tarefas concluídas corretamente.
  Analogia: a taxa de aprovação.
- `latência`:
  o tempo operacional entre o momento em que o loop precisa agir e a
  ação seguinte ficar pronta.
  Analogia: o intervalo entre olhar a tela e conseguir soltar a próxima
  ação, incluindo mais do que o raciocínio puro.
- `VRAM`:
  a memória rápida da placa de vídeo.
  Analogia: a bancada de trabalho mais rápida disponível para o modelo.
- `RAM`:
  a memória principal da máquina.
  Analogia: um depósito maior, mas mais lento que a bancada principal.
- `BF16`:
  um formato de número usado para rodar o modelo com alta fidelidade,
  normalmente exigindo mais memória.
  Analogia: trabalhar com uma cópia mais fiel e pesada da ferramenta.
- `quantized`:
  palavra em inglês muito usada para dizer que o modelo foi
  `quantizado`, isto é, compactado para caber melhor no hardware.
  Em geral, usa menos memória, mas pode perder parte da qualidade.
- `quantização`:
  uma versão mais compacta do modelo para caber em menos memória.
  Analogia: como comprimir uma ferramenta grande para caber na mochila,
  aceitando alguma perda de precisão.
- `Q4`, `Q5`, `4-bit`:
  nomes comuns de quantizações mais compactas.
  Em termos simples, são versões mais leves do modelo para tentar fazê-lo
  caber na GPU.
- `offload`:
  quando parte do trabalho sai da GPU e vai para a RAM/CPU.
  Analogia: deixar uma parte do material na bancada rápida e outra parte
  no depósito, o que ajuda a caber, mas costuma deixar o processo mais
  lento.
- `native` ou `precisão nativa`:
  executar o modelo de forma mais direta, sem essa compactação extra.
  Em geral, preserva melhor a forma original do modelo, mas exige mais
  memória.

### Leitura prática

No fim, este benchmark quer responder uma pergunta muito simples:

> entre os modelos testados, qual realmente consegue operar um browser
> local com mais acerto, menos erro e custo aceitável neste computador?

## Hardware e ambiente

Antes de rodar qualquer benchmark, o harness deve detectar e registrar
automaticamente:

- CPU;
- RAM total;
- GPU;
- VRAM disponível;
- driver NVIDIA;
- versão CUDA;
- sistema operacional;
- espaço livre em disco.

Esses valores não devem ser assumidos manualmente. O relatório final
precisa refletir o ambiente real da máquina.

## Modelos prioritários

Prioridade inicial:

1. Microsoft Fara1.5-4B
2. Microsoft Fara-7B
3. OpenCUA-7B
4. UI-TARS-1.5-7B
5. Outros modelos open-weight entre aproximadamente 7B e 14B que sejam
   fortes em GUI/browser/computer-use e viáveis no hardware detectado

Status medido até 2026-08-12 neste host:

- GPU local detectada no Windows e no WSL2: 8188 MiB de VRAM;
- armazenamento oficial reportado no Hugging Face:
  - `microsoft/Fara-7B`: 15.46 GB;
  - `microsoft/Fara1.5-4B`: 8.47 GB;
  - `microsoft/Fara1.5-9B`: 17.55 GB.

Isso torna inviável, na rota oficial sem quantização/offload adicional,
a execução local direta de `Fara-7B` e `Fara1.5-9B` nesta RTX 4060
8 GB.
`Fara1.5-4B` fica no limite e continua arriscado para uso local oficial
com runtime de serving completo.

## Matriz de execução atual

Para a matriz consolidada com conclusão por classe de execução, usar
primeiro [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md).

Status medido até 2026-08-12 para `microsoft/Fara1.5-4B`:

- `official/native local`:
  - stack oficial local testada em WSL2 com `vllm 0.26.0` e `uv --torch-backend=auto`;
  - o modelo avançou até carga real de pesos em BF16;
  - a inicialização falhou no runtime CUDA/FlashAttention com erro de
    driver insuficiente para a versão do runtime usada por esse stack;
  - classificação atual: `não funcional neste host nessa rota oficial local`.
- `quantized`:
  - `transformers + bitsandbytes 4-bit` validado com visão + emissão de
    `<tool_call>` sobre screenshot real da Suite A;
  - runs reais já executadas na Suite A:
    - `t1-product-navigation`: sucesso;
    - `t2-create-customer`: sucesso;
    - `t3-open-order`: sucesso;
    - `t4-pending-highest`: falha funcional;
    - `t5-customer-recent-order`: falha funcional;
  - rerun curto de encerramento em 2026-08-12:
    - `t5-customer-recent-order` piorou e terminou em
      `/orders?q=Carlos%20Pereira`, sem chegar ao encerramento válido;
  - nas trajetórias mais próximas do sucesso, o gargalo atual passou a
    ser emissão de resposta final fora do protocolo oficial;
  - classificação atual: `funcional`.
- `offload`:
  - `transformers` em BF16 com `device_map="auto"` validado com
    offload parcial para CPU;
  - gerou ação visual plausível sobre screenshot real;
  - runs reais já executadas na Suite A:
    - `t1-product-navigation`: sucesso;
    - `t2-create-customer`: sucesso;
    - `t3-open-order`: sucesso;
    - `t4-pending-highest`: falha funcional;
    - `t5-customer-recent-order`: falha funcional;
  - a Fase 6.1 mostrou que, nessas duas tarefas difíceis, o BF16
    `offload` não superou o `Q4`;
  - nova análise de 2026-08-12 confirmou o mesmo padrão de
    encerramento inválido em tarefas quase resolvidas:
    - `arguments.answer` sem `action:"terminate"`;
    - `terminate` sem `answer`;
  - o rerun curto de `t4` em 2026-08-12 ficou parcial por timeout do
    shell, mas os artefatos parciais repetem esse mesmo padrão;
  - a tentativa de rerun curto de `t5` em 2026-08-12 falhou com
    `500 Internal Server Error` no endpoint local offload;
  - classificação atual: `funcional`.

Status atual de `microsoft/Fara-7B`:

- `native/BF16`: manter como `inviável em 8 GB` para uso local direto;
- `GGUF Q4_K_M`:
  - validado em `llama.cpp` Vulkan com `ctx-size=1024`,
    `image-min-tokens=64` e `image-max-tokens=256`;
  - nessa configuração, a rota multimodal respondeu com visão +
    `<tool_call>` tanto em `llama-cli` quanto em uma chamada
    compatível com OpenAI;
  - em benchmark real, `t1-product-navigation` falhou funcionalmente:
    `success=false`, `steps_executed=25`, `duration_seconds=948.433`,
    `peak_vram_mb=8048.94`, `final_url=/`;
  - classificação atual: `não funcional no benchmark real deste host
    nessa rota GGUF`.
- `GGUF Q5_K_M`:
  - carregou em `llama-cli` com a mesma configuração restrita de
    contexto/imagem;
  - o primeiro probe multimodal retornou `<tool_call>` malformado e
    incompatível com o harness;
  - não foi promovido para run real do benchmark;
  - classificação atual: `ainda não validado funcionalmente`.

Antes de instalar ou baixar qualquer modelo, verificar:

- repositório oficial;
- documentação;
- formato do checkpoint;
- licença;
- suporte a quantização;
- runtime recomendado;
- compatibilidade com GPU;
- memória estimada.

Se houver opção adequada, priorizar inicialmente quantizações próximas
de Q4 ou Q5. Toda execução deve registrar checkpoint, quantização e
runtime exatos.

## Regra de VRAM

A GPU pode ser dedicada quase integralmente ao experimento, mas o
benchmark deve:

- evitar OOM;
- manter margem para runtime, vision encoder, KV cache e buffers;
- registrar pico de VRAM;
- registrar explicitamente qualquer offload para RAM;
- marcar como inviável no hardware atual configurações que só funcionem
  com offload pesado ou desempenho artificialmente degradado.

## Arquitetura do benchmark

O projeto deve usar um harness reutilizável com fluxo conceitual
semelhante a este:

```text
Objetivo
  ->
Browser
  ->
Screenshot / estado atual
  ->
Modelo
  ->
Decisão / ação
  ->
Executor
  ->
click / type / scroll / keyboard
  ->
Browser atualizado
```

Quando compatível, a preferência é Chromium + Playwright.

Para modelos orientados por visão, não fornecer DOM ou árvore de
acessibilidade se isso descaracterizar a tarefa proposta pelo próprio
modelo. Se um modelo exigir uma arquitetura oficial diferente, a
integração deve seguir essa arquitetura e documentar a diferença.

No estado atual deste benchmark, o harness já suporta `click` e `type`
por coordenadas além de seletores, para evitar que a Suite A dependa
exclusivamente de CSS selectors internos.

Também já suporta `mouse_move`, `navigate` e `back`, o que permite
acoplar adaptadores para endpoints compatíveis com OpenAI sem depender
apenas de seletores.

Na rodada de 2026-08-12, o adaptador também passou a:

- aceitar `pause_and_memorize_fact` como ação válida;
- exigir `answer` explícita quando o modelo usa `terminate`;
- manter como inválidas respostas finais implícitas ou ambíguas.

## Segurança

Executar somente em páginas de teste e ambientes controlados.

Não executar ações como:

- compras reais;
- envio de mensagens reais;
- uso de credenciais reais;
- alteração de contas reais;
- exclusão de dados;
- bypass de CAPTCHA;
- operações irreversíveis.

Sempre que necessário, criar páginas locais próprias para o benchmark.

## Aplicação de teste

O benchmark deve usar uma pequena aplicação ou site local reproduzível
com, no mínimo:

- página inicial;
- menus;
- formulário;
- tabela;
- paginação;
- busca;
- modal;
- menu suspenso;
- checkbox;
- botão de opção;
- abas;
- scroll;
- validação de campos;
- páginas intermediárias;
- mensagens de sucesso e erro.

IDs internos podem existir para validação automática do harness, mas não
devem ser expostos ao modelo.

No estado atual, os endpoints internos da aplicação controlada exigem um
token do harness e o agente recebe apenas o contexto público da tarefa,
sem `task_id` interno.

## Tarefas do benchmark

O conjunto inicial de tarefas deve cobrir:

1. Navegação simples
2. Preenchimento de formulário
3. Busca de pedido
4. Filtros e identificação de maior valor
5. Fluxo multi-step com navegação e interpretação
6. Interação com elemento fora da viewport inicial
7. Abertura e confirmação de modal
8. Recuperação após erro induzido
9. Página visualmente ambígua
10. Sequência longa com pelo menos 10 ações corretas

Cada tarefa deve ter critério de sucesso validado automaticamente pelo
estado final da aplicação, não apenas pela declaração do modelo.

### O que são T4 e T5 na prática

Os nomes `t4-pending-highest` e `t5-customer-recent-order` são IDs
internos do harness. O que importa no benchmark é a habilidade que cada
uma delas testa:

- `T4 - Filtros`:
  o agente começa na lista de pedidos, precisa filtrar por um status
  específico e, dentro desse recorte, descobrir qual pedido tem o maior
  valor.
- `T5 - Multi-step`:
  o agente começa na lista de clientes, precisa encontrar uma cliente,
  abrir a área de pedidos dessa pessoa e identificar qual é o pedido
  mais recente.

Em termos práticos, essas duas tarefas existem para medir coisas
diferentes:

- `T4` mede se o modelo consegue aplicar filtro, manter contexto,
  ler uma tabela e comparar valores sem se perder no meio do fluxo.
- `T5` mede se o modelo consegue navegar por várias telas, manter o
  objetivo em memória e interpretar corretamente qual registro é o mais
  recente.

Por isso `T4` e `T5` são mais importantes que um clique simples:
elas aproximam melhor o comportamento esperado de um agente que precisa
operar sistemas reais, e não apenas interagir com uma página fácil.

## Status atual da Suite A

No estado atual deste benchmark, as 10 tarefas iniciais da Suite A estão
implementadas na aplicação controlada.

As tarefas controladas são parametrizadas dinamicamente por run para
reduzir hardcode trivial no adaptador.

O runner agora captura screenshots no viewport, não em `full_page`,
para manter coerência entre imagem entregue ao modelo e coordenadas de
ações executadas no browser.

## Repetições e aquecimento

Para a campanha canônica mínima descrita no `PLAYBOOK.md`, executar
cada combinação `modelo x tarefa` 1 vez nas 5 tarefas fixadas:
`t1`, `t2`, `t3`, `t4` e `t5`.

Para campanha estendida ou validação adicional, o alvo recomendado
continua sendo 3 repetições por combinação, desde que isso seja
declarado antes do início da campanha e refletido no manifesto.

Antes das medições oficiais:

- registrar tempo de carregamento do modelo;
- executar aquecimento;
- separar primeira inferência das inferências posteriores.

## Métricas

Cada execução deve registrar, sempre que possível:

```json
{
  "model": "",
  "quantization": "",
  "runtime": "",
  "task": "",
  "success": false,
  "actions": 0,
  "invalid_actions": 0,
  "recovery_actions": 0,
  "duration_seconds": 0,
  "average_action_latency_ms": 0,
  "peak_vram_mb": 0,
  "peak_ram_mb": 0,
  "gpu_utilization_average": 0,
  "gpu_utilization_peak": 0,
  "tokens_generated": 0,
  "tokens_per_second": 0,
  "notes": ""
}
```

Se uma métrica não puder ser medida corretamente, usar `null`.

Também é desejável separar:

- tempo de screenshot;
- preprocessing;
- inferência;
- execução da ação;
- carregamento da página;
- tempo total do loop.

## Monitoramento NVIDIA

Quando disponível, usar `nvidia-smi` e/ou NVML para coletar
periodicamente:

- VRAM;
- utilização da GPU;
- temperatura;
- potência;
- clocks, se fizer sentido.

Os dados brutos devem ser salvos para análise posterior.

## Resolução e contexto

As comparações devem manter condições visuais e de contexto consistentes:

- usar resolução fixa por padrão, por exemplo `1280x720`;
- registrar qualquer resolução diferente recomendada oficialmente por um
  modelo;
- começar com contexto conservador;
- registrar o contexto configurado;
- avaliar separadamente o impacto de aumentar contexto em tarefas longas
  e no uso de VRAM.

## Evidências e saídas

Cada execução deve produzir artefatos em estrutura semelhante a:

```text
runs/
  <modelo>/
    <tarefa>/
      run-01/
        metadata.json
        metrics.json
        actions.jsonl
        gpu.csv
        screenshots/
        final-state.json
```

No estado atual deste benchmark, o runner já gera `actions.jsonl`,
`metadata.json`, `metrics.json`, `final-state.json` e `gpu.csv` por
run.

Para integrar um modelo remoto ou auto-hospedado por endpoint
compatível com OpenAI, o CLI já expõe:

```bash
cua-bench controlled-endpoint-run \
  --task-id t1-product-navigation \
  --endpoint-url http://127.0.0.1:5000 \
  --model microsoft/Fara-7B
```

No estado atual, também existem scripts auxiliares para probes locais em
WSL:

- [probe_vllm_load.py](scripts/probe_vllm_load.py)
- [probe_transformers_fara_action.py](scripts/probe_transformers_fara_action.py)
- [transformers_openai_server.py](scripts/transformers_openai_server.py)
- [launch_transformers_server.sh](scripts/launch_transformers_server.sh)

Ao final, o benchmark deve gerar:

```text
results/
  summary.json
  summary.md
  results.csv
```

O `summary.md` deve incluir:

- hardware detectado;
- modelos testados;
- checkpoint, quantização, runtime e configuração;
- tabela consolidada de resultados;
- resultado por tarefa;
- classificação de falhas observadas;
- hashes e trilha de auditoria compartilhados da campanha.

As recomendações objetivas sobre melhor rota, confiabilidade,
velocidade, equilíbrio e custo-benefício devem aparecer na leitura
humana consolidada, como `CONSOLIDATED_RESULTS.md`, a partir do resumo
determinístico gerado pelo consolidator.

## Checklist para reproduzir em outra VGA

Este benchmark foi desenhado para ser reproduzível em outra GPU, mas os
resultados não devem ser copiados de um host para outro sem rerun
completo.

O que deve permanecer fixo entre hosts:

- a mesma Suite A controlada;
- o mesmo estado inicial determinístico da Suite A;
- o mesmo mecanismo de reset e a mesma semente ou o mesmo snapshot de
  dados;
- as mesmas tarefas e validadores;
- os mesmos prompts;
- a mesma resolução;
- o mesmo limite de passos;
- o mesmo checkpoint por modelo;
- a mesma quantização exata por rota comparada;
- o mesmo runtime e a mesma versão do runtime;
- a mesma política de offload, quando houver;
- a mesma forma de salvar artefatos e métricas;
- a mesma classificação por classe de execução:
  `official/native`, `quantized`, `offload` e `inviável`.

O que deve ser medido novamente em cada VGA:

- GPU real detectada;
- VRAM total e pico de VRAM;
- RAM total e volume de offload;
- driver NVIDIA e versão CUDA;
- runtime realmente usado;
- tempo por tarefa;
- taxa de sucesso por tarefa;
- erros de protocolo, executor e modelo;
- sinais de instabilidade operacional.

Checklist objetivo de portabilidade:

1. Registrar o novo ambiente em `ENVIRONMENT_INVENTORY.md` ou artefato
   equivalente, sem reaproveitar números do host anterior.
2. Fixar antes da campanha o mesmo `checkpoint`, a mesma quantização,
   o mesmo runtime e a mesma política de offload que serao comparados
   entre hosts.
3. Revalidar se cada modelo cabe na nova VGA em cada classe de
   execução: `official/native`, `quantized` e `offload`.
4. Garantir o mesmo estado inicial determinístico da Suite A antes de
   cada run, com o mesmo reset de dados.
5. Repetir probes mínimos de carga e ação visual antes de promover um
   modelo para run real.
6. Rodar a Suite A sem mudar prompts, tarefas, resolução ou critérios
   de sucesso.
7. Salvar artefatos completos por run:
   `metadata.json`, `metrics.json`, `actions.jsonl`, `gpu.csv`,
   `final-state.json` e screenshots.
8. Consolidar os resultados do novo host separadamente, sem misturar
   métricas da VGA anterior.
9. Comparar os hosts apenas depois da consolidação, destacando:
   viabilidade, latência, uso de VRAM, necessidade de offload e taxa de
   sucesso.
10. Se a comparação incluir Suites B ou C, repetir também o mesmo
    escopo externo nos dois hosts; caso contrário, declarar
    explicitamente que a comparação cruzada vale apenas para a
    Suite A controlada.

Regra prática:

- o benchmark é portável entre GPUs;
- a conclusão não é portável sem nova medição;
- hoje, a comparação cruzada mais limpa entre hosts é a comparação da
  Suite A controlada, salvo quando Suites B ou C forem repetidas com o
  mesmo escopo e as mesmas regras.

## Pontuação

O benchmark pode gerar um score agregado, mas a métrica principal
continua sendo `task success rate`.

Pesos iniciais sugeridos:

- 50% taxa de sucesso;
- 20% eficiência / número de ações;
- 15% tempo;
- 10% recuperação de erros;
- 5% uso de recursos.

Velocidade não deve mascarar um modelo com baixa taxa de sucesso.

## Estrutura sugerida

Uma organização inicial razoável para o código é:

```text
src/
  agents/
    base.py
    fara.py
    opencua.py
    uitars.py
  browser/
  benchmark/
  metrics/
  reporting/
```

A estrutura pode mudar se surgir uma alternativa tecnicamente melhor,
desde que novos modelos continuem sendo adicionados via adaptadores.

## Ordem de execução

1. Inspecionar hardware e software.
2. Pesquisar documentação oficial atual dos modelos.
3. Definir runtimes adequados.
4. Criar ambiente isolado.
5. Criar o site local de benchmark.
6. Implementar o harness.
7. Implementar a coleta de métricas.
8. Integrar um modelo primeiro.
9. Validar o fluxo ponta a ponta.
10. Integrar os demais modelos.
11. Executar aquecimento.
12. Rodar o benchmark.
13. Gerar relatório.
14. Analisar resultados e propor próximos experimentos.

## Critério final

O objetivo não é provar que um agente consegue clicar uma vez.

O objetivo é responder, de forma mensurável e reproduzível:

> Qual modelo local realmente consegue operar um browser de maneira
> autônoma, consistente e mensurável neste computador?
