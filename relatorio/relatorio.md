# Analisador Lexico

Trabalho da disciplina de Compiladores: IDE e analisador lexico para um dialeto
da linguagem Pascal.

| | |
| --- | --- |
| Autores | Blendhon Pontini Delfino, Maria Clara Gueler Feitani |
| Implementacao | `src/lexer/` |
| Testes | `tests/test_lexer.py` (135), `tests/test_dfa.py` (107) |

---

## 1. Objetivo

O analisador lexico recebe o texto-fonte de um programa e produz uma sequencia
de tokens, cada um com seu lexema e sua posicao no arquivo. Sobre esse
resultado sao construidas a tabela de simbolos, o relatorio de erros lexicos e
a especificacao do automato finito deterministico que reconhece a linguagem.

A interface em PySide6 consome esses dados em sete paineis (Tokens, Erros,
Avisos, Tabela de simbolos, Classes de tokens, DFA - estados e DFA - transicoes)
e sublinha em vermelho, no editor, cada erro encontrado.

---

## 2. Definicao da linguagem

### 2.1 Alfabeto

O alfabeto e o conjunto ASCII imprimivel. As letras do alfabeto sao exatamente
`[A-Za-z]`; nao ha acentos, conforme a regra `ID` da especificacao. Caracteres
fora dessa faixa nao pertencem a nenhuma classe de lexema e produzem erro
lexico.

### 2.2 Classes de lexemas

As tres classes de variaveis seguem a definicao da especificacao:

```
ID      -> [A-Za-z][letra | digito | _]*
NUM     -> digitos | digitos . digitos
LITERAL -> ' [letra | digito | CARACTERE_ESPECIAL]*

digitos -> dig digitos*
dig     -> [0-9]
```

Em regex, como exibido na aba *Classes de tokens*:

| Token | Expressao regular |
| --- | --- |
| `ID` | `[A-Za-z][A-Za-z0-9_]{0,14}` |
| `NUM` | `[0-9]+(\.[0-9]+)?` |
| `LITERAL` | `'(letra\|digito\|especial)*'` |

O limite de 15 caracteres de `ID` vem de `MAX_IDENTIFIER_LENGTH` em
`src/config.py`, fonte unica de verdade.

### 2.3 Palavras reservadas

| Lexema | Token | Lexema | Token |
| --- | --- | --- | --- |
| `program` | `PROGRAM` | `procedure` | `PROCEDURE` |
| `begin` | `BEGIN` | `function` | `FUNCTION` |
| `end` | `END` | `if` | `IF` |
| `const` | `CONST` | `else` | `ELSE` |
| `var` | `VAR` | `then` | `THEN` |
| `integer` | `INTEGER` | `while` | `WHILE` |
| `real` | `REAL` | `do` | `DO` |
| `char` | `CHAR` | `repeat` | `REPEAT` |
| `string` | `STRING` | `until` | `UNTIL` |
| `ou` | `OU` | `break` | `BREAK` |
| `e` | `E` | `continue` | `CONTINUE` |

O reconhecimento **nao diferencia maiusculas de minculas**: `BEGIN`, `Begin` e
`begin` produzem o mesmo token `BEGIN`, e o lexema guardado e sempre o texto
original como aparece no arquivo.

A tabela tambem aceita `programa` como sinonimo de `program`, para que o modelo
de programa do editor (`src/config.py`) seja analisado sem erro.

### 2.4 Simbolos

| Lexema | Token | Lexema | Token |
| --- | --- | --- | --- |
| `;` | `PONTO_E_VIRGULA` | `<=` | `MENOR_OU_IGUAL_QUE` |
| `.` | `PONTO` | `>=` | `MAIOR_OU_IGUAL_QUE` |
| `,` | `VIRGULA` | `+` | `ADICAO` |
| `:` | `DOIS_PONTOS` | `-` | `SUBTRACAO` |
| `=` | `IGUALDADE_COMPARACAO` | `*` | `MULTIPLICACAO` |
| `:=` | `ATRIBUICAO` | `/` | `DIVISAO` |
| `<>` | `DIFERENTE_DE` | `(` | `ABRE_PARENTESES` |
| `<` | `MENOR_QUE` | `)` | `FECHA_PARENTESES` |
| `>` | `MAIOR_QUE` | `[` | `ABRE_COLCHETES` |
| | | `]` | `FECHA_COLCHETES` |

