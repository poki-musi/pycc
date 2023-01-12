int main() {
  int *x = (int*) malloc(3);
  for(int i = 0; i < 3; i=i+1) {
    x[i] = i;
  }
  free((void*)x);
}
