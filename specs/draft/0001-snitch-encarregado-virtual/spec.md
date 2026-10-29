# Especificação integrada: SNITCH — Encarregado Virtual

| Campo | Valor |
| --- | --- |
| Formato | Specsfy/2.0 |
| ID | SPEC-0001 |
| Slug | 0001-snitch-encarregado-virtual |
| Status | Implementing |
| Effort | 7 |
| Effort updated at | 2026-10-29 |
| Effort rationale | Épico inteiro: motor, painel, EPI, ociosidade, avisos e histórico. |
| ClickUp Task | |
| Milestones | |
| Definition Gate | Passed |
| Plan Gate | Passed |
| Delivery Gate | In Progress |
| Evidence Contract | 1 |
| Interface para pessoas | Sim |
| Atualizada em | 2026-10-29 |

## Ato I — Definir

### 1. Problema e resultado

#### Problema

Fiscalização presencial desgastante, sem evidência estatística imparcial de EPI e ociosidade.

#### Resultado desejado

Gestores e admins veem, por empresa e localidade, conformidade, ociosidade, foto do momento e avisos. A análise roda na VPS da empresa.

#### Métricas de sucesso

- Cada episódio de EPI ou ociosidade guarda foto, data e hora no registro do funcionário.
- O painel global mostra totais do dia e do mês sem o nome do colaborador.
- A câmera aberta mostra a imagem com caixas e não cria registro extra.

### 2. Research e esclarecimentos

#### Researchs executados

- **R-001**: YOLO e supervision entregam quadro a quadro, não um vídeo pronto. O Python monta a imagem com caixas. Impacto: o ao vivo é SSE com essa imagem.
- **R-002**: Jev responde um POST com estado em JSON. Não é o motor do vídeo. Impacto: a decisão usa o estado, não a imagem de cada quadro.

#### Fontes e contexto consultados

- specs/inbox/2026-10-27-131239-snitch-encarregado-virtual-com-visao-computacional.md
- specs/backlog/0001-snitch-encarregado-virtual.md
- .specsfy/DATABASE.md

#### Documentação consultada

- Ultralytics Predict, modo stream em RTSP, consultado em 28/10/2026.
- Supervision, rastreio e anotação de quadros, consultado em 28/10/2026.
- Jev Decide, POST com estado JSON, consultado em 28/10/2026.

#### Artefatos de pesquisa armazenados

- Nenhum artefato externo copiado. As conclusões normativas estão nesta spec.

#### Dúvidas respondidas

- **Q**: Onde a análise roda? → **A**: Na VPS da empresa, junto do painel. A câmera só entrega o fluxo.
- **Q**: Como o painel vê o ao vivo? → **A**: SSE. O Python envia a imagem já com as caixas.
- **Q**: Onde ficam os registros e a foto? → **A**: PostgreSQL na mesma VPS. A foto fica no registro do funcionário.

#### Dúvidas abertas

- O peso do ajuste fino do modelo para detectar celular ainda não tem número.
- Levar o mesmo rastreio do funcionário para outra localidade ainda será testado.

### 3. Escopo e atores

#### Incluído

- Motor YOLO com SH17, supervision para trilha e zona, Jev para a decisão.
- Painel Laravel e análise Python na VPS de cada empresa.
- EPI, ociosidade de zona de passagem, smartphone, avisos, histórico e foto.
- Painel global e painel da localidade.

#### Fora de escopo

- Nada da primeira entrega ficou de fora do épico.
- A imagem de conceito enviada no chat não é layout a copiar.

#### Atores

- **Admin**: alcança a empresa inteira e apaga zona, câmera ou localidade.
- **Gestor**: vê o histórico e muda zona, câmera e aviso só na localidade dele.
- **Colaborador**: é único na empresa. O registro diz onde ele estava. Não vê o próprio histórico.

### 4. Princípios e restrições do projeto

- **PR-001**: A análise e o painel ficam na VPS da empresa. A câmera só entrega o fluxo.
- **PR-002**: Abrir a câmera não cria registro. O registro nasce quando uma regra configurada estoura.
- **PR-003**: Mudar a regra do smartphone vale só para a frente. O passado fica marcado com a regra anterior.

### 5. Histórias de usuário

#### US-001 — Prova de EPI e ociosidade (P1)

Como gestor, quero a foto, a data e a hora no registro do funcionário quando uma regra estoura, para ter prova do momento.

