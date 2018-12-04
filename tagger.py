from reader import read
from runner import Runner


def main():
    basefilename = "library.bib"
    content = read(basefilename)
    runner = Runner(content)
    runner.loop()


if __name__ == '__main__':
    main()
