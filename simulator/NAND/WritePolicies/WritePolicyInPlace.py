# This file is part of the WAF-Simulator by Nicholas Fiorentini (2015)
# and is released under Creative Common Attribution 4.0 International (CC BY 4.0)
# see README.txt or LICENSE.txt for details

"""
This is an improved policy for writes in case the block is full:
the garbage collector is run in place: as soon a block is full the block is modified in-memory and erased.
"""

# IMPORTS
from simulator.NAND.WritePolicies.WritePolicyInterface import WritePolicyInterface
from simulator.NAND.common import check_block, check_page, PAGE_EMPTY, PAGE_DIRTY, PAGE_IN_USE


class WritePolicyInPlace(WritePolicyInterface):
    """
    To be written ...
    """
    # METHODS
    def get_write_policy_name(self):
        return "in place"

    @check_block
    @check_page
    def full_block_write_policy(self, block=0, page=0):
        """

        :param block:
        :return:
        """
        # change the status of the original page, so we don't need to read it
        self._ftl[block][page] = PAGE_DIRTY

        # STEP 1: temporary copy the block data (this also simulates the in-memory change)
        #         this is a read and only useful data are read
        temp_block = dict()
        for p in range(0, self.pages_per_block):
            res, status = self.raw_read_page(block=block, page=p)
            if res:
                temp_block[p] = PAGE_IN_USE  # the page is valid and in use
            else:
                temp_block[p] = PAGE_EMPTY  # reset the page, even if is dirty

        # in-memory change
        temp_block[page] = PAGE_IN_USE

        # STEP 2: erase
        self.raw_erase_block(block=block)

        # STEP 3: write the IN USE pages only
        for p in range(0, self.pages_per_block):
            if temp_block[p] == PAGE_IN_USE:
                self.raw_write_page(block=block, page=p)

        # cannot fail as the substitution is in place
        return True