**Por que P1**: é o resultado que substitui a fiscalização presencial.
**Teste independente**: um EPI faltante gera um registro com foto.
**Requisitos**: FR-001, FR-002, FR-003

#### US-002 — Câmera ao vivo (P1)

Como gestor, quero abrir a câmera e ver a imagem já com as caixas, para conferir o instante sem criar outro registro.

**Por que P1**: o painel precisa mostrar o que o motor já está vendo.
**Teste independente**: abrir a câmera mostra a imagem e o banco não ganha registro só por isso.
**Requisitos**: FR-004

### 6. Cenários BDD de aceite

#### AC-001 — EPI faltante

**Cobre**: US-001, FR-001

```gherkin
Feature: Registro de EPI

  Scenario: Falta um EPI obrigatório
    Given um colaborador já ligado a uma trilha
    And a localidade marca esse EPI como obrigatório
    When o EPI falta
    Then o sistema guarda a foto, a data e a hora no registro dele
```

#### AC-002 — Zona de passagem

**Cobre**: US-001, FR-002

```gherkin
Feature: Ociosidade na zona

  Scenario: Tempo máximo da zona de passagem
    Given um colaborador numa zona de passagem
    When o tempo máximo estoura
    Then conta como ociosidade e guarda a foto no registro dele
```

#### AC-003 — Smartphone

**Cobre**: US-001, FR-003

```gherkin
Feature: Ociosidade por smartphone

  Scenario: Celular na mão depois do limite
    Given o smartphone ligado na localidade
    When o tempo na mão estoura o limite
    Then cada minuto conta como um minuto de ociosidade
    And a foto fica no registro dele
```

#### AC-004 — Câmera aberta

**Cobre**: US-002, FR-004

```gherkin
Feature: Ao vivo

  Scenario: Abrir a câmera não cria registro
    Given o gestor com a câmera aberta
    When o Python envia a imagem já com as caixas
    Then o painel mostra essa imagem
    And nenhum registro extra nasce só por a câmera estar aberta
```

#### AC-006 — EPI não marcado

**Cobre**: US-001, FR-001

```gherkin
Feature: Registro de EPI

  Scenario: EPI não obrigatório não gera registro
    Given um EPI que a localidade não marcou
    When ele falta na imagem
    Then nenhum registro de inconformidade nasce
```

#### AC-007 — Pessoa sem vínculo

**Cobre**: US-001, FR-001, US-002

```gherkin
Feature: Registro de EPI

  Scenario: Trilha ainda não ligada
    Given uma pessoa na câmera sem vínculo confirmado pelo gestor
    When falta um EPI obrigatório
    Then a imagem ao vivo mostra a caixa
    And o registro não entra no histórico de um funcionário
```

#### AC-008 — Zona que não é passagem

**Cobre**: US-001, FR-002

```gherkin
Feature: Ociosidade na zona

  Scenario: Permanência fora da zona de passagem
    Given uma zona que não é do tipo passagem
    When o tempo máximo estoura
    Then não nasce registro de ociosidade por essa zona
```

#### AC-009 — Zona sem tempo

**Cobre**: US-001, FR-002

```gherkin
Feature: Ociosidade na zona

  Scenario: Zona de passagem sem tempo máximo
    Given uma zona de passagem sem tempo máximo
    When alguém permanece nela
    Then não nasce registro de ociosidade
```

#### AC-010 — Smartphone desligado

**Cobre**: US-001, FR-003

```gherkin
Feature: Ociosidade por smartphone

  Scenario: Modalidade desligada
    Given o smartphone desligado na localidade
    When o celular fica na mão
    Then não conta ociosidade de smartphone
```

#### AC-011 — Smartphone antes do limite

**Cobre**: US-001, FR-003

```gherkin
Feature: Ociosidade por smartphone

  Scenario: Ainda dentro do limite
    Given o smartphone ligado
    When o tempo na mão ainda não estourou o limite
    Then não nasce registro
```

#### AC-012 — SSE interrompido

**Cobre**: US-002, FR-004

```gherkin
Feature: Ao vivo

  Scenario: O envio da imagem para
    Given a câmera aberta
    When o SSE interrompe
    Then o painel mostra erro
    And o registro já gravado permanece
```

#### AC-013 — Câmera sem fluxo

**Cobre**: US-002, FR-004

