"""Module for defining selections"""
import utils


class Selector:
    """Class for selection mechanics"""

    def __init__(self, visual):
        """
        :param conf: Configuration
        """
        self.cached_selection = None
        self.visual = visual

    def update_reference(self, entry_id_list):
        """Renew reference id list and selection"""
        if self.cached_selection is not None:
            # remap the selected indices by id
            selected_ids = [self.entry_id_list[i] for i in self.cached_selection]
            covered_ids = [x for x in selected_ids if x in entry_id_list]
            lost_ids = [x for x in selected_ids if x not in entry_id_list]
            if lost_ids:
                self.visual.error(f"Selection not covered by new reference entry list -- droping {len(lost_ids)} entries: {lost_ids}")
            self.cached_selection = [entry_id_list.index(c) for c in covered_ids]
        self.entry_id_list = entry_id_list


    def clear_cached(self):
        """Function to clear the cached selection"""
        self.cached_selection = None

    def select_by_id(self, inp, yield_ones_index=False):
        """Select item(s) from the entry list by entry ID
        :param inp: str, String representing a selection by ID
        :return idxs: list, List of index selection to the reference
        """
        if inp not in self.entry_id_list:
            return None
        entry_index = self.entry_id_list.index(inp)
        return self.select_by_index(entry_index, yield_ones_index=yield_ones_index, parse_ones_index=False)

    def correct_for_sorting(self):
        """Adjust selections to the correct reference, if they were made via a sorted enumeration"""
        self.cached_selection = [self.visual.sorting_index[s] for s in self.cached_selection]

    def select_by_index(self, inp, yield_ones_index=False, parse_ones_index=True):
        """Select item(s) from the entry list by numeric index

        :param inp: str, String representing a selection
        :return idxs: list, List of index selection to the reference

        """
        if inp is None or inp == "":
            return self.get_selection(yield_ones_index)

        orig_idxs = utils.get_index_list(inp, len(self.entry_id_list))
        if orig_idxs is None:
            self.visual.log("Invalid selection: {}".format(inp))
            return
        if parse_ones_index:
            idxs = [i-1 for i in orig_idxs]
        invalids = [i for i in range(len(idxs)) if idxs[i] not in range(len(self.entry_id_list))]
        if invalids:
            self.visual.error("Invalid index(es): {}".format([orig_idxs[i] for i in invalids]))
        idxs = [idxs[i] for i in range(len(idxs)) if i not in invalids]
        self.cached_selection = idxs

        # correct for selections on a sorted list
        self.correct_for_sorting()

        return self.get_selection(yield_ones_index)

    def get_selection(self, yield_ones_index=False):
        """Retrieve the selected entries"""
        if not self.cached_selection:
            return None
        if yield_ones_index:
            return [n+1 for n in self.cached_selection]
        return self.cached_selection
