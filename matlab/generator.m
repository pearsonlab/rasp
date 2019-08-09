% MAT file is generated from Tolias_mesoscope_2.h5
%
% import h5py
% with h5py.File('/Users/Chaichontat/Desktop/Lab/rasp/data/Tolias_mesoscope_2.hdf5', 'r') as file:
%     keys = list(file.keys())
%     data = file[keys[0]].value #only one dset per file atm
%     print('data is ', len(data))
% 
% import scipy.io as sio
% sio.savemat('np_vector.mat', {'data':data})

raw = load('np_vector.mat');

img = memmapfile('scanbox.mmap', 'Format', {'int16', [440 256], 'data'}, 'Writable', true);
header = memmapfile('header.mmap', 'Format', 'int16', 'Writable', true);

i = 0;
header.Data(1) = 0;
header.Data(2) = 0;

while header.Data(2) ~= 1
    pause(0.5)
end

fprintf('Starting!')

while true
    pause(1/15);
    img.Data.data = raw.data(mod(i, 1000) + 1, :, :);
    header.Data(1) = 1;
    i = i + 1;
end