```gherkin
Feature: Ao vivo

  Scenario: Localidade sem câmera
    Given uma localidade sem câmera
    When o gestor abre a localidade
    Then a lista de câmeras fica vazia
```

#### AC-014 — Aviso só no painel

**Cobre**: US-001, FR-005

```gherkin
Feature: Aviso

  Scenario: Nenhum canal extra ligado
    Given um registro de EPI
    And nenhum canal extra ligado para esse tipo
    When o registro nasce
    Then ele aparece no painel ao vivo
    And não sai por WhatsApp, Telegram, SMS ou e-mail
```

#### AC-015 — Aviso de outro tipo

**Cobre**: US-001, FR-005

```gherkin
Feature: Aviso

  Scenario: Canal ligado para outro tipo
    Given o WhatsApp ligado só para ociosidade
    When nasce um registro de EPI
    Then o EPI aparece no painel
    And o WhatsApp não recebe esse EPI
```

#### AC-016 — VPS da empresa

**Cobre**: NFR-001

```gherkin
Feature: Isolamento da empresa

  Scenario: Dados na VPS da empresa
    Given duas empresas
    When cada uma grava um registro
    Then o registro fica no PostgreSQL da VPS daquela empresa
```

#### AC-017 — Análise na mesma VPS

**Cobre**: NFR-001

```gherkin
Feature: Isolamento da empresa

  Scenario: Análise e painel juntos
    Given a VPS de uma empresa
    When a câmera entrega o fluxo
    Then Python e Laravel dessa empresa processam o fluxo
```

#### AC-018 — Outra empresa

**Cobre**: NFR-001

```gherkin
Feature: Isolamento da empresa

  Scenario: Gestor não vê outra empresa
    Given um gestor de uma empresa
    When ele abre o painel
    Then não vê registros de outra empresa
```

#### AC-019 — Credencial fora do histórico

**Cobre**: NFR-002

```gherkin
Feature: Credencial

  Scenario: Histórico sem credencial
    Given um registro no funcionário
    When o gestor abre esse registro
    Then a credencial da câmera não aparece
```

#### AC-020 — Credencial some com a câmera

**Cobre**: NFR-002

```gherkin
Feature: Credencial

  Scenario: Admin apaga a câmera
    Given uma câmera com credencial
    When o admin apaga a câmera
    Then a credencial sai
    And o histórico de EPI permanece
```

#### AC-021 — Credencial de DVR

**Cobre**: NFR-002

```gherkin
Feature: Credencial

  Scenario: Câmera de DVR
    Given uma câmera ligada a um DVR
    When o gestor vê o histórico do funcionário
    Then a credencial do DVR não aparece nesse histórico
```

#### AC-005 — Aviso

**Cobre**: US-001, FR-005

```gherkin
Feature: Aviso

  Scenario: Registro nasce e o aviso sai
    Given um registro de EPI ou ociosidade
    When ele nasce
    Then aparece no painel ao vivo
    And sai também pelos canais que o gestor ligou para esse tipo
```

### 7. Requisitos

#### Funcionais

- **FR-001**: O sistema deve guardar foto, data e hora no registro do funcionário quando falta um EPI marcado na localidade.
- **FR-002**: O sistema deve contar ociosidade e guardar a foto quando o tempo máximo de uma zona de passagem estoura.
- **FR-003**: Se o smartphone estiver ligado, o sistema deve contar um minuto de ociosidade por minuto depois do limite.
- **FR-004**: O painel deve mostrar por SSE a imagem já com as caixas, sem criar registro só por a câmera estar aberta.
- **FR-005**: Um registro de EPI ou ociosidade deve aparecer no painel ao vivo e nos canais extras ligados para esse tipo.

#### Não funcionais

- **NFR-001**: Cada empresa tem a própria VPS, com Laravel, Python e PostgreSQL. **Verificação**: inspeção do ambiente da empresa.
- **NFR-002**: A credencial da câmera não aparece no histórico do colaborador. **Verificação**: inspeção do registro do funcionário.

#### Erros e casos-limite

- Zona ou smartphone sem configuração → essa parte não gera registro.
- Admin apaga zona, câmera ou localidade → o histórico de EPI e ociosidade permanece.
- Obstrução, inconclusivo e erro → ficam só nos logs, não no histórico do colaborador.

## Ato II — Projetar e provar

### 8. Plano técnico

#### Contexto existente

- O repositório atual ainda não contém o SNITCH. A stack decidida é Laravel, Python, PostgreSQL e SSE.

