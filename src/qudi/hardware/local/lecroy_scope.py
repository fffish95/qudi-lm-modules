# -*- coding: utf-8 -*-


from qtpy import QtCore
from qudi.interface.scope_interface import ScopeInterface
from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex

import socket
import struct # for unpacking c structs
from ctypes import c_ubyte, c_int, Structure, sizeof
import numpy as np


# c struct for header frame
class LECROY_TCP_HEADER(Structure):
    """ defines LeCroy VICP protocol (TCP header) 
    _fields_ are byte, byte[3] and int (4-byte)
    """
    _fields_ = [("bEOI_Flag", c_ubyte),
                ("reserved", c_ubyte * 3),
                ("iLength", c_int)]


class Lecroy(ScopeInterface):
    """     
    Class for remote control and download of LeCroy oscilloscope data
    tested for WaveSurfer 452
    Methods
    ------------
    send(message) : message to device (commands, etc.)
    readOld() : old implementation of read message back from device, not tested lately
    readAll() : newer implementation, might not be robust, returns ascii string 
    
    getDataBytes(channel="C1", block="DAT1"): binary data download, 8-bit
    getDataWords(channel="C1", block="DAT1"): binary data download, 16-bit
    getDataFloats(channel="C1", block="DAT1"): unit, vertical data (downloads 16-bit binary)
    getHorProperties(channel="C1") : returns (unit, offset, interval) in time dir. 

    Example config for copy-paste:

    lecroy_scope:
        module.Class: 'local.lecroy_scope.Lecroy'
        options:
            ip_address: '10.140.1.221'
    """

    # config options
    _ip_address = ConfigOption('ip_address', missing='error')

    # various flags just in case in hex
    LECROY_EOI_FLAG		=	0x01
    LECROY_SRQ_FLAG		=	0x08
    LECROY_CLEAR_FLAG	=	0x10
    LECROY_LOCKOUT_FLAG	=	0x20
    LECROY_REMOTE_FLAG	=	0x40
    LECROY_DATA_FLAG	=	0x80

    LECROY_SERVER_PORT = 1861 # as defined by LeCroy

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()


    def on_activate(self):
        """ Connect to the IP, using LeCroy.LECROY_SERVER_PORT as port
        creates a socket at LeCroy.s
        """
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self._ip_address, self.LECROY_SERVER_PORT))

        except:
            self.log.critical('Connection not established.')





    def on_deactivate(self):
        self.s.close()



    #############################################
    # Methods of the main class
    #############################################


    def send(self, message):
        """ Send a message through the socket to LeCroy oscilloscope. 
        Sends message length in header frame and then writes to the 
        socket until all is received by the oscilloscope
        returns 0 if abnormal exit
        """
        msglen = len(message)
        # set the header info
        head = LECROY_TCP_HEADER(self.LECROY_DATA_FLAG | self.LECROY_EOI_FLAG,
                                 (1, 0, 0),
                                 socket.htonl(msglen))

        # write the header first
        written = self.s.send(head)
        if (written != sizeof(head)):
            raise RuntimeError("could not write header successfully, returned {}".format(tmp))

        # write the message
        byteindx = 0
        msgbytes = message.encode('ascii')
        while (byteindx < msglen):
            xferd = self.s.send(msgbytes[byteindx:])
            if xferd < 0:
                raise RuntimeError("could not write the data block, returned {}".format(xferd))
            byteindx += xferd


    def __translate(self, data):
        """ Takes the device header (data) and finds the flag and data length 
        the device has specified in the usual Byte, Byte[3], Int format
        See the documentation for possible eofflags
        returns (eofflag, datalen)
        """
        headdata = struct.unpack("B3BI", data) # get response (header from device)
        datalen = socket.ntohl(headdata[-1]) # data length to be captured
        eofflag = headdata[0]
        return (eofflag, datalen)
        
            
    def __getHeader(self):
        """
        Receive a 8-byte header from socket LeCroy.s
        translate it and return the (eofflag, datalen)
        """
        data = self.s.recv(8)
        return self.__translate(data)

    def readAll(self):
        """ Read all that the device gives us (ascii) on Lecroy.s socket
        1) Get header from device (flag, len)
        2) receive len bytes and decode it
        returns the flag of the last transmission frame and complete data string in ascii
        NB! assumes all data frame transfers can be done in one go
        """
        dtstr = ""
        while True:
            flg, lnt = self.__getHeader() # find how 
            dtstr += self.s.recv(lnt).decode('ascii') # gather data
            if flg != self.LECROY_DATA_FLAG: # data flag 0x80
                break
        return flg, dtstr


    def getDataBytes(self, channel="C1", block="DAT1"):
        """
        Simplest data retrieval, by byte values (low precision)
        Use only for verification (should work regardless of data packing)
        Channel can be "C1" or "C2", 
        data type "DAT1" for first block or "DAT2" for second (special, look at doc.)
        returns list of values in 8-bit signed precision
        """
        self.send("CFMT DEF9,BYTE,BIN") # by 1 byte, binary
        # gets all the data of specified block on specified channel (waveform)
        self.send("{}:WF? {}".format(channel, block)) 
        self.s.recv(38) # two data lines with headers 2*(8+11) characters
        dta = b""
        while True:
            dta1 = b""
            flg, aln = self.__getHeader()
            if flg != self.LECROY_DATA_FLAG:
                en = self.s.recv(aln)
                if en != b'\n':
                    print("unexpected return, instead newline got {} \n next length was {}, flag {}".format(en, aln, flg))
                break
            # loop until all aln data is transferred
            while len(dta1) < aln:
                dta1 += self.s.recv(aln-len(dta1))
            dta += dta1
        #aa = [struct.unpack("b", ov) for ov in dta]
        aa = [iup for iup in struct.iter_unpack("b", dta)]
        return aa

    
    def getDataWords(self, channel="C1", block="DAT1"):
        """
        return data in tuple of word values (-32768 to 32767)
        Reads header, and double checks:
        1: that the data stream ended correctly (!LECROY_DATA_FLAG flag with "\n" end),
        2: length of the byte vector matches the specified length in the header
        channel : "C1" or "C2"
        block : "DAT1" (mostly), or "DAT2"
        
        returns list of values (16-bit signed)
        """

        self.send("CFMT DEF9,WORD,BIN") # by 2-byte word
        self.send("{}:WF? {}".format(channel, block)) # gets all the data on C2 waveform data
        self.send("CORD LO") #<LSB><MSB> 
        # rethead : first 10 bytes ascii string (like response)
        # followed by #9 xxxx xxxxx where x are 9 numbers to give len. of bin. blck
        # so ... #9002000004 means 2000004 bytes in binary array
        # or in our (2-byte word) case 1 000 002 numbers
        rethead = self.s.recv(38) # two data lines with headers 2*(8+11) characters
        
        if rethead[-11:-9] != b'#9':
            # we are not in a correct place, abort!
            raise RuntimeError("incorrectly returned header")
        # get the number of bytes expected by conv to str, lstrip leading 0
        exp_bytes = int(rethead[-9:].decode('ascii').lstrip("0")) # check later
        if (exp_bytes % 2) != 0:
            # incorrect, should be an even number of bytes
            raise RuntimeError("odd number of bytes expected")

        # accumulate the data from the socket
        dta = b"" # bytes data accumulator
        while True:
            dta1 = b"" # local accumulator (smaller chunks)
            flg, alen = self.__getHeader() # flg=LECROY_DATA_FLAG : more data coming
            if flg != self.LECROY_DATA_FLAG:
                # no more data expected
                en = self.s.recv(alen)
                # does it end correctly
                if en != b'\n':
                    print("unexpected return, instead newline got {} \n next length was {}, flag {}".format(en, alen, flg))
                break
            # loop until all alen data is transferred
            while len(dta1) < alen:
                dta1 += self.s.recv(alen-len(dta1))
            dta += dta1 # if the local accum. is done, only then append

        # we have byte values now
        # check if the length is correct
        if len(dta) != exp_bytes:
            raise AssertionError("Expected {} bytes, got {}".format(exp_bytes,
                                                                    len(dta)))        
        return struct.unpack('<{}h'.format(len(dta)//2), dta)

    def getDataFloats(self, channel="C1", block="DAT1"):
        """
        return the data in measured units in np.float64
        channel : "C1" or "C2"
        block : "DAT1" (mostly), or "DAT2"
        DAT1 is basic integer data block for storing measurements
        DAT2 is used to hold the results of processing functions (extrema, FFT, etc.)
        returns (VERTUNIT, array) : properly scaled numpy array of vertical value data
        """
        word_values = np.array(self.getDataWords(channel=channel, block=block))
        # get vertical offset
        self.send('{}:INSPECT? "VERTICAL_OFFSET"'.format(channel))
        r1, r2 = self.readAll()
        VOS = float(r2.split(":")[-1].split('"\n')[0].strip(" "))
        # get vertical gain
        self.send('{}:INSPECT? "VERTICAL_GAIN"'.format(channel))
        r1, r2 = self.readAll()
        VG = float(r2.split(":")[-1].split('"\n')[0].strip(" "))
        # get vertical unit
        self.send('{}:INSPECT? "VERTUNIT"'.format(channel))
        r1, r2 = self.readAll()
        VERTUNIT = r2.split("Unit Name = ")[-1].split('"\n')[0]
        # value = VERT_GAIN * data - VERT_OFFSET
        return (VERTUNIT, VG*np.array(word_values, dtype=np.float64) - VOS)

    def getHorProperties(self, channel="C1"):
        """
        return the time vector data for the measurement for channel "channel"
        for single sweep waveforms, for data point i, we have the horiz.
        time from trigger being
        t[i] = HORIZ_INTERVAL * i + HORIZ_OFFSET
        in specified HORIZ_UNIT units
        returns (HORUNIT, HORIZ_OFFSET, HORIZ_INTERVAL)
        where
        HORUNIT (string) is horizontal unit
        HORIZ_OFFSET (double) is trigger offset for the first sweep of the trigger,
                                 seconds b.w. the trig. and 1st data point
        HORIZ_INTERVAL (float) is sampling interal for time domain waveforms
        """
        self.send('{}:INSPECT? "HORUNIT"'.format(channel))
        r1, r2 = self.readAll()
        HORUNIT = r2.split("Unit Name = ")[-1].split('"\n')[0]
        self.send('{}:INSPECT? "HORIZ_OFFSET"'.format(channel))
        r1, r2 = self.readAll()
        HOS = float(r2.split(":")[-1].split('"\n')[0].strip(" "))
        self.send('{}:INSPECT? "HORIZ_INTERVAL"'.format(channel))
        r1, r2 = self.readAll()
        HInV = float(r2.split(":")[-1].split('"\n')[0].strip(" "))

        return (HORUNIT, HOS, HInV)