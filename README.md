# Trabalho de Compiladores - Analisadores Lexico, Sintatico e Semantico

IDE e analisadores lexico, sintatico e semantico para um dialeto da linguagem
Pascal, desenvolvido como trabalho da disciplina de Compiladores.

O analisador lexico esta implementado em `src/lexer/`, o sintatico em
`src/parser/` e o semantico em `src/semantic/`; todos estao ligados a interface
em `src/app.py` (`build_lexer`).

A segunda parte do trabalho acrescenta ao compilador: a estrutura de controle
`for`, o aviso de "instrucao sem efeito" e, como ponto extra, os tipos `record` e
enumeracao. A terceira parte acrescenta a analise semantica: tabela de simbolos
com escopos encadeados (global, programa e um por procedimento/funcao),
verificacao de identificadores nao declarados, de redeclaracoes, de
compatibilidade de tipos em atribuicao, aritmetica, comparacoes e chamadas, com
erros e avisos na mesma aba e no mesmo sublinhado das fases antigas.

A quarta entrega transforma o IDE em compilador de verdade: o menu
**Executar > Executar (F5)** salva o programa, o traduz para uma fonte C
autossuficiente (`src/codegen/`), la com o Tiny C Compiler embutido em
`tools/tcc/` — sempre regravando o `.exe` nativo do Windows ao lado do
`.pas`, mesmo que um velho exista — e abre o binario em um console novo, onde
`read`/`readln` funcionam interativamente; o console avisa se o
programa terminou sem erros e espera uma tecla antes de fechar. A interface tambem ganhou
abas de editor, explorador de arquivos, busca e substituicao (Ctrl+F/Ctrl+H),
arquivos recentes, zoom pela roda do mouse, layout persistido entre sessoes e
tema proprio por pasta.

## Requisitos

- Python 3.12 ou superior
- PySide6 (instalado via `requirements.txt`)
- pytest (mesmo arquivo, usado apenas nos testes)

## Como executar

```
python -m pip install -r requirements.txt
python main.py
```

## Executavel

O IDE tambem vira um `.exe` unico, com o icone da `img/racoon.png`.

```
python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
.\build.ps1
```

Se o PowerShell recusar o script por politica de execucao:

```
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

O `build.ps1` refaz `img/racoon.ico` a partir de `img/racoon.png` (recorta a moldura
transparente, reduz a arte proporcionalmente para caber em 256x256 e a centraliza,
depois grava os sete tamanhos que o Windows usa) e depois chama o PyInstaller com o
`Guaxinim.spec`. O resultado fica em `dist\Guaxinim.exe`, cerca de 43 MB, sem janela
de console.

Argumentos:

| Argumento | Efeito |
| --- | --- |
| `-PularIcone` | nao regenera o `.ico`, reutiliza o que ja esta em `img\` |

Feche o `Guaxinim.exe` antes de recompilar: o PyInstaller nao consegue sobrescrever
um arquivo em uso, e o `build.ps1` avisa antes de tentar.

Se o `.exe` recompilado continuar com o icone antigo, e o cache de icones do Windows:
abra o Explorador de Arquivos, va em **Exibir > Exibir > Opcoes de pasta**, desmarque
**Sempre mostrar icones, nunca mostrar miniaturas**, aplique e volte a marcar; ou rode
`ie4uinit.exe -show` e reinicie o Explorador.

## Testes

```
python -m pytest tests\ -q
python tests\smoke_ui.py
```

| Arquivo | Testes | Cobre |
| --- | --- | --- |
| `tests/test_lexer.py` | 135 | palavras reservadas, simbolos, identificadores, numeros, literais, comentarios, erros e tabela de simbolos |
| `tests/test_dfa.py` | 139 | invariantes do automato: determinismo, alcancabilidade, aceitacao e maximo casamento |
| `tests/test_grammar.py` | 26 | transcricao do Anexo I, extensoes da parte 2 e consistencia terminal/token |
| `tests/test_parser.py` | 144 | programas validos e invalidos, `for`, `record`, enumeracao, acesso a campo, chamada de funcao em expressao, `;` final facultativo, aviso de instrucao sem efeito e recuperacao |
| `tests/test_semantic.py` | 101 | escopos e sombreamento, identificador nao declarado, redeclaracao, compatibilidade de tipos, operadores, condicoes, alias, enumeracao e registro, aridade e tipos de argumentos, retorno de funcao, `for`, constantes, avisos e os tres casos de teste em `.pas` |
| `tests/test_highlighter.py` | 43 | realce por classe de token, cores do tema, preferencias, comentarios e integracao com a janela |
| `tests/test_theme.py` | 107 | os 8 temas: registro, cores da paleta, realce e erro proprios, contraste minimo, escolha no dialogo, persistencia e fundo acompanhando a troca de tema |
| `tests/test_background.py` | 23 | imagem de fundo do editor: caminho, opacidade, pintura, ajuste que cobre a area e persistencia |
| `tests/test_icon.py` | 7 | icone do executavel: arquivos presentes, tamanhos do `.ico`, transparencia, arte inteira no quadro e carga no Qt |
| `tests/test_codegen.py` | 38 | tradutor Pascal->C (tipos, record, enumeracao, lacos, strings, E/S, funcoes), integracao real com o TCC embutido, incluindo o `valido.pas` canonico, e a cadeia do cmd que segura o console aberto com aviso e `pause` |
| `tests/test_ui_qol.py` | 42 | menu Exibir, explorador, sons so no tema Resident Evil (e antes do dialogo), recentes, busca/substituicao, zoom, geometria, temas por pasta (e o fundo junto), abas, foco do editor, acao unica do Executar (F5) e geracao de executavel pela janela |

Total: 813 testes.

O teste de fumaca abre a interface em modo `offscreen`, digita um programa e
valida aba por aba (tokens, erros, avisos, simbolos, classes de tokens, DFA e
gramatica), alem das preferencias (tema, fonte, cores, realce), da persistencia em disco,
das abas de editor, do explorador, da barra de busca e da traducao + compilacao
com o TCC embutido.

## Relatorio

| Arquivo | Conteudo |
| --- | --- |
| `relatorio/relatorio.md` | O relatorio do trabalho. A secao 7 descreve os tres analisadores, a secao 10 tem o diagrama de modulos e a secao 11 a tabela de tokens |
| `relatorio/checklist.md` | Checklist e roteiro de apresentacao, com as respostas preparadas para as perguntas provaveis |
| `relatorio/exemplo.pas` | Programa de demonstracao: 250 tokens, 23 simbolos, sem erro |
| `relatorio/casos_de_teste/` | Os tres casos de teste da etapa 2: `valido.pas` (valido nas tres fases), `erro_sintatico.pas` (dois erros com recuperacao) e `erros_semanticos.pas` (9 erros e 2 avisos) |
| `relatorio/diagrama_modulos.png` | O diagrama da secao 10 ja renderizado, para leitores sem Mermaid |

A tabela de tokens da secao 11 e gerada a partir do codigo, e nao escrita a mao:

```
python tools/gerar_tabela_tokens.py            # imprime a tabela
python tools/gerar_tabela_tokens.py --write    # reescreve a secao 11 do relatorio
```

O script le `src/lexer/tokens.py` e o metodo `Lexer._atributos`, que e o mesmo
que preenche a coluna de atributos da aba *Tokens* da IDE. Por isso a tabela do
relatorio nao consegue divergir do que o programa faz.

## Atalhos

| Atalho | Ação |
| --- | --- |
| `Ctrl+N` | Novo programa (abre em uma aba nova) |
| `Ctrl+O` | Abrir programa |
| `Ctrl+S` | Salvar |
| `Ctrl+Shift+S` | Salvar como |
| `Ctrl+B` | Compilar (análise léxica, sintática e semântica imediatas) |
| `F5` | Executar: salva, gera o `.exe` de novo com o TCC embutido e abre em um console novo, com aviso de fim e espera por uma tecla |
| `Ctrl+F` | Localizar no editor |
| `Ctrl+H` | Localizar e substituir |
| `Ctrl+L` | Limpar a aba Saída |
| `Ctrl+,` | Preferências (tema, fonte, cores, realce e fundo) |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Aumentar / diminuir / restaurar a fonte (também pela roda do mouse com `Ctrl`) |

## Funcionalidades da interface

- Editor com numero da linha corrente e sublinhado vermelho para erros lexico,
  sintaticos e semanticos, com analise ao vivo durante a digitacao (debounce de
  250 ms)
- Abas de editor: cada arquivo aberto vira uma aba (o botao `+` abre outra,
  fechar aba alterada pergunta se quer salvar; fechar a ultima cria outra no
  lugar) e a janela lembra das abas modificadas ao sair
- Realce sintatico por classe de token: palavra reservada (em negrito), tipo primario,
  numero, literal e comentario (em italico); identificadores e simbolos ficam com a
  cor normal do tema
- Imagem de fundo no editor (`img/background.jpg` por padrao), ajustada para cobrir
  a area de codigo mantendo a proporcao e com opacidade ajustavel (padrao 15%);
  o fundo automatico acompanha a troca de tema (o tema Resident Evil usa a imagem
  dele e os demais voltam ao padrao), enquanto uma imagem escolhida a mao e
  preservada
- Explorador de arquivos e pastas a esquerda, no estilo VSCode: raiz e a ultima
  pasta usada (persistida), botoes de abrir pasta e atualizar, subpastas com
  carga preguicosa, arquivos com ponto ignorados, duplo clique abre no editor e
  o arquivo aberto fica em negrito
- Barra de localizar e substituir acima do editor (`Ctrl+F` / `Ctrl+H`): proxima
  e anterior com volta ao inicio, diferenciar maiusculas, substituir a atual,
  substituir todas com contagem e realce amarelo das ocorrencias
- Arquivo > Recentes: os 5 ultimos arquivos abertos/salvos, em ordem de uso,
  gravados nas preferencias
- Menu **Exibir**: mostra/esconde cada painel (Explorador, Paineis de saida,
  Tokens e automato) e restaura o layout padrao; a posicao da janela e dos
  paineis persiste entre sessoes
- Ferramentas > **Fixar tema para esta pasta**: grava o tema atual como tema da
  pasta do arquivo salvo e o re-aplica ao abrir qualquer arquivo de la;
  "Remover tema da pasta" volta a pasta ao tema global
- Autocompletar no editor com `Ctrl+Space` (e sozinho apos 2 letras): palavras
  reservadas mais os simbolos declarados no programa atual
- Sons de botao, compilacao e musica de fundo **apenas no tema Resident Evil**,
  tocando no momento em que o dialogo abre
- Icone proprio (`img/racoon.png`) na janela, na barra de tarefas e no executavel;
  no Windows o `AppUserModelID` evita que o Explorador mostre o icone do Python
- Abas de saida: Tokens, Erros, Avisos, Tabela de Simbolos, Classes de Tokens,
  DFA - Estados, DFA - Transicoes e Gramatica
- Dez temas em **Preferencias > Aparencia**: Sistema, Claro, Escuro, Oceano, Sepia,
  Alto contraste, Floresta, Solarized (claro e escuro) e Resident Evil. Cada tema
  traz a paleta da interface, as cores do realce e a cor do erro; o tema do
  sistema segue a paleta do desktop. Uma preferencia de cor sempre vence a cor
  do tema.
- Preferencias em JSON (tema, fonte, cores do editor e do
  terminal, cores do realce, imagem de fundo, recentes, tema por pasta e
  geometria da janela) com visualizacao ao vivo
- Numero maximo de identificadores (15 caracteres), comentarios em `//`, `{ }` e `(* *)`,
  palavras reservadas em minusculas - tratados pelo analisador em `src/lexer/`

