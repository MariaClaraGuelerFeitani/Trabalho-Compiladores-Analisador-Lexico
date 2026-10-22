/* Gerado pelo Guaxinim Pascal IDE; nao editar a mao. */
#include <stdio.h>
#include <string.h>
#include <math.h>

#define GX_TAM_STRING 256

static char gx_bufs[8][GX_TAM_STRING];
static int gx_buf_atual = 0;

static char* gx_proximo_buffer(void) {
	char* b = gx_bufs[gx_buf_atual];
	gx_buf_atual = (gx_buf_atual + 1) % 8;
	return b;
}

static char* gx_concat(const char* a, const char* b) {
	char* saida = gx_proximo_buffer();
	snprintf(saida, GX_TAM_STRING, "%s%s", a, b);
	return saida;
}

static char* gx_char_para_str(char c) {
	char* saida = gx_proximo_buffer();
	saida[0] = c;
	saida[1] = '\0';
	return saida;
}

static char gx_str_para_char(const char* s) {
	return s ? s[0] : '\0';
}

static void gx_consumir_linha(void) {
	int ch;
	while ((ch = getchar()) != '\n' && ch != EOF) { }
}

int gx_a;
int gx_b;
int gx_resultado;

int main(void) {
	setvbuf(stdout, NULL, _IONBF, 0);
	printf("%s", "Digite o primeiro numero: ");
	scanf("%d", &gx_a);
	gx_consumir_linha();
	printf("%s", "Digite o segundo numero: ");
	scanf("%d", &gx_b);
	gx_consumir_linha();
	gx_resultado = gx_a + gx_b;
	printf("%s%d\n", "O resultado da soma eh: ", gx_resultado);
	/* instrucao sem efeito: readkey */
	return 0;
}
