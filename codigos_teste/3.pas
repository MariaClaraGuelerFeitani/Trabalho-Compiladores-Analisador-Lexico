program ParOuImpar;
var
  num: integer;
begin
  write('Digite um numero inteiro: ');
  readln(num);
  
  if num mod 2 = 0 then
    writeln(num, ' eh par')
  else
    writeln(num, ' eh impar');
    
  readkey;
end.   