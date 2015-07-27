# This file is part of the WAF-Simulator by Nicholas Fiorentini (2015)
# and is released under Creative Common Attribution 4.0 International (CC BY 4.0)
# see README.txt or LICENSE.txt for details

"""
This is the base class to handle a single NAND cell in a very naive and basic implementation.
"""

# IMPORTS
import simulator.common as common
from decimal import *


# USEFUL DECORATORS
def check_block(f):
    """
    A wrapper to validate the block parameter for a BaseNANDDisk class.
    """
    def wrapper(s, **kwargs):
        if 'block' in kwargs:
            block = kwargs['block']
            if block < 0 or block >= s.total_blocks:
                raise ValueError("block parameter out of range.")

        # seems fine, let's proceed
        return f(s, **kwargs)
    return wrapper


def check_page(f):
    """
    A wrapper to validate the page parameter for a BaseNANDDisk class.
    """
    def wrapper(s, **kwargs):
        if 'page' in kwargs:
            page = kwargs['page']
            if page < 0 or page >= s.pages_per_block:
                raise ValueError("page parameter out of range.")

        # seems fine, let's proceed
        return f(s, **kwargs)
    return wrapper


# BaseNANDDISK class
class BaseNANDDisk:
    """
    This class ...
    """

    # ATTRIBUTES
    # PHYSICAL CHARACTERISTICS
    total_blocks = 256
    """ The total physical number of block available. Usually should be a multiple of 2.
        This is an integer value. Must be greater than zero.
    """

    pages_per_block = 64
    """ The number of pages per single block. Usually should be a multiple of 2.
        This is an integer value. Must be greater than zero.
    """

    page_size = 4096
    """ The physical size of a single page in [KiB]. 1 KiB = 2^20.
        This is an integer value. Must be greater than zero.
    """

    total_pages = pages_per_block * total_blocks
    """ The total physical number of pages available.
        This is an integer value. Must be greater than zero.
    """

    block_size = page_size * pages_per_block
    """ The physical size of a single block in [KiB].
        It's computed as the number of pages per block times the size of a page.
        This is an integer value. Must be greater than zero.
    """

    total_disk_size = block_size * total_blocks
    """ The total physical size of this NAND cell in [KiB].
        It's computed as the number of total physical blocks times the size of a block.
        This is an integer value. Must be greater than zero.
    """

    write_page_time = 250
    """ The time to write a single page in [microseconds] (10^-6 seconds).
        This is an integer value. Must be greater than zero.
    """

    read_page_time = 25
    """ The time to read a single page in [microseconds] (10^-6 seconds).
        This is an integer value. Must be greater than zero.
    """

    erase_block_time = 1500
    """ The time to erase a single block in [microseconds] (10^-6 seconds).
        This is an integer value. Must be greater than zero.
    """

    # CONSTRUCTOR
    def __init__(self):
        """

        :return:
        """
        # INTERNAL STATISTICS
        self._elapsed_time = 0
        """ Keep track of the total elapsed time for the requested operations [microseconds].
            A microsecond is 10^-6 seconds. This variable is an integer.
        """

        self._host_page_write_request = 0
        """ Number of page written as requested by the host.
            This is an integer value.
        """

        self._page_write_executed = 0
        """ Total number of page actually written by the disk.
            This is an integer value.
        """

        self._page_write_failed = 0
        """ Total number of page unable to be writted due to disk error (no empty pages).
            This is an integer value.
        """

        self._host_page_read_request = 0
        """ Number of page read as requested by the host.
            This is an integer value.
        """

        self._page_read_executed = 0
        """ Total number of page actually read by the disk.
            This is an integer value.
        """

        self._block_erase_executed = 0
        """ Total number of block erase executed.
            This is an integer value.
        """

        # INTERNAL STATE
        self._ftl = dict()
        """ This is the full state of the flash memory.
            It's an array of blocks. Every block is an array of page.
            For every page we keep the status of the page.
            Furthermore, every block has the following extra information:
                empty:  total number of empty pages in the given block;
                dirty:  total number of dirty pages in the given block.
        """

        # set the decimal context
        getcontext().prec = common.DECIMAL_PRECISION

        # initialize the FTL
        for b in range(0, self.total_blocks):
            # for every block initialize the page structure
            self._ftl[b] = dict()
            for p in range(0, self.pages_per_block):
                # for every page set the empty status
                self._ftl[b][p] = common.PAGE_EMPTY

            # for every block initialize the internal data
            self._ftl[b]['empty'] = self.pages_per_block  # all pages are empty
            self._ftl[b]['dirty'] = 0  # no dirty pages at the beginning

    # METHODS
    # PYTHON UTILITIES
    def __str__(self):
        """

        :return:
        """
        return ""

    # STATISTICAL UTILITIES
    def write_amplification(self):
        """

        :return:
        """
        return Decimal(self._page_write_executed) / Decimal(self._host_page_write_request)

    def number_of_empty_pages(self):
        """

        :return:
        """
        tot = 0
        for b in range(0, self.total_blocks):
            tot += self._ftl[b]['empty']
        return tot

    def number_of_dirty_pages(self):
        """

        :return:
        """
        tot = 0
        for b in range(0, self.total_blocks):
            tot += self._ftl[b]['dirty']
        return tot

    def failure_rate(self):
        """

        :return:
        """
        return (Decimal(self._page_write_failed) * 100) / Decimal(self._page_write_executed)

    def elapsed_time(self):
        """

        :return:
        """
        return Decimal(self._elapsed_time) / Decimal(1000000)

    def IOPS(self):
        """

        :return:
        """
        ops = self._page_write_executed + self._page_read_executed
        return int(ops / self.elapsed_time())

    # DISK OPERATIONS UTILITIES
    @check_block
    def get_empty_page(self, block=0):
        """

        :param block:
        :return:
        """
        # first check availability
        if self._ftl[block]['empty'] <= 0:
            raise ValueError("No empty pages available in this block.")

        # get the first empty page available in the provided block
        for p in range(0, self.pages_per_block):
            if self._ftl[block][p] == common.PAGE_EMPTY:
                return p

        # should not be reachable
        raise ValueError("No empty pages available in this block.")

    @check_block
    @check_page
    def full_block_write_policy(self, block=0, page=0):
        """

        :param block:
        :return:
        """
        # naive policy: just find the first available page in a different block
        for b in range(0, self.total_blocks):
            if b != block and self._ftl[b]['empty'] > 0:
                # FOUND a block with empty pages
                p = self.get_empty_page(block=b)

                # change the status of the original page
                self._ftl[block][page] = common.PAGE_DIRTY

                # change the status of the new page
                self._ftl[b][p] = common.PAGE_IN_USE

                # we need to update the statistics
                self._ftl[block]['dirty'] += 1  # we have one more dirty page in this block
                self._ftl[b]['empty'] -= 1  # we lost one empty page in this block
                self._elapsed_time += self.write_page_time  # time spent to write the data
                self._page_write_executed += 1  # one page written
                return True

        # no empty page found
        return False

    # RAW DISK OPERATIONS
    @check_block
    @check_page
    def raw_write_page(self, block=0, page=0):
        """

        :param block:
        :param page:
        :return: True if the write is successful, false otherwise (the write is discarded)
        """
        # read the FTL to check the current status
        s = self._ftl[block][page]

        # if status is EMPTY => WRITE OK
        if s == common.PAGE_EMPTY:
            # change the status of this page
            self._ftl[block][page] = common.PAGE_IN_USE

            # we need to update the statistics
            self._ftl[block]['empty'] -= 1  # we lost one empty page in this block
            self._elapsed_time += self.write_page_time  # time spent to write the data
            self._page_write_executed += 1  # one page written
            return True

        # if status is IN USE => we consider a data change,
        # we use the current disk policy to find a new page to write the new data. In case of success we invalidate
        # the current page, otherwise the operation fails.
        elif s == common.PAGE_IN_USE:
            # is the block full?
            if self._ftl[block]['empty'] <= 0:
                # yes, we need a policy to decide how to write
                if self.full_block_write_policy(block=block, page=page):
                    # all statistic MUST BE updated inside the policy method
                    return True
                else:
                    # we didn't found a suitable place to write the new data, the write request failed
                    # this is a disk error: the garbage collector was unable to make room for new data
                    self._page_write_failed += 1
                    return False
            else:
                # no, we still have space, we just need a new empty page on this block
                # find and write the new page
                newpage = self.get_empty_page(block=block)

                # change the status of this page
                self._ftl[block][page] = common.PAGE_DIRTY

                # change the status of the new page
                self._ftl[block][newpage] = common.PAGE_IN_USE

                # we need to update the statistics
                self._ftl[block]['empty'] -= 1  # we lost one empty page in this block
                self._ftl[block]['dirty'] += 1  # we have one more dirty page in this block
                self._elapsed_time += self.write_page_time  # time spent to write the data
                self._page_write_executed += 1  # one page written
                return True

        # if status is DIRTY => we discard this write operation
        # (it's not a disk error, it's a bad random value)
        return False

    @check_block
    @check_page
    def raw_read_page(self, block=0, page=0):
        """

        :param block:
        :param page:
        :return:
        """
        # read the FTL to check the current status
        s = self._ftl[block][page]

        if s == common.PAGE_IN_USE:
            # update statistics
            self._elapsed_time += self.read_page_time  # time spent to read the data
            self._page_read_executed += 1  # we executed a read of a page
            return True

        # no valid data to read
        return False

    @check_block
    def raw_erase_block(self, block=0):
        """

        :param block:
        :return:
        """
        # should mark the full block as dirty and then erase it
        # as we are in a simulation, we directly erase it
        for p in range(0, self.pages_per_block):
            # for every page set the empty status
            self._ftl[block][p] = common.PAGE_EMPTY

        # for every block initialize the internal data
        self._ftl[block]['empty'] = self.pages_per_block  # all pages are empty
        self._ftl[block]['dirty'] = 0  # fresh as new

        # update the statistics
        self._block_erase_executed += 1  # new erase operation
        self._elapsed_time += self.erase_block_time  # time spent to erase a block
        return True

    @check_block
    @check_page
    def host_write_page(self, block=0, page=0):
        """

        :param block:
        :param page:
        :return:
        """
        if self.raw_write_page(block=block, page=page):
            # update statistics
            self._host_page_write_request += 1  # the host actually asked to write a page
            return True

        return False