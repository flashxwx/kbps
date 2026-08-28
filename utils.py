import time

from threading import Event

def sleep_with_event(event: Event, seconds: float):
    is_full = event.wait(seconds)

    if is_full:
        return False
    else:
        return True

def sleep_until_with_event(event: Event, timestamp: float):
    while not event.is_set():
        remaining = timestamp - time.time()

        if remaining <= 0:
            return True
        
        event.wait(remaining)
    
    return False