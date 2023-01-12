void fizzbuzz(int x) {
  for (int i = 1; i <= x; i = i + 1) {
    if (i % 5 != 0 && i % 3 != 0) {
      printf("%i\n", i);
    }

    if (i % 5 == 0) {
      printf("fizz");
    }
    if (i % 3 == 0) {
      printf("buzz");
    }
    printf("\n");
  }
}

int main() {
  int x;
  scanf("%i", &x);
  fizzbuzz(x);
}
