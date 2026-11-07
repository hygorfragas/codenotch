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
