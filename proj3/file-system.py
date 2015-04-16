#!/bin/python

import pickle

DEBUG = False
DISK_DIR = './disk/'
NUM_BLOCKS_IN_DISK = 64
NUM_BYTES_IN_BLOCK = 64
NUM_BYTES_IN_INT = 4
NUM_DESCRIPTORS_IN_BLOCK = 4
NUM_BITS_IN_BYTE = 8
NUM_ENTRIES_IN_OFT = 4

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
  for i in range(18):
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
    # Dict of oft_index: [rw_buffer, curr_pos, fd_index]
    self.OFT = {}

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
    for i in range(1, NUM_ENTRIES_IN_OFT):
      if i not in self.OFT:
        return i
    raise FSError('No more free entries in OFT!')

  def set_bitmap_value(self, index, value):
    bitmap = self.current_disk.read_block(0)
    bitmap[index] = value
    self.current_disk.write_block(0, bitmap)

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
      # Remove from OFT table if file is open
      for i in range(1, NUM_ENTRIES_IN_OFT):
        if i in self.OFT and self.OFT[i][2] == fd_index:
          self.close_file(i)

      # Remove directory entry
      self.remove_directory_entry(name)

      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      
      # Update bit map
      for i in range(1, NUM_DESCRIPTORS_IN_BLOCK):
        if i > 0 and block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i] > -1:
          self.set_bitmap_value(block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i], 0)

      # Free file descriptor
      block_data[index*NUM_DESCRIPTORS_IN_BLOCK] = -1
      for i in range(1, NUM_DESCRIPTORS_IN_BLOCK):
        disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i]
        block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i] = -1
        self.current_disk.write_block(disk_block_num, [None] * NUM_BYTES_IN_BLOCK)
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
      self.OFT[oft_index] = [None, 0, fd_index]

      # Read block 0 of file into buffer
      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+1]

      # Allocate block
      if disk_block_num == -1:
        disk_block_num = self.find_empty_block()
        block_data[index*NUM_DESCRIPTORS_IN_BLOCK+1] = disk_block_num
        self.current_disk.write_block(block_num, block_data)
        self.set_bitmap_value(disk_block_num, 1)

      self.OFT[oft_index][0] = self.current_disk.read_block(disk_block_num)

      return name + ' opened ' + str(oft_index)

  def close_file(self, oft_index):
    oft_index = int(oft_index)
    if oft_index in self.OFT:
      rw_buffer, curr_pos, fd_index = self.OFT[oft_index]

      # Write buffer to disk
      disk_offset = curr_pos // NUM_BYTES_IN_BLOCK + 1
      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+disk_offset]
      self.current_disk.write_block(disk_block_num, rw_buffer)

      # Update file length in descriptor
      file_length = 0
      for i in range(1, NUM_DESCRIPTORS_IN_BLOCK):
        tmp_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i]
        for j in self.current_disk.read_block(tmp_block_num):
          if j != None:
            file_length += 1
          else:
            break
      block_data[index*NUM_DESCRIPTORS_IN_BLOCK] = file_length
      self.current_disk.write_block(block_num, block_data)

      # Free OFT entry
      del self.OFT[int(oft_index)]
      return str(oft_index) + ' closed'
    else:
      raise FSError('Index "' + str(oft_index) + '" does not exist in OFT!')

  def read_file(self, oft_index, count):
    oft_index = int(oft_index)
    count = int(count)

    if oft_index in self.OFT:
      printed_message = ''
      rw_buffer, curr_pos, fd_index = self.OFT[oft_index]
      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      file_length = block_data[index*NUM_DESCRIPTORS_IN_BLOCK]
      for i in range(curr_pos, curr_pos + count):
        # Reached end of file
        curr_pos = i
        if file_length == i:
          break

        disk_offset = i // NUM_BYTES_IN_BLOCK + 1
        disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+disk_offset]
        rw_buffer = self.current_disk.read_block(disk_block_num)
        printed_message += rw_buffer[i%NUM_BYTES_IN_BLOCK]
      
      self.OFT[oft_index][0] = rw_buffer
      self.OFT[oft_index][1] = curr_pos
      return printed_message
    else:
      raise FSError('Index "' + str(oft_index) + '" does not exist in OFT!')
    
  def write_file(self, oft_index, char, count):
    oft_index = int(oft_index)
    count = int(count)

    if oft_index in self.OFT:
      rw_buffer, curr_pos, fd_index = self.OFT[oft_index]
      block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
      index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
      block_data = self.current_disk.read_block(block_num)
      curr_disk_offset = curr_pos // NUM_BYTES_IN_BLOCK + 1

      for i in range(curr_pos, curr_pos + count):
        # Exceed 3 disk blocks
        if i > 3 * NUM_BYTES_IN_BLOCK - 1:
          break

        rw_buffer[i%NUM_BYTES_IN_BLOCK] = char

        # End of buffer reached
        if ((i+1) % NUM_BYTES_IN_BLOCK) == 0 and i != 3 * NUM_BYTES_IN_BLOCK - 1:
          self.current_disk.write_block(block_num, rw_buffer)
          prev_disk_offset = curr_disk_offset
          curr_disk_offset = (i+1) // NUM_BYTES_IN_BLOCK + 1
          
          # Write the buffer to disk block
          prev_disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+prev_disk_offset]
          self.current_disk.write_block(prev_disk_block_num, rw_buffer)
          next_disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+curr_disk_offset]

          # If block does not exist yet
          if next_disk_block_num == -1:
            # Allocate new block (search and update bitmap)
            next_disk_block_num = self.find_empty_block()
            self.set_bitmap_value(next_disk_block_num, 1)
            # Update file descriptor with new block number
            block_data[index*NUM_DESCRIPTORS_IN_BLOCK+curr_disk_offset] = next_disk_block_num
            self.current_disk.write_block(block_num, block_data)

          rw_buffer = self.current_disk.read_block(next_disk_block_num)

      curr_pos += count
      self.OFT[oft_index][0] = rw_buffer
      self.OFT[oft_index][1] = curr_pos
      # Update file length in descriptor
      file_length = 0
      for i in range(1, NUM_DESCRIPTORS_IN_BLOCK):
        tmp_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+i]
        if tmp_block_num != -1:
          for j in self.current_disk.read_block(tmp_block_num):
            if j != None:
              file_length += 1
            else:
              break
      block_data[index*NUM_DESCRIPTORS_IN_BLOCK] = file_length
      self.current_disk.write_block(block_num, block_data)

      return str(count) + ' bytes written'
    else:
      raise FSError('Index "' + str(oft_index) + '" does not exist in OFT!')

  def seek_file(self, oft_index, pos):
    oft_index = int(oft_index)
    pos = int(pos)

    if oft_index in self.OFT:
      rw_buffer, curr_pos, fd_index = self.OFT[oft_index]
      current_block = curr_pos // NUM_BYTES_IN_BLOCK
      seeked_block = pos // NUM_BYTES_IN_BLOCK

      if current_block != seeked_block:
        # Read block 0 of file into buffer
        block_num = fd_index // NUM_DESCRIPTORS_IN_BLOCK + 1
        index = fd_index % NUM_DESCRIPTORS_IN_BLOCK
        block_data = self.current_disk.read_block(block_num)
        disk_block_num = block_data[index*NUM_DESCRIPTORS_IN_BLOCK+1]
        self.OFT[oft_index][0] = self.current_disk.read_block(disk_block_num)

      # TODO: Check that new position not beyond file length

      # Set the current position to the new position
      self.OFT[oft_index][1] = pos
      return 'position is ' + str(pos)
    else:
      raise FSError('Index "' + str(oft_index) + '" does not exist in OFT!')

  def list_dir_files(self):
    file_names = []
    for block_num in range(7, 10):
      block_data = self.current_disk.read_block(block_num)
      for i in range(len(block_data)/2):
        if block_data[i*2] != -1:
          file_names.append(convert_int_to_filename(block_data[i*2]))
    return ' '.join(file_names)

  def init_disk(self, name=''):
    self.OFT = {0: [0, 0, 0]}
    try:
      if name != '':
        with open(DISK_DIR + name, 'r') as f:
          self.current_disk = Disk(name, pickle.loads(f.read()))
          return 'disk restored' 
      else:
        raise IOError
    except IOError:
      self.current_disk = Disk(name, [])
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
    'cl': fs.close_file,
    'rd': fs.read_file,
    'wr': fs.write_file,
    'sk': fs.seek_file,
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
        print ''
    except FSError as e:
      print e.value if DEBUG else 'error'
    except EOFError:
      break

if __name__ == '__main__':
  main()