#### Arquitetura e módulos

- Python lê o fluxo, roda YOLO e supervision, desenha as caixas e envia a imagem por SSE.
- Jev recebe o estado em JSON, não a imagem de cada quadro.
- Laravel exibe o painel e grava os registros no PostgreSQL da mesma VPS.

#### Migrations

- [Mudança de schema, ordem, rollback e compatibilidade ou “Não aplicável”.]

#### Models

- [Model, responsabilidade, invariantes e arquivo.]

#### Controllers e casos de uso

- [Controller/handler/use case, entrada, saída, autorização e arquivo.]

#### Views e experiência

- [Tela/componente, estados loading/empty/error/success, acessibilidade e arquivo.]

#### Queries e repositórios

- [Query/repository, filtros, paginação, índices, consistência e arquivo.]

#### Jobs e processamento assíncrono

- [Job/event consumer, retry, idempotência e dead-letter ou “Não aplicável”.]

#### Estrutura de arquivos

```text
specs/draft/0001-snitch-encarregado-virtual/
  spec.md
  research/
src/
tests/
```

### 9. Modelo de dados

#### Entidades

| Entidade | Identidade | Atributos e regras | Relações |
| --- | --- | --- | --- |
| [Entidade] | [chave] | [campos, validações] | [cardinalidade] |

#### Estados e transições

| Entidade | Estado atual | Evento | Próximo estado | Invariantes |
| --- | --- | --- | --- | --- |
| [Entidade] | [estado] | [evento] | [estado] | [regra] |

#### Migração e retenção

- [Estratégia ou “Não aplicável”.]

### 10. Interfaces e contratos

#### Interface para pessoas

- **Há interface para pessoas**: Sim. Gestores e admins usam o painel no navegador.

#### Stack e convenções de interface

- Laravel no navegador. A imagem ao vivo chega por SSE, já com as caixas feitas pelo Python. A imagem de conceito enviada no chat não é layout a copiar. Não há telas anteriores neste repositório.

#### Telas e responsabilidades

- **Painel global**: gestor vê totais do dia e do mês, a lista de localidades e episódios de EPI e ociosidade sem o nome.
- **Painel da localidade**: gestor vê câmeras, totais, episódios com colaborador e o quadro de funcionários.
- **Câmera expandida**: gestor vê a imagem ao vivo com caixas. Não cria registro.
- **Painel do funcionário**: gestor vê média do dia e do mês, foto, anexos e histórico.

#### Fluxo de informação e navegação

- O gestor entra na empresa, abre uma localidade e, de lá, uma câmera ou um funcionário.
- Breadcrumb: empresa, localidade, tela atual.

#### Menus e navegação principal

- Menu principal, item Painel global, destino a visão da empresa.
- Menu principal, item Localidades, destino a lista de localidades.
- Menu da localidade, itens Câmeras, Episódios e Funcionários, cada um com o próprio destino.
- Admin vê a empresa inteira. Gestor não abre o menu de outra localidade.

#### Formulários e ações

- Zona: nome, tipo (descanso, passagem ou risco), tempo máximo e desenho na câmera.
- Câmera: nome, setor, endereço do fluxo, endereço da câmera e credencial.
- Conformidade: escolha das categorias por localidade.
- Smartphone: sim ou não, mais a duração do limite.
- Aviso: canais extras e o tipo. O painel ao vivo é sempre o canal padrão.

#### Composição e disposição

- O painel global fica no topo da empresa. A localidade abre em seguida. A câmera expandida ocupa a área principal quando o gestor clica nela.
- Breadcrumb: empresa, localidade, tela atual.
- Laravel sem React nesta versão. Octane não foi decidido.

#### Blocos React e componentes selecionados

| Tela | Bloco React | Responsabilidade | Arquivo previsto | Componente ou composição | Origem | Reuso ou extensão |
| --- | --- | --- | --- | --- | --- |
| Painel | Nenhum bloco React | O painel é Laravel | A definir na implementação | Página Laravel | Próprio | Sem React nesta versão |

- Não há shadcn/ui nem ReUI. A interface confirmada é Laravel.

#### Estados e acessibilidade

- Sem câmera, a localidade mostra a lista vazia. Se o SSE cair, a câmera mostra erro e o registro já gravado permanece.
- Gestor sem permissão não abre outra localidade. O breadcrumb liga os itens anteriores e marca a tela atual.

#### Contrato CRUD

