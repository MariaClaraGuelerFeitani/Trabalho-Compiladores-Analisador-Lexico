programa Incorreto;

{ Caso de teste 3 - erros e avisos semânticos.
  Cada linha comentada indica o diagnóstico esperado. }

const
  limite: integer = 10;

var
  contador, invisivel: integer;
  nome: string;
  total: real;

procedure somar(a, b: integer);
begin
  contador := a + b
end;

begin
  contador := 'texto';        { erro: atribuição incompatível string -> integer }
  total := contador;          { ok: integer promove para real }
  nome := 42;                 { erro: atribuição incompatível integer -> string }
  contador := total;          { erro: atribuição incompatível real -> integer }

  somar(1);                   { erro: 'somar' espera 2 argumento(s), encontrado 1 }
  somar(1, 2, 3);             { erro: 'somar' espera 2 argumento(s), encontrado 3 }
  somar('a', 2);              { erro: argumento 1 ('a'): esperado integer, encontrado string }

  contador := naoexiste;      { erro: identificador 'naoexiste' não declarado }
  limite := 5;                { erro: 'limite' é uma constante }
  for limite := 1 to 10 do    { erro: o laço 'for' exige uma variável }
    contador := 1;

  nome;                       { aviso: instrução sem efeito (aceita, mas avisado) }
  invisivel;                  { aviso: instrução sem efeito }
end.
