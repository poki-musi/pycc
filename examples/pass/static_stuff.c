int main() {
  static int x;
  int *y[3];

  *y[0] = x + 1;
}