Os nomes dos tokens sao escritos em `UPPER_SNAKE_CASE` sem acentos, seguindo a
convencao ja presente no projeto (`PONTO_E_VIRGULA`). Acentos aparecem somente
em mensagens exibidas ao usuario.

### 2.5 Espacos em branco e comentarios

Sao descartados antes do reconhecimento e nao geram token.

| Forma | Descricao |
| --- | --- |
| `espaco`, `\t`, `\r`, `\n`, `\v`, `\f` | Espaco em branco |
| `//` | Comentario de linha, ate o fim da linha |
| `{ ... }` | Comentario de bloco, com aninhamento |
| `(* ... *)` | Comentario de parenteses, com aninhamento |

Na ambiguidade classica `(*x)`, o comentario tem precedencia e `(` so produz
`ABRE_PARENTESES` quando nao e seguido de `*`.

---

## 3. O automato finito deterministico

O reconhecedor e um unico AFD construido por refinamento das classes, com
**119 estados** e **218 transicoes**, disponivel nas abas *DFA - estados* e
*DFA - Transicoes*.

### 3.1 Nomes de estado

| Prefixo do nome | Significado |
| --- | --- |
| `q0` | Estado inicial |
| `q_id` | Estado de aceitacao do identificador |
| `q_num_inteiro`, `q_num_decimal`, `q_num_fracao` | Numeros |
| `q_lit_dentro`, `q_lit_fim` | Literais |
| `q_ponto_e_virgula`, `q_ponto`, ... | Um estado por simbolo simples |
| `q_dois_pontos`, `q_atribuicao`, `q_menor`, `q_menor_ou_igual`, `q_diferente`, `q_maior`, `q_maior_ou_igual` | Simbolos de dois caracteres |
| `q_kw_<prefixo>` | Um estado por prefixo de palavra reservada |

Os rotulos das transicoes sao classes de caracteres sempre que a regra agrupa
varios simbolos: `letra`, `digito`, `_`, `caractere especial`,
`quebra de linha` e `outra letra, digito ou _`. Os simbolos literais
(`,` `;` `(` `:=` ...) aparecem como eles mesmos.

### 3.2 Caminho do identificador

```
q0 --letra--> q_id --letra|digito|_--> q_id      (aceita ID)
```

### 3.3 Caminhos das palavras reservadas

As palavras reservadas nao tem estados proprios: elas compartilham o mesmo
automato do identificador por uma arvore de prefixos.

```
q0 --p--> q_kw_p --r--> q_kw_pr --o--> q_kw_pro --g--> q_kw_prog
    --r--> q_kw_progr --a--> q_kw_progra --m--> q_kw_program   (aceita PROGRAM)
```

Cada estado intermediario da arvore possui, alem da transicao para o proximo
prefixo, uma aresta `outra letra, digito ou _` que leva ao estado `q_id`. E o
que garante que `programador` seja reconhecido como um unico `ID` e nao como
`PROGRAM` seguido do resto:

```
programador --p--> q_kw_p --r--> ... --m--> q_kw_program (PROGRAM)
              --a--> q_kw_progr --outra letra, digito ou _--> q_id --r--> q_id ...
              => ID("programador")
```

Os prefixos compartilhados entre palavras sao fundidos em um unico estado. Por
exemplo, `e` (de `e ou`) e `else` passam pelo mesmo `q_kw_e`; `q_kw_e` e de
aceitacao (token `E`) e ao mesmo tempo tem aresta para `q_kw_el`.

### 3.4 Caminho dos numeros

```
q0 --digito--> q_num_inteiro --digito--> q_num_inteiro    (aceita NUM)
                       |
                       '.'
                       v
                 q_num_decimal --digito--> q_num_fracao --digito--> q_num_fracao
                                                       (aceita NUM)
```

`q_num_decimal` **nao** e um estado de aceitacao: o ponto so completa o numero
se vier seguido de pelo menos um digito. Com isso, o maximo casamento recua
corretamente:

