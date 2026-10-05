# Checklist de apresentacao

Roteiro curto para apresentar o trabalho em sala. Cada bloco corresponde a um
requisito da especificacao e cabe em um ou dois minutos de demonstracao.

Os trechos marcados com **digitar** sao para digitar ao vivo no editor. Todos foram
executados contra o analisador antes de este texto ser escrito: linha, coluna e
mensagem aqui registradas sao as que aparecem na tela.

---

## 1. Antes de abrir o projetor

- [ ] `python -m pip install -r requirements.txt`
- [ ] `python -m pytest tests\ -q` e deixar `512 passed` na tela
- [ ] `python main.py` e maximizar a janela
- [ ] `Ctrl+,` e deixar o tema **escuro** (fica melhor no projetor)
- [ ] `Ctrl+O` e abrir `relatorio/exemplo.pas`
- [ ] Ter em maos `relatorio/relatorio.md` (secoes 10 e 11 sao o diagrama e a tabela)
- [ ] Testar o projetor de video: a fonte do editor e Consolas 11

O programa ja abre com um modelo valido. Se preferir comecar do zero, `Ctrl+N`.

---

## 2. Abertura (30 segundos)

Diga o nome e o que o programa faz:

> "A linguagem se chama **Guaxinim**. E um dialeto de Pascal. O que voces vao ver
> e a IDE completa: editor com analise ao vivo, tabela de tokens, tabela de
> simbolos, e o automato finito deterministico que reconhece a linguagem. Como
> nao ha gerador de codigo, 'Compilar' significa rodar a analise lexico e a
> sintatica."

Aponte para a barra de status: `Ln 1, Col 1` a esquerda, `Pronto` a direita.

---

## 3. Requisitos (a) a (k)

| # | Requisito | Onde esta no codigo |
| --- | --- | --- |
| a | Nome da linguagem | `src/config.py` |
| b | IDE | `src/main_window.py`, `src/panels/` |
| c | Nao diferencia maiusculas | `dfa.simbolo_lido` |
| d | Identificador: 15, comeca em letra | `tokens.REGEX_IDENTIFICADOR`, `Lexer._validar` |
| e | Palavras reservadas reservadas | `tokens.PALAVRAS_RESERVADAS` |
| f | Comentarios removidos | `Lexer._consumir_comentario` |
| g | Espacos em branco removidos | `Lexer._consumir_espaco` |
| h | Erro com linha e coluna, sublinhado | `error_recovery.py`, `CodeEditor.set_error_marks` |
| i | Analise enquanto digita | `AnalysisController` |
| i | Tabela de simbolos | `Lexer._montar_tabela_de_simbolos` |
| j | Recuperacao de erros | `error_recovery.py`, `Lexer._recuperar` |
| k | AFD deterministico | `src/lexer/dfa.py` |

### a) Nome

**digitar:** `programa Teste;`

O nome da linguagem esta em uma unica linha, `LANGUAGE_NAME = "Guaxinim"` em
`src/config.py`. Da para mostrar que mudar ali muda o titulo da janela, a
extensao do arquivo e o filtro do dialogo de abrir.

### b) IDE

Mostre a janela inteira: editor no centro, dock de baixo com **Saida**, **Erros**,
**Avisos**, **Tokens** e **Tabela de simbolos**; dock da direita com **Classes de
tokens**, **DFA - estados**, **DFA - transicoes** e **Gramatica**. Sao 9 abas.

### c) Nao diferencia maiusculas

**digitar:** apague tudo e escreva em caixa mista:

```
PROGRAM t;
BeGiN
  x := 1
EnD.
```

Vai para **Erros (0)**. Depois va para a aba **Tokens**: os quatro viram
`PROGRAM`, `BEGIN`, `END`, `PONTO`. O lexema guardado e o texto original, com a
caixa que voce digitou.

O truque esta em `dfa.simbolo_lido`: dentro de um ramo de palavra reservada a
letra lida e convertida para minuscula **antes** de a transicao ser procurada, e a
tripla de palavras reservadas tambem esta em minusculas. Nao ha duas entradas
para `begin` e `BEGIN`.

### d) Identificadores

**digitar** na secao `var`, um de cada vez:

```
var nome_do_usuario: integer;    // 15 caracteres: passa
```

```
var nome_do_usuario1: integer;   // 16 caracteres: erro
```

O primeiro nao produz nada. O segundo marca em vermelho e a aba **Erros** mostra,
exatamente:

