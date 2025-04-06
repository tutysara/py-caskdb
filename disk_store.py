"""
disk_store module implements DiskStorage class which implements the KV store on the
disk

DiskStorage provides two simple operations to get and set key value pairs. Both key and
value needs to be of string type. All the data is persisted to disk. During startup,
DiskStorage loads all the existing KV pair metadata.  It will throw an error if the
file is invalid or corrupt.

Do note that if the database file is large, then the initialisation will take time
accordingly. The initialisation is also a blocking operation, till it is completed
the DB cannot be used.

Typical usage example:

    disk: DiskStorage = DiskStore(file_name="books.db")
    disk.set(key="othello", value="shakespeare")
    author: str = disk.get("othello")
    # it also supports dictionary style API too:
    disk["hamlet"] = "shakespeare"
"""
import os.path
import time
import typing

from format import HEADER_SIZE, KeyEntry, encode_kv, decode_kv, decode_header


# DiskStorage is a Log-Structured Hash Table as described in the BitCask paper. We
# keep appending the data to a file, like a log. DiskStorage maintains an in-memory
# hash table called KeyDir, which keeps the row's location on the disk.
#
# The idea is simple yet brilliant:
#   - Write the record to the disk
#   - Update the internal hash table to point to that byte offset
#   - Whenever we get a read request, check the internal hash table for the address,
#       fetch that and return
#
# KeyDir does not store values, only their locations.
#
# The above approach solves a lot of problems:
#   - Writes are insanely fast since you are just appending to the file
#   - Reads are insanely fast since you do only one disk seek. In B-Tree backed
#       storage, there could be 2-3 disk seeks
#
# However, there are drawbacks too:
#   - We need to maintain an in-memory hash table KeyDir. A database with a large
#       number of keys would require more RAM
#   - Since we need to build the KeyDir at initialisation, it will affect the startup
#       time too
#   - Deleted keys need to be purged from the file to reduce the file size
#
# Read the paper for more details: https://riak.com/assets/bitcask-intro.pdf


class DiskStorage:
    """
    Implements the KV store on the disk

    Args:
        file_name (str): name of the file where all the data will be written. Just
            passing the file name will save the data in the current directory. You may
            pass the full file location too.
    """

    def __init__(self, file_name: str = "data.db"):
        self.file_name = file_name
        self.key_dir = {}
        # keep tab of where to write next
        # while reading we seek to different pos in file
        # so, always move to write_position before writing
        # TODO: Check if this is performant or keeping a hashmap as cache is required
        self.write_position = 0
        # if we have an existing file, read from it
        if os.path.exists(file_name):
            self._init_key_dir()

        # keep an open file object derived from file_name
        self.file = open(self.file_name, 'a+b') # append + write mode

        
    
    def _init_key_dir(self): # lifted from hit docs
        # in original paper the path is a dir and we have to read all files from it
        # TODO: change it to confirm with spec in paper
        print("****----------initialising the database----------****")
        with open(self.file_name, "rb") as f:
            while header_bytes := f.read(HEADER_SIZE):
                timestamp, key_size, value_size = decode_header(data=header_bytes)
                key_bytes = f.read(key_size)
                value_bytes = f.read(value_size)
                key = key_bytes.decode("utf-8")
                value = value_bytes.decode("utf-8")
                total_size = HEADER_SIZE + key_size + value_size
                kv = KeyEntry(
                    timestamp=timestamp,
                    position=self.write_position,
                    total_size=total_size,
                )
                self.key_dir[key] = kv
                self.write_position += total_size
                print(f"loaded k={key}, v={value}")
        print("****----------initialisation complete----------****")

    def _write(self, data:bytes):
        # writing to file is hard?
        # TODO: read about https://danluu.com/file-consistency/
        self.file.write(data)
        #TODO:read more about fsync: https://docs.python.org/3/library/os.html#os.fsync
        self.file.flush()
        os.fsync(self.file.fileno())

    def set(self, key: str, value: str) -> None:
        # convert key and value into encoded form (bytes)
        # write to disk and move the write pointer
        # keep an entry in key_dir mapping key->KeyEntry (position, totalsize)
        # use the key in key_dir to read value directly from disk
        timestamp = int(time.time())
        size, data = encode_kv(timestamp=timestamp, key=key, value=value)
        self._write(data)
        kv = KeyEntry(timestamp=timestamp, position=self.write_position, total_size=size)
        self.key_dir[key] = kv
        # update after saving the starting position
        self.write_position += size

    def get(self, key: str) -> str:
        kv:KeyEntry = self.key_dir.get(key)
        if kv is None:
            return "" # can we return None instead?
        self.file.seek(kv.position, os.SEEK_SET) # meaning seek from start of stream (0)
        data = self.file.read(kv.total_size)
        timestamp, key, value = decode_kv(data)
        return value

    def close(self) -> None: # lifted from hint doc
        # before we close the file, we need to safely write the contents in the buffers
        # to the disk. Check documentation of DiskStorage._write() to understand
        # following the operations
        self.file.flush()
        os.fsync(self.file.fileno())
        self.file.close()

    def __setitem__(self, key: str, value: str) -> None:
        return self.set(key, value)

    def __getitem__(self, item: str) -> str:
        return self.get(item)
