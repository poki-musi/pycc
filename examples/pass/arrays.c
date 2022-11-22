int* back(int **a) {
  return *a;
}

int** back2(int *a) {
  return &a;
}

int main() {
  printf("PRUEBA DE ARRAYS CORRECTOS...\n");
  int a[3];
  int b[1];
  b[0] = 5;
  printf("Array de una sola posicion: %i", b[0]);
  int x = a[0];
  x = x + 1;
  a[1] = 2;
  printf("Asignacion de primera posicion sin inicializar: %i", x);
  printf("segunda posicion del vector (2): %i", a[1]);
  a[2] = a[1]*3 -(4-3);
  printf("tercera posicion del vector igual a expresion (5): %i", a[2]);
  printf("Imprimir puntero de array(error?): %i", a);
}