## Geracao de executavel

O fluxo completo mora em `src/codegen/` e roda apenas quando lexico, sintaxe e
semantico terminam sem erros:

1. `tradutor.py` refaz a descida recursiva sobre os tokens (a mesma gramatica do
   parser) e emite uma fonte C autossuficiente: `record` vira `struct`,
   enumeracao vira `enum`, `string` e `char[256]` com `strcpy`/`strcmp`/`+` via
   helpers do preludio, `write`/`writeln` viram `printf` por tipo, `read`/`readln`
   viram `scanf` (com descarte de linha), `for` avalia os limites uma unica vez
   em temporarios e o resultado de funcao e uma variavel local devolvida por
   `return`. Identificadores ganham o prefixo `gx_` para nao colidir com C;
   construcoes que o C nao reproduz (como indexar algo que nao e `string`)
   param com `ErroDeTraducao` e mensagem em portugues, nunca codigo quebrado.
2. `compilador.py` grava o `.c` ao lado do `.pas` pedido e invoca o
   `tools/tcc/tcc.exe` (Tiny C Compiler 0.9.27 win64, embutido no repositorio e
   no executavel do IDE; `tools/tcc/LICENSE.txt` registra origem e licenca
   LGPL). O `.exe` sai no mesmo diretorio do fonte.
