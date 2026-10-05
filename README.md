# Trabalho de Compiladores - Analisadores Lexico e Sintatico

IDE e analisadores lexico e sintatico para um dialeto da linguagem Pascal,
desenvolvido como trabalho da disciplina de Compiladores.

O analisador lexico esta implementado em `src/lexer/` e o analisador sintatico em
`src/parser/`; ambos estao ligados a interface em `src/app.py` (`build_lexer`).

A segunda parte do trabalho acrescenta ao compilador: a estrutura de controle
`for`, o aviso de "instrucao sem efeito" e, como ponto extra, os tipos `record` e
enumeracao.

## Requisitos

- Python 3.12 ou superior
- PySide6 (instalado via `requirements.txt`)
- pytest (mesmo arquivo, usado apenas nos testes)

## Como executar

```
python -m pip install -r requirements.txt
python main.py
```

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
| `tests/test_highlighter.py` | 38 | realce por classe de token, cores do tema, preferencias, comentarios e integracao com a janela |
| `tests/test_background.py` | 23 | imagem de fundo do editor: caminho, opacidade, pintura, ajuste que cobre a area e persistencia |

Total: 505 testes.

O teste de fumaca abre a interface em modo `offscreen`, digita um programa e
valida aba por aba (tokens, erros, avisos, simbolos, classes de tokens, DFA e
gramatica), alem das preferencias (tema, fonte, cores, realce) e da persistencia em disco.

## Atalhos

| Atalho | Ação |
| --- | --- |
| `Ctrl+N` | Novo programa |
| `Ctrl+O` | Abrir programa |
| `Ctrl+S` | Salvar |
| `Ctrl+Shift+S` | Salvar como |
| `Ctrl+B` | Compilar (análise léxica e sintática imediatas) |
| `Ctrl+L` | Limpar a aba Saída |
| `Ctrl+,` | Preferências (tema, fonte, cores, realce e fundo) |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Aumentar / diminuir / restaurar a fonte |

## Funcionalidades da interface

- Editor com numero da linha corrente e sublinhado vermelho para erros lexico-sintaticos,
  com analise ao vivo durante a digitacao (debounce de 250 ms)
- Realce sintatico por classe de token: palavra reservada (em negrito), tipo primario,
  numero, literal e comentario (em italico); identificadores e simbolos ficam com a
  cor normal do tema
- Imagem de fundo no editor (`img/background.jpg` por padrao), ajustada para cobrir
  a area de codigo mantendo a proporcao e com opacidade ajustavel
- Abas: Tokens, Erros, Avisos, Tabela de Simbolos, Classes de Tokens,
  DFA - Estados, DFA - Transicoes e Gramatica
- Preferencias em JSON (tema claro/escuro/sistema, fonte, cores do editor e do
  terminal, cores do realce, imagem de fundo) com visualizacao ao vivo
- Numero maximo de identificadores (15 caracteres), comentarios em `//`, `{ }` e `(* *)`,
  palavras reservadas em minusculas - tratados pelo analisador em `src/lexer/`

## Analisadores

| Arquivo | Responsabilidade |
| --- | --- |
| `src/lexer/tokens.py` | Tabelas de palavras reservadas e simbolos, regex e classes de tokens |
| `src/lexer/dfa.py` | Automato finito deterministico unico mesclado (136 estados, 251 transicoes) |
| `src/lexer/lexer.py` | Scanner com maximo casamento, comentarios e tabela de simbolos |
| `src/lexer/error_recovery.py` | Criacao de erros lexicos e pontos de sincronizacao |
| `src/parser/grammar.py` | Anexo I em forma de dados, mais as extensoes da parte 2 |
| `src/parser/parser.py` | Analisador sintatico por descida recursiva, com recuperacao |
| `src/parser/service.py` | Encadeia lexico e sintatico em um unico `AnalysisResult` |

A construcao do automato e as regras de identificacao estao descritas em
`relatorio/relatorio.md`.

## Estrutura do projeto

```
src/
  app.py                 Fabrica da janela; ponto de conexao da analise (build_lexer)
  config.py              Constantes: nome da linguagem, extensao .pas, fonte
  settings.py            Preferencias do usuario (JSON)
  theme.py               Paletas claro/escuro e restauracao do tema do sistema
  main_window.py         Janela principal, menus, atalhos, paineis de saida
  editor/
    code_editor.py       Editor com numero de linha e sublinhado de erro
    highlighter.py       Realce sintatico por classe de token
  panels/
    data_table.py        Tabela somente leitura
    console_view.py      Aba Saida
    settings_dialog.py   Dialogo de preferencias
  services/
    file_service.py      Abrir/salvar arquivos
    analysis_controller.py  Analise com debounce de 250 ms
    lexer_service.py     Contrato LexerService e modelos de dados
  lexer/                 tokens, DFA, scanner, recuperacao de erros
  parser/                grammar, parser, service
tests/
  smoke_ui.py            Teste de fumaca da interface
  test_lexer.py          Testes do analisador lexico
  test_dfa.py            Testes do automato
  test_grammar.py        Testes da gramatica
  test_parser.py         Testes do analisador sintatico
  test_highlighter.py    Testes do realce sintatico
  test_background.py     Testes da imagem de fundo do editor
img/
  background.jpg         Imagem de fundo do editor (padrão)
relatorio/
  relatorio.md           Relatorio do trabalho
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
| 1l Relatorio e tabela de tokens | `relatorio/relatorio.md`, aba *Classes de tokens* e aba *Gramatica* |
| 2 Estrutura de controle `for` | `Parser._instrucao_para` e `src/parser/grammar.py` |
| 2 Warning de instrucao sem efeito | `Parser._instrucao_identificador` |
| 2 Ponto extra: registro e enumeracao | `Parser._corpo_registro`, `Parser._lista_enumeracao`, `Lexer._declarar_registro` |

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

## Autores

- Blendhon Pontini Delfino
- Maria Clara Gueler Feitani