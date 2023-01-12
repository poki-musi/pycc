int main() {
  int a;
  int *b = &a;
  int **c = &b;
  *b = 3;
  **&*&*&*c = 4;
}
