# Laboratório: marco, juiz local e JEV com imagem

Medido em 7 de novembro de 2026, no MacBook Air M3, com o motor nativo parado. A sessão Colab `laya` estava encerrada e a porta 8787 livre.

A chave foi lida de `~/.config/snitch/jev_api_key` (permissão 600) e não foi copiada para o git, para o log nem para este relatório. A chamada feita antes do repouso do Mac não ficou em disco. Uma sonda nova, de 280×280, foi gravada no cache e autenticou. O cache é o SHA-256 do JPEG em `~/.config/snitch/jev-image-cache`. O andamento do laboratório está em `~/.config/snitch/jev-lab`. Retomar o script não reenvia uma imagem já cobrada.

## Custo e latência

O preço usado é o informado pelo Hygor: US$ 0,10 por mil imagens, isto é US$ 0,0001 por imagem. A documentação de imagem da TypeSafe não publica esse preço. O teto do teste era US$ 0,50. A chamada que o cruzaria não sai.

| | |
| --- | --- |
| Imagens no ledger | 676 |
| Gasto no ledger | US$ 0,0676 |
| Chamada anterior ao repouso, sem cache | cerca de US$ 0,0001 |
| Gasto total conhecido | cerca de US$ 0,0677 |
| Latência do JEV, p50 | 301 ms |
| Latência do JEV, p95 | 394 ms |
| Chamadas com latência | 675 |

A latência é o tempo da API, não o cálculo local. O noul vem como probabilidade. Verdadeiro quando é pelo menos 0,5.

## O que foi medido

Faixas pela altura da cabeça do SH17, as mesmas do juiz local:

| Faixa | Cabeça |
| --- | --- |
| Longe | menos de 55 px |
| Média | 55 a 109 px |
| Perto | 110 px ou mais |

A validação oficial do SH17 não estava disponível. O EPI veio do teste rotulado HB1204/PPE_Detection (208 imagens com cabeça). Não é o val do SH17. O rótulo é da imagem inteira. O braço A usa as regras de confiança do marco `snitch-marco-2026-11-07-coreml`: o item dentro da pessoa é "com", senão é "sem".

Precisão e recall são da classe positiva: o EPI está presente, o celular está em uso, ou a pessoa está dentro do polígono. Acurácia trata "indeterminado" como erro. A precisão do "sem" é a acusação: entre as vezes em que o braço disse que faltava, quantas vezes faltava mesmo. Célula vazia significa que o braço não emitiu aquele veredito.

| Braço | O que decide |
| --- | --- |
| A | Detector do marco, sem juiz e sem JEV |
| B | A, mais o juiz local de fatos, sem imagem |
| C | Só o JEV, olhando o recorte |
| D | A, e o JEV só na dúvida: juiz indeterminado, ou detecção com confiança abaixo de 0,35 |

O recorte da cabeça leva capacete e óculos. O recorte da pessoa leva colete, luva e celular. A imagem sobe até o mínimo que a API aceita (lado de 280 px e área de 78.400) e não passa de 1.568 px. Encolher um recorte que já é válido não baixa o preço, que é por imagem, então o recorte legal não é reduzido.

Não houve conjunto rotulado para abafador supra-auricular, plug intra-auricular, botina, máscara e cinto. O painel pede esses itens, menos o plug, que o SH17 não tem. As sementes de plug do Roboflow continuam só como exemplo local, sem imagens. Nada disso foi enviado ao JEV.

## Capacete

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 30 | A | 1,00 | 0,86 | 0,87 | 0,20 | 0 |
| Longe | 30 | B | 1,00 | 0,83 | 0,80 |  | 0,20 |
| Longe | 30 | C | 1,00 | 0,90 | 0,90 | 0,25 | 0 |
| Longe | 30 | D | 1,00 | 0,90 | 0,90 | 0,25 | 0 |
| Média | 93 | A | 1,00 | 0,81 | 0,83 | 0,38 | 0 |
| Média | 93 | B | 1,00 | 0,80 | 0,71 |  | 0,29 |
| Média | 93 | C | 1,00 | 0,98 | 0,98 | 0,83 | 0 |
| Média | 93 | D | 1,00 | 0,98 | 0,98 | 0,83 | 0 |
| Perto | 77 | A | 1,00 | 0,76 | 0,88 | 0,81 | 0 |
| Perto | 77 | B | 1,00 | 0,76 | 0,88 | 0,81 | 0 |
| Perto | 77 | C | 1,00 | 0,92 | 0,96 | 0,93 | 0 |
| Perto | 77 | D | 1,00 | 0,76 | 0,88 | 0,81 | 0 |

