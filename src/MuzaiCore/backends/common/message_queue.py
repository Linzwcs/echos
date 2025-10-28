# file: src/MuzaiCore/backends/common/message_queue.py
"""
A simple, thread-safe message queue for communication between the main
thread and the real-time audio thread.
"""
import queue
from typing import Callable, Any


class RealTimeMessageQueue:
    """
    A wrapper around Python's standard queue to provide a clear interface
    for SPSC (Single-Producer, Single-Consumer) communication.

    In a production C++ application, this would be a lock-free ring buffer.
    For Python, queue.Queue is a robust and sufficient choice.
    """

    def __init__(self):
        self._queue = queue.Queue()

    def push(self, message: Any):
        """
        Pushes a message onto the queue. Called by the main thread (producer).
        This is a non-blocking operation.
        """
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            # This should ideally never happen with an unbounded queue.
            # In a real-world bounded queue, this indicates a performance problem.
            print("Warning: Real-time message queue is full!")

    def drain(self, handler: Callable[[Any], None]):
        """
        Drains all pending messages from the queue and applies a handler to each.
        Called by the audio thread (consumer) at the start of a processing cycle.
        This is non-blocking and processes only what's currently in the queue.
        """
        while True:
            try:
                message = self._queue.get_nowait()
                handler(message)
            except queue.Empty:
                # The queue is empty, we've processed all pending messages.
                break
