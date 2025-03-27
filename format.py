"""
format module provides encode/decode functions for serialisation and deserialisation
operations

format module is generic, does not have any disk or memory specific code.

The disk storage deals with bytes; you cannot just store a string or object without
converting it to bytes. The programming languages provide abstractions where you don't
have to think about all this when storing things in memory (i.e. RAM). Consider the
following example where you are storing stuff in a hash table:

    books = {}
    books["hamlet"] = "shakespeare"
    books["anna karenina"] = "tolstoy"

In the above, the language deals with all the complexities:

    - allocating space on the RAM so that it can store data of `books`
    - whenever you add data to `books`, convert that to bytes and keep it in the memory
    - whenever the size of `books` increases, move that to somewhere in the RAM so that
      we can add new items

Unfortunately, when it comes to disks, we have to do all this by ourselves, write
code which can allocate space, convert objects to/from bytes and many other operations.

format module provides two functions which help us with serialisation of data.

    encode_kv - takes the key value pair and encodes them into bytes
    decode_kv - takes a bunch of bytes and decodes them into key value pairs

**workshop note**

For the workshop, the functions will have the following signature:

    def encode_kv(timestamp: int, key: str, value: str) -> tuple[int, bytes]
    def decode_kv(data: bytes) -> tuple[int, str, str]
"""

import struct
HEADER_FORMAT = "<LLL" #little endian, long unsigned int (4 bytes)
HEADER_SIZE = 12 # 4+4+4

def encode_header(timestamp: int, key_size: int, value_size: int) -> bytes:
    return struct.pack(HEADER_FORMAT, timestamp, key_size, value_size)
    


def encode_kv(timestamp: int, key: str, value: str) -> tuple[int, bytes]:
    """
    encode_kv encodes the KV pair into bytes

    Args:
        timestamp (int): Timestamp at which we wrote the KV pair to the disk. The value
            is current time in seconds since the epoch.
        key (str): the key (cannot exceed the maximum size)
        value (str): the value (cannot exceed the maximum size)

    Returns:
        tuple containing the size of encoded bytes and the byte object

    Raises:
        struct.error when parameters don't match the specific type / size
    """
    header:bytes = encode_header(timestamp, len(key), len(value))
    data:bytes = b"".join([str.encode(key), str.encode(value)])
    return HEADER_SIZE + len(data), header + data


def decode_kv(data: bytes) -> tuple[int, str, str]:
    """
    decode_kv decodes the data bytes into appropriate KV pair

    Args:
        data (bytes): byte object containing the encoded KV data

    Returns:
        A tuple containing:

            timestamp (int): timestamp in epoch seconds
            key (str): the key
            value (str): the value

    Raises:
        struct.error: when parameters don't match the specific type / size
        IndexError: if the length of bytes is shorter than expected
        UnicodeDecodeError: if the key or values bytes could not be decoded to string
    """
    # get the ksz and value_sz from fixed header (12 bytes) to split the key and value bytes
    tstamp, ksz, value_sz = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    kbytes: bytes = data[HEADER_SIZE: HEADER_SIZE + ksz]
    vbytes: bytes = data[HEADER_SIZE + ksz:]
    key: str = kbytes.decode()
    value: str = vbytes.decode()
    return (tstamp, key, value)


def decode_header(data: bytes) -> tuple[int, int, int]:
    """
    decode_header decodes the bytes into header using the `HEADER_FORMAT` format
    string

    Args:
        data (bytes): byte object containing the encoded header data

    Returns:
        A tuple containing:

            timestamp (int): timestamp in epoch seconds
            key_size (int): size of the key
            value_size (int): size of the value

    Raises:
        struct.error: when parameters don't match the specific type / size
    """
    tstamp, ksz, value_sz = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    return (tstamp, ksz, value_sz)
