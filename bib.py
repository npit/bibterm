import argparse

import clipboard

import visual
from config import Config
from reader.reader import Reader
from runner import Runner
from utils import paste
from writer import Writer

# abstract for gui.
# show screen
# update screen
# 
# show table (impl for my manual shit, impl for terminaltables)
# ...

def merge(conf, vis, merge_args, string_data=None):
    copying_single_string = False
    reader = Reader(conf)
    reader.read()
    reader2 = Reader(conf)

    if merge_args:
        vis.print("Merging from argument: {}.".format(merge_args))
        reader2.read(merge_args[0])
    else:
        vis.print("Merging copied content.")
        reader2.read_string(paste(single_line=False))
    if len(reader2.get_entry_collection().entries) == 0:
        vis.print("Zero items extracted from the collection to merge, exiting.")
        return
    writer = Writer(conf)
    merged_collection = writer.merge(reader.get_entry_collection(), reader2.get_entry_collection())
    copying_single_string = len(reader2.get_entry_collection().entries) == 1
    if merged_collection is None:
        return
    # inspect, if merging a large one
    if not copying_single_string:
        # copying a large collection from a file: inspect and verify overwriting
        vis.print("Inspecting the merged collection.")
        runner = Runner(conf, entry_collection=merged_collection)
        runner.loop()
        writer.write_confirm(merged_collection)
    else:
        citation_key = next(iter(reader2.get_entry_collection().entries.values())).get_citation()
        vis.print("Writing updated library.")
        writer.write(merged_collection)
        clipboard.copy(citation_key)
        vis.print("Copied citation key to clipboard: {}".format(citation_key))


def main():
    conf = Config()
    help_str = ['Bibtex file explorer.'] + \
        ["Configuration file at {}\n".format(conf.get_filepath())]

    # read bib database configuration
    conf_dict = conf.get()

    # args
    parser = argparse.ArgumentParser(description="\n".join(help_str))
    parser.add_argument("actions", nargs="*", help="Available: {}".format(", ".join(conf_dict["actions"])))
    parser.add_argument("-d", "--debug", action="store_true", help="Debug mode.")
    parser.add_argument("-u", "--ui", dest="ui", default="ttables", help="Override user interface type.")
    parser_args = parser.parse_args()

    for arg in vars(parser_args):
        value = getattr(parser_args, arg)
        if arg in conf.user_setting_keys:
            if value is None:
                continue
            valid, msg = conf.update_user_setting(arg, value)
            if not valid:
                print(msg)
                return
        else:
            conf.update_setting(arg, value)

    vis = visual.instantiator.setup(conf)
    runner, input_cmd = None, None

    if parser_args.actions:
        cmd, *args = parser_args.actions

        if cmd == "merge":
            merge(conf, vis, args)
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
            # then it has to be a runner control, pass it down
            runner = Runner(conf)
            # if not any([cmd.startswith(x) for x in conf.controls.values()]):
            #     print("Undefined command: {}".format(cmd))
            #     return
            # else, pass it down
            input_cmd = " ".join(parser_args.actions)

    # if no action specified, explore
    if runner is None:
        runner = Runner(conf)
    runner.loop(input_cmd=input_cmd)

if __name__ == '__main__':
    main()
