# O Último Sinal 

Terror psicológico em primeira pessoa feito para PCs antigos (testado no raciocínio para Core i3-2120 + Intel HD 2000).
Não usa OpenGL, Ursina nem shaders: o 3D é desenhado pela CPU com raycasting e todas as texturas e sons são gerados por código.

## Como rodar (Windows)
Dê dois cliques em `jogar.bat`, ou abra o CMD **dentro desta pasta** e execute:

```bat
py -3 -m pip install -r requirements.txt
py -3 main.py
```

Se `py` não funcionar, use o caminho do seu Python:
`"C:\caminho\python.exe" -m pip install -r requirements.txt` e depois `"C:\caminho\python.exe" main.py`.
Se a instalação do pygame-ce falhar no Python 3.14, instale o Python 3.12 ou 3.13.

## Controles
| Tecla | Ação |
|---|---|
| W A S D | mover |
| MOUSE | olhar (inclusive para cima e para baixo) |
| Setas | girar e olhar para cima/baixo (alternativa ao mouse) |
| ESPAÇO | pular |
| SHIFT | correr (gasta fôlego) |
| E | interagir (ler, pegar, abrir porta, acionar interruptor) |
| ESC | pausar (R recomeça o capítulo) |
| F1 | muda a qualidade gráfica (256x144 → 480x270) |
| F3 | mostra FPS |
| M | liga/desliga o som |
| H | oculta a linha de ajuda |
| F11 | tela cheia |

## Novidades
- **Visual**: texturas procedurais por tema (casa, hospital, poço, ruído), neblina e luz tingida, chão e teto em gradiente, vinheta, efeitos de sanidade baixa e resolução interna maior (padrão 400x225, bem mais nítida).
- **Olhar para cima/baixo** e **pulo/corrida**, com câmera que balança ao andar.
- **Parkour**: caixas baixas e altas para escalar, vãos sem fundo (quem cai volta ao último chão firme) e saltos encadeados.
- **Puzzles**: chaves e portas trancadas, interruptores que só funcionam na ordem certa (a pista está nas notas) e portões que abrem.
- **A Sombra**: uma entidade que só se move quando você NÃO a está olhando. Se te alcançar, você perde sanidade e volta ao último ponto seguro.
- **Sanidade e fôlego**: a sanidade cai ao ver a Sombra, errar a ordem dos interruptores ou cair; recupera sozinha com o tempo.
- **História expandida**: prólogo, 4 capítulos com cenas de transição, notas espalhadas, 12 lembranças e 2 finais (depende da sua sanidade).
- **Som**: ambiente, passos, pulo, sustos etc., gerados por código (sem arquivos).

## Desempenho
O jogo reduz a qualidade sozinho se o FPS ficar abaixo de ~23. Você também pode apertar F1 a qualquer momento.
Se ainda ficar pesado, comece na qualidade Mínima (F1 até aparecer 256x144).

## Arquivos
`main.py` (motor e lógica), `world.py` (mapas e textos dos capítulos), `story.py` (prólogo, transições, finais), `textures.py` (texturas), `audio.py` (sons).
Para editar um mapa, veja a legenda no topo de `world.py`.