3. `Executar > Executar (F5)` salva o `.pas` (se houver mudancas) e roda os
   passos 1 e 2 sempre — mesmo que um `.exe` velho ja exista — e em seguida
   abre o binario com `CREATE_NEW_CONSOLE`, entao o
   programa roda interativo: `readln` le do teclado do proprio console,
   como um programa Pascal nativo. O console e aberto por um `cmd` que,
   quando o programa termina, mostra uma linha de separacao (48 tracos) e
   avisa se ele saiu sem erros (ou com erro em tempo de execucao), ficando
   aberto ate uma tecla ser pressionada, para dar tempo de ler a saida.
   Se a analise ou a compilacao falhar, nada e executado.

## Analisadores

| Arquivo | Responsabilidade |
| --- | --- |
| `src/lexer/tokens.py` | Tabelas de palavras reservadas e simbolos, regex e classes de tokens |
| `src/lexer/dfa.py` | Automato finito deterministico unico mesclado (136 estados, 251 transicoes) |
| `src/lexer/lexer.py` | Scanner com maximo casamento, comentarios e tabela de simbolos |
| `src/lexer/error_recovery.py` | Criacao de erros lexicos e pontos de sincronizacao |
| `src/parser/grammar.py` | Anexo I em forma de dados, mais as extensoes da parte 2 |
| `src/parser/parser.py` | Analisador sintatico por descida recursiva, com recuperacao e ganchos para o semantico |
| `src/parser/service.py` | Encadeia lexico, sintatico e semantico em um unico `AnalysisResult` |
| `src/semantic/tipos.py` | Modelo de tipos (`integer`, `real`, `char`, `string`, logico) e regras de compatibilidade |
| `src/semantic/tabela.py` | Tabela de simbolos com escopos encadeados e categorias de entrada |
| `src/semantic/semantico.py` | Verificador semantico: declaracoes, escopos, tipos, chamadas e laço `for` |

A construcao do automato e as regras de identificacao estao descritas em
`relatorio/relatorio.md`.

## Estrutura do projeto

