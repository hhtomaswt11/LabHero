# Roadmap do Jogo — Estruturação das Ideias

## 1. Estrutura de missões e bosses (23–35... na verdade 21–35)

Pelos números que deste, a estrutura de missões por cientista/boss fica assim:

| Cientista/Boss | Missões |
|---|---|
| Vega | 21, 22 |
| Luna | 23, 24 |
| Smith | 25, 26 |
| Ribeiro | 27, 28 |
| Li | 29, 30, 31 |
| Chen | 32, 33, 34 |
| **Final Boss** | 35 |


---

## 2. Progressão / Gating do mapa (sistema de portas)

Duas portas de bloqueio, cada uma condicionada à conclusão de uma missão específica:

| Porta | Localização | Condição de abertura | Bloqueia acesso a |
|---|---|---|---|
| Porta 1 | A seguir ao Lab 3 | Missão 6 completa | Labs 4, 5, 6 + Golden Lab + Labs dos bosses |
| Porta 2 | A seguir ao Lab 6 | Missão 35 completa | Golden Lab + Labs dos bosses |

**Nota:** a Porta 2 abre depois da missão 35 (que é o Final Boss), e o Golden Lab também "desbloqueia" com a missão 35. 
---

## 3. Golden Lab (conteúdo pós-jogo / endgame)

Desbloqueado após a missão final (35). Conteúdo a incluir:

- **Mesa de cientistas famosos** — NPCs interativos (diálogo apenas, para já)
  - *Decisão em aberto:* terão missões próprias ou são só "lore"? Sugestão: começar sem missões (mais simples de implementar e testar) e adicionar como expansão futura se o tempo permitir.
- **Computador com modelo de levedura** — simulador interativo
  - Este mesmo simulador é novo e será utilizado nas missões dos bosses (uma missão por boss usa o simulador). Este simulador deve ser similar ao computador simulador que já existe no jogo para a E. Coli, mas adaptado para leveduras. Este novo computador simulador será usado depois da missão 35, nas missões 36,37, 38, etc para trazer mais variedade ao jogo.

**Fim de jogo:** após completar as missões de todos os bosses, o jogo termina (ecrã de fim/creditos).

---

## 4. Sistema de chaves e hints

### Inventário de chaves
- Início: 15 bronze, 10 prata, 5 ouro
- Menu de inventário (tecla **E**) mostra: contagem de chaves + skins (menu unificado)

### Lógica de consumo por etapa de hint
| Etapa da hint | Chave gasta |
|---|---|
| 1ª etapa | 1x Bronze |
| 2ª etapa | 1x Prata |
| 3ª etapa | 1x Ouro |

### Pontuação por missão (com base em hints usadas)
| Hints usadas | Pontos |
|---|---|
| 0 | 5 |
| 1 etapa | 3 |
| 2 etapas | 2 |
| 3 etapas | 1 |

**Pontos a decidir/testar:**
- O que acontece se o jogador ficar sem chaves de um tipo? Impede o acesso a essa etapa da hint, ou passa para o tipo seguinte (ex: sem bronze, gasta prata)?

---

## 5. UI unificada (Inventário)
Um único menu (tecla **E**) com abas ou secções para:
- Skins (seleção/preview)
- Chaves (contagem visual: bronze/prata/ouro)

---

## 6. Modos de dificuldade

| Modo | Missões por cientista | Público-alvo |
|---|---|---|
| Normal | Todas (atual) | Uso completo/avaliação aprofundada |
| Fácil | 1 por cientista | Aulas de 2-3h, avaliação em tempo real |

**Nota de implementação:** para não duplicares conteúdo, considera marcar nas missões um flag `incluida_no_modo_facil: true/false` 

---

## 7. Conteúdo educativo

### Livros
- Rever e simplificar: tornar mais "clean" e diretamente ligados às missões (o aluno lê para aprender o necessário, não um manual extenso).

### Buddy de IA (RAG)
- Assistente in-game para perguntas de biologia / missões.
- Fase inicial (MVP): respostas baseadas apenas no conteúdo dos livros (RAG sobre os próprios livros do jogo) — reduz risco de alucinação e mantém o âmbito controlado.
- Consequência positiva que já identificaste: com o buddy a facilitar a "pesquisa", os livros podem crescer em conteúdo sem sobrecarregar o aluno, porque ele já não precisa de os vasculhar manualmente.

---

## 8. Fases finais do projeto

1. **Testes completos** — garantir que todos os sistemas acima funcionam em conjunto (missões, portas, chaves, pontuação, Golden Lab).
2. **Portar para versão Web** — validar localmente que tudo funciona (idealmente reaproveitando o motor atual, ex: se for Godot/Unity, exportar para HTML5/WebGL).
3. **Deploy do web service** — disponibilizar online (nos servidores da universidade), cumprindo o objetivo final do estágio.

---

## Ordem sugerida de implementação (por dependências)

1. Consolidar tabela/estrutura de missões (1–35) como fonte de verdade
2. Sistema de portas (depende de saber quando as missões 6 e 35 completam)
3. Sistema de chaves + hints + pontuação (sistema autónomo, pode ser feito em paralelo)
4. UI unificada de inventário (skins + chaves)
5. Golden Lab: mesa de cientistas (sem missões, versão simples) + simulador de levedura
6. Reutilizar simulador de levedura nas missões dos bosses
7. Rever/reescrever livros
8. Buddy de IA com RAG (pode ser feito em paralelo aos livros, aliás beneficia de livros já revistos)
9. Modo Fácil (depende da tabela de missões do ponto 1)
10. Testes completos
11. Port para Web
12. Deploy do web service

---

## Perguntas em aberto para fechar antes de implementar
2. Cientistas do Golden Lab: terão missões ou só diálogo? (sugiro decidir isto antes de desenhar o UI da mesa)
3. Comportamento do sistema de chaves quando um tipo se esgota.