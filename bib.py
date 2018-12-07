from runner import Runner
from reader import Reader
from writer import BibWriter
from config import get_config, get_conf_filepath
import argparse
from collections import namedtuple
import visual

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

    vis = visual.setup(conf)

    if args.actions:
        cmd, *args = args.actions
        if cmd == "add":
            writer = BibWriter(conf)
            writer.add()
            return
        elif cmd == "merge":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            reader = Reader(conf)
            reader.read()

            reader2 = Reader(conf)
            reader2.bib_path = args[0]
            reader2.read()

            writer = BibWriter(conf)
            merged_collection = writer.merge(reader.get_entry_collection(), reader2.get_entry_collection())
            vis.print("Inspecting merged collection.")
            runner = Runner(conf, entry_collection=merged_collection)
            runner.loop()
            what = vis.input("Proceed to write? [y]es [n]o: ")
            if what.lower() == "y":
                writer.write(merged_collection)
                vis.print("Wrote.")
            else:
                vis.print("Aborting.")
            return
        elif cmd == "inspect":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            conf_dict["bib_path"] = args[0]
            conf = to_namedtuple(conf_dict)
            reader = Reader(conf)
            reader.read()
            runner = Runner(conf, entry_collection=reader.get_entry_collection())
            runner.loop()
            return
        else:
            print("Undefined command: {}".format(cmd))
            return


    # if no action specified, explore
    runner = Runner(conf)
    runner.loop()

if __name__ == '__main__':
    main()
