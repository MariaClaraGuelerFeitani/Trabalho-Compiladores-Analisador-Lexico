program Soma;
var
  a, b, resultado: integer;
begin
  write('Digite o primeiro numero: ');
  readln(a);
  write('Digite o segundo numero: ');
  readln(b);
  
  resultado := a + b;
  writeln('O resultado da soma eh: ', resultado);
  readkey; {Pausa para visualização}
end.   