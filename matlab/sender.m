img =  memmapfile('scanbox.mmap', 'Format', {'int16', [440 256], 'data'}, 'Writable', true);
header =  memmapfile('header.mmap', 'Format', 'int16', 'Writable', true);
            