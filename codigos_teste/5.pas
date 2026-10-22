program Hipotenusa;
var
  cat1, cat2, hip: real;

function CalcularHipo(x, y: real): real;
begin
  CalcularHipo := sqrt(sqr(x) + sqr(y));
end;

begin
  write('Cateto A: ');
  readln(cat1);
  write('Cateto B: ');
  readln(cat2);
  
  hip := CalcularHipo(cat1, cat2);
  writeln('Hipotenusa: ', hip:5:2);
end.