```
identificador com 16 caracteres, o limite é 15
```

Repare que o token `ID` **continua aparecendo** na aba **Tokens** mesmo com o
erro. Isso e proposital: o scanner emite o lexema e reporta o problema, para a
recuperacao nao perder o token.

Depois mostre o primeiro caractere:

**digitar:** `var _x: integer;`

Erro: `caractere inválido '_'`, na coluna 5. O underline so vale a partir do
segundo caractere.

E o caractere especial:

**digitar:** `var n$ou: integer;`

Erro: `caractere inválido '$'`, na coluna 6. E um caractere por vez, e a analise
continua.

Vale olhar a aba **Tokens** aqui: o `$` foi pulado, e o `ou` que vem logo em
seguir virou o token `OU`, palavra reservada. A recuperacao pulou exatamente um
caractere e o automato voltou a funcionar no mesmo instante.

### e) Palavras reservadas

Vá para a aba **Classes de tokens**: 52 linhas, 51 tokens distintos. `program` e
`programa` sao o mesmo token `PROGRAM`, e por isso aparecem duas linhas.

Explique que a palavra reservada esta no dicionario do automato, nao em um `if`
dentro do scanner: sao 109 dos 136 estados, montados como uma arvore de prefixos
com os prefixos compartilhados.

### f) Comentarios

O arquivo `exemplo.pas` ja tem os tres formatos. **digitar** um de cada:

```
// este e descartado
{ este tambem
  e este { aninhado } }
(* e este
   (* com aninhamento *) *)
```

Vá para a aba **Tokens**: nenhum deles produz token. O realcador pinta os tres em
italico, e o `{ aninhado }` dentro de `{ ... }` continua cinza.

Detalhe para citar se perguntarem: `(*x)` e comentario, porque o comentario e
testado antes do automato. `(` so vira `ABRE_PARENTESES` quando nao e seguido de
`*`.

### g) Espacos em branco

Mostre o arquivo inteiro com indentacao e linhas em branco. Nenhum espaco, tab ou
quebra de linha vira token. O automatismo esta em `Lexer._consumir_espaco`.

### h) Erro com linha, coluna e sublinhado vermelho

Este e o bloco mais importante. **digitar**, esperando o sublinhado aparecer
sozinho:

```
programa Erro;
begin
  x := 1 @ 2;
end.
```

- O `@` fica **sublinhado em vermelho ondulado**, sem precisar compilar
- Aba **Erros**: `linha 3`, `coluna 10`, lexema `@`, mensagem `caractere inválido '@'`
- Aba **Tokens**: os tokens antes e depois do `@` continuam la, o que prova que a
  analise nao parou

Repare que coluna 10 e a posicao **declarada** e nao a posicao na tela. Quem
calcula o sublinhado e `CodeEditor._positions_for`, que converte linha e coluna
1-based em deslocamento no `QTextDocument` e limita no fim da linha.

Outros tres para citar, todos verificados:

| O que digitar | Linha, coluna | Mensagem |
| --- | --- | --- |
| `s := 'aberta;` | 4, 8 | `lexema incompleto ou não reconhecido` |
| `(* isto nunca fecha` | 2, 1 | `comentário iniciado em '(*' não foi fechado` |
| `x := 1);` | 3, 9 | `')' sem '(' correspondente` |

### i) Analise enquanto o usuario digita

Este e o item (i) e nao depende de nenhum botao. **digitar** devagar e observar:
os contadores das abas mudam sozinhos.

Explique o mecanismo: `textChanged` chama `AnalysisController.request`, que
reinicia um `QTimer` de 250 ms. So dispara a analise quando o usuario para de
digitar por esse tempo. E por isso que o `Ctrl+B` chama `analyze_now`, que cancela
o timer pendente e analisa na hora.

**digitar** rapidissimo sem parar: nada acontece. Isso **e** o debounce
funcionando, e vale a pena mostrar de proposito.

### i) Tabela de simbolos

Abra `relatorio/exemplo.pas` e va para **Tabela de simbolos**. Sao 23 entradas,
uma por declaracao, na ordem da primeira declaracao. As colunas sao
`Identificador`, `Classe`, `Tipo`, `Valor`, `Linha`:

| Identificador | Classe | Tipo | Valor |
| --- | --- | --- | --- |
| `Fatorial` | programa | | |
| `limite` | constante | `INTEGER` | `10` |
| `titulo` | constante | | `'numeros'` |
| `cor` | tipo_enumeracao | | |
| `vermelho` | constante_enumeracao | | |
| `ponto` | tipo_registro | | |
| `x` | campo | `REAL` | |
| `contador` | variavel | `INTEGER` | |
| `atual` | variavel | `cor` | |
| `p` | variavel | `ponto` | |
| `mostrar` | procedimento | | |
| `texto` | parametro | `STRING` | |
| `dobro` | funcao | `INTEGER` | |

Repare em `atual` e `p`: o tipo nao e um token primitivo, e o identificador do
tipo definido pelo usuario. E em `titulo`: declarado sem `: tipo`, a coluna de
tipo fica vazia e o valor vem do literal.

Se declara o mesmo nome duas vezes, o que acontece **nao** e erro: a primeira
declaracao e mantida e aparece um **aviso**.

**digitar:** `var x: integer;` e depois `var x: real;`

Aba **Avisos**: `'x' já declarado na linha 2 como variavel`. Faca isso porque
mostra a separacao entre erro e aviso.

### j) Recuperacao de erros

Explique as tres estrategias de `src/lexer/error_recovery.py`:

1. **Caractere isolado invalido**: registra o erro e avanca um caractere. E o que
   acontece com o `@`.
2. **Construcao aberta**: registra o erro e sincroniza ate o proximo `;` ou
   quebra de linha. E o que acontece com o literal `'aberta`. A sincronizacao
   para *no* caractere, sem consumir, para a contagem de linha nao se perder.
3. **Pareamento de delimitadores**: uma pilha durante toda a passagem localiza
   fecha faltando e fecha nao aberta.

O argumento forte e o do final: **a analise nunca aborta**. Mostre um arquivo
com `@` na linha 3, um literal aberto na linha 5 e um `)` solto na linha 8. Os
tres erros aparecem juntos, em uma unica passagem.

### k) Automato finito deterministico

Va para **DFA - estados** e depois **DFA - transicoes**:

- 136 estados, 251 transicoes, 53 estados de aceitacao
- Determine: para cada par (estado, simbolo) existe **no maximo uma** transicao.
  E o que `tests/test_dfa.py` verifica em 139 testes

Para mostrar o maximo casamento funcionando, **digitar** `12.` e mostrar que sai
um `NUM 12` e um `PONTO .` separado, e nao um `NUM 12.`. O automato tem um estado
nao aceito depois do ponto, que so se torna aceito quando vem um digito.

O mesmo para `.5`: sai `PONTO .` e `NUM 5`.

---

## 4. Analisador sintatico (segunda parte)

**Ctrl+B** e mostre que a analise lexico roda primeiro: se ha erro lexico, o
parser nem e chamado, para nao multiplicar mensagem sobre fonte ja quebrada.

Em `exemplo.pas` os dois Analisadores passam. Agora quebre de proposito: apague
o `end.` final, ou troque um `begin` por `banana`.

Erros de sintaxe aparecem na **mesma** aba **Erros**, com o **mesmo** sublinhado
vermelho, so que comecam com `sintaxe: `. O motivo e que o parser constroi
`LexicalError`, o mesmo tipo de dado do lexico, e assim a interface nao muda.

Mostre ainda:

- `for i := 1 to 5 do` e `for j := 5 downto 1 do`, que sao a estrutura de controle
  acrescentada na segunda parte
- `type` com `record` e com enumeracao, inclusive com intervalo `claro..escuro`
- O aviso `instrucao sem efeito`, que so dispara quando o identificador nao e um
  procedimento nem uma funcao declarados

---

## 5. Extras, se sobrar tempo

- [ ] **Ctrl+,** e mostrar as 4 guias de preferencias com previa ao vivo
- [ ] Trocar o tema em claro e escuro
- [ ] `Ctrl+,` aba **Fundo**, mexer na opacidade da imagem do editor
- [ ] Zoom com `Ctrl++` e `Ctrl+-`
- [ ] Abrir a aba **Gramatica**: as producoes do Anexo I como dado, e as
      extensoes da segunda parte
- [ ] `dist/Guaxinim.exe`: arquivo unico de 43 MB, sem janela de console

---

## 6. Perguntas que o professor pode fazer

Respostas curtas, com a justificativa pronta. A secao 8 do relatorio lista as dez
discrepancias entre a especificacao e a implementacao; a maioria das respostas
abaixo aponta para uma delas, e as que nao apontam sao perguntas sobre o
automato, a recuperacao e o escopo do trabalho.

