import json

import terminaltables
from terminaltables import AsciiTable
from terminaltables.terminal_io import terminal_size

import utils
from visual.io import Io


class TermTables(Io):
    name = "ttables"

    def __init__(self, conf):
        Io.__init__(self, conf)

    @staticmethod
    def get_instance(conf=None):
        if TermTables.instance is not None:
            return TermTables.instance
        if conf is None:
            TermTables.error("Need configuration to instantiate visual")
        print("Instantiating the {} ui".format(TermTables.name))
        TermTables.instance = TermTables(conf)
        return TermTables.instance

    # def gen_entry_strings(self, entry, maxlens=None):
    #     # do not limit / pad lengths
    #     return (self.ID_str(entry.ID, None), self.title_str(entry.title, len(entry.title)), self.keyword_str(entry.keywords))

    def print_entries_enum(self, x_iter, entry_collection, at_most=None, print_newline=False):
        if (self.only_debug and not self.do_debug) or not x_iter:
            return
        if not x_iter:
            return
        cols = self.conf.get_user_settings()['view_columns']
        cols = self.conf.get_default_view_columns() if not cols else cols
        entries_strings = self.gen_entries_strings(x_iter, cols)

        self.print_enum(entries_strings, at_most=at_most, additionals=None, header=cols, preserve_col_idx=[0])
        if print_newline:
            self.newline()

    def print_entries_contents(self, entries, header=None):
        """Function to print all available entry information in multiple rows"""
        if self.only_debug and not self.do_debug:
            return
        if header is None:
            header = ["attribute", "value"]
        contents = [list(self.get_entry_details(cont).items()) for cont in entries]
        self.print_multiline_items(contents, header)

    def print_multiline_items(self, items, header, preserve_col_idx=None):
        """Print single-column (plus enumeration) multiline items"""
        header = ["idx"] + header
        if preserve_col_idx is not None:
            preserve_col_idx = [0] + [x+1 for x in preserve_col_idx]
        table_contents = [header]
        if len(header) != len(table_contents[0]):
            self.error("Header length mismatch!")
            return
        num = 0
        for item in items:
            num += 1
            attributes, values = [], []
            for (name, value) in item:
                attributes.append(str(name))
                values.append(str(value))
            table_contents.append([str(num), "\n".join(attributes).strip(), "\n".join(values).strip()])
        self.print(self.get_table(table_contents, preserve_col_idx=preserve_col_idx, inner_border=True, is_multiline=True))

    def get_table(self, contents, preserve_col_idx=[], inner_border=False, is_multiline=True):
        table = self.fit_table(AsciiTable(contents), preserve_col_idx, is_multiline)
        if inner_border:
            table.inner_row_border = True
        return table.table

    def print_entry_contents(self, entry):
        if self.only_debug and not self.do_debug:
            return
        contents = self.get_entry_contents(entry)
        contents = [["attribute", "value"]] + list(contents.items())
        self.print(self.get_table(contents))

    # get table column max lengths, considering newline elements
    def get_table_column_max_widths(self, data):
        widths = []
        for row in data:
            rw = []
            for col in row:
                if "\n" in col:
                    # get max of column element
                    llen = max([len(x) for x in col.split("\n")])
                else:
                    llen = len(col)
                rw.append(llen)
            widths.append(rw)
        return widths

    def fit_table(self, table, preserve_col_idx=None, is_multiline=False):
        change_col_idx = range(len(table.table_data[0]))
        if preserve_col_idx is not None:
            change_col_idx = [i for i in change_col_idx if i not in preserve_col_idx]
            change_col_idx = sorted(change_col_idx, reverse=True)

        iter, max_iter = 0, 5
        while not table.ok:
            data = table.table_data
            if not change_col_idx:
                self.fatal_error("Table does not fit but no changeable columns defined.")
            widths = self.get_table_column_max_widths(data)
            # med = zwidths[len(zwidths)//2]
            # mean_lengths = [sum(x)/len(x) for x in zwidths]
            # anything larger than 2 * the median, prune it
            zwidths = list(zip(*widths))
            maxwidths = [max(z) for z in zwidths]

            termwidth = terminal_size()[0]
            max_column_sizes = [table.column_max_width(k) for k in range(len(data[0]))]
            # print(termwidth)
            # print(max_column_sizes)
            # print(maxwidths)
            # calc the required reduction; mx is negative for overflows
            # max_size_per_col = [mw - mcs if mcs < 0 else mw for (mw, mcs) in zip(maxwidths, max_column_sizes)]
            # get widths for each row
            for col in change_col_idx:
                max_sz = max_column_sizes[col]
                if max_sz < 0:
                    # column's ok
                    continue
                for row, row_widths in enumerate(widths):
                    col_width = row_widths[col]
                    if col_width > max_sz:
                        # prune the corresponding column
                        data[row][col] = self.prune_string(data[row][col], max_sz)
                        widths[row][col] = len(data[row][col])
            table = AsciiTable(data)
            iter += 1
            if iter > max_iter:
                break
        return table

    def prune_string(self, content, prune_to=None, repl="..."):
        # consider newlines
        if "\n" in content:
            content = content.split("\n")
            pruned = [self.prune_string(ccc, prune_to, repl) for ccc in content]
            return "\n".join(pruned)
        if len(content) > prune_to:
            to = max(0, prune_to - len(repl))
            content = content[:to] + repl
        return content

    def print_enum(self, x_iter, at_most=None, additionals=None, header=None, preserve_col_idx=None):
        """Print collection, with a numeric column per line
        """
        if preserve_col_idx is None:
            preserve_col_idx = []
        if self.only_debug and not self.do_debug:
            return
        x_iter = utils.listify(x_iter)
        # check which items will be printed
        if at_most is not None and len(x_iter) > at_most:
            idxs_print = list(range(at_most - 1)) + [len(x_iter) - 1]
            dots = ["..."] * (len(x_iter[0]) + 1) # +1 for the enumeration
        else:
            idxs_print = list(range(len(x_iter)))
            dots = None

        table_data = []
        for i, row in enumerate(x_iter):
            if i in idxs_print:
                try:
                    len(row)
                except:
                    row = [row]
                row = [str(r) for r in row]
                table_data.append([str(i+1)] + row)
        if dots:
            table_data.insert(len(table_data)-1, dots)

        if header:
            table_data = [["idx"] +  header] + table_data
        preserve_col_idx = [0] + [p+1 for p in preserve_col_idx]
        table = self.get_table(table_data, preserve_col_idx=preserve_col_idx)

        self.newline()
        self.print(table)
