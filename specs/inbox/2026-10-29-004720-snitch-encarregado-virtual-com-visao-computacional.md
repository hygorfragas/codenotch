# Inbox: SNITCH — Encarregado Virtual com visão computacional

| Metadado | Valor |
| --- | --- |
| Status | Capturada |
| Capturada em | 2026-10-29T00:47:20Z |
| Slug | snitch-encarregado-virtual-com-visao-computacional |
| Origem | Input do usuário |
| Processamento | Análise inicial sem perguntas |
| Sessão de descoberta | Captura avulsa. |
| Turno da conversa | Não se aplica. |
| Integridade do original | SHA-256 `0a7f792318007e7d128d154aaf092c3c66b79bbc9b139b6cd337ed4e628bc11b` |
| Backlog derivado | Nenhum |
| Spec derivada | Nenhuma |

## Texto original

conceito inicial da ideia: O **SNITCH** é uma plataforma de inteligência operacional baseada em visão computacional projetada para atuar como um **"Encarregado Virtual"** em canteiros de obras, plantas industriais e empresas[1]. O objetivo central do produto é converter o fluxo contínuo de câmeras de segurança (RTSP/DVR) em dados estatísticos **determinísticos, imparciais e auditáveis** sobre **segurança do trabalho (EPIs)** e **produtividade (tempo de ociosidade)**[1].

Em vez de depender da fiscalização presencial desgastante ou do atrito frequente entre encarregados e trabalhadores, o SNITCH fornece relatórios estatísticos frios que respaldam decisões gerenciais, inibem comportamentos de risco e protegem a empresa juridicamente[1][6].

---

### **A Evolução da Ideia: Do Rascunho Inicial à Arquitetura do MVP**

1. **Premissa Original do Rascunho:**
  * A ideia inicial considerava tirar *screenshots* das regiões detectadas a cada intervalo de quadros para enviá-los a APIs externas com prompts de texto dinâmicos[3].
  * **Gargalo identificado:** Tirar *screenshots* e depender de chamadas de API externas para análise de imagem causaria latência e custos computacionais inviáveis para streams de vídeo ao vivo (30 a 60 FPS)[3].
2. **Arquitetura Determinística Escolhida:**
  * **Processamento Local em VPS:** A análise de vídeo roda em um container/VPS local, eliminando o envio contínuo de capturas de tela para serviços de imagem externos[3].
  * **Motor de Detecção Visual (YOLO + SH17):** Utiliza modelos pré-treinados e especializados com a base **SH17**, garantindo alta precisão na detecção do sexteto de segurança e em itens pequenos como **luvas, botinas e protetores auriculares**[9].
  * **Rastreamento e Geometria (** **supervision** **):** O algoritmo `ByteTrack` mantém um ID único persistente para cada trabalhador no vídeo[4][12]. A métrica **\\text{IoS} (Interseção sobre Área Menor)** valida geometricamente se o EPI está contido nas regiões do corpo do operador (cabeça, tronco, pés, mãos)[4].
  * **Filtro Temporal de Infrações:** Utiliza um buffer de retardo (1 a 10s) para exigir que a infração persista por quadros consecutivos antes de formalizar um alerta, evitando falsos alarmes por oclusões rápidas[15][16].
  * **Engine de Decisão Estruturada (TypeSafe Jev):** O script local envia um **JSON de estado** com as coordenadas e itens para o **Jev**, que responde a perguntas atômicas em paralelo em milissegundos[3].

---

### **Funcionalidades e Entregáveis do Produto (Features)**

* **1\. Fiscalização e Associação Anatômica de EPIs:**
  * Mapeamento direto entre o corpo do operador e o equipamento necessário[4][14].
  * Validação geométrica que impede falsos indicativos (ex: capacete segurado nas mãos ou botina no chão)[13][20].
* **2\. Módulo "Encarregado Virtual" & Controle de Ociosidade (Dwell Time):**
  * Marcação de **zonas poligonais** no painel (banheiros, áreas de descanso, corredores, zonas de risco)[1].
  * Medição contínua do tempo de permanência parado por ID de colaborador para identificar perda de produtividade[3][21].