**Por que `programa` e nao so `program`?**
A especificacao lista `PROGRAM`. `programa` foi acrescentado porque o modelo de
programa que a IDE abre ao criar um arquivo novo usa essa grafia. As duas geram o
mesmo token `PROGRAM`.

**Por que acento da erro?**
A regra `ID` da especificacao e ASCII estrita. `numero` passa, `número` da erro
no `ú`. Preferimos seguir a regra escrita.

**O que acontece com identificador de 16 caracteres?**
Emite o token `ID` **e** registra erro. Se o token fosse descartado, a recuperacao
perderia a informacao do lexema.

**Por que `''` dentro de literal?**
Nao esta na regra `LITERAL`, mas e padrao no Pascal e permite `'d''art'`
significando `d'art`.

**Por que a lista de parametros e facultativa?**
O Anexo I exige `PROCEDURE ID ( parametros )`, mas Pascal aceita `procedure Q;`.
As duas formas passam, para nao gerar erro espurio na sintaxe mais comum.

**Por que o `;` final e facultativo?**
O Anexo I escreve `ID := exprOp ;`, o que exigiria `;` na ultima instrucao de todo
bloco. Nenhum Pascal real escreve `x := 1 end.`, entao passou a ser facultativo
antes de `end`, `until`, `else` e `.`. No meio do bloco continua obrigatorio.

**Por que `x := f(1)` funciona se o Anexo I so mostra `ID ( parametros2 ) ;`?**
`parametros2` ja e a lista de argumentos de chamada, entao foi acrescentada a
producao `fator -> variavel ( parametros2 )`. Sem isso, chamada de funcao em
expressao seria indeDerivavel.

**Como o analisador lexico sabe que `enum` e palavra e `enumerate` e identificador?**
Os estados da arvore de palavras reservadas tem uma transicao de saida para o
estado de identificador quando a proxima letra nao continua nenhuma palavra. E a
regra do maximo casamento fazendo o trabalho dela.

**Como o analisador lexico se recover de um erro e continua?**
Tres mecanismos, em `error_recovery.py`: pular o caractere invalido, sincronizar
no proximo `;` ou quebra de linha, e uma pilha de delimitadores. A analise nunca
aborta, entao varios erros sao reportados em uma passagem.

**Um bloco `begin ... end` aninhado exige `;` depois do `end`. Isso esta certo?**
Resposta honesta: e uma divergencia conhecida. O Anexo I especifica
`bloco -> BEGIN instrucoes END ;` e foi seguido a risca, mas o Pascal real dispensa
esse ponto e virgula. Ate o item 8 desta lista, que deixa a `;` final facultativo
*dentro* do bloco, o `;` que vem *depois* do `end` continua obrigatorio. Vale
admitir em vez de defender: a forma aceita hoje e `end;`. Detalhado na secao 8 do
relatorio, item 10.

**Por que o programa nao executa?**
O escopo do trabalho e a analise lexico-sintatica. Nao ha geracao de codigo nem
maquina virtual. `writeln` e reconhecido como identificador, e a analise termina
depois da gramatica.

**Como voce garante que o automato e determinista?**
`tests/test_dfa.py` monta a tabela de transicoes inteira e verifica que nao
existem dois simbolos iguais saindo do mesmo estado, que todo estado e
alcançavel a partir de `q0`, e que todo caminho de maximo casamento termina no
token esperado. Sao 139 testes so nisso.

---

## 7. Plano B

| Problema | O que fazer |
| --- | --- |
| O pip install falha | Os testes nao dependem de rede depois de `PySide6` instalado. Rode `pytest` mesmo assim e use o `.exe`. |
| A IDE nao abre | Rode `python main.py` e leia o erro no terminal. O executavel pronto e `dist/Guaxinim.exe`. |
| O projetor nao mostra o editor | `Ctrl+,` e aumente a fonte, ou `Ctrl++` duas vezes. |
| Um exemplo falhar | Os tres arquivos que importam sao `relatorio/exemplo.pas` (analise limpa, 250 tokens), o programa novo do editor e o exemplo embutido em `src/lexer/lexer.py`, que os testes exercitam em 135 casos. |
| O professor pedir o codigo | `README.md` tem a arvore de diretorios, `relatorio/relatorio.md` secao 10 tem o diagrama de modulos e a secao 11 a tabela de tokens. |