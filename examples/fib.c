int fib(int n) {
  return n <= 1 && n || (fib(n-1) + fib(n-2));
}

int main() {
  printf("%i\n", fib(10));
}