- [Quando houver CRUD, todas as telas usam o mesmo `PageHeader` componentizado
  e reutilizável para lista, detalhe, criação e edição.]
- [A listagem usa `DataGrid` em largura total, mantém a coluna `ID` visível,
  transforma a linha inteira em link para o detalhe e oferece botões
  independentes de editar e apagar.]
- [Registre em `INTERFACE.md` os componentes reaproveitados e os novos, com
  seus consumidores, estados e regra de extensão.]

#### Revisão visual durante o desenvolvimento

- [A revisão visual ocorre durante a implementação, mesmo sem pedido da
  pessoa, e confere bordas, espaçamentos, margens, padding e tipografia do
  sistema nos estados e viewports relevantes.]
- [Registre método, viewport, estados, achados e ajustes na tarefa. Para uma
  tarefa sem interface, registre `Não aplicável` e o motivo concreto.]

#### APIs expostas

- [Método/rota ou evento, autenticação, request, response, erros e versionamento.]

#### APIs externas utilizadas

- [Serviço, operação, versão, autenticação, timeout, retry e fallback ou “Nenhuma”.]

#### Documentação das APIs consultadas

- [Título, versão/data, URL ou caminho local e decisões extraídas.]

#### Eventos e outros contratos

- [Schema, produtor, consumidor, compatibilidade ou “Não aplicável”.]

### 11. Estratégia TDD

- **Unidade**: [regras e componentes].
- **Integração/contrato**: [fronteiras].
- **BDD/aceite**: [Gherkin de referência que orienta o entendimento e o desenho dos testes TDD].
- **Runner TDD**: [PHP = Pest; Node = decisão confirmada com o usuário e
  materializada em `test:tdd`; outra stack = runner existente ou decisão explícita].
- **E2E**: [jornadas essenciais ou “Não aplicável”.]
- **Verificação manual**: [somente o inevitável, com motivo].

#### Evidência RED-GREEN-REFACTOR

| IDs | BDD de referência | Teste TDD informado pelo BDD | RED observado | GREEN observado | Refactor/regressão |
| --- | --- | --- | --- | --- | --- |
| US-001, FR-001, AC-001 | AC-001 na seção 6 | snitch/tests/Feature/Snitch/Ac001Test.php com SPECSFY: US-001 FR-001 AC-001 | RED: 404 em vez de 201. php artisan test --env=testing --filter=Ac001 | Pending | Pending |
| US-001, FR-001, NFR-001, AC-002 | [AC-002 na seção 6] | [caso 2 em tests/Feature/RecursoTest.php com marcador próprio `SPECSFY:`] | Pending | Pending | Pending |
| US-001, FR-001, NFR-001, AC-003 | [AC-003 na seção 6] | [caso 3 em tests/Feature/RecursoTest.php com marcador próprio `SPECSFY:`] | Pending | Pending | Pending |

### 12. Plano de testes e rastreabilidade

| Requisito | Cenário BDD | Nível | Arquivo/comando esperado | Evidência |
| --- | --- | --- | --- | --- |
| FR-001 | AC-001 | Unidade | [tests/arquivo] | Pending |
| FR-001 | AC-002 | [nível] | [tests/arquivo] | Pending |
| FR-001 | AC-003 | [nível] | [tests/arquivo] | Pending |
| NFR-001 | AC-001 | [nível] | [comando] | Pending |
| NFR-001 | AC-002 | [nível] | [comando] | Pending |
| NFR-001 | AC-003 | [nível] | [comando] | Pending |

### 13. Validações

#### Gate do Ato I — Definição

- **Resultado**: READY
- **Data**: 2026-10-28
- **Comando**: `node .agents/skills/specsfy-04-validate/scripts/validate_spec.mjs specs/draft/0001-snitch-encarregado-virtual/spec.md`
- **Achados**: Cobertura de 3 AC por US, FR e NFR preenchida. Interface da seção 10 descrita. WARNING — o peso do ajuste fino do celular continua sem número.
- Findings especializados, quando aplicáveis, seguem `FIND-PROD|ARCH|SEC-NNN`,
  severidade `P1|P2|P3`, estado `Open|Resolved|Accepted`, refs e evidência.

#### Gate do Ato II — Plano

