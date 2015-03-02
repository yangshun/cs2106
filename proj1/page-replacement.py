#!/bin/python

SIZE = 16

def main():
  rs = [int(p) for p in raw_input().split(' ')]
  fifo(rs[:])
  lru(rs[:])
  second_chance(rs[:])

def generate_pm():
  return list(range(SIZE))

def print_faults(page_faults):
  output = [len(page_faults)]
  output.extend(page_faults)
  print ' '.join([str(f) for f in output])

def fifo(rs):
  pm = generate_pm()
  pages = set(pm)
  page_faults = []
  pointer_index = 0
  for time, page in enumerate(rs):
    if page not in pages:
      page_faults.append(time + 1)
      pages.remove(pm[pointer_index])
      pages.add(page)
      pm[pointer_index] = page
      pointer_index = (pointer_index + 1) % SIZE
  print_faults(page_faults)

def lru(rs):
  pm = generate_pm()
  pages = set(pm)
  page_faults = []
  queue = pm[:] # reverse of the pm
  for time, page in enumerate(rs):
    if page not in pages:
      page_faults.append(time + 1)
      pages.remove(queue[0])
      queue.pop(0)
      pages.add(page)
      queue.append(page)
    else:
      queue.pop(queue.index(page))
      queue.append(page)
  print_faults(page_faults)

def second_chance(rs):
  pm = generate_pm()
  bits = dict([(p, 1) for p in pm])
  page_faults = []
  pointer_index = 0
  for time, page in enumerate(rs):
    if page not in bits:
      page_faults.append(time + 1)
      while bits[pm[pointer_index]] == 1:
        bits[pm[pointer_index]] = 0
        pointer_index = (pointer_index + 1) % SIZE
      del bits[pm[pointer_index]]
      pm[pointer_index] = page
      pointer_index = (pointer_index + 1) % SIZE
    bits[page] = 1
  print_faults(page_faults)

if __name__ == "__main__":
  main()
