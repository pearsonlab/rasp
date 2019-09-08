function initMemMap(src,event,arguments)
    global mm;
    global header;
    mm = memmapfile('scanimage256.mmap', 'Format', {'double', [256, 256], 'data'}, 'Writable', true);
    header = memmapfile('header.mmap', 'Format', 'int16', 'Writable', true);
    fprintf('Memmapfile available.\n')
end