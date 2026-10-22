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

double gx_cat1;
double gx_cat2;
double gx_hip;
double gx_calcularhipo(double gx_x, double gx_y);

double gx_calcularhipo(double gx_x, double gx_y) {
	double gx_ret_calcularhipo = 0;
	gx_ret_calcularhipo = sqrt(((gx_x) * (gx_x)) + ((gx_y) * (gx_y)));
	return gx_ret_calcularhipo;
}

int main(void) {
	printf("%s", "Cateto A: ");
	scanf("%lf", &gx_cat1);
	gx_consumir_linha();
	printf("%s", "Cateto B: ");
	scanf("%lf", &gx_cat2);
	gx_consumir_linha();
	gx_hip = gx_calcularhipo(gx_cat1, gx_cat2);
	printf("%s%5.2f\n", "Hipotenusa: ", gx_hip);
	return 0;
}