* **3\. Disparo Ativo de Alertas em Tempo Real:**
  * Envio de notificações automáticas via **WhatsApp ou WebSockets** ao detectar ausência de EPI em zonas críticas ou estouro do tempo limite de ociosidade[1].
  * Dispensa a necessidade de um operador vigiando telas de monitoramento 24/7[22].
* **4\. Histórico, Pontuação e Inventário do Funcionário:**
  * Consolidação diária e mensal do tempo em conformidade e tempo ocioso por colaborador[6][23].
  * Geração de uma **média estatística do funcionário**, fornecendo métricas para reuniões de feedback, campanhas de incentivo/premiação e respaldo em auditorias[1].
* **5\. Dashboard e Painel de Controle:**
  * Painel gráfico contendo gráficos de desempenho da empresa e inventário por funcionário[1][6].
  * Exibição visual com caixas verdes (conforme) e vermelhas (infração) diretamente no fluxo de vídeo para verificação rápida do gestor[4].

---

### **Estratégia de Onboarding e Implantação no Cliente**

* **Conexão com Câmeras Existentes:** Ingestão dos fluxos de vídeo através das URLs RTSP/DVRs já instalados no local[4][5].
* **Fine-Tuning Desacoplado:** Quando um novo cliente exigir cores ou padrões específicos de uniforme/EPI, realiza-se um breve ajuste fino (*fine-tuning*) no modelo SH17 usando gravações locais[2]. Toda a estrutura de código do SNITCH permanece **100% fixa**, apenas carregando o novo arquivo de pesos[2][3].

ferramentas ja determinadas para uso: ### 1. `ahmadmughees/SH17dataset` (Dataset e Pesos Pré-Treinados de EPIs)

* **URL de Referência:** `[suspicious link removed]`[1]
* **O que faz na íntegra (Stock):**
  * É um conjunto de dados e repositório especializado com 8.099 imagens e 75.994 instâncias anotadas distribuídas em 17 categorias corporais e de equipamentos de proteção[2].
  * Disponibiliza pesos pré-treinados do YOLO (arquiteturas v8, v9 e v10, cobrindo do tamanho Nano até X-Large)[1].
  * Mapeia desde pessoas e equipamentos de grande porte (capacete, colete) até componentes corporais e itens diminutos de segurança (botinas, luvas, protetores auriculares, viseiras, mãos, pés e ouvidos)[1].
* **O que complementa para o projeto SNITCH:**
  * **Núcleo de Detecção de Precisão:** Entrega o motor visual pronto para identificar o sexteto de segurança e acessórios críticos sem a necessidade de coletar e rotular manualmente dezenas de milhares de imagens industriais[1][3].
  * **Sensibilidade em Objetos Pequenos:** Resolve a perda de precisão em botinas (`Shoes`) e luvas (`Gloves`), cujas amostras ocupam frações reduzidas (menos de 1%) da área da imagem e costumam falhar em detectores genéricos[3].
* **Bônus / Ganhos Extra para o SNITCH:**
  * **Expansão Modular de Regras:** Como o modelo já reconhece protetores auriculares (`Earmuffs`/`Ear`), viseiras (`Face-guard`) e extremidades (`Hands`/`Foot`), você poderá vender módulos adicionais de auditoria (ex: áreas de ruído intenso ou proteção facial/química) sem mexer na estrutura do código[1][2].
  * **Escalabilidade de Hardware:** A disponibilidade de modelos desde *Nano* até *X-Large* permite rodar o SNITCH tanto em instâncias cloud/VPS mais baratas quanto em servidores GPU dedicados para clientes de grande porte[1].

---

### 2. `roboflow/supervision` (Toolkit Reutilizável de Visão Computacional)

