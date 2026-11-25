# DJ-Tech 4-Mix no Blender — ações (add-on control_surface 0.1.51)

Atualizado em 2026-11-22. "Object" e "Edit" indicam o modo do Blender em que a
ação funciona; "—" = sem efeito nesse modo.

## Fileira de cima

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 1 | S1 PLAY | Object Mode | pisca enquanto está em Object Mode | ✔ | ✔ |
| 2 | S2 PLAY | Edit Mode | pisca enquanto está em Edit Mode | ✔ | ✔ |
| 3 | A | alterna ortográfica ↔ perspectiva (da câmera → ortográfica) | sem LED | ✔ | ✔ |
| 4 | B | perspectiva | sem LED | ✔ | ✔ |
| 5 | C | Frame All | sem LED | ✔ | ✔ |
| 6 | D | Frame Selected | sem LED | ✔ | ✔ |
| 7 | CUE A | vista Front; de novo → Back | aceso em Front, piscando em Back, apagado fora | ✔ | ✔ |
| 8 | CUE B | vista Top; de novo → Bottom | aceso em Top, piscando em Bottom, apagado fora | ✔ | ✔ |
| 9 | CUE C | vista Right; de novo → Left | aceso em Right, piscando em Left, apagado fora | ✔ | ✔ |
| 10 | CUE D | liga/desliga a vista da câmera | aceso na vista da câmera | ✔ | ✔ |
| 11 | Encoder (PRESS TO ENTER), girar | zoom; na vista da câmera: câmera para frente/trás (dolly) | — | ✔ | ✔ |
| 12 | Encoder, apertar | — (a vista da câmera foi para o CUE D) | — | | |
| 13 | S1 VOL | tamanho do passo do platter: 1–10 cm (mover, vista, câmera), 1–10 % (scale), 1–10° (rotação); 1 até ser mexido | — | ✔ | ✔ |
| 13b | S2 VOL | tamanho da grade do Blender (grid scale de todas as 3D Views): 1 mm (embaixo) a 10 m (em cima), em passos 1-2-5 (1, 2, 5 mm, 1, 2, 5 cm …); aparece "grid: 50 cm" por 1,5 s; a grade não muda até o fader ser mexido. É a grade do snap de grade, do Cursor/Selection to Grid e do snap do próprio Blender | — | ✔ | ✔ |
| 14 | C FILTER (depois de passar pelo centro) | seleciona um objeto na ordem do Outliner, proporcional ao curso do knob | — | ✔ | — |