- **Resultado**: READY
- **Data**: 2026-10-28
- **Comando**: `node .agents/skills/specsfy-05-tasks/scripts/validate_tasks.mjs specs/draft/0001-snitch-encarregado-virtual/spec.md`
- **Achados**: Predecessores TDD das tarefas de código em RED. Os demais testes da seção 14 continuam abertos e não bloqueiam o código.

#### Gate do Ato III — Entrega

- **Resultado**: Pending
- **Comando**: `node .agents/skills/specsfy-06-tdd-bdd/scripts/check_traceability.mjs specs/draft/0001-snitch-encarregado-virtual/spec.md .`
- **Achados**: [Pending.]

### 14. Tarefas

#### Fase 1 — RED TDD informado pelo BDD

- [x] T001 [TEST] [TDD] [US-001] Derivar do AC-001 um caso Pest falhando em tests/Feature/Snitch/Ac001Test.php — Refs: US-001, FR-001, AC-001 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac001 tests/Feature/Snitch/Ac001Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Nenhuma melhoria no teste: a falha já é a rota ausente.


- [x] T002 [TEST] [TDD] [US-001] Derivar do AC-002 um caso Pest falhando em tests/Feature/Snitch/Ac002Test.php — Refs: US-001, FR-002, AC-002 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac002 tests/Feature/Snitch/Ac002Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T003 [TEST] [TDD] [US-001] Derivar do AC-003 um caso Pest falhando em tests/Feature/Snitch/Ac003Test.php — Refs: US-001, FR-003, AC-003 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac003 tests/Feature/Snitch/Ac003Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T004 [TEST] [TDD] [US-002] Derivar do AC-004 um caso Pest falhando em tests/Feature/Snitch/Ac004Test.php — Refs: US-002, FR-004, AC-004 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac004 tests/Feature/Snitch/Ac004Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T005 [TEST] [TDD] [US-001] Derivar do AC-005 um caso Pest falhando em tests/Feature/Snitch/Ac005Test.php — Refs: US-001, FR-005, AC-005 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac005 tests/Feature/Snitch/Ac005Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T006 [TEST] [TDD] [US-001] Derivar do AC-006 um caso Pest falhando em tests/Feature/Snitch/Ac006Test.php — Refs: US-001, FR-001, AC-006 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac006 tests/Feature/Snitch/Ac006Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T007 [TEST] [TDD] [US-001] Derivar do AC-007 um caso Pest falhando em tests/Feature/Snitch/Ac007Test.php — Refs: US-001, FR-001, US-002, AC-007 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac007 tests/Feature/Snitch/Ac007Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T008 [TEST] [TDD] [US-001] Derivar do AC-008 um caso Pest falhando em tests/Feature/Snitch/Ac008Test.php — Refs: US-001, FR-002, AC-008 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac008 tests/Feature/Snitch/Ac008Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T009 [TEST] [TDD] [US-001] Derivar do AC-009 um caso Pest falhando em tests/Feature/Snitch/Ac009Test.php — Refs: US-001, FR-002, AC-009 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac009 tests/Feature/Snitch/Ac009Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T010 [TEST] [TDD] [US-001] Derivar do AC-010 um caso Pest falhando em tests/Feature/Snitch/Ac010Test.php — Refs: US-001, FR-003, AC-010 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac010 tests/Feature/Snitch/Ac010Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T011 [TEST] [TDD] [US-001] Derivar do AC-011 um caso Pest falhando em tests/Feature/Snitch/Ac011Test.php — Refs: US-001, FR-003, AC-011 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac011 tests/Feature/Snitch/Ac011Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T012 [TEST] [TDD] [US-002] Derivar do AC-012 um caso Pest falhando em tests/Feature/Snitch/Ac012Test.php — Refs: US-002, FR-004, AC-012 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac012 tests/Feature/Snitch/Ac012Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T013 [TEST] [TDD] [US-002] Derivar do AC-013 um caso Pest falhando em tests/Feature/Snitch/Ac013Test.php — Refs: US-002, FR-004, AC-013 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac013 tests/Feature/Snitch/Ac013Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T014 [TEST] [TDD] [US-001] Derivar do AC-014 um caso Pest falhando em tests/Feature/Snitch/Ac014Test.php — Refs: US-001, FR-005, AC-014 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac014 tests/Feature/Snitch/Ac014Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [x] T015 [TEST] [TDD] [US-001] Derivar do AC-015 um caso Pest falhando em tests/Feature/Snitch/Ac015Test.php — Refs: US-001, FR-005, AC-015 — Depends: none
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Rodar php artisan test --filter=Ac015 tests/Feature/Snitch/Ac015Test.php e observar RED.
  - [x] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [x] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [x] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T016 [TEST] [TDD] [US-001] Derivar do AC-016 um caso Pest falhando em tests/Feature/Snitch/Ac016Test.php — Refs: NFR-001, AC-016 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac016 tests/Feature/Snitch/Ac016Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T017 [TEST] [TDD] [US-001] Derivar do AC-017 um caso Pest falhando em tests/Feature/Snitch/Ac017Test.php — Refs: NFR-001, AC-017 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac017 tests/Feature/Snitch/Ac017Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T018 [TEST] [TDD] [US-001] Derivar do AC-018 um caso Pest falhando em tests/Feature/Snitch/Ac018Test.php — Refs: NFR-001, AC-018 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac018 tests/Feature/Snitch/Ac018Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T019 [TEST] [TDD] [US-001] Derivar do AC-019 um caso Pest falhando em tests/Feature/Snitch/Ac019Test.php — Refs: NFR-002, AC-019 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac019 tests/Feature/Snitch/Ac019Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T020 [TEST] [TDD] [US-001] Derivar do AC-020 um caso Pest falhando em tests/Feature/Snitch/Ac020Test.php — Refs: NFR-002, AC-020 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac020 tests/Feature/Snitch/Ac020Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T021 [TEST] [TDD] [US-001] Derivar do AC-021 um caso Pest falhando em tests/Feature/Snitch/Ac021Test.php — Refs: NFR-002, AC-021 — Depends: none
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac021 tests/Feature/Snitch/Ac021Test.php e observar RED.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só materializa teste.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


