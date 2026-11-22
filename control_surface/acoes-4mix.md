# DJ-Tech 4-Mix no Blender — ações (add-on control_surface 0.1.38)

Atualizado em 2026-11-21. "Object" e "Edit" indicam o modo do Blender em que a
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
| 10 | CUE D | — | — | | |
| 11 | Encoder (PRESS TO ENTER), girar | zoom; na vista da câmera: câmera para frente/trás (dolly) | — | ✔ | ✔ |
| 12 | Encoder, apertar | liga/desliga a vista da câmera | aceso na vista da câmera | ✔ | ✔ |
| 13 | S1 VOL | tamanho do passo do platter: 1–10 cm (mover, vista, câmera), 1–10 % (scale), 1–10° (rotação); 1 até ser mexido | — | ✔ | ✔ |
| 14 | C FILTER (depois de passar pelo centro) | seleciona um objeto na ordem do Outliner, proporcional ao curso do knob | — | ✔ | — |

## Deck A (lado esquerdo)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 15 | IN | abre o menu Add (o mesmo do Shift+A, desenhado no viewport); com o menu aberto: entra no submenu ou insere o item no 3D Cursor e fecha | aceso com o menu aberto | ✔ | ✔ (menu de malha) |
| 16 | Platter esquerdo, menu aberto | anda pelos itens (~14 pulsos por item) | — | ✔ | ✔ |
| 17 | OUT, menu aberto | cancelar: fecha o menu sem adicionar | pisca enquanto o menu está aberto | ✔ | ✔ |

## Deck C (lado esquerdo)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 18 | SYNC | apagado → aceso → piscando → apagado; ligar desliga as outras ferramentas | aceso / piscando | ✔ | ✔ |
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
| 32 | OUT | apaga a seleção, sem confirmação (Edit: vértices/arestas/faces pelo modo de seleção); confirma antes um grab em andamento | aceso 2 s se funcionou | ✔ objetos | ✔ |

| 32b | VINYL MODE (deck C) | Edit: modo de seleção vértice → aresta → face | apagado = vértice, aceso = aresta, piscando = face | — | ✔ |

## Deck B (lado direito)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 33a | IN | abre o menu do Properties (desenhado à direita do viewport) com as abas do Properties do Blender, na mesma ordem e só as que existem para o objeto (Render, Output, View Layer, Scene, World, Collection, Object, Modifiers, Particles, Physics, Constraints, Mesh/Camera/Light…, Material, Texture); com o menu aberto: entra no nível, executa a ação, liga/desliga, ou começa a editar um número/lista; IN de novo mantém o valor | aceso com o menu aberto; piscando editando | ✔ | ✔ |
| 33b | Platter direito, menu aberto | anda pelas linhas (~14 pulsos por linha); editando: muda o valor (o passo do próprio Blender para aquele campo — ex.: 1 mm na lente, 0,01 no roughness — vezes 1 a 10 pelo S1 VOL; ângulos 1–10°; inteiros e listas a cada ~14 pulsos) | — | ✔ | ✔ |
| 33c | OUT, menu aberto | editando: volta o valor anterior; senão: fecha o menu | pisca com o menu aberto | ✔ | ✔ |
| 33d | Modifiers › Add Modifier | o menu Add Modifier do Blender (Edit / Generate / Deform / …); IN no modificador adiciona e volta para a lista | — | ✔ | ✔ |
| 33e | Modifiers › (um modificador) | os campos do modificador com o valor ao lado, e Apply / Delete; o Properties de verdade vai para a aba Modifiers com esse painel aberto | — | ✔ | ✔ |
| 33f | Constraints › Add Constraint / (uma constraint) | igual aos modificadores: adicionar, campos (alvo, influência…), Apply / Delete | — | ✔ | ✔ |
| 33g | Physics | os botões (Cloth, Collision, Rigid Body…) adicionam a física; depois aparecem os campos dela | — | ✔ | ✔ |
| 33h | Material / World › Surface | as entradas do shader ligado à saída (Base Color, Roughness, Metallic…; no World: Color, Strength) | — | ✔ | ✔ |
| 33i | Listas e escolhas (vertex groups, UV maps, slots, Active Material, World…) | IN numa linha da lista a torna ativa; nas escolhas, IN escolhe o datablock ou "New" cria um | — | ✔ | ✔ |

## Decks B e D (direito)

| # | Controle | Ação | LED | Object | Edit |
|---|---|---|---|---|---|
| 33 | VINYL MODE (deck B ou D) | liga/desliga Orbit Around Selection | pisca enquanto ligado | ✔ | ✔ |

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
| 45 | Deck A: todos os botões exceto IN e OUT; deck B exceto IN, OUT, platter e VINYL MODE; deck D exceto VINYL MODE |
| 46 | CUE D |
| 47 | Deck C: SHIFT + os outros botões; VINYL MODE no Object Mode |