Perto, o marco já está confiante, então D não chama o JEV e repete A. Na média e longe, D chama o JEV e acompanha C. O "sem" do marco na média só acerta 38%. O juiz local prefere não acusar. O JEV sobe essa acusação para 83%.

## Óculos

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 3 | A |  | 0,00 | 0,33 | 0,33 | 0 |
| Longe | 3 | B |  | 0,00 | 0,00 |  | 1,00 |
| Longe | 3 | C | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Longe | 3 | D | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Média | 56 | A | 0,43 | 0,07 | 0,16 | 0,12 | 0 |
| Média | 56 | B | 0,20 | 0,02 | 0,02 |  | 0,91 |
| Média | 56 | C | 1,00 | 0,87 | 0,89 | 0,63 | 0 |
| Média | 56 | D | 0,91 | 0,87 | 0,82 | 0,50 | 0 |
| Perto | 44 | A | 0,47 | 0,58 | 0,70 | 0,83 | 0 |
| Perto | 44 | B | 0,50 | 0,58 | 0,73 | 0,93 | 0,07 |
| Perto | 44 | C | 1,00 | 0,42 | 0,84 | 0,82 | 0 |
| Perto | 44 | D | 0,53 | 0,75 | 0,75 | 0,89 | 0 |

Longe tem 3 imagens: não dá para concluir. Na média, o detector do marco quase não serve para óculos neste conjunto. O JEV recupera o "com" (precisão 1,00, recall 0,87), mas o "sem" dele ainda erra em 37% dos casos.

## Luva

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 10 | A | 1,00 | 0,80 | 0,80 | 0,00 | 0 |
| Longe | 10 | B | 1,00 | 0,10 | 0,10 |  | 0,90 |
| Longe | 10 | C | 1,00 | 0,80 | 0,80 | 0,00 | 0 |
| Longe | 10 | D | 1,00 | 0,80 | 0,80 | 0,00 | 0 |
| Média | 75 | A | 0,98 | 0,73 | 0,75 | 0,31 | 0 |
| Média | 75 | B | 1,00 | 0,26 | 0,23 |  | 0,77 |
| Média | 75 | C | 1,00 | 0,94 | 0,95 | 0,69 | 0 |
| Média | 75 | D | 1,00 | 0,94 | 0,95 | 0,69 | 0 |
| Perto | 49 | A | 0,75 | 0,86 | 0,88 | 0,94 | 0 |
| Perto | 49 | B | 0,67 | 0,14 | 0,67 | 0,94 | 0,27 |
| Perto | 49 | C | 1,00 | 0,86 | 0,96 | 0,95 | 0 |
| Perto | 49 | D | 0,92 | 0,86 | 0,94 | 0,94 | 0 |

Longe, nem o marco nem o JEV conseguem acusar a falta de luva (precisão do sem 0). Perto, os dois acusam com precisão 0,94 a 0,95.

## Colete

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 21 | A | 1,00 | 0,72 | 0,76 | 0,38 | 0 |
| Longe | 21 | B | 1,00 | 0,72 | 0,62 |  | 0,38 |
| Longe | 21 | C | 1,00 | 0,94 | 0,95 | 0,75 | 0 |
| Longe | 21 | D | 1,00 | 0,94 | 0,95 | 0,75 | 0 |
| Média | 91 | A | 1,00 | 0,76 | 0,79 | 0,39 | 0 |
| Média | 91 | B | 1,00 | 0,76 | 0,66 |  | 0,34 |
| Média | 91 | C | 1,00 | 0,96 | 0,97 | 0,80 | 0 |
| Média | 91 | D | 1,00 | 0,96 | 0,97 | 0,80 | 0 |
| Perto | 63 | A | 1,00 | 0,65 | 0,87 | 0,83 | 0 |
| Perto | 63 | B | 1,00 | 0,65 | 0,87 | 0,83 | 0 |
| Perto | 63 | C | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Perto | 63 | D | 1,00 | 0,65 | 0,87 | 0,83 | 0 |

