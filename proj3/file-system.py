#!/bin/python

import pickle

DEBUG = True
DISK_DIR = './disk/'
NUM_BLOCKS_IN_DISK = 64
NUM_BYTES_IN_BLOCK = 64
NUM_BYTES_IN_INT = 4
NUM_DESCRIPTORS_IN_BLOCK = 4
NUM_BITS_IN_BYTE = 8

def convert_filename_to_int(name):
  result = 0
  for char in name:
    result <<= NUM_BITS_IN_BYTE
    result |= ord(char) 
  return result

def convert_int_to_filename(num):
  filename = ''
  while num > 0:
    filename = chr(num & 0xff) + filename
    num >>= NUM_BITS_IN_BYTE
  return filename

def print_blocks(blocks):
  for i in range(NUM_BLOCKS_IN_DISK):
    print i, ':', blocks[i]

class FSError(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class Disk(object):
  def __init__(self, name, blocks=[]):
    self.name = name
    self.blocks = blocks

    if blocks == []:
      # Init bitmap
      self.blocks.append([])
      for i in range(NUM_BYTES_IN_BLOCK):
        self.blocks[0].append(0)
      for i in range(10):
        # Block   0 - bitmap
        # Block 1-6 - file descriptors
        # Block 7-9 - directory
        self.blocks[0][i] = 1

      for i in range(1, 10):
        block = []
        for j in range(NUM_BYTES_IN_BLOCK/NUM_BYTES_IN_INT):
          block.append(-1)
        self.blocks.append(block)

      for i in range(10, NUM_BLOCKS_IN_DISK):
        block = []
        for j in range(NUM_BYTES_IN_BLOCK):
          block.append(None)
        self.blocks.append(block)

      # Slot 0 - Directory
      self.blocks[1][0] = 0
      self.blocks[1][1] = 7
      self.blocks[1][2] = 8
      self.blocks[1][3] = 9

  def read_block(self, num):
    return self.blocks[num]

  def write_block(self, num, block):
    self.blocks[num] = block

  def save_disk(self, name):
    f = open(DISK_DIR + name, 'w+')
    f.write(pickle.dumps(self.blocks))
    f.close()

class FileSystem(object):
  def __init__(self):
    self.current_disk = None
    self.OFT = {}
    self.buffer = None

  def retrieve_file(self, name):
    if not self.current_disk:
      raise FSError('Disk not initialized!')
    num = convert_filename_to_int(name)
    for block_num in range(7, 10):
      block_data = self.current_disk.read_block(block_num)
      for i in range(len(block_data)/2):
        if block_data[i*2] == num:
          return block_data[i*2+1]
    return -1

  def remove_directory_entry(self, name):
    if not self.current_disk:
      raise FSError('Disk not initialized!')
    num = convert_filename_to_int(name)
    for block_num in range(7, 10):
      block_data = self.current_disk.read_block(block_num)
      for i in range(len(block_data)/2):
        if block_data[i*2] == num:
          block_data[i*2] = -1
          block_data[i*2+1] = -1
          self.current_disk.write_block(block_num, block_data)
          return

  def find_empty_block(self):
    bitmap = self.current_disk.read_block(0)
    for i in range(NUM_BLOCKS_IN_DISK):
      if bitmap[i] == 0:
        return i
    return -1

  def get_OFT_free_entry(self):
    for i in range(3):
      if i not in self.OFT:
        return i
    raise FSError('No more free entries in OFT!')

  def create_file(self, name):
    fd_index = self.retrieve_file(name)
    if fd_index >= 0:
      raise FSError('File already exists!')
    else:
      # Find a free file descriptor
      descriptor_index = -1
      for num in range(6):
        block_num = num + 1
        block_data = self.current_disk.read_block(block_num)
        for i in range(NUM_DESCRIPTORS_IN_BLOCK):
          if block_data[i*NUM_DESCRIPTORS_IN_BLOCK] == -1:
            descriptor_index = num * NUM_DESCRIPTORS_IN_BLOCK + i
            # Update file descriptor
            block_data[i*NUM_DESCRIPTORS_IN_BLOCK] = 0
            self.current_disk.write_block(block_num, block_data)
            break
        if descriptor_index != -1:
          break

      # Find a free directory entry
      free_directory_found = False
      for block_num in range(7, 10):
        block_data = self.current_disk.read_block(block_num)
        for i in range(len(block_data)/2):
          if block_data[i*2] == -1:
            block_data[i*2] = convert_filename_to_int(name)
            block_data[i*2+1] = descriptor_index
            self.current_disk.write_block(block_num, block_data)
            free_directory_found = True
            break
        if free_directory_found:
          break

      return name + ' created'

  def destroy_file(self, name):
    # Search directory to find file descriptor
    fd_index = self.retrieve_file(name)
    if fd_index < 0:
      raise FSError('File "' + name + '" does not exist!')
    else:
      # Remove directory entry
      self.remove_directory_entry(name)

      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      
      # Update bit map
      bitmap = self.current_disk.read_block(0)
      for i in range(NUM_DESCRIPTORS_IN_BLOCK):
        if i > 0 and block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i] > -1:
          bitmap[block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i]] = 0
      self.current_disk.write_block(0, bitmap)

      # Free file descriptor
      for i in range(NUM_DESCRIPTORS_IN_BLOCK):
        block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i] = -1
      self.current_disk.write_block(block_num, block_data)

      return name + ' destroyed'

  def open_file(self, name):
    # Search directory to find file descriptor
    fd_index = self.retrieve_file(name)
    if fd_index < 0:
      raise FSError('File "' + name + '" does not exist!')
    else:
      # Allocate a free OFT entry
      oft_index = self.get_OFT_free_entry()

      # Fill in file descriptor index and current position
      self.OFT[oft_index] = (fd_index, 0)

      # Read block 0 of file into buffer
      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+1]
      self.buffer = self.current_disk.read_block(disk_block_num)

      return name + ' opened ' + str(oft_index)

  def close_file(self, name):
    # Search directory to find file descriptor
    fd_index = self.retrieve_file(name)
    if fd_index < 0:
      raise FSError('File "' + name + '" does not exist!')
    else:
      for key, value in self.OFT.items():
        if value[0] == fd_index:
          oft_index = key
          break

      # TODO: Write buffer to disk
      # TODO: Update file length in descriptor

      # Free OFT entry
      del self.OFT[oft_index]

      return oft_index + ' closed'

  def list_dir_files(self):
    file_names = []
    for block_num in range(7, 10):
      block_data = self.current_disk.read_block(block_num)
      for i in range(len(block_data)/2):
        if block_data[i*2] != -1:
          file_names.append(convert_int_to_filename(block_data[i*2]))
    return ' '.join(file_names)

  def init_disk(self, name=''):
    self.OFT = {0: 0}
    try:
      if name != '':
        with open(DISK_DIR + name, 'r') as f:
          self.current_disk = Disk(name, pickle.loads(f.read()))
          return 'disk restored' 
      else:
        raise IOError
    except IOError:
      self.current_disk = Disk(name)
      return 'disk initialized'

  def save_disk(self, name):
    if not self.current_disk:
      raise FSError('No disk has been initialized!')
    else:
      self.OFT = {}
      self.current_disk.save_disk(name)
      return 'disk saved'


def main():

  fs = FileSystem()

  commands_mapping = {
    'cr': fs.create_file,
    'de': fs.destroy_file,
    'op': fs.open_file,
    # 'cl': close_file,
    # 'rd': read_file,
    # 'wr': write_file,
    # 'sk': seek_file,
    'dr': fs.list_dir_files,
    'in': fs.init_disk,
    'sv': fs.save_disk
  }

  while True:
    try:
      cmd = [p.strip() for p in raw_input().split(' ') if p.strip() != '']
      if cmd:
        print commands_mapping[cmd[0]](*cmd[1:])
      else:
        continue
    except FSError as e:
      print e.value if DEBUG else 'error'
    except EOFError:
      break

if __name__ == '__main__':
  main()
