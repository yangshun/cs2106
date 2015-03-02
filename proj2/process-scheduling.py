#!/bin/python

from math import *
from copy import *

def main():
  input_str = [int(p) for p in raw_input().split(' ')]
  processes = []
  for i in range(len(input_str)//2):
    process = { 'process_id': i, 
                'arrival_time': input_str[i*2], 
                'service_time': input_str[i*2+1]
              }
    processes.append(process)
  processes.sort(key=lambda x:x['arrival_time'])
  
  fifo(deepcopy(processes))
  sjf(deepcopy(processes))
  srt(deepcopy(processes))
  mlf(deepcopy(processes))

def print_real_times(real_times):
  real_times.sort(key=lambda x:x[0])
  real_times = [x[1] for x in real_times]
  average = float(int(float(sum(real_times))/len(real_times) * 100))/100
  print '{0:.2f} {1}'.format(average, ' '.join([str(f) for f in real_times]))

def fifo(processes):
  real_times = []
  current_time = 0
  while len(processes) > 0:
    # Update priority of all processes
    for process in processes:
      process['priority'] = current_time - process['arrival_time']
    processes.sort(key=lambda x:x['priority'], reverse=True)
    current_process = processes[0]
    real_times.append((current_process['process_id'], current_time - current_process['arrival_time'] + current_process['service_time']))
    current_time += current_process['service_time']
    processes.pop(0)
  print_real_times(real_times)

def sjf(processes):
  real_times = []
  current_time = 0
  while len(processes) > 0:
    # Update priority of all processes
    available_processes = [p for p in processes if p['arrival_time'] <= current_time]
    for process in available_processes:
      process['priority'] = process['service_time']
    available_processes.sort(key=lambda x:x['priority'])
    current_process = available_processes[0]
    real_times.append((current_process['process_id'], current_time - current_process['arrival_time'] + current_process['service_time']))
    current_time += current_process['service_time']
    processes = [p for p in processes if p['process_id'] != current_process['process_id']]
  print_real_times(real_times)

def srt(processes):
  real_times = []
  current_time = 0
  for process in processes:
    process['remaining_time'] = process['service_time']
    process['waiting_time'] = 0

  while len(processes) > 0:
    # Update priority of all processes
    available_processes = [p for p in processes if p['arrival_time'] <= current_time]
    for process in available_processes:
      process['priority'] = -process['remaining_time']
      process['waiting_time'] += 1
    available_processes.sort(key=lambda x:x['priority'], reverse=True)

    current_process = available_processes[0]
    current_process['waiting_time'] -= 1
    current_process['remaining_time'] -= 1
    if (current_process['remaining_time'] == 0):
      real_times.append((current_process['process_id'], current_process['waiting_time'] + current_process['service_time']))
      processes = [p for p in processes if p['process_id'] != current_process['process_id']]
    current_time += 1
  print_real_times(real_times)

import time

def mlf(processes):
  N = 5
  T = 1
  real_times = []
  current_time = 0
  for process in processes:
    process['waiting_time'] = 0
    process['remaining_time'] = process['service_time']

  priority_levels = []
  for i in range(N):
    priority_levels.append([])

  def processes_remaining(priority_levels):
    return sum([len(pq) for pq in priority_levels])

  def print_pq(priority_levels):
    if processes_remaining(priority_levels) > 0:
      for i in range(N):
        print i, ': ', ' '.join([str((l['process_id'], l['time_received'], l['waiting_time'])) for l in priority_levels[i]])

  def top_process(priority_levels):
    if processes_remaining(priority_levels) > 0:
      for i in range(N):
        if len(priority_levels[i]) > 0:
          return i, priority_levels[i][0]

  def update_waiting_time(priority_levels):
    for i in range(N):
      for process in priority_levels[i]:
        process['waiting_time'] += 1

  while True:
    new_processes_at_current_time = [p for p in processes if p['arrival_time'] == current_time]
    for process in new_processes_at_current_time:
      process['time_received'] = 0
      priority_levels[0].append(process)
    level, current_process = top_process(priority_levels)
    current_process['time_received'] += 1
    current_process['remaining_time'] -= 1

    if current_process['remaining_time'] == 0:
      priority_levels[level].pop(0) # Pop current process
      real_times.append((current_process['process_id'], current_process['waiting_time'] + current_process['service_time']))
    elif current_process['time_received'] == 2 ** level * T:
      priority_levels[level].pop(0) # Pop current process
      current_process['time_received'] = 0
      priority_levels[level+1].append(current_process)
    update_waiting_time(priority_levels)
    current_process['waiting_time'] -= 1
    
    processes = [p for p in processes if p['arrival_time'] != current_time]
    
    current_time += 1
    if processes_remaining(priority_levels) == 0:
      break
    
  print_real_times(real_times)

if __name__ == "__main__":
  main()
