int main() {
  printf("PRUEBA DE EXPRESIONES CORRECTAS...\n");
  int temp;
  temp = 3 * 4;
  int x = 1 + temp * 4 - 5 - -temp;
  int y = temp + 2 *(3-2)/2;
  temp = temp - ((temp/(2-1)) + (x*2 -56));

  printf("Expresion con variables(56): %i\n", x);
  printf("Uso de variables y parentesis(13): %i\n", y);
  printf("modificacion de variables y parentesis anidados(-56): %i\n", temp);

  int z = 10/3;
  printf("Division truncada(3): %i\n", z);
  z = 3 *(10/3) + 1/2;
  printf("Expresion con division truncada(9): %i\n", z);
  z = 2 * 3/2 * 3;
  printf("Asociatividad por la izquierda(9): %i\n", z);
}
