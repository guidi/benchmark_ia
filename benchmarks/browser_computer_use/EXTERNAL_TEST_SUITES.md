# External Test Suites

Ultima atualizacao: 2026-08-09

## Objetivo

Definir os cenarios externos do benchmark para complementar a suite
controlada com testes mais realistas, sem perder criterio de validacao
e sem executar acoes perigosas.

## Principios

- Testes externos nao substituem a suite controlada.
- Resultados externos devem ser reportados separadamente.
- Sucesso nunca sera validado apenas pelo texto produzido pelo modelo.
- Toda tarefa precisa ter criterio observavel por codigo.
- Falhas precisam ser classificadas entre:
  - falha do modelo;
  - falha do site;
  - falha de rede;
  - falha de autenticacao;
  - bloqueio anti-automacao.

## Suite B - Externa publica

## B1 - Receita Federal / Portal e-CAC publico

Classe:

- portal governamental publico.

URL inicial:

- [Portal e-CAC na Receita Federal](https://www.gov.br/receitafederal/pt-br/canais_atendimento/atendimento-virtual)

Objetivo do teste:

- medir navegacao publica em portal real;
- localizar links e secoes relevantes;
- seguir fluxo correto ate a pagina de acesso.

Tarefas candidatas:

1. abrir a pagina publica do e-CAC e localizar o link de acesso ao
   portal;
2. navegar para a pagina de acesso correta;
3. voltar e localizar a secao de ajuda sobre formas de acesso.

Validacao:

- URL final esperada;
- titulo correto da pagina;
- presenca do link de acesso ao e-CAC;
- presenca da secao ou texto esperado na pagina alvo.

Observacao:

- a pagina da Receita Federal consultada hoje, 9 de agosto de 2026, foi
  atualizada em 25 de maio de 2026.

## B2 - AdminLTE Live Preview

Classe:

- dashboard publico complexo.

URL inicial:

- [AdminLTE Live Preview](https://adminlte.io/themes/v4/)

Objetivo do teste:

- medir grounding visual em dashboard real;
- medir navegacao em sidebar, widgets e secoes;
- testar leitura de cards, areas com tabelas e componentes mistos.

Tarefas candidatas:

1. localizar o card "New Orders" e informar o valor exibido;
2. abrir a documentacao a partir do link visivel na pagina;
3. localizar a area de chat e identificar o placeholder do campo de
   mensagem.

Validacao:

- valor textual esperado na pagina;
- URL final da documentacao, quando aplicavel;
- presenca do elemento correto na area de chat.

Restricoes:

- nao enviar mensagens;
- nao interagir com qualquer fluxo que altere estado externo.

## B3 - OpenCart Demo Storefront

Classe:

- e-commerce publico de demonstracao.

URL inicial:

- [OpenCart Demo](https://www.opencart.com/index.php?route=cms/demo)

URL operacional esperada:

- storefront acessado a partir da pagina oficial de demo.

Objetivo do teste:

- medir busca, navegacao por categorias, filtros simples e pagina de
  produto em ambiente externo mais parecido com e-commerce real.

Tarefas candidatas:

1. abrir a demonstracao oficial e entrar no storefront;
2. localizar uma categoria especifica;
3. buscar um produto e abrir sua pagina de detalhes;
4. ordenar ou navegar entre listagens, quando a interface permitir isso
   sem efeitos permanentes.

Validacao:

- URL da pagina do storefront;
- nome do produto ou categoria correta na pagina final;
- elementos visiveis esperados na listagem ou pagina do produto.

Restricoes:

- nao usar area administrativa;
- nao concluir compra;
- nao criar conta;
- nao preencher checkout.

Observacao:

- a pagina oficial de demo do OpenCart consultada hoje, 9 de agosto de
  2026, indica links separados para storefront e administration.

## Suite C - Externa autenticada e sensivel

## Regra principal

Esta suite sera estritamente read-only.

Nao e permitido:

- protocolar;
- transmitir;
- assinar;
- pagar;
- alterar cadastro;
- confirmar operacoes;
- enviar documentos;
- emitir documentos com efeito pratico;
- executar qualquer acao fiscal real.

O acesso sera feito por certificado digital ja existente, conforme
disponibilidade do ambiente do usuario.

## C1 - e-CAC com certificado digital existente

Classe:

- portal governamental autenticado e sensivel.

URLs principais:

- [Pagina publica do e-CAC](https://www.gov.br/receitafederal/pt-br/canais_atendimento/atendimento-virtual)
- [Portal e-CAC](https://cav.receita.fazenda.gov.br/)
- [Como acessar com gov.br](https://www.gov.br/receitafederal/pt-br/canais_atendimento/atendimento-virtual/acesso-govbr)

Base oficial confirmada hoje, 9 de agosto de 2026:

- a pagina publica do e-CAC foi atualizada em 25 de maio de 2026;
- a pagina "Como acessar" informa que o acesso pode ser feito com
  certificado digital e que alguns servicos ainda estao restritos a
  certificado digital;
- a pagina "Como acessar" tambem informa que o e-CAC nao esta adaptado
  para login por QR Code.

Objetivo do teste:

- medir se o modelo consegue navegar ate o portal correto;
- acionar o fluxo de autenticacao adequado;
- lidar com o contexto de portal real autenticado;
- chegar ao estado logado e retornar com logout limpo.

Escopo permitido por padrao:

1. abrir a pagina publica do e-CAC;
2. localizar e abrir o portal correto;
3. selecionar a forma de acesso apropriada;
4. concluir o acesso com certificado digital existente;
5. confirmar que a home autenticada foi alcancada;
6. navegar apenas em secoes informacionais ou catalogos sem efeito
   transacional;
7. encerrar sessao com logout.

Tarefas iniciais permitidas:

1. `C1-Acesso`
   Objetivo: sair da pagina publica e chegar ao estado autenticado no
   e-CAC com certificado digital existente.
   Validacao:
   - URL final em dominio esperado;
   - presenca de elemento exclusivo do estado autenticado;
   - ausencia de erro de permissao ou login.

2. `C1-Catalogo`
   Objetivo: a partir da home autenticada, localizar uma area segura de
   catalogo, menu ou servicos e abrir essa area sem executar acao com
   efeito real.
   Validacao:
   - pagina alvo carregada;
   - titulo/rotulo esperado visivel;
   - nenhuma submissao, protocolo ou confirmacao executada.

3. `C1-Logout`
   Objetivo: encerrar a sessao corretamente.
   Validacao:
   - retorno para tela de login ou logout bem-sucedido;
   - evidencia observavel de sessao encerrada.

Tarefas desabilitadas por padrao:

- abrir caixa postal com dados reais;
- consultar pendencias reais;
- abrir dados fiscais especificos;
- navegar em servicos que possam produzir efeito juridico ou financeiro.

Essas tarefas so podem ser habilitadas depois de revisao explicita de
risco e com criterio de minimizacao de exposicao de dados.

## Regras de implementacao para Suite C

- Preferir Chrome ou browser com suporte comprovado ao certificado ja
  instalado no ambiente do usuario.
- Tratar prompts de certificado como parte da instrumentacao do teste.
- Registrar em log quando a falha ocorrer antes do modelo atuar, por
  exemplo por indisponibilidade do certificado.
- Nao persistir em artefatos o conteudo sensivel lido em tela.
- Redigir screenshots ou metadados se contiverem identificadores
  pessoais ou fiscais.

## Como os resultados externos serao reportados

Cada run externa deve registrar:

- suite;
- URL inicial;
- URL final;
- tarefa;
- sucesso;
- motivo de falha;
- classificacao da falha;
- observacoes sobre estabilidade do site;
- observacoes sobre autenticacao, quando aplicavel.

Os resultados devem sair separados por:

- `Suite B - externa publica`
- `Suite C - externa autenticada e sensivel`
