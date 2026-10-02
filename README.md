# Trabalho de Compiladores - Analisador Lexico

IDE e analisador lexico para um dialeto da linguagem Pascal, desenvolvido como
trabalho da disciplina de Compiladores.

O analisador lexico esta implementado em `src/lexer/` e ligado a interface em
`src/app.py` (`build_lexer`). A analise sintatica continua sendo apenas o
esqueleto em `src/parser/`.

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
python -m pytest tests\test_lexer.py tests\test_dfa.py -q
python tests\smoke_ui.py
```

`test_lexer.py` cobre palavras reservadas, simbolos, identificadores, numeros,
literais, comentarios, erros, recuperacao e tabela de simbolos (135 testes).
`test_dfa.py` cobre os invariantes do automato: determinismo, alcancabilidade,
aceitacao e maximo casamento (107 testes).

O teste de fumaça abre a interface em modo `offscreen`, digita um programa e
valida aba por aba (tokens, erros, avisos, simbolos, classes de tokens, DFA),
além das preferencias (tema, fonte, cores) e da persistencia em disco.

## Atalhos

| Atalho | Ação |
| --- | --- |
| `Ctrl+N` | Novo programa |
| `Ctrl+O` | Abrir programa |
| `Ctrl+S` | Salvar |
| `Ctrl+Shift+S` | Salvar como |
| `Ctrl+B` | Compilar (análise léxica imediata) |
| `Ctrl+L` | Limpar a aba Saída |
| `Ctrl+,` | Preferências (tema, fonte, cores) |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Aumentar / diminuir / restaurar a fonte |

## Funcionalidades da interface

- Editor com numero da linha corrente e sublinhado vermelho para erros lexicos,
  com analise ao vivo durante a digitacao (debounce de 250 ms)
- Abas: Tokens, Erros, Avisos, Tabela de Simbolos, Classes de Tokens,
  DFA - Estados e DFA - Transicoes
- Preferencias em JSON (tema claro/escuro/sistema, fonte, cores do editor e do
  terminal) com visualizacao ao vivo
- Numero maximo de identificadores, comentarios em `//`, `{ }` e `(* *)`,
  palavras reservadas em minusculas - tratados pelo analisador em `src/lexer/`

## Analisador lexico

| Arquivo | Responsabilidade |
| --- | --- |
| `src/lexer/tokens.py` | Tabelas de palavras reservadas e simbolos, regex e classes de tokens |
| `src/lexer/dfa.py` | AutOmato finito deterministico unico mesclado (119 estados, 218 transicoes) |
| `src/lexer/lexer.py` | Scanner com maximo casamento, comentarios e tabela de simbolos |
| `src/lexer/error_recovery.py` | Criacao de erros lexicos e pontos de sincronizacao |
| `src/lexer/models.py` | Tabela de simbolos do programa |

A construcao do autOmato e as regras de identificacao estao descritas em
`relatorio/relatorio.md`.

## Estrutura do projeto

```
src/
  app.py                 Fabrica da janela; ponto de conexao do analisador (build_lexer)
  config.py              Constantes: nome da linguagem, extensao .pas, fonte
  settings.py            Preferencias do usuario (JSON)
  theme.py               Paletas claro/escuro e restauracao do tema do sistema
  main_window.py         Janela principal, menus, atalhos
  editor/
    code_editor.py       Editor com numero de linha e sublinhado de erro
  panels/
    data_table.py        Tabela somente leitura
    console_view.py      Aba Saida
    settings_dialog.py   Dialogo de preferencias
  services/
    file_service.py      Abrir/salvar arquivos
    analysis_controller.py  Analise com debounce
    lexer_service.py     Contrato LexerService e modelos de dados
  lexer/                 tokens, DFA, lexer, recuperacao de erros
  parser/                esqueleto: gramatica com "for" e analise sintatica
tests/
  smoke_ui.py            Teste de fumaca da interface
  test_lexer.py          Testes do analisador lexico
  test_dfa.py            Testes do automato
relatorio/
  relatorio.md           Relatorio do analisador lexico
```

## Mapa dos requisitos

| Requisito | Implementacao |
| --- | --- |
| 1a Nome da linguagem | `src/config.py` |
| 1b IDE | interface em `src/main_window.py` e `src/panels/` |
| 1c Case-insensitive | `PALAVRAS_RESERVADAS` em `src/lexer/tokens.py`, `dfa.simbolo_lido` normaliza a letra lida |
| 1d Identificadores (max. 15, letra inicial) | `REGEX_IDENTIFICADOR` em `src/lexer/tokens.py`, validacao em `Lexer._validar` |
| 1e Palavras reservadas | `PALAVRAS_RESERVADAS` em `src/lexer/tokens.py`,ACEITACAO em `src/lexer/dfa.py` |
| 1f Comentarios | `Lexer._consumir_comentario` em `src/lexer/lexer.py` |
| 1g Espacos em branco | `Lexer._consumir_espaco` em `src/lexer/lexer.py` |
| 1h Erros com linha/coluna e sublinhado | `src/lexer/error_recovery.py` + `src/editor/code_editor.py` |
| 1i Tabela de simbolos | `Lexer._montar_tabela_de_simbolos` e `SymbolTable` em `src/lexer/models.py` |
| 1j Recuperacao de erros | `src/lexer/error_recovery.py` e `Lexer._recuperar` |
| 1k DFA deterministico | `src/lexer/dfa.py` (verificado em `tests/test_dfa.py`) |
| 1l Relatorio e tabela de tokens | `relatorio/relatorio.md` e aba Tokens da interface |
| 2 Estrutura de controle `for` | `src/parser/grammar.py` (a implementar) |
| 2 Warning de instrucao sem efeito | `src/parser/parser.py` (a implementar) |

### Decisoes de projeto

- Nomes de token em `UPPER_SNAKE_CASE` sem acentos (`ADICAO`, `VIRGULA`,
  `PONTO_E_VIRGULA`), seguindo a convencao ja presente no codigo. Acentos
  aparecem apenas em mensagens exibidas ao usuario.
- `programa` e reconhecido alem de `program`, para que o modelo do editor
  (`src/config.py`) analise sem erro.
- Identificador com mais de 15 caracteres gera **erro lexico** mas ainda e
  emitido como token `ID`, para que a recuperacao continue.
- A regra `ID` e ASCII estrita: `número` gera erro no `ú`.
- `'` dobrado dentro de literal (`'d''art'`) equivale a um apostrofo, como no
  Pascal padrao.

## Autores

- Blendhon Pontini Delfino
- Maria Clara Gueler Feitani