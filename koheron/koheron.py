#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import numpy as np
import string
import json
import requests
import time

import pprint

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
            self.client.last_device_called = device_name
            self.client.last_cmd_called = cmd_name
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
    if 'N' in array_params and int(array_params['N']) != len(array):
        raise ValueError('Invalid array length. Expected {} but received {}.'
                         .format(array_params['N'], len(array)))

    if cpp_to_np_types[array_params['T']] != array.dtype:
        raise TypeError('Invalid array type. Expected {} but received {}.'
                        .format(cpp_to_np_types[array_params['T']], array.dtype))

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
        elif is_std_array(arg['type']):
            size += append_array(payload, args[i], get_std_array_params(arg['type']))
        elif is_std_vector(arg['type']):
            size += append(payload, len(args[i]), 8)
            append_array(payload, args[i], get_std_vector_params(arg['type']))
            payload.extend(build_payload(cmd_args[i+1:], args[i+1:])[0])
            break
        else:
            raise ValueError('Unsupported type "' + arg['type'] + '"')

    return payload, size

def is_std_array(_type):
    return _type.split('<')[0].strip() == 'std::array'

def is_std_vector(_type):
    return _type.split('<')[0].strip() == 'std::vector'

def is_std_tuple(_type):
    return _type.split('<')[0].strip() == 'std::tuple'

def get_std_array_params(_type):
    templates = _type.split('<')[1].split('>')[0].split(',')
    return {
      'T': templates[0].strip(),
      'N': templates[1].split('u')[0].strip()
    }

def get_std_vector_params(_type):
    return {'T': _type.split('<')[1].split('>')[0].strip()}