```
src/
  app.py                 Fabrica da janela; ponto de conexao da analise (build_lexer)
  config.py              Constantes: nome da linguagem, extensao .pas, fonte
  settings.py            Preferencias do usuario (JSON)
  theme.py               Paletas dos 8 temas (com realce e cor de erro) e
                         restauracao do tema do sistema
  main_window.py         Janela principal, menus, atalhos, abas, paineis de saida
  codegen/
    tradutor.py          Tradutor Guaxinim Pascal -> C (descida recursiva sobre os tokens)
    compilador.py        Driver do TCC embutido e execucao do .exe em console novo
    preludio.py          Helpers C emitidos antes de todo codigo gerado
  editor/
    code_editor.py       Editor com numero de linha, sublinhado de erro, busca e autocompletar
    highlighter.py       Realce sintatico por classe de token
  panels/
    data_table.py        Tabela somente leitura
    console_view.py      Aba Saida
    settings_dialog.py   Dialogo de preferencias
    file_explorer.py     Explorador de arquivos/pastas lateral
    find_bar.py          Barra de localizar e substituir
  services/
    file_service.py      Abrir/salvar arquivos
    analysis_controller.py  Analise com debounce de 250 ms
    lexer_service.py     Contrato LexerService e modelos de dados
  lexer/                 tokens, DFA, scanner, recuperacao de erros
  parser/                grammar, parser, service
  semantic/              tipos, tabela de simbolos com escopos, verificador
tests/
  smoke_ui.py            Teste de fumaca da interface
  test_lexer.py          Testes do analisador lexico
  test_dfa.py            Testes do automato
  test_grammar.py        Testes da gramatica
  test_parser.py         Testes do analisador sintatico
  test_semantic.py       Testes do analisador semantico
  test_highlighter.py    Testes do realce sintatico
  test_background.py     Testes da imagem de fundo do editor
  test_codegen.py        Testes do tradutor Pascal->C e da compilacao com TCC
  test_ui_qol.py         Testes das melhorias de interface (abas, explorador, busca...)
img/
  background.jpg         Imagem de fundo do editor (padrão)
  racoon.png             Ícone da janela, barra de tarefas e executável
  racoon.ico             Ícone do executável, gerado por tools/make_icon.py
relatorio/
  relatorio.md           Relatorio do trabalho
  checklist.md           Checklist e roteiro de apresentacao em sala
  exemplo.pas            Programa de demonstracao (250 tokens, sem erro)
  casos_de_teste/        valido.pas, erro_sintatico.pas e erros_semanticos.pas
tools/
  make_icon.py           Gera img/racoon.ico a partir de img/racoon.png
  gerar_tabela_tokens.py Gera a tabela de tokens do relatorio a partir do codigo
  tcc/                   Tiny C Compiler 0.9.27 win64 embutido (tcc.exe, lib/, include/;
                         LICENSE.txt com origem e licenca) usado pelo Executar (F5)
```

## Mapa dos requisitos

| Requisito | Implementacao |
| --- | --- |
| 1a Nome da linguagem | `src/config.py` |
| 1b IDE | interface em `src/main_window.py` e `src/panels/` |
| 1c Case-insensitive | `PALAVRAS_RESERVADAS` em `src/lexer/tokens.py`, `dfa.simbolo_lido` normaliza a letra lida |
| 1d Identificadores (max. 15, letra inicial) | `REGEX_IDENTIFICADOR` em `src/lexer/tokens.py`, validacao em `Lexer._validar` |
| 1e Palavras reservadas | `PALAVRAS_RESERVADAS` em `src/lexer/tokens.py`, `ACEITACAO` em `src/lexer/dfa.py` |
| 1f Comentarios | `Lexer._consumir_comentario` em `src/lexer/lexer.py` |
| 1g Espacos em branco | `Lexer._consumir_espaco` em `src/lexer/lexer.py` |
| 1h Erros com linha/coluna e sublinhado | `src/lexer/error_recovery.py` + `src/editor/code_editor.py` |
| 1i Analise enquanto o usuario digita | `AnalysisController` com `QTimer` de 250 ms |
| 1i Tabela de simbolos | `Lexer._montar_tabela_de_simbolos` e `SymbolTable` em `src/lexer/models.py` |
| 1j Recuperacao de erros | `src/lexer/error_recovery.py`, `Lexer._recuperar` e `Parser._sincronizar` |
| 1k DFA deterministico | `src/lexer/dfa.py` (verificado em `tests/test_dfa.py`) |
| 1l Relatorio e tabela de tokens | `relatorio/relatorio.md` (secao 10: diagrama de modulos; secao 11: tabela de tokens), `relatorio/checklist.md`, `relatorio/exemplo.pas` |
| 2 Estrutura de controle `for` | `Parser._instrucao_para` e `src/parser/grammar.py` |
| 2 Warning de instrucao sem efeito | `Parser._instrucao_identificador` |
| 2 Ponto extra: registro e enumeracao | `Parser._corpo_registro`, `Parser._lista_enumeracao`, `Lexer._declarar_registro` |
| 3 Tabela de simbolos com escopos encadeados | `src/semantic/tabela.py` (`TabelaDeSimbolos`, `Escopo`, `Entrada`) |
| 3 Identificador nao declarado e redeclaracao | `AnaliseSemantica.acesso`, `AnaliseSemantica._declarar` |
| 3 Compatibilidade de tipos (atribuicao, aritmetica, comparacoes, retorno de funcao) | `src/semantic/tipos.py`, `verificar_atribuicao`, `combinar_aritmetico`, `comparar`, `combinar_logico` |
| 3 Chamadas: aridade e tipos dos argumentos | `AnaliseSemantica.verificar_chamada` |
| 3 Atribuicao a funcao so no proprio corpo | `abrir_subprograma` (entrada propria) e `acesso(como_alvo=True)` |
| 3 Laço `for` com variavel inteira e limites inteiros | `verificar_controle_de_for`, `verificar_limite_de_for` |
| 3 Erros com linha/coluna nas tres fases | `LexicalError`/`Warning` reutilizados, prefixos `sintaxe: ` e `semantica: ` |
| 4 Executar (`F5`) gera e roda | `src/codegen/tradutor.py` (Pascal->C), `src/codegen/compilador.py` (TCC, `CREATE_NEW_CONSOLE` e cadeia do `cmd` com aviso de fim e `pause`) e `tools/tcc/` |
| 4 Abas, explorador, busca/substituicao, recentes, layout e tema por pasta | `src/main_window.py`, `src/panels/file_explorer.py`, `src/panels/find_bar.py` |