O "com" do marco é preciso em todas as faixas. O "sem" só fica acima de 0,80 perto. O JEV chega a 0,75 longe, 0,80 na média e 1,00 perto.

## Zona

Até 40 imagens por faixa. Em cada uma, um polígono em volta da pessoa (dentro) e um canto vazio (fora). A e B usam a geometria do marco, então acertam por construção. D não chama o JEV, porque a geometria não fica em dúvida. C é o JEV olhando o polígono verde desenhado na foto. Isto não é um acervo de zonas reais.

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 64 | A, B, D | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Longe | 64 | C | 1,00 | 0,91 | 0,95 | 0,91 | 0 |
| Média | 80 | A, B, D | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Média | 80 | C | 1,00 | 0,98 | 0,99 | 0,98 | 0 |
| Perto | 80 | A, B, D | 1,00 | 1,00 | 1,00 | 1,00 | 0 |
| Perto | 80 | C | 1,00 | 0,88 | 0,94 | 0,89 | 0 |

Para zona, o polígono local é mais estável do que o JEV.

## Uso de celular

São os 66 recortes já rotulados. Positivo é "uso" (24). Na mão, sem uso e sem celular são negativo. O marco aprovado não tem detector de celular, então A nunca diz uso. B, sem votos de celular, também não. D só chamaria o JEV na dúvida, e esta regra não dispara: o resultado de D é o de A. Quem olha a foto é C.

Foto parada não mede "mexendo". O JEV foi perguntado se a pessoa mexe, olha ou leva o aparelho à orelha. Sem movimento entre quadros, o gesto de mexer não aparece.

| Faixa | n | Braço | Precisão | Recall | Acurácia | Precisão do sem | Indet. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Longe | 14 | A, B, D |  | 0,00 | 0,93 | 0,93 | 0 |
| Longe | 14 | C |  | 0,00 | 0,93 | 0,93 | 0 |
| Média | 9 | A, B, D |  | 0,00 | 0,78 | 0,78 | 0 |
| Média | 9 | C |  | 0,00 | 0,78 | 0,78 | 0 |
| Perto | 29 | A, B, D |  | 0,00 | 0,41 | 0,41 | 0 |
| Perto | 29 | C | 1,00 | 0,59 | 0,76 | 0,63 | 0 |
| Sem cabeça | 14 | A, B, D |  | 0,00 | 0,71 | 0,71 | 0 |
| Sem cabeça | 14 | C | 0,60 | 0,75 | 0,79 | 0,89 | 0 |

Perto, o JEV não inventou uso (precisão 1,00) e achou 59% dos usos. Longe e na média, com poucos casos, não achou nenhum.

## Projeção mensal por câmera

Premissas, todas explícitas:

- US$ 0,0001 por imagem.
- Uma câmera, 22 dias, 8 horas com alguém na cena: 633.600 segundos.
- Não mandar os 25 quadros por segundo. Isso seria cerca de 15,8 milhões de imagens e US$ 1.584, acima dos US$ 5.
- Dúvida medida: em 120 das 208 imagens de EPI havia pelo menos um item em dúvida (57,7%).
- Evento: 30 episódios por dia. Isto não foi medido. É hipótese.

| Modo | Imagens no mês | Custo | Cabe nos US$ 5 |
| --- | --- | --- | --- |
| 1 imagem por segundo, só se houver dúvida | cerca de 366 mil | US$ 36,55 | não |
| No máximo 1 imagem a cada 13 s, e só na dúvida | cerca de 28 mil | US$ 2,81 | sim |
| 30 eventos por dia, 1 imagem cada | 660 | US$ 0,07 | sim |

Os US$ 5 inteiros, numa câmera, pagam 50.000 imagens no mês: uma a cada 12,7 segundos se a pessoa fica o tempo todo na cena. Zona não precisa de JEV. Celular, do jeito que D está definido, também não chama, porque o marco não declara dúvida.

## FPS

