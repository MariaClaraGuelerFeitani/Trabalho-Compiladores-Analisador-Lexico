"""Análise semântica: verificação de declarações, escopos e tipos.

`AnaliseSemantica` não percorre a fonte por conta própria: o analisador
sintático de descida recursiva chama seus métodos (ganchos) nos pontos em que
cada construção é reconhecida — declarações, atribuições, chamadas, acessos a
campos e expressões. Cada gancho recebe o `Token` envolvido, de modo que todo
erro e aviso sai com linha, coluna e lexema, no mesmo formato dos erros
léxicos e sintáticos (`LexicalError` / `Warning`), e o IDE os exibe nas mesmas
abas e com o mesmo sublinhado.

Regras implementadas (ver `relatorio/relatorio.md`, seção da etapa 2):

- escopos encadeados: global + um escopo por procedimento/função, com
  sombreamento permitido e redeclaração no mesmo escopo rejeitada;
- declaração obrigatória de todo identificador usado;
- compatibilidade de tipos em atribuição, com única promoção `integer` para
  `real` (regra de Pascal); divisão `/` sempre produz `real`;
- operadores aritméticos exigem operandos numéricos; `E`, `OU` e os
  comparadores exigem operandos comparáveis/lógicos;
- nome de função só recebe atribuição dentro do próprio corpo e com o tipo de
  retorno declarado;
- chamadas verificam número e tipos dos argumentos, inclusive das funções
  predefinidas (`write`, `writeln`, `read`, `readln`);
- laço `for` exige variável inteira não constante como controle;
- variáveis declaradas e não usadas geram aviso ao fechar o escopo.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..lexer.tokens import DIVISAO
from ..services.lexer_service import LexicalError, Token, Warning
from . import tabela as tb
from . import tipos as tp

PREDEFINIDOS = ("write", "writeln", "read", "readln")

COMPARADORES = ("=", "<>", "<", "<=", ">", ">=")


@dataclass(frozen=True)
class InfoAcesso:
    """Resultado de um acesso `id`, `id[expr]` ou `id.campo`."""

    token: Token
    categoria: str = ""
    tipo: str = ""
    eh_campo: bool = False


@dataclass(frozen=True)
class ResultadoSemantico:
    """Erros, avisos e a tabela final da análise semântica."""

    erros: tuple[LexicalError, ...] = ()
    avisos: tuple[Warning, ...] = ()
    tabela: tuple[tb.Entrada, ...] = ()


class AnaliseSemantica:
    """Verificador semântico dirigido pelos ganchos do parser."""

    def __init__(self) -> None:
        self._tabela = tb.TabelaDeSimbolos()
        self._erros: list[LexicalError] = []
        self._avisos: list[Warning] = []
        self._subprogramas: list[tb.Entrada] = []
        self._registradas: list[tb.Entrada] = []
        for nome in PREDEFINIDOS:
            self._declarar(tb.Entrada(nome, tb.PREDEFINIDO, variadico=True), None)

    # --- Diagnóstico ------------------------------------------------------

    def _erro(self, mensagem: str, token: Token | None) -> None:
        if token is None:
            self._erros.append(LexicalError(1, 1, f"semantica: {mensagem}"))
            return
        self._erros.append(
            LexicalError(
                token.linha,
                token.coluna,
                f"semantica: {mensagem}",
                token.lexema,
                max(1, len(token.lexema)),
            )
        )

    def _aviso(self, mensagem: str, token: Token | None) -> None:
        if token is None:
            self._avisos.append(Warning(1, 1, f"semantica: {mensagem}"))
            return
        self._avisos.append(
            Warning(token.linha, token.coluna, f"semantica: {mensagem}")
        )

    def resultado(self) -> ResultadoSemantico:
        """Consolida erros, avisos e todas as entradas declaradas."""
        return ResultadoSemantico(
            tuple(self._erros),
            tuple(self._avisos),
            tuple(self._registradas),
        )

    # --- Ciclo de vida do programa ----------------------------------------

    def programa_iniciar(self) -> None:
        self._tabela.abrir_escopo("programa")

    def programa_encerrar(self) -> None:
        encerrado = self._tabela.fechar_escopo()
        self._avisar_nao_usadas(encerrado)

    def abrir_subprograma(
        self,
        token: Token,
        eh_funcao: bool,
        parametros: tuple[tuple[str, str], ...],
        tipo_retorno: str,
    ) -> None:
        """Declara o subprograma no escopo externo e abre o escopo do corpo."""
        categoria = tb.FUNCAO if eh_funcao else tb.PROCEDIMENTO
        for _, tipo_parametro in parametros:
            if not self._tipo_valido(tipo_parametro):
                self._erro(f"tipo '{tipo_parametro}' não declarado", token)
        if eh_funcao and not self._tipo_valido(tipo_retorno):
            self._erro(f"tipo '{tipo_retorno}' não declarado", token)
        entrada = tb.Entrada(
            token.lexema,
            categoria,
            tipo=tipo_retorno,
            linha=token.linha,
            coluna=token.coluna,
            parametros=list(parametros),
            tipo_retorno=tipo_retorno,
        )
        self._declarar(entrada, token)
        self._tabela.abrir_escopo(token.lexema.lower())
        self._subprogramas.append(entrada)
        for nome_parametro, tipo_parametro in parametros:
            self._declarar(
                tb.Entrada(
                    nome_parametro,
                    tb.PARAMETRO,
                    tipo=tipo_parametro,
                    linha=token.linha,
                    coluna=token.coluna,
                ),
                token,
            )
        if eh_funcao:
            # Dentro do corpo, o nome da função é o "variável" de retorno:
            # é assim que `dobro := n * 2` é validado.
            self._declarar(
                tb.Entrada(
                    token.lexema,
                    tb.FUNCAO,
                    tipo=tipo_retorno,
                    linha=token.linha,
                    coluna=token.coluna,
                    parametros=list(parametros),
                    tipo_retorno=tipo_retorno,
                    eh_propria=True,
                ),
                token,
            )

    def fechar_subprograma(self) -> None:
        if not self._subprogramas:
            return
        self._subprogramas.pop()
        encerrado = self._tabela.fechar_escopo()
        self._avisar_nao_usadas(encerrado)

    def _avisar_nao_usadas(self, escopo: tb.Escopo) -> None:
        for entrada in escopo.entradas.values():
            if entrada.categoria == tb.VARIAVEL and not entrada.usado:
                self._aviso(
                    f"variável '{entrada.nome}' declarada e não usada",
                    Token("ID", entrada.nome, entrada.linha, entrada.coluna),
                )

    # --- Declarações ------------------------------------------------------

    def _declarar(self, entrada: tb.Entrada, token: Token | None) -> None:
        anterior = self._tabela.declarar(entrada)
        self._registradas.append(entrada)
        if anterior is not None and token is not None:
            self._erro(
                f"'{entrada.nome}' já declarado na linha {anterior.linha} "
                f"como {anterior.categoria}",
                token,
            )

    def declarar_variaveis(
        self, nomes: tuple[Token, ...], tipo: str
    ) -> None:
        if not tipo:
            return
        if not self._tipo_valido(tipo):
            self._erro(f"tipo '{tipo}' não declarado", nomes[0] if nomes else None)
            return
        for token in nomes:
            self._declarar(
                tb.Entrada(token.lexema, tb.VARIAVEL, tipo, token.linha, token.coluna),
                token,
            )

    def declarar_constante(
        self, token: Token, tipo_declarado: str, tipo_valor: str
    ) -> None:
        if tipo_declarado and not self._tipo_valido(tipo_declarado):
            self._erro(f"tipo '{tipo_declarado}' não declarado", token)
            return
        if (
            tipo_declarado
            and tipo_valor
            and not tp.compativel_atribuicao(tipo_declarado, tipo_valor)
        ):
            self._erro(
                f"valor de tipo {tp.descrever(tipo_valor)} incompatível "
                f"com a constante {tp.descrever(tipo_declarado)}",
                token,
            )
            return
        self._declarar(
            tb.Entrada(
                token.lexema,
                tb.CONSTANTE,
                tipo_declarado or tipo_valor,
                token.linha,
                token.coluna,
            ),
            token,
        )

    def declarar_tipo(
        self,
        token: Token,
        tipo_base: str,
        campos: tuple[tuple[str, str], ...] | None,
        constantes: tuple[str, ...] | None,
    ) -> None:
        if campos is not None:
            for _, tipo_campo in campos:
                if not self._tipo_valido(tipo_campo):
                    self._erro(f"tipo '{tipo_campo}' não declarado", token)
            entrada = tb.Entrada(
                token.lexema,
                tb.TIPO_REGISTRO,
                linha=token.linha,
                coluna=token.coluna,
                campos={nome.lower(): tipo for nome, tipo in campos},
            )
            self._declarar(entrada, token)
            return
        if constantes is not None:
            entrada = tb.Entrada(
                token.lexema,
                tb.TIPO_ENUMERACAO,
                linha=token.linha,
                coluna=token.coluna,
            )
            self._declarar(entrada, token)
            for nome in constantes:
                self._declarar(
                    tb.Entrada(
                        nome,
                        tb.CONSTANTE_ENUM,
                        tipo=token.lexema,
                        linha=token.linha,
                        coluna=token.coluna,
                    ),
                    token,
                )
            return
        if tipo_base and not self._tipo_valido(tipo_base):
            self._erro(f"tipo '{tipo_base}' não declarado", token)
            return
        self._declarar(
            tb.Entrada(
                token.lexema,
                tb.TIPO,
                tipo_base,
                token.linha,
                token.coluna,
            ),
            token,
        )

    # --- Tipos ------------------------------------------------------------

    def _resolver(self, nome: str) -> str:
        """Segue a cadeia de apelidos até o tipo real do dialeto."""
        base_de: dict[str, str] = {}
        escopo: tb.Escopo | None = self._tabela.atual
        while escopo is not None:
            for chave, entrada in escopo.entradas.items():
                if entrada.categoria == tb.TIPO:
                    base_de.setdefault(chave, entrada.tipo)
            escopo = escopo.pai
        return tp.resolver_alias(nome, base_de)

    def _tipo_valido(self, tipo: str) -> bool:
        if not tipo:
            return False
        resolvido = self._resolver(tipo)
        if resolvido in (tp.INTEIRO, tp.REAL, tp.CHAR, tp.TIPO_STRING):
            return True
        entrada = self._tabela.buscar(resolvido)
        return entrada is not None and entrada.categoria in (
            tb.TIPO,
            tb.TIPO_ENUMERACAO,
            tb.TIPO_REGISTRO,
        )

    # --- Acessos ----------------------------------------------------------

    def acesso(self, token: Token, como_alvo: bool = False) -> InfoAcesso:
        """Avalia o uso de `token` como valor (ou como alvo de atribuição)."""
        entrada = self._tabela.buscar(token.lexema)
        if entrada is None:
            self._erro(f"identificador '{token.lexema}' não declarado", token)
            return InfoAcesso(token, tipo=tp.DESCONHECIDO)
        if como_alvo:
            return self._acesso_como_alvo(token, entrada)
        if entrada.categoria in (tb.PROCEDIMENTO, tb.PREDEFINIDO):
            self._erro(
                f"'{token.lexema}' é um procedimento e não pode ser usado "
                "em uma expressão",
                token,
            )
            return InfoAcesso(token, entrada.categoria, tp.DESCONHECIDO)
        if entrada.categoria in (tb.TIPO, tb.TIPO_ENUMERACAO, tb.TIPO_REGISTRO):
            self._erro(
                f"'{token.lexema}' é um tipo e não pode ser usado como valor",
                token,
            )
            return InfoAcesso(token, entrada.categoria, tp.DESCONHECIDO)
        if entrada.categoria == tb.FUNCAO:
            return InfoAcesso(token, tb.FUNCAO, entrada.tipo_retorno)
        return InfoAcesso(token, entrada.categoria, self._resolver(entrada.tipo))

    def _acesso_como_alvo(self, token: Token, entrada: tb.Entrada) -> InfoAcesso:
        if entrada.categoria == tb.CONSTANTE:
            self._erro(
                f"'{token.lexema}' é uma constante e não pode receber atribuição",
                token,
            )
            return InfoAcesso(token, entrada.categoria, tp.DESCONHECIDO)
        if entrada.categoria in (tb.PROCEDIMENTO, tb.PREDEFINIDO):
            self._erro(f"'{token.lexema}' não é uma variável", token)
            return InfoAcesso(token, entrada.categoria, tp.DESCONHECIDO)
        if entrada.categoria == tb.FUNCAO and not entrada.eh_propria:
            self._erro(
                f"'{token.lexema}' é uma função; somente o próprio corpo "
                "pode atribuir a ela",
                token,
            )
            return InfoAcesso(token, entrada.categoria, tp.DESCONHECIDO)
        if entrada.categoria == tb.FUNCAO:
            return InfoAcesso(token, tb.FUNCAO, entrada.tipo_retorno)
        return InfoAcesso(token, entrada.categoria, self._resolver(entrada.tipo))

    def acesso_campo(self, base: InfoAcesso, campo: Token | None) -> InfoAcesso:
        """Tipo do campo `base.campo`; exige que `base` seja um registro."""
        if campo is None:
            return base
        if not base.tipo:
            return InfoAcesso(campo, tipo=tp.DESCONHECIDO)
        resolvido = self._resolver(base.tipo)
        entrada_tipo = self._tabela.buscar(resolvido)
        if entrada_tipo is None or entrada_tipo.categoria != tb.TIPO_REGISTRO:
            self._erro(f"'{tp.descrever(base.tipo)}' não é um registro", campo)
            return InfoAcesso(campo, tipo=tp.DESCONHECIDO)
        tipo_campo = entrada_tipo.campos.get(campo.lexema.lower())
        if tipo_campo is None:
            self._erro(
                f"o campo '{campo.lexema}' não existe em '{resolvido}'", campo
            )
            return InfoAcesso(campo, tipo=tp.DESCONHECIDO)
        return InfoAcesso(campo, "campo", self._resolver(tipo_campo), True)

    def acesso_indice(self, base: InfoAcesso, marca: Token | None) -> InfoAcesso:
        """Índices são aceitos sem checagem de tipo: o dialeto não declara
        vetores; a expressão do índice já foi analisada pelo próprio parser."""
        return base

    # --- Instruções -------------------------------------------------------

    def verificar_atribuicao(self, alvo: InfoAcesso, tipo_expr: str) -> None:
        if not alvo.tipo or not tipo_expr:
            return
        if not tp.compativel_atribuicao(alvo.tipo, tipo_expr):
            self._erro(
                f"atribuição incompatível: não é possível atribuir "
                f"{tp.descrever(tipo_expr)} a {tp.descrever(alvo.tipo)}",
                alvo.token,
            )

    def verificar_condicao(
        self, tipo: str, token: Token | None, comando: str
    ) -> None:
        if tipo and tipo != tp.LOGICO:
            self._erro(
                f"o comando '{comando}' espera uma condição lógica, "
                f"encontrado {tp.descrever(tipo)}",
                token,
            )

    def verificar_controle_de_for(self, token: Token) -> str:
        """A variável de controle do `for` deve ser uma variável inteira."""
        entrada = self._tabela.buscar(token.lexema)
        if entrada is None:
            self._erro(f"identificador '{token.lexema}' não declarado", token)
            return tp.DESCONHECIDO
        if entrada.categoria in (tb.CONSTANTE, tb.CONSTANTE_ENUM):
            self._erro(
                f"o laço 'for' exige uma variável; '{token.lexema}' "
                f"é uma constante",
                token,
            )
            return tp.DESCONHECIDO
        if entrada.categoria not in (tb.VARIAVEL, tb.PARAMETRO):
            self._erro(
                f"o laço 'for' exige uma variável; '{token.lexema}' "
                f"é um {entrada.categoria}",
                token,
            )
            return tp.DESCONHECIDO
        tipo = self._resolver(entrada.tipo)
        if tipo != tp.INTEIRO:
            self._erro(
                f"o laço 'for' espera uma variável integer; '{token.lexema}' "
                f"é {tp.descrever(tipo)}",
                token,
            )
        return tipo

    def verificar_limite_de_for(
        self, tipo_controle: str, tipo_limite: str, token: Token | None
    ) -> None:
        if tipo_controle == tp.INTEIRO and tipo_limite and tipo_limite != tp.INTEIRO:
            self._erro(
                "o laço 'for' espera limites inteiros, "
                f"encontrado {tp.descrever(tipo_limite)}",
                token,
            )

    def verificar_chamada(
        self,
        token: Token,
        tipos_argumentos: tuple[str, ...],
        como_instrucao: bool = False,
    ) -> str:
        """Confere existência, aridade e tipos; devolve o tipo de retorno."""
        entrada = self._tabela.buscar(token.lexema)
        if entrada is None:
            self._erro(f"identificador '{token.lexema}' não declarado", token)
            return tp.DESCONHECIDO
        if not entrada.eh_subprograma:
            self._erro(
                f"'{token.lexema}' não é um procedimento ou função", token
            )
            return tp.DESCONHECIDO
        if not entrada.variadico:
            esperados = len(entrada.parametros)
            encontrados = len(tipos_argumentos)
            if encontrados != esperados:
                self._erro(
                    f"'{token.lexema}' espera {esperados} argumento(s), "
                    f"encontrado {encontrados}",
                    token,
                )
                return entrada.tipo_retorno
            for indice, ((nome, tipo), tipo_argumento) in enumerate(
                zip(entrada.parametros, tipos_argumentos), start=1
            ):
                if not tp.compativel_atribuicao(self._resolver(tipo), tipo_argumento):
                    self._erro(
                        f"argumento {indice} ('{nome}'): esperado "
                        f"{tp.descrever(self._resolver(tipo))}, "
                        f"encontrado {tp.descrever(tipo_argumento)}",
                        token,
                    )
        return entrada.tipo_retorno

    def instrucao_isolada(self, token: Token) -> bool:
        """`Q;` é uma chamada quando `Q` é subprograma; senão, não faz efeito.

        Um identificador não declarado em instrução isolada não vira erro de
        declaração: o enunciado exige apenas o aviso de instrução sem efeito,
        que o próprio parser emite ao receber `False` aqui.
        """
        entrada = self._tabela.buscar(token.lexema)
        if entrada is None:
            return False
        if entrada.categoria == tb.PROCEDIMENTO:
            self.verificar_chamada(token, ())
            return True
        if entrada.categoria == tb.PREDEFINIDO:
            return True
        if entrada.categoria == tb.FUNCAO:
            if entrada.parametros:
                self._erro(
                    f"'{token.lexema}' exige {len(entrada.parametros)} "
                    "argumento(s)",
                    token,
                )
            return True
        return False

    def uso_sem_argumentos(self, token: Token, info: InfoAcesso) -> str:
        """Uso de `token` em expressão sem parênteses: chamada sem argumentos."""
        entrada = self._tabela.buscar(token.lexema)
        if entrada is None:
            return tp.DESCONHECIDO
        if entrada.categoria == tb.FUNCAO and entrada.parametros:
            self._erro(
                f"'{token.lexema}' exige {len(entrada.parametros)} argumento(s); "
                f"use '{token.lexema}(...)'",
                token,
            )
            return tp.DESCONHECIDO
        if entrada.categoria == tb.FUNCAO:
            return entrada.tipo_retorno
        return info.tipo

    # --- Inferência de expressões -----------------------------------------

    def combinar_aritmetico(
        self, esquerda: str, direita: str, operador: Token
    ) -> str:
        resultado = tp.resultado_aritmetico(esquerda, direita)
        if not esquerda or not direita:
            return tp.DESCONHECIDO
        if resultado == tp.DESCONHECIDO:
            self._erro(
                f"operandos incompatíveis em '{operador.lexema}': "
                f"{tp.descrever(esquerda)} e {tp.descrever(direita)}",
                operador,
            )
            return tp.DESCONHECIDO
        if operador.tipo == DIVISAO:
            # Divisão `/` de Pascal: sempre produz `real`.
            return tp.REAL
        return resultado

    def combinar_unario(self, tipo: str, operador: Token) -> str:
        if not tipo:
            return tp.DESCONHECIDO
        if tipo not in tp.TIPOS_NUMERICOS:
            self._erro(
                f"o operador '{operador.lexema}' espera um valor numérico, "
                f"encontrado {tp.descrever(tipo)}",
                operador,
            )
            return tp.DESCONHECIDO
        return tipo

    def comparar(self, esquerda: str, direita: str, operador: Token) -> str:
        if esquerda and direita and not tp.comparaveis(esquerda, direita):
            self._erro(
                f"tipos incompatíveis em '{operador.lexema}': "
                f"{tp.descrever(esquerda)} e {tp.descrever(direita)}",
                operador,
            )
        return tp.LOGICO

    def combinar_logico(
        self, esquerda: str, direita: str, operador: Token
    ) -> str:
        if esquerda and direita and tp.LOGICO not in (esquerda, direita):
            self._erro(
                f"o operador '{operador.lexema}' espera valores lógicos, "
                f"encontrado {tp.descrever(esquerda)} e {tp.descrever(direita)}",
                operador,
            )
        elif esquerda and direita and (esquerda != tp.LOGICO or direita != tp.LOGICO):
            invalido = esquerda if esquerda != tp.LOGICO else direita
            self._erro(
                f"o operador '{operador.lexema}' espera valores lógicos, "
                f"encontrado {tp.descrever(invalido)}",
                operador,
            )
        return tp.LOGICO


__all__ = [
    "PREDEFINIDOS",
    "AnaliseSemantica",
    "InfoAcesso",
    "ResultadoSemantico",
]