cpp_to_np_types = {
  'bool': 'bool',
  'uint8_t': 'uint8', 'int8_t': 'int8',
  'uint16_t': 'uint16', 'int16_t': 'int16',
  'uint32_t': 'uint32', 'unsigned int': 'uint32',
  'int32_t': 'int32', 'int': 'int32',
  'uint64_t': 'uint64', 'int64_t': 'int64',
  'float': 'float32',
  'double': 'float64'
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
            except BaseException as e:
                raise ConnectionError('Failed to connect to {}:{} : {}'.format(host, port, e))
        elif unixsock != "":
            try:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(unixsock)
                self.is_connected = True
            except BaseException as e:
                raise ConnectionError('Failed to connect to unix socket address ' + unixsock)
        else:
            raise ValueError('Unknown socket type')

        if self.is_connected:
            self.load_devices()

    def load_devices(self):
        try:
            self.send_command(1, 1)
        except:
            raise ConnectionError('Failed to send initialization command')

        self.commands = self.recv_json(check_type=False)
        # pprint.pprint(self.commands)
        self.devices_idx = {}
        self.cmds_idx_list = [None]*(2 + len(self.commands))
        self.cmds_args_list = [None]*(2 + len(self.commands))
        self.cmds_ret_types_list = [None]*(2 + len(self.commands))

        for device in self.commands:
            self.devices_idx[device['class']] = device['id']
            cmds_idx = {}
            cmds_args = {}
            cmds_ret_type = {}
            for cmd in device['functions']:
                cmds_idx[cmd['name']] = cmd['id']
                cmds_args[cmd['name']] = cmd['args']
                cmds_ret_type[cmd['name']] = cmd.get('ret_type', None)
            self.cmds_idx_list[device['id']] = cmds_idx
            self.cmds_args_list[device['id']] = cmds_args
            self.cmds_ret_types_list[device['id']] = cmds_ret_type

    def get_ids(self, device_name, command_name):
        device_id = self.devices_idx[device_name]
        cmd_id = self.cmds_idx_list[device_id][command_name]
        cmd_args = self.cmds_args_list[device_id][command_name]
        return device_id, cmd_id, cmd_args

    def check_ret_type(self, expected_types):
        device_id = self.devices_idx[self.last_device_called]
        ret_type = self.cmds_ret_types_list[device_id][self.last_cmd_called]
        if ret_type not in expected_types:
            raise TypeError('{}::{} returns a {}.'.format(self.last_device_called, self.last_cmd_called, ret_type))

    def check_ret_array(self, dtype, arr_len):
        device_id = self.devices_idx[self.last_device_called]
        ret_type = self.cmds_ret_types_list[device_id][self.last_cmd_called]
        if not is_std_array(ret_type):
            raise TypeError('{}::{} returns a {}.'.format(self.last_device_called, self.last_cmd_called, ret_type))
        params = get_std_array_params(ret_type)
        if dtype != cpp_to_np_types[params['T']]:
            raise TypeError('{}::{} expects elements of type {}.'.format(self.last_device_called, self.last_cmd_called, params['T']))
        if arr_len != int(params['N']):
            raise ValueError('{}::{} expects {} elements.'.format(self.last_device_called, self.last_cmd_called, params['N']))

    def check_ret_vector(self, dtype):
        device_id = self.devices_idx[self.last_device_called]
        ret_type = self.cmds_ret_types_list[device_id][self.last_cmd_called]
        if not is_std_vector(ret_type):
            raise TypeError('{}::{} returns a {}.'.format(self.last_device_called, self.last_cmd_called, ret_type))
        vect_type = get_std_vector_params(ret_type)['T']
        if dtype != cpp_to_np_types[vect_type]:
            raise TypeError('{}::{} expects elements of type {}.'.format(self.last_device_called, self.last_cmd_called, vect_type))

    # TODO add types check
    def check_ret_tuple(self):
        device_id = self.devices_idx[self.last_device_called]
        ret_type = self.cmds_ret_types_list[device_id][self.last_cmd_called]
        if not is_std_tuple(ret_type):
            raise TypeError('{}::{} returns a {} not a std::tuple.'.format(self.last_device_called, self.last_cmd_called, ret_type))

    # -------------------------------------------------------
    # Send/Receive
    # -------------------------------------------------------

    def send_command(self, device_id, cmd_id, cmd_args=[], *args):
        cmd = make_command(device_id, cmd_id, cmd_args, *args)
        if self.sock.send(cmd) == 0:
            raise ConnectionError('send_command: Socket connection broken')

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

    def recv_payload(self):
        reserved, length = struct.unpack('>IQ', self.recv_all(struct.calcsize('>IQ')))
        assert reserved == 0
        return self.recv_all(length)

    def recv(self, fmt="I"):
        buff = self.recv_payload()
        assert len(buff) == struct.calcsize(fmt)
        return struct.unpack(fmt, buff)[0]

    def recv_uint32(self):
        self.check_ret_type(['uint32_t', 'unsigned int'])
        return self.recv()

    def recv_uint64(self):
        self.check_ret_type(['uint64_t', 'unsigned long'])
        return self.recv(fmt='Q')

    def recv_int32(self):
        self.check_ret_type(['int32_t', 'int'])
        return self.recv(fmt='i')

    def recv_float(self):
        self.check_ret_type(['float'])
        return self.recv(fmt='f')

    def recv_double(self):
        self.check_ret_type(['double'])
        return self.recv(fmt='d')

    def recv_bool(self):
        self.check_ret_type(['bool'])
        val = self.recv()
        return val == 1

    def recv_string(self, check_type=True):
        if check_type:
            self.check_ret_type(['std::string', 'const char *', 'const char*'])
        return self.recv_payload()[:-1].decode('utf8')

    def recv_json(self, check_type=True):
        if check_type:
            self.check_ret_type(['std::string', 'const char *', 'const char*'])
        return json.loads(self.recv_string(check_type=False))

    def recv_vector(self, dtype='uint32', check_type=True):
        '''Receive a numpy array with unknown length.'''
        if check_type:
            self.check_ret_vector(dtype)
        dtype = np.dtype(dtype)
        buff = self.recv_payload()
        return np.frombuffer(buff, dtype=dtype.newbyteorder('<'))

    def recv_array(self, shape, dtype='uint32', check_type=True):
        '''Receive a numpy array with known shape.'''
        if check_type:
            if isinstance(shape, tuple):
                arr_len = 1
                for val in shape:
                    arr_len *= val
            else:
                arr_len = shape
            self.check_ret_array(dtype, arr_len)
        dtype = np.dtype(dtype)
        buff = self.recv_payload()
        assert len(buff) == dtype.itemsize * int(np.prod(shape))
        return np.frombuffer(buff, dtype=dtype.newbyteorder('<')).reshape(shape)

    def recv_tuple(self, fmt, check_type=True):
        if check_type:
            self.check_ret_tuple()
        fmt = '>' + fmt
        buff = self.recv_payload()
        assert len(buff) == struct.calcsize(fmt)
        return tuple(struct.unpack(fmt, buff))

    def __del__(self):
        if hasattr(self, 'sock'):
            self.sock.close()
