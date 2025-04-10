#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   RWLock.py
@Time    :   2024/10/19 00:04:20
@Author  :   MuliMuri
@Version :   1.0
@Desc    :   Readwrite Lock
'''


import threading


class WritePriorityReadWriteLock():
    def __init__(self) -> None:
        self.readers = 0
        self.writers_waiting = 0
        self.writer = False
        self.condition = threading.Condition()

    def acquire_read(self, timeout=None) -> bool:
        with self.condition:
            # Wait until there are no more writers or writers waiting.
            while self.writer or self.writers_waiting > 0:
                if not self.condition.wait(timeout=timeout):
                    # Timeout return
                    return False
            # Add reader count
            self.readers += 1
        return True

    def release_read(self) -> None:
        with self.condition:
            self.readers -= 1
            if self.readers == 0:
                # If there are no readers, wake up all threads to check if they can write.
                self.condition.notify_all()

    def acquire_write(self, timeout=None) -> bool:
        with self.condition:
            self.writers_waiting += 1
            while self.readers > 0 or self.writer:
                if not self.condition.wait(timeout=timeout):
                    self.writers_waiting -= 1
                    # Timeout return
                    return False
            self.writers_waiting -= 1
            self.writer = True
        return True

    def release_write(self) -> None:
        with self.condition:
            self.writer = False
            # After the write lock is released, wake up all waiting threads.
            self.condition.notify_all()
