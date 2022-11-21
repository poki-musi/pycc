int fib(int n) {
  return n <= 1 && n || (fib(n-1) + fib(n-2));
}

int main() {
  int n = 0;
  scanf("%i\n", &n);
  printf("%i\n", fib(n));
}
