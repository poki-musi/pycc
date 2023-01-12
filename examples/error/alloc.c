int main() {
  int *x = (int*) malloc(3);
  int x;
  for(int i = 0; i < 3; i=i+1) {
    x[i] = i;
    int i;
  }
  free(x);
  free((void*)x);
}