* **URL de Referência:** `https://github.com/roboflow/supervision` (Documentação: `https://supervision.roboflow.com/`)[4][5]
* **O que faz na íntegra (Stock):**
  * É uma biblioteca Python agnóstica de visão computacional projetada para desacoplar a inferência neural da lógica de pós-processamento[6][7].
  * Possui algoritmos nativos de rastreamento multi-objeto (`ByteTrack`), gestão de áreas poligonais (`PolygonZone`), métricas de sobreposição espacial (`box_iou_batch`, `OverlapMetric.IOS`) e análise de tempo de permanência (*Dwell Time*)[6].
  * Fornece anotações visuais customizáveis (`BoxAnnotator`, `LabelAnnotator`) e utilitários para carregar, fundir, fatiar e converter datasets em formatos industriais (YOLO, COCO, Pascal VOC)[10].
* **O que complementa para o projeto SNITCH:**
  * **Rastreamento de Pessoas:** O módulo `sv.ByteTrack` atribui e mantém um ID persistente (`tracker_id`) para cada colaborador ao longo dos quadros do vídeo[9][13].
  * **Associação Geométrica de EPIs ao Corpo:** Utiliza a métrica de Interseção sobre Área Menor (\\text{IoS}) para validar matematicamente se um capacete, luva ou botina está contido nos limites corporais do trabalhador[9][14].
  * **Medição de Ociosidade (Encarregado Virtual):** O `sv.PolygonZone` monitora o tempo de permanência de um ID dentro de polígonos definidos (banheiros, áreas de descanso ou zonas de risco) para alimentar o indicador estatístico de tempo ocioso[6][8].
* **Bônus / Ganhos Extra para o SNITCH:**
  * **Renderização para o Front-end/Dashboard:** Os anotadores gráficos nativos permitem desenhar caixas verdes/vermelhas e rótulos de conformidade diretamente no fluxo do vídeo para exibição no painel de controle do gestor[9][10].
  * **Módulos Futuros de Velocidade e Contagem:** A biblioteca possui recursos prontos para estimativa de velocidade (*Speed Estimation*) e contagem de travessia de linhas (*Line Zone*), que podem ser aproveitados em futuras versões para monitorar empilhadeiras, correria em canteiros ou fluxo de pessoas[15].
  * **Gestão e Fine-Tuning de Datasets:** Se um cliente solicitar a adição de um EPI exclusivo, as funções de manipulação de dataset do Supervision facilitam a extração de novos recortes para re-treinar o modelo rapidamente[8].
### 1. Estratégia de Fine-Tuning para Novos Clientes (Sem Alterar Código)

Para adaptar o SNITCH a empresas com exigências ou uniformes específicos sem aumentar a complexidade ou ter que refazer o projeto:

* **Coleta Local de Amostras:** Durante o onboarding do cliente, gravam-se trechos curtos das próprias câmeras IP/RTSP da empresa para capturar a iluminação, distância e ângulos reais das rotas de trabalho[1].
* **Fine-Tuning sobre o SH17:** Em vez de treinar uma rede do zero, utiliza-se o checkpoint pré-treinado do **SH17** (que já possui mais de 75 mil anotações em 17 classes de segurança[2]) como ponto de partida. Realizam-se poucas épocas de ajuste fino com as imagens do novo local.
* **Injeção Desacoplada do Arquivo de Pesos:** Toda a estrutura de código — rastreamento, geometria, regras do Jev e comunicação — permanece 100% fixa. No ambiente do cliente, a aplicação apenas carrega o arquivo de pesos específico (`model = YOLO("pesos_cliente_A.pt")`)[1]. Isso garante escalabilidade e elimina a necessidade de manutenção de código por cliente.

---

### 2. Detecção de Zonas e Ociosidade (O "Encarregado Virtual")

O módulo de controle de ociosidade e monitoramento estatístico funciona através da infraestrutura visual do Supervision e do pipeline de dados:

* **Marcação Poligonal Dinâmica (PolygonZone):** No painel do cliente, o gestor desenha polígonos gráficos sobre a imagem da câmera definindo zonas específicas (ex: banheiros, áreas de descanso, corredores ou zonas de risco)[3][4].
* **Identidade Persistente (ByteTrack):** O algoritmo `sv.ByteTrack` atribui um identificador único (`tracker_id`) para cada operador no vídeo[1][5], mantendo o acompanhamento do indivíduo mesmo com pequenas oclusões.
* **Cálculo de Dwell Time (Tempo de Permanência):** O sistema calcula exatamente quantos minutos cada `tracker_id` permaneceu dentro do polígono marcado[3][4].
* **Consolidação Estatística e Alertas:** Em vez de depender de fiscalização presencial, o sistema atua como um **"Encarregado Virtual"**[6]:
  1. Consolida o tempo de ociosidade e a taxa de uso de EPIs em um perfil diário e mensal por colaborador[6][7].
  2. Filtra infrações momentâneas via retardo de tempo (1 a 10s)[8][9].
  3. Dispara alertas automáticos em tempo real (via WhatsApp ou WebSockets) quando um limite de permanência ou risco é ultrapassado

## Contexto consultado

Nenhuma fonte contextual consultada.

## Resumo processado

**Inferência:** Plataforma SNITCH que transforma câmeras RTSP/DVR em métricas determinísticas e auditáveis de conformidade de EPIs e tempo de ociosidade, com processamento local, YOLO/SH17, supervision, Jev e alertas.

## Análise inicial

### Problema ou oportunidade

**Declaração ou inferência identificada:** Fiscalização presencial desgastante, atrito entre encarregados e trabalhadores e ausência de evidência estatística imparcial para decisões de segurança do trabalho e produtividade.

### Pessoas afetadas ou beneficiadas

**Declaração ou inferência identificada:** Gestores e empresas em canteiros de obras e plantas industriais; encarregados; trabalhadores monitorados (por ID de rastreamento, não necessariamente identificados nominalmente no texto).

### Resultado ou valor esperado

**Declaração ou inferência identificada:** Relatórios frios e auditáveis, inibição de risco, respaldo jurídico, alertas em tempo real, histórico/pontuação por colaborador e dashboard de desempenho.

### Sinais de escopo, regras ou solução

**Sinais extraídos, não decisões:** Ingestão RTSP/DVR; VPS/container local; YOLO + pesos SH17 (17 classes EPI/corporais); ByteTrack; validação IoS cabeça/tronco/pés/mãos; buffer temporal 1–10s; engine Jev com JSON de estado; PolygonZone e dwell time; WhatsApp/WebSockets; fine-tuning desacoplado (só pesos .pt); dashboard com overlay verde/vermelho.

### Informações que talvez precisem ser guardadas

**Sinais para conversar depois, não confirmação:** Consolidação diária/mensal por colaborador (conformidade EPI, ociosidade); tracker_id persistente; zonas poligonais configuráveis; possível inventário/perfil estatístico do funcionário — sinal para conversa futura em DATABASE.md.

### Riscos e dependências

**Análise preliminar:** Caminho descartado (screenshots + API externa) por latência/custo; falsos alarmes mitigados por filtro temporal; dependência de qualidade de câmera/iluminação; fine-tuning por cliente; conformidade/privacidade de vídeo em ambiente de trabalho (não detalhada no texto).

## Possíveis direções futuras

**Hipóteses para backlog ou spec, não requisitos:** MVP com pipeline determinístico local; módulo Encarregado Virtual (ociosidade); alertas; histórico e dashboard; onboarding via RTSP existente; expansão modular (protetores auriculares, face-guard, speed/line zone futuros).

## Pontos a revisar no futuro

**A revisar:** Escopo exato do MVP vs cinco features listadas; arquitetura backend/frontend e multi-tenant; identificação nominal vs tracker anônimo e LGPD; provedor WhatsApp; referências [1]–[23] sem fonte anexada; link SH17 removido como suspeito — confirmar URL oficial do dataset.

## Rastreabilidade

- Formulação original preservada integralmente nesta captura.
- Análises não substituem decisões do usuário.
- Backlogs e specs derivados devem referenciar este arquivo.

## Próximo passo

Manter em `specs/inbox/` ou refinar com `$specsfy-02-backlog`.
