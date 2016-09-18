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

def live_instrument(host):
    live_instrument = requests.get('http://{}/api/instruments/live'.format(host)).json()
    name = live_instrument['name']
    version = live_instrument['sha']
    return name, version

def get_name_version(filename):
    # filename = 'name-version.zip'
    tokens = filename.split('.')[0].split('-')
    name = '-'.join(tokens[:-1])
    version = tokens[-1]
    return name, version

def upload_instrument(host, filename, run=False):
    with open(filename, 'rb') as fileobj:
        url = 'http://{}/api/instruments/upload'.format(host)
        r = requests.post(url, files={filename: fileobj})
    if run:
        name, version = get_name_version(filename)
        r = requests.get('http://{}/api/instruments/run/{}/{}'.format(host, name, version))

def run_instrument(host, name=None, version=None, restart=False):
    instrument_running = False
    instrument_in_store = False

    live_name, live_version = live_instrument(host)
    name_ok = (live_name == name)
    version_ok = ((version is None) or (live_version == version))
    
    if (name is None) or (name_ok and version_ok): # Instrument already running
        name, version = live_name, live_version
        instrument_running = True

    if not instrument_running: # Find the instrument in the local store:
        instruments = requests.get('http://{}/api/instruments/local'.format(host)).json()
        versions = instruments.get(name)
        if versions is None:
            raise ValueError('Instrument %s not found' % name)

        if version is None:
            # Use the first version found by default
            version = versions[0]
        if version in versions:
            instrument_in_store = True
        else:
            raise ValueError('Did not found version {} for instrument {}'.format(version, name))

    if instrument_in_store or (instrument_running and restart):
        r = requests.get('http://{}/api/instruments/run/{}/{}'.format(host, name, version))

def connect(host, *args, **kwargs):
    run_instrument(host, *args, **kwargs)
    client = KoheronClient(host)
    return client

def load_instrument(host, instrument='blink', always_restart=False):
    print('Warning: load_instrument() is deprecated, use connect() instead')
    run_instrument(host, instrument, restart=always_restart)
    client = KoheronClient(host)
    return client

# --------------------------------------------
# Command decorator
# --------------------------------------------

def command(classname=None, funcname=None):
    def real_command(func):
        def wrapper(self, *args):
            device_name = classname or self.__class__.__name__
            cmd_name = funcname or func.__name__
            device_id, cmd_id, cmd_args = self.client.get_ids(device_name, cmd_name)
            self.client.send_command(device_id, cmd_id, cmd_args, *args)
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

def append_array(buff, array, array_params):
    # We check the std::array length only if N is an explicit numeric value.
    # The N template argument might come from a define or a constexpr function
    # in which case it will be dificult to know the value without compiler help.
    # Ex. N = WFM_SIZE/2 won't be checked.
    if 'N' in array_params and array_params['N'].isdigit() and int(array_params['N']) != len(array):
        raise ValueError('Invalid array length. Expected {} but received {}.'
                         .format(array_params['N'], len(array)))

    arr_bytes = bytearray(array)
    buff += arr_bytes
    return len(arr_bytes)

# http://stackoverflow.com/questions/14431170/get-the-bits-of-a-float-in-python
def float_to_bits(f):
    return struct.unpack('>l', struct.pack('>f', f))[0]

def double_to_bits(d):
    return struct.unpack('>q', struct.pack('>d', d))[0]

def build_payload(cmd_args, args):
    size = 0
    payload = bytearray()
    assert len(cmd_args) == len(args)
    for i, arg in enumerate(cmd_args):
        if arg['type'] in ['uint8_t','int8_t']:
            size += append(payload, args[i], 1)
        elif arg['type'] in ['uint16_t','int16_t']:
            size += append(payload, args[i], 2)
        elif arg['type'] in ['uint32_t','int32_t']:
            size += append(payload, args[i], 4)
        elif arg['type'] in ['uint64_t','int64_t']:
            size += append(payload, args[i], 8)
        elif arg['type'] == 'float':
            size += append(payload, float_to_bits(args[i]), 4)
        elif arg['type'] == 'double':
            size += append(payload, double_to_bits(args[i]), 8)
        elif arg['type'] == 'bool':
            if args[i]:
                size += append(payload, 1, 1)
            else:
                size += append(payload, 0, 1)
        elif arg['type'].split('<')[0].strip() == 'std::array':
            size += append_array(payload, args[i], get_std_array_params(arg))
        elif arg['type'].split('<')[0].strip() == 'std::vector':
            size += append(payload, len(args[i]), 8)
            append_array(payload, args[i], get_std_vector_params(arg))
            payload.extend(build_payload(cmd_args[i+1:], args[i+1:])[0])
            break
        else:
            raise ValueError('Unsupported type "' + arg['type'] + '"')

    return payload, size

def get_std_array_params(arg):
    templates = arg['type'].split('<')[1].split('>')[0].split(',')
    return {
      'T': templates[0].strip(),
      'N': templates[1].strip()
    }

def get_std_vector_params(arg):
    return {
      'T': arg['type'].split('<')[1].split('>')[0].strip()
    }

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
        self.cmds_args_list = []

        for dev_idx, device in enumerate(self.commands):
            self.devices_idx[device['name']] = dev_idx
            cmds_idx = {}
            cmds_args = {}
            for cmd_idx, cmd in enumerate(device['operations']):
                cmds_idx[cmd['name']] = cmd_idx
                cmds_args[cmd['name']] = cmd['args']
            self.cmds_idx_list.append(cmds_idx)
            self.cmds_args_list.append(cmds_args)

    def get_ids(self, device_name, command_name):
        device_id = self.devices_idx[device_name]
        cmd_id = self.cmds_idx_list[device_id][command_name]
        cmd_args = self.cmds_args_list[device_id][command_name]
        return device_id, cmd_id, cmd_args

    # -------------------------------------------------------
    # Send/Receive
    # -------------------------------------------------------

    def send_command(self, device_id, cmd_id, cmd_args=[], *args):
        cmd = make_command(device_id, cmd_id, cmd_args, *args)
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
