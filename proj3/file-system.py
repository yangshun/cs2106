#!/bin/python

DEBUG = True
NUM_BLOCKS_IN_DISK = 64
NUM_BYTES_IN_BLOCK = 64
NUM_BYTES_IN_INT = 4
NUM_BITS_IN_BYTE = 8

class FSError(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class Disk(object):
  def __init__(self, name):
    self.name = name
    self.blocks = []

    # Init bitmap
    self.blocks.append([])
    for i in range(NUM_BYTES_IN_BLOCK):
      self.blocks[0].append(0)
    for i in range(10):
      # Block   0 - bitmap
      # Block 1-6 - file descriptors
      # Block 7-9 - directory
      self.blocks[0][i] = 1

    for i in range(1, NUM_BLOCKS_IN_DISK):
      block = []
      for j in range(NUM_BYTES_IN_BLOCK/NUM_BYTES_IN_INT):
        block.append(-1)
      self.blocks.append(block)

    # Slot 0 - Directory
    self.blocks[1][0] = 0
    self.blocks[1][1] = 7
    self.blocks[1][2] = 8
    self.blocks[1][3] = 9

  def read_block(num):
    return self.blocks[num]

  def write_block(num, block):
    self.blocks[num] = block

class FileSystem(object):
  def __init__(self):
    self.disks = {}
    self.current_disk = None
    self.OFT = {}

  # def convert_filename_to_int(name):
  #   result = 0
  #   for char in name:
  #     result <<= NUM_BITS_IN_BYTE
  #     result |= ord(char) 
  #   return result

  # def convert_int_to_filename(num):
  #   filename = ''
  #   while num > 0:
  #     filename = chr(num & 0xff) + filename
  #     num >>= NUM_BITS_IN_BYTE
  #   return filename

  # def check_existence_of_file(name):
  #   if not self.current_disk:
  #     raise FSError('Disk not initialized!')
  #   num = convert_filename_to_int(name)

  # def create_file(name):
  #   if not self.current_disk:
  #     raise FSError('Disk not initialized!')
  #   if name not in files:
  #     files.append(name)
  #     return name + ' created'
  #   else:
  #     raise FSError('File <' + name + '> already exists!')

  # def destroy_file(name):
  #   if name in files:
  #     files.remove(name)
  #     return name + ' destroyed'
  #   else:
  #     raise FSError('File <' + name + '> does not exist!')

  # def open_file(name):
  #   if name in files:
  #     files.remove(name)
  #     return name + ' destroyed'
  #   else:
  #     raise FSError('File <' + name + '> does not exist!')

  def init_disk(self, name=''):
    if name in self.disks:
      self.current_disk = self.disks[name]
      return 'disk restored'
    else:
      self.current_disk = Disk(name)
      return 'disk initialized'

  def save_disk(self, name):
    self.disks[name] = self.current_disk
    return 'disk saved'


def main():

  fs = FileSystem()

  commands_mapping = {
    # 'cr': create_file,
    # 'de': destroy_file,
    # 'op': open_file,
    # 'cl': close_file,
    # 'rd': read_file,
    # 'wr': write_file,
    # 'sk': seek_file,
    # 'dr': list_dir_files,
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
