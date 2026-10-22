# codigos_teste — pasta temporaria

> **Esta pasta e temporaria.** Ela existe so para registrar, em uso real, a
> cadeia Pascal -> C -> `.exe` da IDE, e nao faz parte da entrega do trabalho:
> pode ser apagada em qualquer commit futuro sem prejuizo de nada.

Sao os cinco programas digitados a mao durante os testes da interface, cada um
com o `.c` gerado pelo tradutor e (quando gerado) o `.exe` do TCC embutido ao
lado:

| Arquivo | O que exercita |
| --- | --- |
| `1.pas` | `OlaMundo` — programa minimo, `writeln` de string |
| `2.pas` | `Soma` — dois `readln` interativos e soma inteira |
| `3.pas` | `ParOuImpar` — `if`/`else` com `mod 2` |
| `4.pas` | `SomaPares` — `repeat ... until` com varias instrucoes |
| `5.pas` | `Hipotenusa` — funcao, `sqrt`/`sqr` e `writeln(x:5:2)` |

Observacoes:

- `2.pas` e `3.pas` terminam com `readkey;` para pausar antes de fechar.
  `readkey` nao e palavra desta linguagem, entao a analise so emite o aviso
  "instrucao sem efeito" e o programa roda normalmente — o terminal embutido
  (F5) e o console novo (F9) ja seguram a tela no fim.
- Os arquivos `.c` e `.exe` sao saida gerada, nao editados a mao; se os
  `.pas` mudarem, basta apertar F5 ou F9 de novo para regrava-los.