O Antes da manhã não tinha a camada de celular nem a pose. A pose deixou de rodar no quadro inteiro. Agora ela só entra se há um celular confirmado, ou se a cabeça tem pelo menos 110 px e falta a parte do corpo, no máximo uma vez por segundo, num recorte de 160 px. O YOLOv8s só roda se o nano já viu um celular. Neste clipe ele não viu, então o S não entrou. Nas 12 medições abaixo a pose também não entrou.

| Condição | Câmera p50 | Câmera p5 | Inferência p50 | Inferência p5 |
| --- | --- | --- | --- | --- |
| Antes, parado | 28,8 | 27,5 | 41,6 | 40,5 |
| Agora, parado, celular desligado | 29,7 | 27,8 | 42,2 | 40,6 |
| Antes, movimento | 25,2 | 22,5 | 37,1 | 32,0 |
| Agora, movimento, celular desligado | 25,7 | 23,6 | 36,5 | 34,7 |
| Agora, movimento, celular ligado | 25,5 | 23,3 | 37,1 | 36,1 |
| Agora, parado, celular ligado | 27,0 | 25,8 | 38,0 | 36,9 |

Parado sem celular ficou acima do Antes. Movimento com celular ligado empata o p50 de inferência do Antes (37,1) e fica acima no p5. Movimento sem celular fica 0,6 abaixo no p50 de inferência (36,5 contra 37,1), dentro da oscilação desta tarde. Parado com celular ligado fica abaixo do Antes parado, porque o nano custa cerca de 6 ms no quadro em que varre. O S não participou dessa conta.

## Braço E, só com o cache

Nenhuma chamada nova. As 675 respostas já estavam no cache, e as quatro classes de EPI e os 66 celulares bateram com o arquivo do hash. Faltou zero imagem. O gasto continua cerca de US$ 0,0677.

Regra: o marco decide. O JEV entra quando o marco diria "sem", ou quando vale a dúvida do D (juiz indeterminado, ou detecção com confiança abaixo de 0,35). Fora isso, fica a resposta do marco.

| Item | n | Chamadas | Taxa | A acurácia | C acurácia | D acurácia | E acurácia | E precisão do sem |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Capacete | 200 | 86 | 0,43 | 0,86 | 0,96 | 0,93 | 0,96 | 0,86 |
| Óculos | 103 | 85 | 0,83 | 0,40 | 0,87 | 0,80 | 0,80 | 0,78 |
| Luva | 134 | 113 | 0,84 | 0,80 | 0,94 | 0,93 | 0,94 | 0,86 |
| Colete | 175 | 89 | 0,51 | 0,82 | 0,98 | 0,93 | 0,98 | 0,93 |

No capacete, na luva e no colete, E alcança C e passa D, porque também manda ao JEV o "sem" que D ainda confiava ao marco. No óculos, E fica em D (0,80) e abaixo de C (0,87): quando o marco diz "com" com confiança, E não pergunta, e nesse conjunto esse "com" erra bastante.

### Por faixa

| Item | Faixa | n | Taxa | A | C | D | E | E precisão do sem |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Capacete | Longe | 30 | 0,30 | 0,87 | 0,90 | 0,90 | 0,90 | 0,25 |
| Capacete | Média | 93 | 0,30 | 0,83 | 0,98 | 0,98 | 0,98 | 0,83 |
| Capacete | Perto | 77 | 0,64 | 0,88 | 0,96 | 0,88 | 0,96 | 0,93 |
| Óculos | Longe | 3 | 1,00 | 0,33 | 1,00 | 1,00 | 1,00 | 1,00 |
| Óculos | Média | 56 | 0,93 | 0,16 | 0,89 | 0,82 | 0,82 | 0,50 |
| Óculos | Perto | 44 | 0,68 | 0,70 | 0,84 | 0,75 | 0,75 | 0,89 |
| Luva | Longe | 10 | 0,90 | 0,80 | 0,80 | 0,80 | 0,80 | 0,00 |
| Luva | Média | 75 | 0,77 | 0,75 | 0,95 | 0,95 | 0,95 | 0,69 |
| Luva | Perto | 49 | 0,94 | 0,88 | 0,96 | 0,94 | 0,96 | 0,97 |
| Colete | Longe | 21 | 0,43 | 0,76 | 0,95 | 0,95 | 0,95 | 0,75 |
| Colete | Média | 91 | 0,35 | 0,79 | 0,97 | 0,97 | 0,97 | 0,80 |
| Colete | Perto | 63 | 0,76 | 0,87 | 1,00 | 0,87 | 1,00 | 1,00 |

