from runner import Runner
import utils
from reader import Reader
from writer import BibWriter
from getter import Getter
from config import get_config, get_conf_filepath
import argparse
from collections import namedtuple
import visual
import clipboard


def to_namedtuple(conf_dict):
    keys = sorted(conf_dict.keys())
    conf = namedtuple("conf", keys)(*[conf_dict[k] for k in keys])
    return conf


def merge(conf, vis, args, string_data=None):
    copying_single_string = False
    reader = Reader(conf)
    reader.read()
    reader2 = Reader(conf)
    if not args:
        if string_data is None:
            vis.print("No file argument specified, merging from clipboard.")
            string_data = clipboard.paste()
        reader2.read_string(string_data)
        if len(reader2.get_entry_collection().entries) == 1:
            # copy citation key for single-item copies, for your pleasure
            copying_single_string = True
            citation_key = next(iter(reader2.get_entry_collection().entries.values())).get_citation()
    else:
        reader2.read(args[0])

    if len(reader2.get_entry_collection().entries) == 0:
        vis.print("Zero items extracted from the collection to merge, exiting.")
        return
    writer = BibWriter(conf)
    merged_collection = writer.merge(reader.get_entry_collection(), reader2.get_entry_collection())
    if merged_collection is None:
        return
    # inspect, if merging a large one
    if not copying_single_string:
        # copying a large collection from a file: inspect and verify overwriting
        vis.print("Inspecting the merged collection.")
        runner = Runner(conf, entry_collection=merged_collection)
        runner.loop()
        what = vis.input("Proceed to write?", "*yes no")
        if utils.matches(what, "yes"):
            writer.write(merged_collection)
            vis.print("Wrote!")
        else:
            vis.print("Aborting.")
    else:
        clipboard.copy(citation_key)
        vis.print("Copied citation key to clipboard: {}".format(citation_key))


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

        if cmd == "merge":
            merge(conf, vis, args)
            return
        elif cmd == "get":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            getter = Getter(conf)
            res = getter.get(" ".join(args))
            # from here, merge from copied string
            merge(conf, vis, None, string_data=res)
            breakpoint()
            return

        elif cmd == "inspect":
            if not args:
                print("Need an argument for command {}".format(cmd))
                return
            reader = Reader(conf)
            reader.read(args[0])
            runner = Runner(conf, entry_collection=reader.get_entry_collection())
            runner.loop()
            return
        else:
            # then it has to be a runner control
            runner = Runner(conf)
            if any([cmd.startswith(x) for x in conf.controls.values()]):
                runner.loop(input_cmd=cmd)
            else:
                print("Undefined command: {}".format(cmd))

            return

    # if no action specified, explore
    runner = Runner(conf)
    runner.loop()


if __name__ == '__main__':
    main()
