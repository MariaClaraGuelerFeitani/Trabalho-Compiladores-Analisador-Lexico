program SomaPares;
var
  superior, soma, num: integer;
begin
  write('Limite superior: ');
  readln(superior);
  
  soma := 0;
  num := 2;
  
  repeat
    soma := soma + num;
    num := num + 2;
  until (num > superior);
  
  writeln('Soma dos pares ate ', superior, ': ', soma);
end.   