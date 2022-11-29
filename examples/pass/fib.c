int fib(int n) {
  if(n <= 1) {
    return 1;
  } else {
    return fib(n-1) + fib(n-2);
  }
}

int fun() { return 3; }

void fun2(int *n) { *n = 0; }

int fun3(int *n, int x) {
  *n = 3;
  return *n + x;
}

int main() {
  int n = 0;
  scanf("%i\n", &n);
  printf("Llamada a funcion de un parametro: %i\n", fib(n));
  printf("Llamada a funcion sin parametros: %i\n", fun());
  fun2(&n);
  printf("Llamada con modificacion de un parametro por referencia(0): %i\n", n);
  int y = fun3(&n, 4);
  printf("Llamada con  dos parametros y modificacion de uno por referencia(3, 12): %i, %i\n",
         n, y);
}
