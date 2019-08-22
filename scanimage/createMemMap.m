f = fopen('scanimage256.mmap', 'w');
for col = 1:256
    row = (1:256)';
    fwrite(f,row,'double');
end
fclose(f);

f = fopen('header.mmap', 'w');
fwrite(f,[1:16],'int16');
fclose(f);
