programa Fatorial;

// Comentario de linha: texto depois de duas barras e descartado.

{ Comentario de bloco.
  Pode ocupar varias linhas e aceita
  {aninhamento} como este. }

(* Comentario de parenteses e asterisco.
   Tambem aceita aninhamento: {isto aqui dentro}. *)

const
  limite: integer = 10;
  titulo = 'numeros';

type
  cor = (vermelho, verde, azul);
  brilho = (claro..escuro);
  ponto = record
    x, y: real;
    rotulo: string;
  end;

var
  contador: integer;
  total: real;
  atual: cor;
  tom: brilho;
  p: ponto;
  mensagem_vazia: string;

procedure mostrar(texto: string);
begin
  writeln(texto)
end;

function dobro(n: integer): integer;
begin
  dobro := n * 2
end;

BEGIN
  // a linguagem nao diferencia maiusculas de minculas
  contador := 0;
  total := 0.0;

  while contador < limite do
  begin
    contador := contador + 1;
    if contador = 3 then
      continue
    else
      total := total + contador / 2.0
  end;

  repeat
    contador := contador - 1
  until contador <= 0;

  for i := 1 to 5 do
    total := total + 1.0;
  for j := 5 downto 1 do
    total := total - 1.0;

  if total > 1.0 e total < 100.0 ou total <> 0.0 then
    mostrar('total no intervalo')
  else
    mostrar('total fora');

  atual := verde;
  tom := claro;

  { identificadores podem ter ate 15 caracteres e o primeiro tem de ser
    uma letra; os demais podem ser letras, numeros ou o underline. }
  mensagem_vazia := titulo;

  p.x := 1.5;
  p.y := 2.5;
  p.rotulo := 'd''art';

  mostrar(p.rotulo);
  mostrar(dobro(21));

  { writeln e apenas um identificador; nada e executado de verdade,
    o trabalho para na analise lexico e sintatico. }
end.