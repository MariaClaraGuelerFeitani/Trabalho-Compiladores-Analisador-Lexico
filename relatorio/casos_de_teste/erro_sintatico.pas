programa Quebrado;

{ Caso de teste 2 - erros sintáticos com recuperação em modo pânico.
  Linha 11: falta o 'then' depois da condição do if.
  Linha 13: falta o 'do' depois do limite do for.
  O parser registra cada erro com linha, coluna, lexema encontrado e o
  token esperado, e continua a análise: as demais linhas são analisadas
  e nenhum outro erro é reportado. }

var
  total: integer;

begin
  total := 10;
  if total > 5 total := total + 1;
  for total := 1 to 10 total := total + 1;
  writeln(total)
end.