A coluna A/C/D/E é a acurácia. Longe de óculos continua com 3 imagens. Longe de luva, E chama em 9 de 10 e mesmo assim a precisão do sem fica 0: o JEV também não sustenta a acusação.

Nas 208 fotos, E pediria 126 recortes de cabeça e 139 de pessoa: 265 imagens, 1,27 por foto.

### Celular com o detector deste branch

Nano a 0,20 e, só se ele vê um aparelho perto do corpo, YOLOv8s a 0,25. É o caminho de `e35ed7f`. Quando os dois veem celular, o JEV do cache confirma ou nega o uso. Sem isso, E diz que não há uso e não chama.

O detector viu celular em 8 dos 66 recortes (taxa 0,12). Nenhum ficou fora do cache.

| Faixa | n | A / D acurácia | C acurácia | E acurácia | E recall do uso |
| --- | --- | --- | --- | --- | --- |
| Longe | 14 | 0,93 | 0,93 | 0,93 | 0,00 |
| Média | 9 | 0,78 | 0,78 | 0,78 | 0,00 |
| Perto | 29 | 0,41 | 0,76 | 0,52 | 0,18 |
| Sem cabeça | 14 | 0,71 | 0,79 | 0,79 | 0,25 |
| Todas | 66 | 0,64 | 0,80 | 0,70 | 0,17 |

No total, a precisão do uso em E é 1,00: não houve confirmação falsa. O recall fica em 0,17 porque o detector local deixa passar a maior parte dos usos, e E só pergunta nesses 8. Foto parada continua sem medir "mexendo". Os 12% não servem de taxa de fábrica: 24 das 66 fotos são uso de propósito.

### Projeção mensal do braço E

As premissas anteriores valem. A taxa nova é 1,27 imagens por foto com pessoa, medida nas 208 imagens de EPI (cabeça e pessoa contam separado quando cada uma dispara).

| Modo | Imagens no mês | Custo | Cabe nos US$ 5 |
| --- | --- | --- | --- |
| 1 ciclo por segundo, com os recortes que E pediria | cerca de 807 mil | US$ 80,72 | não |
| No máximo 1 ciclo a cada 17 s | cerca de 47 mil | US$ 4,75 | sim |
| 30 eventos por dia, 1,27 recortes cada (hipótese) | 838 | US$ 0,08 | sim |

Um ciclo é uma olhada na pessoa. Os US$ 5 pagam 50.000 imagens: com 1,27 recortes por olhada, isso é uma olhada a cada 16 s. A linha de 17 s fica em US$ 4,75.

## Abafador e plug

Não rodei A–E. Não há conjunto público com positivo e negativo que dê para baixar sem conta.

O que falta, em concreto:

- O SH17 tem a classe `ear-mufs`, mas as imagens e os rótulos não estão no GitHub. O repositório público só tem o `sh17.yaml` e um script que baixa fotos do Pexels, sem as caixas. O arquivo completo está no Kaggle e no Zenodo, e o Zenodo marca os arquivos como restritos. Não há `kaggle.json` nesta máquina, e não criei conta.
- Abafador no Roboflow: o conjunto "Earmuff Detector 2" (154 imagens, treino/validação/teste) responde 403 sem chave. Os outros conjuntos de abafador e de plug do Universe também exigem API key para exportar. Não há chave da Roboflow aqui.
- No Hugging Face, os datasets com "earplug" no nome são vídeos de braço robótico, sem rótulo de com plug e sem plug.

Para medir, precisa de um destes: acesso ao val do SH17 (Kaggle ou Zenodo), ou uma API key da Roboflow para um conjunto que tenha as duas classes, com e sem. Não gastei os US$ 0,10 reservados para isso.

## Protocolo de vídeo para o Hygor