## Deck A (lado esquerdo)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 15 | IN | abre o menu Add (o mesmo do Shift+A, na janela do 4-Mix com os ícones do Blender); com o menu aberto: entra no submenu ou insere o item no 3D Cursor e abre na hora a **configuração do objeto** (15b) | aceso com o menu aberto | ✔ | ✔ (menu de malha) |
| 15b | IN / platter / OUT / SYNC, configuração aberta | a configuração do objeto recém-adicionado (a mesma da caixa "Add Cylinder" do Blender: vértices, raio, profundidade…), na janela do 4-Mix: o platter anda pelos campos; IN edita, o platter muda o valor, IN guarda (OUT desfaz a edição); OUT ou SYNC fecham e o objeto fica. O objeto é refeito a cada mudança, no mesmo lugar. Também com o mouse na janela. A caixa "Add …" do Blender passa a ser a desse objeto (o bug do objeto que sumia) | IN aceso (piscando editando), OUT piscando | ✔ | ✔ |
| 16 | Platter esquerdo, menu aberto | anda pelos itens (~14 pulsos por item) | — | ✔ | ✔ |
| 17 | OUT, menu aberto | toque curto: volta um nível (no primeiro nível, fecha); segurado 0,5 s: fecha | pisca enquanto o menu está aberto | ✔ | ✔ |
| 17b | SYNC (deck A), menu aberto | fecha o menu de qualquer nível | aceso com o menu aberto | ✔ | ✔ |
| 17c | 1 (deck A) | leva o 3D Cursor para o mouse (o mesmo do Shift + botão direito: na superfície embaixo do mouse); não faz nada com o menu Add ou a configuração do objeto aberta | aceso 1 s depois de funcionar | ✔ | ✔ |
| 17d | 2 / 3 / 4 (deck A) | escolhe o eixo X / Y / Z: o platter esquerdo move o 3D Cursor nesse eixo, pelo `step` do S1 VOL; o mesmo botão de novo desliga; abrir o menu Add (IN) desliga, e com o menu ou a configuração aberta eles não fazem nada; CUP, CUE ou PLAY/PAUSE do deck A (com ou sem SHIFT) também desligam | aceso enquanto o eixo está escolhido | ✔ | ✔ |
| 17e | Platter esquerdo, menu fechado, eixo escolhido | move o 3D Cursor no eixo escolhido (1–10 cm por pulso, pelo S1 VOL); com o snap de grade, pula de linha em linha da grade do S2 VOL | — | ✔ | ✔ |
| 17n | VINYL MODE do lado esquerdo (deck A ou C, Object e Edit) | snap (o imã do Blender, Shift+Tab): desligado → **A, grade** → **B, geometria** → desligado. Grade: mover cai na grade do Blender (S2 VOL); escalar em passos de 10 × o passo do S1 VOL (0,1–1,0); o platter do cursor anda na grade. Geometria: o objeto (ou o vértice, no Edit) gruda no vértice/aresta/face de outro objeto embaixo do mouse; o botão 1 leva o cursor ao vértice/aresta/face embaixo do mouse. Vale também para o G/S do teclado. Durante o mover/escalar aparece uma marca laranja: um anel com VERTEX/EDGE/FACE no alvo e um ponto no canto que gruda (o canto mais perto do mouse na tela), ou "snap: grid 50 cm" (o tamanho) embaixo à esquerda | aceso = grade, piscando = geometria | ✔ | ✔ |
| 17f0 | SYNC, cursor andando (eixo 2/3/4 ou escolha de vértice do CUP) | encerra o movimento do cursor; o cursor fica onde está | aceso enquanto o cursor anda | ✔ | ✔ |
| 17f | SYNC (menu fechado, cursor parado) | Cursor to Selected: o cursor vai para o centro da seleção | aceso 1 s | ✔ | ✔ |
| 17g | CUP | Cursor to Active: o cursor vai para o objeto ativo (Edit: vértice ativo). **CUP de novo enquanto ele está aceso (3 s)**: escolher vértice — o platter esquerdo leva o cursor de um vértice ao vizinho (~14 pulsos cada); **mais um CUP** encerra e o cursor fica | aceso 3 s; piscando escolhendo vértice | ✔ | ✔ |
| 17h | CUE | Cursor to Grid: o cursor vai para o ponto da grade mais próximo (grade do Blender: o tamanho do S2 VOL, 1 m se não mexido) | aceso 1 s | ✔ | ✔ |
| 17i | PLAY/PAUSE | Cursor to World Origin: o cursor volta para (0, 0, 0) | aceso 1 s | ✔ | ✔ |
| 17j | SHIFT + SYNC | Selection to Cursor: cada selecionado vai para o cursor (todos no mesmo ponto) | aceso 1 s | ✔ | ✔ |
| 17k | SHIFT + CUP | Selection to Active: os selecionados vão para o objeto ativo | aceso 1 s | ✔ | ✔ |
| 17l | SHIFT + CUE | Selection to Grid: cada selecionado vai para o ponto da grade mais próximo | aceso 1 s | ✔ | ✔ |
| 17m | SHIFT + PLAY/PAUSE | Selection to Cursor (Keep Offset): a seleção vai em bloco, o centro dela no cursor | aceso 1 s | ✔ | ✔ |

