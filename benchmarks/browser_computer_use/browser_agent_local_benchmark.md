# Benchmark local de modelos para Browser / Computer Use

## Objetivo

Montar e executar um benchmark local para descobrir qual modelo
open-weight pequeno oferece a melhor experiência de **browser/computer
use** nesta máquina.

O objetivo não é apenas medir tokens por segundo. O teste deve avaliar:

-   capacidade de entender screenshots;
-   capacidade de localizar elementos da interface;
-   capacidade de decidir a próxima ação;
-   navegação multi-etapas;
-   uso de mouse, teclado, scroll e formulários;
-   recuperação após erro;
-   estabilidade em tarefas longas;
-   consumo de VRAM e RAM;
-   utilização da GPU;
-   latência por ação;
-   tempo total por tarefa;
-   taxa de sucesso;
-   qualidade do raciocínio/planejamento quando observável.

A prioridade é descobrir o melhor equilíbrio entre **inteligência,
confiabilidade e desempenho** no hardware disponível.

## Hardware alvo

Antes dos testes, detectar e registrar automaticamente:

-   CPU;
-   quantidade de RAM;
-   GPU;
-   VRAM disponível;
-   versão do driver NVIDIA;
-   versão CUDA;
-   sistema operacional;
-   espaço livre em disco.

Não assumir os valores: coletá-los da máquina e gravá-los no relatório.

## Modelos prioritários

Pesquisar a forma atual/recomendada de executar localmente cada modelo
antes de instalar.

Prioridade inicial:

1.  **Microsoft Fara-7B**
2.  **OpenCUA-7B**
3.  **UI-TARS-1.5-7B**
4.  Outros modelos open-weight de aproximadamente 7B--14B que atualmente
    sejam fortes em GUI/browser/computer-use e sejam razoavelmente
    executáveis no hardware detectado.

Não baixar cegamente todos os modelos. Primeiro verificar:

-   repositório oficial;
-   documentação;
-   formato disponível;
-   suporte a quantização;
-   runtime recomendado;
-   compatibilidade com a GPU;
-   memória estimada;
-   licença.

Se existir uma versão quantizada apropriada, priorizar inicialmente algo
próximo de **Q4/Q5**, desde que o modelo e o runtime suportem isso
adequadamente.

Registrar exatamente qual checkpoint/quantização foi usado.

## Regra importante sobre VRAM

A máquina pode dedicar praticamente toda a GPU ao experimento.

Entretanto:

-   evitar OOM;
-   deixar margem razoável para runtime, vision encoder, KV cache e
    buffers;
-   registrar pico de VRAM;
-   se houver offload para RAM, registrar explicitamente;
-   não comparar duas configurações como equivalentes se uma estiver
    fazendo offload pesado.

Se um modelo não couber de maneira razoável, registrar como **inviável
neste hardware**, em vez de forçar uma configuração extremamente lenta
apenas para fazê-lo executar.

## Arquitetura do experimento

Criar um harness reutilizável.

Fluxo esperado:

``` text
Objetivo
  ↓
Browser
  ↓
Screenshot / estado atual
  ↓
Modelo
  ↓
Decisão / ação
  ↓
Executor
  ↓
click / type / scroll / keyboard
  ↓
Browser atualizado
  ↓
novo screenshot
  ↓
Modelo
  ↓
...
```

Preferir Chromium + Playwright quando compatível.

Para modelos de computer-use visual, não fornecer DOM/accessibility tree
se isso mudar artificialmente a tarefa para algo diferente da proposta
original do modelo.

Se determinado modelo tiver arquitetura oficial diferente, implementar o
caminho recomendado pelo próprio projeto e documentar a diferença.

## Segurança do benchmark

Executar somente em páginas de teste/controladas.

Não:

-   realizar compras reais;
-   enviar mensagens reais;
-   alterar contas reais;
-   inserir credenciais reais;
-   excluir dados;
-   contornar CAPTCHA;
-   executar ações irreversíveis.

Criar páginas locais próprias quando necessário.

## Ambiente de testes

Criar uma pequena aplicação/site local para benchmark, de modo que os
resultados sejam reproduzíveis.

Ela deve possuir pelo menos:

-   página inicial;
-   menus;
-   formulário;
-   tabela;
-   paginação;
-   busca;
-   modal;
-   dropdown;
-   checkbox;
-   radio button;
-   abas;
-   scroll;
-   campos com validação;
-   páginas intermediárias;
-   mensagens de sucesso e erro.

Adicionar IDs internos para o harness validar o resultado, mas **não
expor esses IDs ao modelo**.

## Tarefas do benchmark

### Tarefa 1 --- Navegação simples

Objetivo:

> Abra a seção Produtos e acesse o produto "Teclado Mecânico".

Medir sucesso e número de ações.

### Tarefa 2 --- Formulário

Objetivo:

> Cadastre um cliente chamado João da Silva, e-mail joao@example.test e
> cidade Curitiba.

O harness deve verificar automaticamente os valores finais.

### Tarefa 3 --- Busca

Objetivo:

> Encontre o pedido número 10482 e abra seus detalhes.

### Tarefa 4 --- Filtros

Objetivo:

> Mostre somente os pedidos com status Pendente e encontre o de maior
> valor.

### Tarefa 5 --- Multi-step

Objetivo:

> Encontre o cliente Maria Oliveira, abra seus pedidos e informe qual é
> o pedido mais recente.

Exige navegação + interpretação.

### Tarefa 6 --- Interface com scroll

Colocar o elemento necessário fora da viewport inicial.

Objetivo deve exigir scroll e interação posterior.

### Tarefa 7 --- Modal

Exigir abrir modal, selecionar uma opção e confirmar.

### Tarefa 8 --- Recuperação de erro

Criar situação em que a primeira ação óbvia leva a uma mensagem de erro
recuperável.

Avaliar se o agente:

1.  percebe o erro;
2.  entende o motivo;
3.  tenta uma estratégia válida;
4.  conclui a tarefa.

### Tarefa 9 --- Página visualmente ambígua

Criar botões/controles semelhantes para testar grounding visual.

### Tarefa 10 --- Sequência longa

Criar tarefa que demande pelo menos aproximadamente 10 ações corretas.

Objetivo: avaliar degradação durante execução prolongada.

## Repetições

Não executar cada tarefa apenas uma vez.

Idealmente executar cada combinação:

**modelo × tarefa = 3 vezes**

Se o custo computacional for excessivo, começar com uma execução
exploratória e depois repetir as configurações mais promissoras.

Usar o mesmo estado inicial em todas as execuções.

## Métricas

Para cada execução registrar:

``` json
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

Quando alguma métrica não puder ser obtida corretamente, usar `null`,
não inventar valores.

## Monitoramento NVIDIA

Quando disponível, utilizar `nvidia-smi`/NVML para coletar
periodicamente:

-   VRAM;
-   GPU utilization;
-   temperatura;
-   potência;
-   clocks, se útil.

A amostragem deve acontecer durante toda a execução da tarefa.

Salvar os dados brutos para análise posterior.

## Latência

Separar, quando possível:

-   tempo de screenshot;
-   preprocessing;
-   inferência;
-   execução da ação;
-   carregamento da página;
-   tempo total do loop.

Isso permitirá distinguir:

> modelo lento

de:

> browser/site lento.

## Warm-up

Não usar a primeira inferência como representação direta da velocidade
normal.

Executar warm-up antes das medições oficiais e registrar:

-   tempo de carregamento do modelo;
-   primeira inferência;
-   inferências posteriores.

## Contexto

Começar com um contexto conservador.

Não configurar 128K/256K simplesmente porque o modelo suporta.

Registrar o tamanho configurado.

Avaliar separadamente se aumentar contexto melhora tarefas longas e
quanto aumenta VRAM.

## Screenshots e resolução

Manter resolução fixa durante comparação.

Exemplo inicial:

``` text
1280x720
```

Se o modelo oficialmente recomendar outra resolução/processamento,
seguir a recomendação e registrar.

Não comparar silenciosamente modelos usando condições visuais muito
diferentes.

## Evidências

Para cada execução salvar:

``` text
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

`actions.jsonl` deve permitir reconstruir o que aconteceu sem depender
apenas do resultado agregado.

## Avaliação automática

Sempre que possível, validar sucesso pelo estado interno da aplicação de
benchmark.

Exemplos:

-   URL correta;
-   registro criado;
-   valor selecionado;
-   conteúdo do banco;
-   elemento final esperado;
-   resposta fornecida pelo agente.

Não usar somente a própria afirmação do modelo de que concluiu a tarefa.

## Score

Criar um score agregado, mas manter todas as métricas individuais
disponíveis.

Uma proposta inicial:

``` text
50% taxa de sucesso
20% eficiência / número de ações
15% tempo
10% recuperação de erros
5% uso de recursos
```

Não permitir que velocidade compense uma taxa de sucesso ruim.

A métrica principal deve continuar sendo **task success rate**.

## Comparação de quantização

Para o melhor modelo que couber na máquina, se houver versões
apropriadas, comparar pelo menos duas quantizações, por exemplo:

``` text
Q4
vs
Q5
```

Avaliar se o aumento de qualidade justifica:

-   VRAM adicional;
-   redução de velocidade;
-   menor espaço para contexto.

## Baseline opcional

Se houver acesso já configurado a uma API/modelo proprietário e isso
puder ser feito sem expor segredos nos logs, permitir uma execução
**opcional** como baseline.

O benchmark local deve funcionar sem isso.

Não adicionar nem solicitar credenciais externas apenas para completar o
benchmark inicial.

## Resultado final

Gerar automaticamente:

``` text
results/
  summary.md
  results.csv
  raw-results.json
```

`summary.md` deve conter:

# Hardware

Configuração detectada.

# Modelos testados

Checkpoint, quantização, runtime e configuração.

# Resultados

Tabela semelhante:

  Modelo   Quant.     Sucesso   Tempo médio   Ações   VRAM pico   tok/s
  -------- -------- --------- ------------- ------- ----------- -------

# Resultado por tarefa

Mostrar onde cada modelo foi bem ou mal.

# Erros observados

Classificar falhas, por exemplo:

-   grounding incorreto;
-   botão errado;
-   hallucinated action;
-   loop;
-   não percebeu mudança de tela;
-   falha de planejamento;
-   perdeu objetivo;
-   erro após scroll;
-   incapacidade de recuperar erro.

# Melhor modelo

Apontar objetivamente o vencedor no hardware testado.

# Recomendação

Responder:

1.  Qual modelo é mais confiável?
2.  Qual é mais rápido?
3.  Qual apresenta melhor equilíbrio?
4.  Qual quantização vale mais a pena?
5.  A GPU atual é suficiente para uso real?
6.  Qual seria o provável benefício de uma GPU de 16, 24 ou 32 GB?
7.  Vale a pena manter esse agente local?

## Implementação

Organizar o projeto para que novos modelos possam ser adicionados por
adapters, sem reescrever o benchmark.

Algo conceitualmente semelhante a:

``` text
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

Não é obrigatório usar exatamente essa estrutura se houver uma
alternativa tecnicamente melhor.

## Ordem de execução

1.  Inspecionar hardware/software.
2.  Pesquisar documentação oficial atual dos modelos.
3.  Definir runtimes adequados.
4.  Criar ambiente isolado.
5.  Criar site de benchmark.
6.  Implementar harness.
7.  Implementar coleta de métricas.
8.  Integrar **um modelo primeiro**.
9.  Validar benchmark ponta a ponta.
10. Só então baixar/integrar os demais.
11. Executar warm-up.
12. Executar benchmark.
13. Gerar relatório.
14. Analisar resultados e sugerir próximos experimentos.

## Regra de autonomia

Pode instalar dependências necessárias e adaptar a implementação ao
ambiente encontrado.

Antes de baixar modelos muito grandes, verificar tamanho e espaço
disponível.

Evitar downloads redundantes.

Se encontrar incompatibilidade de CUDA, PyTorch, Transformers ou
runtime, investigar e corrigir em vez de simplesmente abandonar o
modelo.

Se um modelo exigir hardware claramente superior ao disponível,
registrar isso e seguir para o próximo.

## Critério final

Não quero uma demonstração em que o agente consegue clicar uma vez.

Quero descobrir:

> **Qual modelo local realmente consegue operar um browser de maneira
> autônoma, consistente e mensurável neste computador?**

O benchmark deve privilegiar **resultado real e reproduzível**, não
apenas fazer o modelo executar.