A faixa é a altura da caixa da cabeça, em px, no quadro que a webcam entrega. No Mac ela costuma abrir em 1280×720. A Apple não publica o ângulo da FaceTime do MacBook Air M3. A conta abaixo usa quadro de 720 px de altura, cabeça de 23 cm e um campo vertical de 48°. Se o primeiro clipe sair em 1920×1080, multiplique os metros por 1,5 e mantenha os px.

| Faixa | Cabeça na tela | Onde começar |
| --- | --- | --- |
| Perto | 140 a 200 px (alvo 160) | 1,2 m |
| Média | 70 a 100 px (alvo 80) | 2,3 m |
| Longe | 35 a 50 px (alvo 40) | 4,7 m |

Ajuste o passo até a caixa da cabeça cair no intervalo. O px manda, o metro é o ponto de partida. Câmera na altura dos olhos, pessoa no centro, do peito para cima.

Luz igual nos 24 clipes: lâmpada ou janela na frente do rosto, sem contra-luz, sem chapéu. Orelha visível nos clipes de plug e de orelha livre. Não misture abafador e plug no mesmo clipe.

Cada clipe dura 10 segundos. São 8 por faixa, 24 no total.

| Arquivo | O que fazer |
| --- | --- |
| `{faixa}-celular-mexendo.mp4` | Celular na mão, dedos na tela, longe da orelha |
| `{faixa}-celular-olhando.mp4` | Rosto virado para a tela, aparelho parado |
| `{faixa}-celular-orelha.mp4` | Aparelho encostado na orelha |
| `{faixa}-celular-na-mao.mp4` | Segura o celular e não olha nem mexe |
| `{faixa}-sem-celular.mp4` | Mãos vazias |
| `{faixa}-com-abafador.mp4` | Abafador supra-auricular, sem plug |
| `{faixa}-com-plug.mp4` | Plug intra-auricular visível, sem abafador |
| `{faixa}-orelhas-livres.mp4` | Sem abafador e sem plug |

`{faixa}` é `perto`, `media` ou `longe`.

Salvar em `snitch/storage/engine/lab-video/`. Essa pasta já fica de fora do git. Não renomeie no meio: o próximo laboratório lê esse nome.

## Motor local melhor, sem JEV

Nenhuma chamada ao JEV. Nenhum treino e nenhum Colab. Os pesos novos ficaram em `/tmp/sh17-weights` e `/tmp/sh17-variants`. O `sh17.pt` do motor e a pasta `weights/` do marco não foram trocados.

Todos os pesos pedidos existem em público, no release `v1` do SH17: v8l, v8x, v9-e e v10x. O v8m em 960 e 1280 foi exportado em CoreML FP16 a partir do mesmo `yolo8m.pt`. O COCO v8m veio do release público do Ultralytics.

As 208 fotos são o teste HB1204, não o Pexels do SH17. Não há indício de que tenham entrado no treino desses pesos. Os recortes com nome do COCO são do val2017, que fica de fora do treino do COCO. O person-loop não pertence a nenhum dos dois.

A faixa de cada foto é a do marco, para a comparação não mudar de grupo. A acurácia trata indeterminado como erro. No detector local não há indeterminado: ou é com, ou é sem.

Acurácia ponderada pelos 612 rótulos (200 capacetes, 103 óculos, 134 luvas, 175 coletes):

| Motor | Acurácia | Inferência p50, parado |
| --- | --- | --- |
| Marco, v8m a 640 | 0,75 | 73,2 |
| v8l a 640 | 0,76 | 50,5 |
| v8x a 640 | 0,77 | 37,7 |
| v10x a 640 | 0,76 | 17,5 |
| v9-e a 640 | 0,74 | 3,6 |
| v8m a 960 | 0,60 | 8,6 |
| v8m a 1280 | 0,52 | 6,1 |
| Zoom do v8m se a cabeça tem menos de 110 px | 0,77 | o clipe do Antes não dispara |
| Regra E, com JEV | 0,93 | não roda no quadro |

O melhor motor local é o v8x, e o ganho sobre o marco é de cerca de dois pontos. A regra E continua uns 16 pontos à frente. Entrada maior que 640 piora este conjunto: o peso foi treinado a 640, e a 1280 a acurácia cai para 0,52. O v9-e também fica abaixo do v8m.

