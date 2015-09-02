#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 <+YOU OR YOUR COMPANY+>.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import numpy
from gnuradio import gr
from PyQt4 import Qt, QtCore, QtGui
import pmt

class table(gr.sync_block, QtGui.QTableWidget):
    """
    This is a PyQT-Table. It will be populated by PDU messages.
    For every new message, it would insert a new row, which might not be
    what you want. So instead, if you specify a "row identifier", that will act
    as  a unique id (as for a normal Database), so that you can update rows
    in case the meta field dict values match.
    If you specify a list of strings as "columns" the meta field will be filtered
    for those in order to just extract the desired values and feed them into the table.

    TODO: give users the chance to NOT filter the meta field
    TODO: give users the chance to NOT specify a unique id (meaning there will be no way to update rows)

    Approach:
    1. Get the message and extract meta field
    2. Assert that the desired row identifier exists
    3. Every other meta field entry will be put into the table
    4. The "columns" parameter can be used to filter out other meta field entries.
    """
    def __init__(self, blkname="table", label="", row_id="", columns=[], *args):
        gr.sync_block.__init__(self,
            name="blkname",
            in_sig=[],
            out_sig=[])
        QtGui.QTableWidget.__init__(self, *args)
        self.message_port_register_in(pmt.intern("pdus"))
        self.set_msg_handler(pmt.intern("pdus"), self.handle_input)
        self.blkname=blkname
        self.log = gr.logger("table_log")
        ## table setup
        self.rowcount = 0
        self.columncount = 0

        self.columns = columns
        self.column_dict = {} # mapping aid for column indices
        self.filter_columns = False
        self.tmp_item = None
        if row_id is not None:
            self.row_id = row_id
            self.ids = {} # mapping aid for identifiers
            # set identifier column
            self.insertColumn(self.columncount)
            self.tmp_item = QtGui.QTableWidgetItem(row_id)
            self.setHorizontalHeaderItem(self.columncount, self.tmp_item)
            self.columncount += 1

            if columns is not None:
                self.filter_columns = True
                # if columns are given, pre-set table header
                # set other column headers
                for col in columns:
                    if col is not self.row_id: # assert we dont have 2 id columns
                        self.insertColumn(self.columncount)
                        self.tmp_item = QtGui.QTableWidgetItem(col)
                        # TODO: this could be a qt qss style param
                        self.tmp_item.setBackground(QtGui.QColor(225,225,225))

                        self.setHorizontalHeaderItem(self.columncount, self.tmp_item)
                        self.column_dict[col] = self.columncount
                        self.columncount += 1
            else:
                # no columns were set. in this case, take every meta field entry
                # that comes along
                self.log.info("No column filter specified. {0} will take all the meta field \
entrys it can gather!".format(self.blkname))
        else:
            self.log.warn("Please support a table row identifier!")

        self.horizontalHeader().setResizeMode(1)
        # make table non-writable
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)

    def handle_input(self, pdu):
        #self.setSortingEnabled(False)

        ######################## Input Checks ########################
        # we expect a pdu (or just a dictionary)
        if not pmt.is_pair(pdu) and not pmt.is_dict(pdu):
            self.log.debug("Message must be a PDU or a dictionary")
            return
        elif pmt.is_pair(pdu): # up to now, pdu vector field is ignored
            meta = pmt.car(pdu)
            if not pmt.is_dict(meta):
                self.log.debug("No meta field present")
                return
            meta_dict = pmt.to_python(meta)
        elif pmt.is_dict(pdu):
            meta_dict = pmt.to_python(pdu)
        else:
            self.log.emerg("Something weird happened")
        ##############################################################


        # for now, we insist on having the row_id pmt within the meta field
        if meta_dict.has_key(self.row_id):
            # get the current row identifier and remove corresponding key
            id_value = meta_dict.pop(self.row_id)
            cur_idx = self.rowcount
            create_new_row = id_value not in self.ids.keys()

            if create_new_row:
                #self.log.debug("Creating new Table Entry with "+str(id_value))
                self.insertRow(self.rowcount)
                self.tmp_item = QtGui.QTableWidgetItem(str(id_value))
                self.tmp_item.setData(QtCore.Qt.EditRole, id_value)
                self.tmp_item.setBackground(QtGui.QColor(225,225,225))
                #self.setRowCount(self.rowcount+1)
                self.setItem(self.rowcount, 0, self.tmp_item)
                self.ids[id_value] = self.tmp_item
                self.rowcount += 1
            else:
                #self.log.debug("Updating Table Entry " + str(id_value))
                # if row id already exists, get and use the respective row idx
                cur_idx = self.ids[id_value].row()

            if self.filter_columns:
                for col, idx in self.column_dict.iteritems():
                    if meta_dict.has_key(col):
                        value = meta_dict[col]
                        # for now, we wont allow meta field entrys other than the specified columns
                        self.tmp_item = QtGui.QTableWidgetItem(str(value))
                        self.tmp_item.setData(QtCore.Qt.EditRole, value)
                        self.setItem(cur_idx, idx, self.tmp_item)
            else:
                for col, value in meta_dict.iteritems():
                    print("Col={0}, Value={1}".format(col, value))
                    if self.column_dict.has_key(col):
                        self.log.debug("Column is present at col: "+str(self.column_dict[col]))
                        self.tmp_item = QtGui.QTableWidgetItem(str(col))
                    else:
                        self.log.debug("Setting new Column: "+ str(col))
                        self.insertColumn(self.columncount)
                        self.tmp_item = QtGui.QTableWidgetItem(str(col))
                        # TODO: this could be a qt qss style param
                        self.tmp_item.setBackground(QtGui.QColor(225,225,225))

                        self.setHorizontalHeaderItem(self.columncount, self.tmp_item)
                        self.column_dict[col] = self.columncount
                        self.tmp_item = QtGui.QTableWidgetItem(str(col))
                        self.columncount +=1
                        self.log.debug("Columncount is now: "+str(self.columncount))

                    # now set data
                    self.tmp_item.setData(QtCore.Qt.DisplayRole, str(value))
                    self.tmp_item.setData(QtCore.Qt.EditRole, value)
                    self.setItem(cur_idx, self.column_dict[col], self.tmp_item)

        else:
            self.log.info("Meta Field "+self.row_id+" not found.")

        #self.setSortingEnabled(True)
    def insert_cell(self, row, col):
        pass
    def update_cell(self, row, col):
        pass

    def work(self, input_items, output_items):
        pass