#### Fase 2 — Fundação

- [ ] T022 [CODE] [MIGRATION] [US-001] Criar tabelas do SNITCH em database/migrations/2026_10_28_000001_create_snitch_tables.php — Refs: US-001, FR-001, AC-001 — Depends: T001, T006, T007
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Aplicar php artisan migrate --env=testing e consultar php artisan migrate:status --env=testing.
  - [ ] **VISUAL**: Não aplicável porque a tarefa altera somente a estrutura persistente.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T023 [CODE] [US-001] Analisar o fluxo e desenhar as caixas em engine/analyze_stream.py — Refs: US-001, FR-001, FR-002, FR-003, AC-001 — Depends: T001, T002, T003
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar o teste Pest do AC-001 e observar o comportamento do motor.
  - [ ] **VISUAL**: Não aplicável porque a tarefa não tem tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T024 [CODE] [US-001] Gravar foto, data e hora no registro em app/Services/EpisodeRecorder.php — Refs: US-001, FR-001, FR-005, AC-001, AC-005 — Depends: T022, T001, T005, T014
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac001 tests/Feature/Snitch/Ac001Test.php.
  - [ ] **VISUAL**: Não aplicável porque a tarefa grava registro sem tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T025 [CODE] [US-002] Enviar a imagem com caixas por SSE em app/Http/Controllers/LiveCameraController.php — Refs: US-002, FR-004, AC-004 — Depends: T023, T004, T012, T013
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Rodar php artisan test --filter=Ac004 tests/Feature/Snitch/Ac004Test.php.
  - [ ] **VISUAL**: Não aplicável porque a tarefa só publica o fluxo.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


#### Fase de interface

- [ ] T026 [CODE] [US-001] Implementar a tela painel global em resources/views/company/dashboard.blade.php e registrar o bloco em INTERFACE.md — Refs: US-001, FR-005, AC-005 — Depends: T024, T005, T014, T015
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Abrir a tela e conferir navegação, formulário e erro.
  - [ ] **VISUAL**: Conferir bordas, espaçamentos, margens, padding e tipografia do sistema nesta tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T027 [CODE] [US-001] Implementar a tela painel da localidade em resources/views/locations/show.blade.php e registrar o bloco em INTERFACE.md — Refs: US-001, FR-001, AC-001 — Depends: T024, T001, T006, T007
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Abrir a tela e conferir navegação, formulário e erro.
  - [ ] **VISUAL**: Conferir bordas, espaçamentos, margens, padding e tipografia do sistema nesta tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T028 [CODE] [US-001] Implementar a tela câmera expandida em resources/views/cameras/live.blade.php e registrar o bloco em INTERFACE.md — Refs: US-002, FR-004, AC-004 — Depends: T024, T004, T012, T013
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Abrir a tela e conferir navegação, formulário e erro.
  - [ ] **VISUAL**: Conferir bordas, espaçamentos, margens, padding e tipografia do sistema nesta tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