O FPS abaixo foi medido no mesmo clipe e com as mesmas 12 amostras, com o motor Docker parado. Ele estava em cerca de 270% de CPU e, sozinho, punha o v8m em uns 19 fps. Com a máquina livre, o v8m desta sessão fica acima do Antes da manhã (inferência 41,6). A coluna da manhã continua sendo o Antes já publicado. A comparação entre variantes é a desta sessão.

| Variante | Câmera p50 / p5 | Inferência p50 / p5 | Cabe no Antes da manhã |
| --- | --- | --- | --- |
| Antes, parado | 28,8 / 27,5 | 41,6 / 40,5 | |
| v8m, parado, Docker parado | 53,2 / 49,8 | 73,2 / 67,3 | sim |
| v8l, todo quadro | 40,4 / 34,5 | 50,5 / 43,0 | sim, nesta máquina livre |
| v8x, todo quadro | 31,8 / 31,1 | 37,7 / 37,1 | não: a inferência fica abaixo de 41,6 |
| v10x, todo quadro | 13,7 / 9,8 | 17,5 / 12,4 | não |
| v9-e, todo quadro | 3,4 / 3,0 | 3,6 / 3,2 | não |
| v8m a 960 | 6,8 / 2,1 | 8,6 / 2,4 | não |
| v8m a 1280 | 5,5 / 1,6 | 6,1 / 1,9 | não |

No movimento, o v8l fica em inferência 50,8 / 49,7 e o v8x em 37,5 / 36,1. O Antes de movimento era 37,1 / 32,0. O v8x no movimento ainda passa esse número; no parado, não.

Uma vez por segundo, o v8x ocupa um quadro lento. Numa janela de 12 quadros isso em geral não muda o p50, e a acurácia do veredito passa a ser a do v8x (0,77), não a do E. Não recupera os 0,93. Rodar o v8x só na dúvida (58% das fotos) continua frequente demais para o FPS, e o teto de acurácia deste peso neste conjunto é 0,77.

### v8x por faixa, ao lado de A e E

| Item | Faixa | A acurácia | A sem | E acurácia | E sem | v8x acurácia | v8x sem |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Capacete | Longe | 0,87 | 0,20 | 0,90 | 0,25 | 0,83 | 0,17 |
| Capacete | Média | 0,83 | 0,38 | 0,98 | 0,83 | 0,89 | 0,50 |
| Capacete | Perto | 0,88 | 0,81 | 0,96 | 0,93 | 0,87 | 0,81 |
| Óculos | Média | 0,16 | 0,12 | 0,82 | 0,50 | 0,36 | 0,18 |
| Óculos | Perto | 0,70 | 0,83 | 0,75 | 0,89 | 0,68 | 0,80 |
| Luva | Média | 0,75 | 0,31 | 0,95 | 0,69 | 0,76 | 0,33 |
| Luva | Perto | 0,88 | 0,94 | 0,96 | 0,97 | 0,90 | 0,92 |
| Colete | Média | 0,79 | 0,39 | 0,97 | 0,80 | 0,76 | 0,35 |
| Colete | Perto | 0,87 | 0,83 | 1,00 | 1,00 | 0,87 | 0,85 |

Óculos longe tem 3 fotos em todos os pesos. O v8x melhora o capacete na média (0,89 contra 0,83) e a luva um pouco. Não chega perto do E, e em vários "sem" continua abaixo de 0,50.

### Outros pesos, no total

| Variante | Capacete | Óculos | Luva | Colete |
| --- | --- | --- | --- | --- |
| A, v8m | 0,86 / 0,63 | 0,40 / 0,38 | 0,80 / 0,64 | 0,82 / 0,63 |
| E | 0,96 / 0,86 | 0,80 / 0,78 | 0,94 / 0,86 | 0,98 / 0,93 |
| v8l | 0,87 / 0,66 | 0,50 / 0,44 | 0,73 / 0,55 | 0,81 / 0,63 |
| v10x | 0,86 / 0,63 | 0,46 / 0,41 | 0,77 / 0,59 | 0,82 / 0,64 |
| v9-e | 0,83 / 0,60 | 0,48 / 0,42 | 0,75 / 0,58 | 0,78 / 0,59 |
| v8m a 960 | 0,65 / 0,42 | 0,40 / 0,38 | 0,61 / 0,45 | 0,69 / 0,50 |
| v8m a 1280 | 0,54 / 0,35 | 0,39 / 0,39 | 0,56 / 0,42 | 0,55 / 0,41 |