## Deck C (lado esquerdo)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 18a | SYNC, com mover / escalar / girar em andamento | termina a operação: o objeto fica travado onde está (o modo livre, sem passar pelo de 90°); a ferramenta continua armada | aceso durante a operação | ✔ | ✔ |
| 18 | SYNC, sem operação em andamento | apagado → aceso → piscando → apagado; ligar desliga as outras ferramentas | aceso / piscando | ✔ | ✔ |
| 19 | Platter esquerdo, SYNC aceso | sobe/desce a vista (na vista da câmera: a câmera) | — | ✔ | ✔ |
| 20 | Platter esquerdo, SYNC piscando | vista para esquerda/direita (na vista da câmera: a câmera) | — | ✔ | ✔ |
| 21 | RE (scale) | 1º toque: começa um scale livre (botão 1 aceso); 2º: liga a cage; 3º: desliga | aceso ligado; piscando com cage | ✔ objetos | ✔ vértices |
| 22 | IN (rotação) | o mesmo ciclo do RE, para rotação | aceso ligado; piscando com cage | ✔ objetos | ✔ vértices |
| 23 | 1 / 2 / 3 / 4 | grab livre / X / Y / Z (com RE ou IN ligado: scale ou rotação nesse eixo); mesmo botão de novo confirma (na rotação: liga o modo 90°, ver 24b); outro número troca o eixo (na rotação, o giro do eixo anterior é desfeito); o mouse funciona como no G/S/R | aceso enquanto a operação roda | ✔ objetos | ✔ vértices |
| 24 | Platter esquerdo, durante um grab | empurra pelo passo do S1 VOL (move no eixo; livre = horizontal da vista; scale; rotação) | — | ✔ | ✔ |
| 24b | 1 / 2 / 3 / 4, 2º clique durante uma rotação | modo 90° ("tombo"): o objeto encaixa no ângulo absoluto mais próximo (0/90/180/270°) naquele eixo e o mouse é ignorado; cada ¼ de volta do platter = exatamente ±90°; outro número troca o eixo mantendo o modo 90°, e a rotação do eixo anterior é desfeita (o novo eixo começa em 0°); 3º clique confirma. No Edit Mode e no eixo livre, os 90° contam do início | o número pisca no modo 90° | ✔ | ✔ |
| 25 | SHIFT + platter esquerdo, cage ligada | troca o ponto fixo entre os 27 pontos da caixa (centro, faces, arestas, cantos); uma volta passa por todos; caixa e ponto desenhados no viewport | — | ✔ | ✔ (caixa dos vértices) |
| 26 | CUP | Object: Clear Location. Edit: **Extrude** e já entra num grab ao longo da normal (mouse + platter); CUP de novo ou clique confirma | Object: aceso 2 s se funcionou. Edit: aceso durante o extrude | ✔ | ✔ |
| 27 | CUE | Object: Clear Rotation. Edit: **Inset** (1 cm); o platter ajusta a espessura; CUE de novo termina | Object: aceso 2 s. Edit: aceso ajustando | ✔ | ✔ |
| 28 | PLAY/PAUSE | Object: Clear Scale. Edit: **Bevel** (1 cm, 1 segmento); platter = largura, SHIFT + platter = segmentos; PLAY de novo termina | Object: aceso 2 s. Edit: aceso ajustando | ✔ | ✔ |
| 29 | SHIFT + CUP | Object: Apply Location. Edit: **Loop Cut** no anel da aresta ativa (ou primeira selecionada); platter = número de cortes; SHIFT + CUP de novo termina | Object: aceso 2 s. Edit: piscando ajustando | ✔ | ✔ |
| 30 | SHIFT + CUE | Object: Apply Rotation. Edit: **Subdivide** | aceso 2 s se funcionou | ✔ | ✔ |
| 31 | SHIFT + PLAY/PAUSE | Object: Apply Scale. Edit: **Merge at Center** | aceso 2 s se funcionou | ✔ | ✔ |
| 32 | OUT (qualquer deck, sem menu aberto) | 1º toque arma a deleção (vale para os 4 decks: arma num, apaga em outro; com um menu aberto, o OUT de A/B fica no menu e o de C/D não faz nada); 2º toque apaga a seleção (Edit: vértices/arestas/faces pelo modo de seleção). Desarma sozinho depois de 5 s, ou ao apertar qualquer outra tecla (de qualquer deck), mudar a seleção ou o modo, ou ligar outra ferramenta. Confirma antes um grab em andamento | pisca rápido enquanto armado; aceso 2 s depois de apagar | ✔ objetos | ✔ |

| 32b | VINYL MODE (deck C) | o snap, igual ao 17n (o VINYL não depende do deck) | aceso = grade, piscando = geometria | ✔ | ✔ |

