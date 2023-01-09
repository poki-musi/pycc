import main as m
import itertools
import sys
import os


def run_tests():
    for path, _, files in os.walk("./examples"):
        for file in files:
            file = path + "/" + file
            print("-" * 10 + " " + file + " " + "-" * 10)
            with open(file, "r") as f:
                data = f.read()
            print(m.process_file(data))
            print("-" * 10 + " " + file + " " + "-" * 10)


if __name__ == "__main__":
    run_tests()
