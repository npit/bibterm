"""Module for parsing input commands
"""
import utils


class CommandParser:
    """Class for parsing input commands"""
    def __init__(self, config, visual):
        """ Constructor
        Keyword Arguments:
        commands_dict -- Input key-command mappipngs
        """
        self.config = config
        self.commands_dict = config.get_controls()
        self.delimiter = ";"

        self.commands_buffer = []

        self.visual = visual
        self.archive_blacklist = []

        # placeholder to denote index list input
        self.placeholder_index_list_id = "indexes"

    def prevent_archiving(self, cmd):
        """Update list of not-to-be-archived commands"""
        self.archive_blacklist.append(cmd)

    def delineate(self, input_str):
        """Break up input string into multiple commands

        :param input_str: str, The input command string
        :returns: List of separate commands
        :rtype: List of str
        """
        return input_str.split(self.delimiter)

    def get_command_and_args(self, inp):
        """Split into command and arguments"""
        if not inp:
            return "", []
        # handle search
        src_symbol = self.commands_dict["search"]
        src_symbol_len = len(src_symbol)
        if inp[:src_symbol_len] == src_symbol:
            return src_symbol, [inp[src_symbol_len:]]
        input_cmd, *args = inp.split(maxsplit=1)
        return input_cmd, args

    def parse(self, input_str):
        """Parse input string into a list of function-argument executions

        :param input_str: str, The input command string
        :returns: List of function calls - kwargs tuplu
        :rtype: 

        """
        inputs = self.delineate(input_str)
        for inp in inputs:
            inp = inp.strip()
            # fetch command as first word
            input_cmd, args = self.get_command_and_args(inp)
            # empty input
            matches = [cmd for cmd in self.commands_dict.items() if cmd[-1].lower() == input_cmd]
            if not matches:
                # check if it's an input list
                if utils.is_index_list(input_str):
                    input_cmd, args = self.placeholder_index_list_id, [input_str]
                else:
                    self.visual.error(f"Undefined command: {input_cmd}, available:")
                    skeys = sorted(self.commands_dict.keys())
                    self.visual.print_enum(list(zip(skeys, [self.commands_dict[k] for k in skeys])), at_most=None, header="action key".split())
                    continue

            elif len(matches) > 1:
                self.visual.error(f"Non-uniquely identifiable command input: {input_cmd}, candidates: {matches})")
                skeys, svalues = list(zip(*matches))
                self.visual.print_enum(skeys, svalues, at_most=None, header="action key".split())
                continue
            else:
                # all good
                input_cmd = matches[0][0]
            # return function identifier and arguments
            self.commands_buffer.append((input_cmd, args))

    def get(self, initial_input=None):
        """Retrieve available command from the parser

        :returns: Command-argument tuple
        :rtype: Tuple of string

        """
        while True:
            if self.commands_buffer:
                cmd, arg = self.commands_buffer.pop()
                if cmd not in self.archive_blacklist:
                    self.last_cmd_arg = cmd, arg
                return cmd, arg
            self.visual.idle()
            if initial_input is not None:
                input_str, initial_input = initial_input, None
                self.visual.newline()
            else:
                input_str = self.visual.receive_command()
            self.parse(input_str)

    def repeat_last(self):
        """Fetches lastly executed command-argument pair

        :returns:  The lastly executed command-argument pair
        :rtype: Tuple of str
        """
        self.commands_buffer.append(self.last_cmd_arg)