| Entrada | Tokenization |
| --- | --- |
| `12` | `NUM(12)` |
| `12.34` | `NUM(12.34)` |
| `12.` | `NUM(12)`, `PONTO(.)` |
| `.5` | `PONTO(.)`, `NUM(5)` |
| `1.2.3` | `NUM(1.2)`, `PONTO(.)`, `NUM(3)` |

### 3.5 Caminho dos literais

```
q0 --'--> q_lit_dentro --caractere especial--> q_lit_dentro
                    |
                    "'"
                    v
              q_lit_fim (aceita LITERAL) --'--> q_lit_dentro
```

A aresta de volta para `q_lit_dentro` implementa o apostrofo duplicado do
Pascal: em `'d''art'` o segundo apóstrofo escapa o terceiro e o lexema todo e
um unico `LITERAL`. O rotulo `quebra de linha` nao possui aresta de saida, de
modo que um literal nunca atravessa o fim da linha.

### 3.6 Caminho dos simbolos

Os simbolos de dois caracteres sao construidos com estados intermediarios, o
que torna o maximo casamento uma consequencia da propria tabela de transicoes,
sem necessidade de lookahead no codigo:

```
q0 --':'--> q_dois_pontos (DOIS_PONTOS) --'='--> q_atribuicao (ATRIBUICAO)
q0 --'<'--> q_menor      (MENOR_QUE)      --'='--> q_menor_ou_igual (MENOR_OU_IGUAL_QUE)
                                                   --'>'--> q_diferente (DIFERENTE_DE)
q0 --'>'--> q_maior      (MAIOR_QUE)      --'='--> q_maior_ou_igual (MAIOR_OU_IGUAL_QUE)
```

### 3.7 Propriedades verificadas

`tests/test_dfa.py` verifica, sobre a tabela completa:

| Propriedade | Teste |
| --- | --- |
| Determinismo: nenhum par `(estado, simbolo)` aparece duas vezes | `test_automato_e_deterministico` |
| Todo destino e origem de aresta existe na tabela de estados | `test_todos_os_destinos_existem`, `test_todas_as_origens_existem` |
| Todo estado e alcancavel a partir de `q0` | `test_todos_os_estados_sao_alcancaveis` |
| Todo estado de aceitacao tem um token conhecido | `test_todo_estado_de_aceitacao_tem_token_conhecido` |
| Nenhum prefixo parcial de palavra e aceito | `test_prefixos_de_palavra_nao_sao_aceitaveis` |
| Maximo casamento produz o lexema esperado | `test_maximo_casamento_no_automato` |

---

## 4. O scanner

`src/lexer/lexer.py` conduz o automato aplicando **maximo casamento**: le
caracteres enquanto houver transicao e, a cada estado de aceitacao, memoriza a
posicao; ao travar, volta para a ultima posicao memorizada e emite o token.

Duas situacoes exigem cuidado no scanner:

1. **Ramo de palavra reservada abandonado.** Se o autOmato entra em um ramo de
   palavra reservada (`b`, `f`, `p`...) e trava antes de qualquer estado de
   aceitacao, o scanner reescreve o lexema desde o inicio como identificador.
   Sem isso, `b;` perderia o token `b`.
2. **Comentarios e espacos.** Sao tratados antes do autOmato, por nao
   pertencerem a nenhuma classe de lexema. Essa e a construcao classica de um
   lexer hibrido (reconhecedor + regras auxiliary), conforme o capitulo 3.4 do
   livro *Compiladores: princpios, construcao e ferramentas*.

Cada `Token` carrega tipo, lexema, linha, coluna e atributos. A coluna e a
linha sao **base 1**, exatamente o que `src/editor/code_editor.py` espera para
sublinhar o erro; `\r\n` conta como uma unica quebra de linha.

---

## 5. Erros lexicos e recuperacao

Todo erro e reportado com linha, coluna, lexema e comprimento, para que o editor
desenhe o sublinhado ondulado exatamente sobre o trecho errado.

