import sys

from .engine import analyze
from .report import render


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    result = analyze(text)
    print(render(result))


if __name__ == "__main__":
    main()