### Decisoes de projeto

- Nomes de token em `UPPER_SNAKE_CASE` sem acentos (`ADICAO`, `VIRGULA`,
  `PONTO_E_VIRGULA`), seguindo a convencao ja presente no codigo. Acentos
  aparecem apenas em mensagens exibidas ao usuario.
- `programa` e reconhecido alem de `program`, para que o modelo do editor
  (`src/config.py`) analise sem erro.
- Identificador com mais de 15 caracteres gera **erro lexico** mas ainda e
  emitido como token `ID`, para que a recuperacao continue.
- A regra `ID` e ASCII estrita: `numero` gera erro no `u` acentuado.
- `'` dobrado dentro de literal (`'d''art'`) equivale a um apostrofo, como no
  Pascal padrao.
- O analisador sintatico so roda quando o lexico nao encontrou erro, para nao
  multiplicar mensagens em cascata sobre uma fonte ja quebrada.
- Erros e avisos do parser usam o mesmo tipo de dado dos lexicos e sao
  precedidos de `sintaxe:`, de modo que reaproveitam o sublinhado vermelho do
  editor sem alteracao na interface.
- A lista de parametros e facultativa (`procedure Q;`), como no Pascal, e o
  `;` antes do `)` tambem e opcional.
- O `;` final e facultativo antes de `end`, `until`, `else` e `.`, porque
  nenhum Pascal real escreve `x := 1 end.`; no meio do bloco ele e obrigatorio.
- Chamada de funcao e aceita como operando (`x := dobro(n)`), alem da chamada de
  procedimento em posicao de instrucao.
- As secoes `var`, `const` e `type` podem aparecer em qualquer ordem antes das
  subrotinas; a gramatica do Anexo I admite um conjunto menor.
- Erros e avisos semanticos ficam em campos proprios do `AnalysisResult`
  (`semantic_errors` e `semantic_warnings`) e so entram no resultado final
  quando nao ha erro sintatico, evitando cascata; a interface os exibe pela
  uniao `all_errors`/`all_warnings`, nas mesmas abas e com o mesmo sublinhado.
- O parser chama ganchos do `AnaliseSemantica` em vez de construir uma arvore
  sintatica: sem o modulo semantico os ganchos ficam inertes, e os testes de
  sintaxe continuam validos.
- Na tabela semantica os identificadores sao sem distincao de maiusculas, como
  no resto da linguagem; sombreamento entre escopos e permitido, e
  redeclaracao no mesmo escopo e erro (o lexer, sem escopo, so avisava).
- `write`, `writeln`, `read` e `readln` nascem declarados como procedimentos
  predefinidos variadicos, para que `writeln('oi', 1)` nao seja "nao declarado".
- Unica promocao de tipos: `integer` em `real`; a divisao `/` produz sempre
  `real`, como no Pascal. O tipo logico dos comparadores e interno: a linguagem
  nao declara `boolean`.
- Variaveis declaradas e nao usadas geram aviso ao fechar o escopo; parametros
  nao geram.

## Autores

- Blendhon Pontini Delfino
- Maria Clara Gueler Feitani