Cada célula é acurácia / precisão do sem.

### Zoom local

Segunda passada do mesmo v8m no recorte da pessoa. Duas regras: cabeça abaixo de 110 px (130 das 208 fotos) ou só na dúvida do D. As duas deram a mesma tabela. O ganho é pequeno: acurácia ponderada 0,77, igual ao v8x, com o v8m no quadro normal.

No clipe do Antes a cabeça fica perto de 238 px, então o zoom não roda e o FPS é o do v8m. Quando roda, a passada extra custa cerca de 50 ms. Uma vez por segundo, o p50 dos outros quadros fica no v8m e a acurácia do veredito fica a desta tabela, não a do E.

| Item | Faixa | A | E | Zoom |
| --- | --- | --- | --- | --- |
| Capacete | Longe | 0,87 / 0,20 | 0,90 / 0,25 | 0,87 / 0,20 |
| Capacete | Média | 0,83 / 0,38 | 0,98 / 0,83 | 0,84 / 0,40 |
| Capacete | Perto | 0,88 / 0,81 | 0,96 / 0,93 | 0,88 / 0,81 |
| Óculos | Média | 0,16 / 0,12 | 0,82 / 0,50 | 0,27 / 0,14 |
| Óculos | Perto | 0,70 / 0,83 | 0,75 / 0,89 | 0,70 / 0,83 |
| Luva | Média | 0,75 / 0,31 | 0,95 / 0,69 | 0,76 / 0,32 |
| Luva | Perto | 0,88 / 0,94 | 0,96 / 0,97 | 0,88 / 0,94 |
| Colete | Média | 0,79 / 0,39 | 0,97 / 0,80 | 0,79 / 0,39 |
| Colete | Perto | 0,87 / 0,83 | 1,00 / 1,00 | 0,87 / 0,83 |

Perto o zoom nem é chamado na regra da cabeça, e os números repetem o marco.

### Celular sem o nano na frente

O marco não tem detector, então a acurácia de A é 0,64: ele sempre diz que não há uso. E, que só pergunta ao JEV quando o nano e o v8s concordam, fica em 0,70. Com o COCO sempre ligado, sem o nano decidir:

| Detector | Acurácia | Precisão | Recall | Precisão do sem | Inferência p50, todo quadro |
| --- | --- | --- | --- | --- | --- |
| A | 0,64 |  | 0,00 | 0,64 | 73,2 |
| E | 0,70 | 1,00 | 0,17 | 0,68 | não roda sempre |
| v8s a 320 | 0,80 | 0,87 | 0,54 | 0,78 | 17,3 |
| v8s a 640 | 0,79 | 0,86 | 0,50 | 0,77 | 19,4 |
| v8m a 640 | 0,82 | 0,88 | 0,58 | 0,80 | 11,0 |

A linha do v8s a 320 sai só do detector: celular perto da mão, do rosto ou da cabeça, limiar 0,25, entrada 320. São 13 acertos e 2 falsos positivos. O total empata com o JEV, mas as decisões coincidem em 50 das 66 fotos, então não é o cache. A rodada anterior, 0,62 de precisão e 0,67 de recall, marcava uso em qualquer caixa de celular na imagem inteira, no mesmo limiar e na mesma entrada. A regra de perto do corpo é o que muda: os falsos positivos caem de 10 para 2 e os acertos de 16 para 13.

O v8m é o melhor celular local e passa o E, porque o E deixa o nano filtrar os casos. Não cabe em todo quadro: a inferência cai de 73 para 11. Uma vez a cada 12 quadros, com o v8s a 320 já carregado, o p50 de inferência ainda cai para 29,1 e o p5 para 7,3. O segundo modelo ocupa o ANE mesmo quando não é chamado. Não há ritmo que recupere o FPS do v8m sozinho enquanto esse peso ficar carregado.

A zona não muda de conclusão. O teste desenha o polígono na caixa da pessoa. Com uma caixa, qualquer um desses pesos acerta por geometria. Não é aí que o modelo maior ganha.
