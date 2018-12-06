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
        if cmd == "merge":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            adder = Adder(conf)
            adder.merge(args[0])
            return

    # if no action specified, explore
    runner = Runner(conf_dict)
    runner.loop()

if __name__ == '__main__':
    main()
