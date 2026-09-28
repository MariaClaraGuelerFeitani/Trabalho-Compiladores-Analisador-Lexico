# Trabalho de Compiladores - Analisador Lexico

IDE e analisador lexico para um dialeto da linguagem Pascal, desenvolvido como
trabalho da disciplina de Compiladores.

A interface do IDE esta completa. O analisador lexico (DFA) e a analise sintatica
sao implementados nos pacotes `src/lexer/` e `src/parser/`, que hoje contem apenas
os arquivos esqueleto. Todo o restante da interface ja consome os resultados do
analisador, bastando conectar a implementacao em `src/app.py` (`build_lexer`).

## Requisitos

- Python 3.12 ou superior
- PySide6 (instalado via `requirements.txt`)

## Como executar

```
python -m pip install -r requirements.txt
python main.py
```

## Testes

```
python tests\smoke_ui.py
```

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
  lexer/                 esqueleto: tokens, DFA, lexer, recuperacao de erros
  parser/                esqueleto: gramatica com "for" e analise sintatica
tests/
  smoke_ui.py            Teste de fumaça da interface
  test_lexer.py          esqueleto de testes do analisador
  test_dfa.py            esqueleto de testes do DFA
relatorio/
  relatorio.md           esqueleto do relatorio final
```

## Mapa dos requisitos

| Requisito | Implementacao |
| --- | --- |
| 1a Nome da linguagem | `src/config.py` |
| 1b IDE | interface em `src/main_window.py` e `src/panels/` |
| 1c Case-insensitive | `src/lexer/tokens.py`, `src/lexer/lexer.py` |
| 1d Identificadores (max. 15, letra inicial) | `src/lexer/tokens.py`, `src/lexer/lexer.py` |
| 1e Palavras reservadas | `src/lexer/tokens.py` |
| 1f Comentarios | `src/lexer/lexer.py` |
| 1g Espacos em branco | `src/lexer/lexer.py` |
| 1h Erros com linha/coluna e sublinhado | `src/lexer/lexer.py` + `src/editor/code_editor.py` |
| 1i Tabela de simbolos | `src/lexer/lexer.py` |
| 1j Recuperacao de erros | `src/lexer/error_recovery.py` |
| 1k DFA deterministico | `src/lexer/dfa.py` |
| 1l Relatorio e tabela de tokens | `relatorio/relatorio.md` |
| 2 Estrutura de controle `for` | `src/parser/grammar.py` |
| 2 Warning de instrucao sem efeito | `src/parser/parser.py` |

## Autores

- Blendhon Pontini Delfino
- Maria Clara Gueler Feitani