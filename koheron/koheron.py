#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import numpy as np
import string
import json
import requests
import time

ConnectionError = requests.ConnectionError

# --------------------------------------------
# HTTP API
# --------------------------------------------

def install_instrument(host, instrument_name, always_restart=False):
    if not always_restart:
        # Don't restart the instrument if already launched
        current_instrument = requests.get('http://{}/api/instruments/live'.format(host)).json()
        if current_instrument['name'] == instrument_name:
            return

    instruments = requests.get('http://{}/api/instruments/local'.format(host)).json()
    if instruments:
        for name, shas in instruments.items():
            if name == instrument_name and len(shas) > 0:
                r = requests.get('http://{}/api/instruments/run/{}/{}'.format(host, name, shas[0]))
                if int(r.text.split('status:')[1].strip()) < 0:
                    raise RuntimeError("Instrument " + instrument_name + " launch failed.")
                return
    raise ValueError("Instrument " + instrument_name + " not found")

def load_instrument(host, instrument='blink', always_restart=False):
    install_instrument(host, instrument, always_restart=always_restart)
    client = KoheronClient(host)
    return client

# --------------------------------------------
# command decorator
# --------------------------------------------

def command(classname=None, funcname=None):
    def real_command(func):
        def wrapper(self, *args):
            device_name = classname or self.__class__.__name__
            cmd_name = funcname or func.__name__
            device_id, cmd_id, cmd_fmt = self.client.get_ids(device_name, cmd_name)
            self.client.send_command(device_id, cmd_id, cmd_fmt, *args)
            return func(self, *args)
        return wrapper
    return real_command

# --------------------------------------------
# Helper functions
# --------------------------------------------

def make_command(*args):
    buff = bytearray()
    append(buff, 0, 4)        # RESERVED
    append(buff, args[0], 2)  # dev_id
    append(buff, args[1], 2)  # op_id
    # Payload
    if len(args[2:]) > 0:
        payload, payload_size = build_payload(args[2], args[3:])
        append(buff, payload_size, 4)
        buff.extend(payload)
    else:
        append(buff, 0, 4)
    return buff

def append(buff, value, size):
    if size <= 4:
        for i in reversed(range(size)):
            buff.append((value >> (8 * i)) & 0xff)
    elif size == 8:
        append(buff, value, 4)
        append(buff, value >> 32, 4)
    return size

def append_array(buff, array):
    arr_bytes = bytearray(array)
    buff += arr_bytes
    return len(arr_bytes)

# http://stackoverflow.com/questions/14431170/get-the-bits-of-a-float-in-python
def float_to_bits(f):
    return struct.unpack('>l', struct.pack('>f', f))[0]

def double_to_bits(d):
    return struct.unpack('>q', struct.pack('>d', d))[0]

def build_payload(fmt, args):
    size = 0
    payload = bytearray()
    assert len(fmt) == len(args)
    for i, type_ in enumerate(fmt):
        if type_ in ['B','b']:
            size += append(payload, args[i], 1)
        elif type_ in ['H','h']:
            size += append(payload, args[i], 2)
        elif type_ in ['I','i']:
            size += append(payload, args[i], 4)
        elif type_ in ['Q','q']:
            size += append(payload, args[i], 8)
        elif type_ is 'f':
            size += append(payload, float_to_bits(args[i]), 4)
        elif type_ is 'd':
            size += append(payload, double_to_bits(args[i]), 8)
        elif type_ is '?': # bool
            if args[i]:
                size += append(payload, 1, 1)
            else:
                size += append(payload, 0, 1)
        elif type_ is 'A':
            size += append_array(payload, args[i])
        elif type_ is 'V':
            size += append(payload, len(args[i]), 8)
            append_array(payload, args[i])
            payload.extend(build_payload(fmt[i+1:], args[i+1:])[0])
            break
        else:
            raise ValueError('Unsupported type "' + type_ + '"')

    return payload, size

# --------------------------------------------
# KoheronClient
# --------------------------------------------

