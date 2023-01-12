int mod(int x, int y) {
  while(x > y) {
    x = x - y;
  }
  return x;
}

int main() {
  for (int x = 1; x <= 15; x = x + 1) {
    if(mod(x, 5) != 0 && mod(x, 3) != 0) {
      continue;
    }

    if (mod(x, 5) == 0) {
      printf("foo");
    }
    if (mod(x, 3) == 0) {
      printf("bar");
    }
  }
}