- [ ] T029 [CODE] [US-001] Implementar a tela painel do funcionário em resources/views/employees/show.blade.php e registrar o bloco em INTERFACE.md — Refs: US-001, FR-001, AC-001 — Depends: T024, T001, T006, T007
  - [ ] **PREP**: Confirmar escopo, IDs e dependências.
  - [ ] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [ ] **VERIFY**: Abrir a tela e conferir navegação, formulário e erro.
  - [ ] **VISUAL**: Conferir bordas, espaçamentos, margens, padding e tipografia do sistema nesta tela.
  - [ ] **EVIDENCE**: Registrar comando, resultado e IDs.
  - [ ] **IMPROVE**: Registrar melhoria aplicada ou justificar nenhuma.


#### Fechamento

- [x] T030 [DOC] Registrar a mudança em .specsfy/STACK.md — Refs: US-001, NFR-001, AC-016 — Depends: T022
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Conferir que STACK.md descreve a decisão desta spec.
  - [x] **VISUAL**: Não aplicável porque a tarefa só atualiza documentação.
  - [x] **EVIDENCE**: `monitor_context.mjs --check` CURRENT; `build_documentation.mjs --check` ok; STACK.md revisado 2026-10-29 (sync parcial: T022 pendente).
  - [x] **IMPROVE**: Nenhuma: hub CodeNotch + SNITCH explicitado na mesma STACK.


- [x] T031 [DOC] Registrar a mudança em .specsfy/DATABASE.md — Refs: US-001, FR-001, AC-001 — Depends: T022
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Conferir que DATABASE.md descreve a decisão desta spec.
  - [x] **VISUAL**: Não aplicável porque a tarefa só atualiza documentação.
  - [x] **EVIDENCE**: PostgreSQL normativo + SQLite teste documentados; entidades alvo até T022; migrations default inventariadas.
  - [x] **IMPROVE**: Nenhuma: seção “domínio normativo” separada do inventário detectado.


- [x] T032 [DOC] Registrar a mudança em .specsfy/RULES.md — Refs: US-001, FR-003, AC-003 — Depends: T022
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Conferir que RULES.md descreve a decisão desta spec.
  - [x] **VISUAL**: Não aplicável porque a tarefa só atualiza documentação.
  - [x] **EVIDENCE**: PR-001–003, FR-003, NFR-002 e papéis registrados em `.specsfy/RULES.md`.
  - [x] **IMPROVE**: Nenhuma melhoria necessária.


- [x] T033 [DOC] Registrar a mudança em PROJECT.md — Refs: US-001, FR-001, AC-001 — Depends: T022
  - [x] **PREP**: Confirmar escopo, IDs e dependências.
  - [x] **EXECUTE**: Produzir a entrega no caminho declarado.
  - [x] **VERIFY**: Conferir que PROJECT.md descreve a decisão desta spec.
  - [x] **VISUAL**: Não aplicável porque a tarefa só atualiza documentação.
  - [x] **EVIDENCE**: `PROJECT.md` descreve SNITCH vs CodeNotch e estado de implementação.
  - [x] **IMPROVE**: Nenhuma melhoria necessária.


### 15. Ordem de execução

1. Testes TDD T001–T021, em paralelo quando não compartilham arquivo.
2. T022 depois de T001.
3. T023 e T024 depois da fundação.
4. T025 depois de T023.
5. Telas T026, T027, T028, T029 depois de T024.
6. Documentação de stack, banco, regras e projeto por último.
### 16. Dependências, riscos e suposições

#### Dependências

- [Dependência ou “Nenhuma”.]

#### Riscos

- [Risco] → [mitigação].

#### Suposições

- [Default assumido.]

### 17. Decisões

- **DEC-001**: [decisão] — [razão, alternativas e trade-off].

### 18. Definition of Done

- [ ] `Definition Gate` está `Passed`.
- [ ] `Plan Gate` está `Passed`.
- [ ] `Delivery Gate` está `Passed`.
- [ ] Todos os cenários `AC` aplicáveis passam.
- [ ] Todos os requisitos possuem evidência de verificação.
- [ ] Todas as tarefas na seção 14 estão concluídas.
- [ ] Testes e checks estáticos disponíveis passam.
