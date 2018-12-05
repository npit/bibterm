from reader import read
from runner import Runner
from adder import Adder
from config import get_config, get_conf_filepath
import argparse
from collections import namedtuple


def main():
    help_str = ['Bibtex file explorer.'] + \
        ["Configuration file at {}\n".format(get_conf_filepath())]


    # read bib database configuration
    conf_dict = get_config()
    keys = sorted(conf_dict.keys())
    conf = namedtuple("conf", keys)(*[conf_dict[k] for k in keys])

    # args
    parser = argparse.ArgumentParser(description="\n".join(help_str))
    parser.add_argument("actions", nargs="*", help="Available: {}".format(", ".join(conf.actions)))
    args = parser.parse_args()


    if args.actions:
        cmd, *args = args.actions
        if cmd == "add":
            adder = Adder(conf)
            adder.add()
            return

    content = read(conf.bib_path)
    runner = Runner(content, conf_dict)
    runner.loop()


if __name__ == '__main__':
    main()