## Deck B (lado direito)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 33a | IN | abre o menu do Properties (na janela do 4-Mix; abas e painéis na mesma ordem do Properties; IN numa lista de opções, como Render Engine, mostra as opções e IN escolhe) com as abas do Properties do Blender, na mesma ordem e só as que existem para o objeto (Render, Output, View Layer, Scene, World, Collection, Object, Modifiers, Particles, Physics, Constraints, Mesh/Camera/Light…, Material, Texture); com o menu aberto: entra no nível, executa a ação, liga/desliga, ou começa a editar um número/lista; IN de novo mantém o valor | aceso com o menu aberto; piscando editando | ✔ | ✔ |
| 33b | Platter direito, menu aberto | anda pelas linhas (~14 pulsos por linha); editando: muda o valor (o passo do próprio Blender para aquele campo — ex.: 1 mm na lente, 0,01 no roughness — vezes 1 a 10 pelo S1 VOL; ângulos 1–10°; inteiros e listas a cada ~14 pulsos) | — | ✔ | ✔ |
| 33c | OUT, menu aberto | toque curto: editando, volta o valor anterior; senão, volta um nível (no primeiro nível, fecha). Segurado 0,5 s: fecha | pisca com o menu aberto | ✔ | ✔ |
| 33c2 | SYNC (deck B), menu aberto | fecha o menu de qualquer nível | aceso com o menu aberto | ✔ | ✔ |
| 33j | Janela do 4-Mix | abre sozinha quando o menu do Properties (IN deck B) ou o Add (IN deck A) abre, e fecha quando os dois fecham; desenhada pelo próprio Blender (ícones, dropdowns, checkboxes, sliders, gráficos de curva), cursor em vermelho, sem cabeçalho, do tamanho do nível; reabre onde você a deixou | — | ✔ | ✔ |
| 33k | Mouse na janela do 4-Mix | clicar numa linha = IN; os campos (checkbox, slider, lista, curva) mudam direto; ← = OUT, ✕ = SYNC | — | ✔ | ✔ |
| 33l | Clicar fora da janela do 4-Mix (no Blender ou em outro programa) | fecha os menus, como o SYNC (uma edição em andamento volta ao valor anterior); o clique também vale onde caiu; passar o mouse fora ou Alt+Tab não fecha. A janela fica por cima dos outros programas enquanto está aberta | — | ✔ | ✔ |
| 33d | Modifiers › Add Modifier | o menu Add Modifier do Blender (Edit / Generate / Deform / …); IN no modificador adiciona e volta para a lista | — | ✔ | ✔ |
| 33e | Modifiers › (um modificador) | os campos do modificador com o valor ao lado, e Apply / Delete; o Properties de verdade vai para a aba Modifiers com esse painel aberto | — | ✔ | ✔ |
| 33f | Constraints › Add Constraint / (uma constraint) | igual aos modificadores: adicionar, campos (alvo, influência…), Apply / Delete | — | ✔ | ✔ |
| 33g | Physics | os botões (Cloth, Collision, Rigid Body…) adicionam a física; depois aparecem os campos dela | — | ✔ | ✔ |
| 33h | Material / World › Surface | as entradas do shader ligado à saída (Base Color, Roughness, Metallic…; no World: Color, Strength) | — | ✔ | ✔ |
| 33i | Listas e escolhas (vertex groups, UV maps, slots, Active Material, World…) | IN numa linha da lista a torna ativa; nas escolhas, IN escolhe o datablock ou "New" cria um | — | ✔ | ✔ |

## Decks B e D (direito)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 33 | VINYL MODE do lado direito (deck B ou D) | Edit: modo de seleção vértice → aresta → face. Object: liga/desliga Orbit Around Selection | Edit: apagado = vértice, aceso = aresta, piscando = face. Object: pisca com o Orbit ligado | ✔ | ✔ |

## Regras gerais

| # | Regra |
|---|---|
| 34 | Uma ferramenta por deck: SYNC, mover, scale e rotação não ficam ligados juntos; ligar uma desliga as outras e confirma a operação em andamento. |
| 35 | Scale e rotação continuam ligados depois que a operação termina, até mudar a seleção de objetos, apertar o botão de novo ou trocar de ferramenta. |
| 36 | Grab: clique esquerdo ou Enter confirmam; botão direito ou Esc cancelam (volta ao começo). |
| 37 | Center tap: os FILTER e os knobs HI/MID/LOW só passam a funcionar depois de chegar ao centro. |
| 38 | LEDs mostram o estado do Blender (mudar pelo teclado também muda o LED); o LED de um botão é reenviado depois de cada toque. |
| 39 | Troca de deck: os LEDs daquele deck acendem um por um e voltam ao estado. |
| 40 | Connect: animação de abertura com todos os LEDs (~1,3 s). |
| 41 | Dois Blenders abertos: o controlador pertence ao último em que se clicou; o outro mostra "Standby". |
| 42 | Painel DJ-Tech (barra lateral N): status, decks/SHIFT, passo, estado das ferramentas e do dono, último erro, botão Debug log (grava em %TEMP%\control_surface_midi.log). |

## Sem função ainda

| # | Controle |
|---|---|
| 43 | Platter direito com o deck D, ou com o deck B e o menu fechado |
| 44 | A, B e D FILTER; knobs HI, MID, LOW |
| 45 | Deck A: RE e os outros SHIFT; deck B exceto IN, OUT, platter e VINYL MODE; deck D exceto VINYL MODE e OUT |
| 47 | Deck C: SHIFT + os outros botões |
