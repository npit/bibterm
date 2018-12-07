from runner import Runner
from adder import Adder
from config import get_config, get_conf_filepath
import argparse
from collections import namedtuple

def to_namedtuple(conf_dict):
    keys = sorted(conf_dict.keys())
    conf = namedtuple("conf", keys)(*[conf_dict[k] for k in keys])
    return conf


def main():
    help_str = ['Bibtex file explorer.'] + \
        ["Configuration file at {}\n".format(get_conf_filepath())]


    # read bib database configuration
    conf_dict = get_config()
    conf = to_namedtuple(conf_dict)

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
        if cmd == "inspect":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            conf_dict["bib_path"] = args[0]
            conf = to_namedtuple(conf_dict)
            adder = Adder(conf)

    # if no action specified, explore
    runner = Runner(conf)
    runner.loop()

if __name__ == '__main__':
    main()
