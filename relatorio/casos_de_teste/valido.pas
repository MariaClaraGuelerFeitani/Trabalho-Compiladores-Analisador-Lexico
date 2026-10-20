programa Estatisticas;

{ Caso de teste 1 - programa 100% valido para as tres fases.
  Exercita: const, type (enumeracao e record), var, procedure, function,
  for ... to / downto, if/else, while, repeat/until, break, continue,
  chamadas com argumentos e as funcoes predefinidas writeln/write. }

type
  cor = (vermelho, verde, azul);
  ponto = record
    x, y: real;
    rotulo: string;
  end;

const
  limite: integer = 5;
  titulo = 'totais';

var
  i, soma, contador: integer;
  media: real;
  atual: cor;
  p: ponto;

procedure mostrar(texto: string; valor: real);
begin
  write(texto, valor)
end;

function dobro(n: integer): integer;
begin
  dobro := n * 2
end;

function maximo(a, b: integer): integer;
begin
  if a > b then
    maximo := a
  else
    maximo := b
end;

BEGIN
  soma := 0;
  contador := 0;

  { laço for com to: o contador de 3 e pulado pelo continue }
  for i := 1 to limite do
  begin
    if i = 3 then
      continue
    else
      soma := soma + i
  end;

  { laço for com downto }
  for i := limite downto 1 do
    contador := contador + 1;

  { laço while }
  while contador > 0 do
    contador := contador - 1;

  { laço repeat/until }
  repeat
    soma := soma - 1
  until soma <= 0;

  { divisão produz real; integer promove para real na atribuição }
  media := soma / 2.0;
  mostrar(titulo, media);

  { enumeração e registro }
  atual := azul;
  p.x := 1.5;
  p.y := dobro(2);
  p.rotulo := 'ponto';
  mostrar(p.rotulo, maximo(3, 7));

  if atual = verde ou soma > 0 then
    writeln(titulo)
  else
    writeln(p.rotulo);

  if soma = 0 then
    writeln('fim')
  else
    break;
end.
