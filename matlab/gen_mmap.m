clear; 

f = fopen('scanbox.mmap', 'w');
for col = 1:256
    row = (1:440)';
    fwrite(f,row,'int16');
end
fclose(f);

f = fopen('header.mmap', 'w');
fwrite(f,[1:16],'int16');
fclose(f);