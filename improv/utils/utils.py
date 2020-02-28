from functools import wraps

# def coroutine(func): #FIXME who uses this and why?
#     ''' Decorator that primes 'func' by calling first {yield}. '''

#     @wraps(func)
#     def primer(*args, **kwargs):
#         gen = func(*args, **kwargs)
#         next(gen)
#         return gen
#     return primer

@coroutine
def get_num_length_from_key():
    '''
    Coroutine that gets the length of digits in LMDB key.
    Assumes that object name does not have any digits.

    For example:
        FileAcquirer puts objects with names 'acq_raw{i}' where i is the frame number.
        {i}, however, is not padded with zero, so the length changes with number.
        The B-tree sorting in LMDB results in messed up number sorting.
    Example:
        >>> num_idx = get_num_length_from_key()
        >>> num_idx.send(b'acq_raw1\x80\x03GA\xd7L\x1b\x8f\xb0\x1b\xb0.')
        1

    '''
    max_num_len = 1  # Keep track of largest digit for performance.

    def worker():
        nonlocal max_num_len
        name_num = key[:-12].decode()

        if not name_num[-max_num_len:].isdigit():
            i = max_num_len
            while not name_num[-i:].isdigit():
                if i < 1:
                    return 0
                i -= 1
            return i

        while name_num[-(max_num_len + 1):].isdigit():
            max_num_len += 1
        return max_num_len

    num = 'Primed!'
    while True:
        key = yield num
        num = worker()
