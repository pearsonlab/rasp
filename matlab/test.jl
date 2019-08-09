using MATLAB
using PyCall

mat"""img = memmapfile('scanbox.mmap', 'Format', {'int16', [440 256], 'data'}, 'Writable', true);
header = memmapfile('header.mmap', 'Format', 'int16', 'Writable', true);"""

function start()
	mat"header.Data(2) = 1"
end

function get_frame()
	mat"""
	while true
		if header.Data(1) == 1
			break;
		end
	end
	header.Data(1) = 0;
	"""
	return mat"img.Data.data"
end