| Situacao | Mensagem | Token emitido |
| --- | --- | --- |
| Caractere fora do alfabeto | `caractere inválido '@'` | nao |
| Identificador com mais de 15 caracteres | `identificador com 19 caracteres, o limite é 15` | sim, como `ID` |
| Literal nao encerrado | `lexema incompleto ou não reconhecido` | nao |
| Comentario nao encerrado | `comentário iniciado em '{' não foi fechado` | nao |
| Fechador sem abertura (`)`, `]`, `}`) | `')' sem '(' correspondente` | sim |
| Abertura nao fechada no fim do arquivo | `'(' não foi fechado antes do fim do arquivo` | nao |

As mensagens acima sao reproduzidas exatamente como o programa as escreve,
com acentuacao completa. O texto corrido deste relatorio, por sua vez, omite
acentos para nao depender da codificacao do editor ou do terminal.

A recuperacao tem duas strategies:

- **Caractere isolado invalido**: registra o erro e avanca um caractere, sem
  interromper o restante do arquivo.
- **Construcao aberta** (literal, comentario): registra o erro e sincroniza ate
  o proximo `;`, `begin`, `end`, `var`, `const`, `procedure`, `function` ou
  quebra de linha, para retomar a analise dali.

Como o analisador nunca aborta, um arquivo com varios erros produce varios
erros em uma unica passagem.

---

## 6. Tabela de simbolos

Construida a partir do fluxo de tokens, percorrendo uma unica vez. Guarda a
primeira declaracao de cada identificador, na ordem em que aparece.

| Classe | Origem | Exemplo | Registro |
| --- | --- | --- | --- |
| `programa` | `programa N;` | `programa Ola;` | `Ola`, `programa`, linha 1 |
| `constante` | secao `const` | `const limite: integer := 10;` | `limite`, `constante`, `INTEGER`, valor `10` |
| `variavel` | secao `var` | `var contador: integer;` | `contador`, `variavel`, `INTEGER` |
| `procedimento` | `procedure N` | `procedure mostrar;` | `mostrar`, `procedimento` |
| `funcao` | `function N: T` | `function somar(...): integer;` | `somar`, `funcao`, tipo de retorno `INTEGER` |
| `parametro` | lista entre parenteses de subprograma | `(a: integer; b: integer)` | `a`, `parametro`, `INTEGER` |

Listas de nomes (`var x, y, z: real;`) geram uma entrada por identificador.
Redeclarar um nome **nao** e erro lexico: a primeira declaracao e mantida e um
**aviso** aparece na aba *Avisos*, apesar do primeiro uso.

---

## 7. Discrepâncias em relação à especificação

Registradas para conhecimento:

1. **`programa` alem de `program`.** A especificacao lista a palavra reservada
   `PROGRAM`, mas o modelo de arquivo do editor (`src/config.py`) usa `programa`.
   As duas grafias sao aceitas e produzem o mesmo token `PROGRAM`.
2. **Acentos rejeitados.** A regra `ID` da especificacao e ASCII estrita, entao
   `numero` e um identificador valido e `número` gera erro lexico no `ú`.
3. **Limite de identificador.** A especificacao nao diz o que fazer com um
   identificador maior que 15 caracteres. Adotou-se: emitir o token e reportar
   erro, para nao perder a informacao do lexema.
4. **Aspas duplicadas em literal.** Nao estao na regra `LITERAL`, mas sao
   padrao no Pascal e foram incluidas.

---

## 8. Testes

```
python -m pytest tests\test_lexer.py tests\test_dfa.py -q
242 passed
```

| Arquivo | Testes | Cobre |
| --- | --- | --- |
| `tests/test_lexer.py` | 135 | palavras reservadas (caixa alta, baixa e mista), 19 simbolos, maximo casamento, identificadores validos e fora do limite, numeros em todas as formas ambiguas, literais, as tres formas de comentario com aninhamento, espacos em branco, contagem de linha e coluna, `CRLF`, caracteres invalidos, fechadores, recuperacao de erro, tabela de simbolos e avisos |
| `tests/test_dfa.py` | 107 | determinismo, existencia de estados, alcancabilidade, aceitacao, ramos de palavra reservada, construcao do caminho dos numeros e dos literais, maximo casamento, consistencia das tabelas exportadas |
| `tests/smoke_ui.py` | 60 verificacoes | interface completa com o analisador real ligado em `src/app.py` |