class KoheronClient:
    def __init__(self, host="", port=36000, unixsock=""):
        ''' Initialize connection with koheron-server

        Args:
            host: A string with the IP address
            port: Port of the TCP connection (must be an integer)
        '''
        if type(host) != str:
            raise TypeError('IP address must be a string')

        if type(port) != int:
            raise TypeError('Port number must be an integer')

        self.host = host
        self.port = port
        self.unixsock = unixsock
        self.is_connected = False

        if host != "":
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Prevent delayed ACK on Ubuntu
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16384)
                so_rcvbuf = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

                #   Disable Nagle algorithm for real-time response:
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                tcp_nodelay = self.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
                assert tcp_nodelay == 1

                # Connect to Kserver
                self.sock.connect((host, port))
                self.is_connected = True
            except socket.error as e:
                print('Failed to connect to {:s}:{:d} : {:s}'.format(host, port, e))
                self.is_connected = False
        elif unixsock != "":
            try:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(unixsock)
                self.is_connected = True
            except socket.error as e:
                print('Failed to connect to unix socket address ' + unixsock)
                self.is_connected = False
        else:
            raise ValueError('Unknown socket type')

        if self.is_connected:
            self.load_devices()

    def load_devices(self):
        try:
            self.send_command(1, 1)
        except:
            raise ConnectionError('Failed to send initialization command')

        self.commands = self.recv_json()

        self.devices_idx = {}
        self.cmds_idx_list = []
        self.cmds_fmt_list = []

        for dev_idx, device in enumerate(self.commands):
            self.devices_idx[device['name']] = dev_idx
            cmds_idx = {}
            cmds_fmt = {}
            for cmd_idx, cmd in enumerate(device['operations']):
                cmds_idx[cmd['name']] = cmd_idx
                cmds_fmt[cmd['name']] = cmd['fmt']
            self.cmds_idx_list.append(cmds_idx)
            self.cmds_fmt_list.append(cmds_fmt)

    def get_ids(self, device_name, command_name):
        device_id = self.devices_idx[device_name]
        cmd_id = self.cmds_idx_list[device_id][command_name]
        cmd_fmt = str(self.cmds_fmt_list[device_id][command_name])
        return device_id, cmd_id, cmd_fmt

    # -------------------------------------------------------
    # Send/Receive
    # -------------------------------------------------------

    def send_command(self, device_id, cmd_id, type_str='', *args):
        cmd = make_command(device_id, cmd_id, type_str, *args)
        if self.sock.send(cmd) == 0:
            raise ConnectionError('send_command: Socket connection broken')

    def recv(self, fmt="I"):
        buff_size = struct.calcsize(fmt)
        data_recv = self.sock.recv(buff_size)
        return struct.unpack(fmt, data_recv)[0]

    def recv_uint32(self):
        return self.recv()

    def recv_uint64(self):
        return self.recv(fmt='Q')

    def recv_int32(self):
        return self.recv(fmt='i')

    def recv_float(self):
        return self.recv(fmt='f')

    def recv_double(self):
        return self.recv(fmt='d')

    def recv_bool(self):
        val = self.recv()
        return val == 1

    def recv_all(self, n_bytes):
        '''Receive exactly n_bytes bytes.'''
        data = []
        n_rcv = 0
        while n_rcv < n_bytes:
            try:
                chunk = self.sock.recv(n_bytes - n_rcv)
                if chunk == '':
                    break
                n_rcv += len(chunk)
                data.append(chunk)
            except:
                raise ConnectionError('recv_all: Socket connection broken')
        return b''.join(data)

    def recv_string(self):
        reserved, length = self.recv_tuple('II')
        return self.recv_all(length)[:-1].decode('utf8')

    def recv_json(self):
        return json.loads(self.recv_string())

    def recv_vector(self, dtype='uint32'):
        '''Receive a numpy array with unknown length.'''
        dtype = np.dtype(dtype)
        reserved, length = self.recv_tuple('IQ')
        assert reserved == 0
        buff = self.recv_all(length)
        return np.frombuffer(buff, dtype=dtype.newbyteorder('<'))

    def recv_array(self, shape, dtype='uint32'):
        '''Receive a numpy array with known shape.'''
        dtype = np.dtype(dtype)
        buff = self.recv_all(dtype.itemsize * int(np.prod(shape)))
        return np.frombuffer(buff, dtype=dtype.newbyteorder('<')).reshape(shape)

    def recv_tuple(self, fmt):
        fmt = '>' + fmt
        buff = self.recv_array(struct.calcsize(fmt), dtype='uint8')
        return tuple(struct.unpack(fmt, buff))

    def __del__(self):
        if hasattr(self, 'sock'):
            self.sock.close()
