int do_stuff(int x, int y) {
  if(x || y) {
    return x;
  } else {
    return y;
  }
  sizeof(int);
  sizeof(int*[3]);
}

int main() {
  int x = 0, y = 0;
  while (do_stuff(x, y)) {
    x = x + 1;
    y = y + 1;

    if(x == 0) { break; }
  }
}
