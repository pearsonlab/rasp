import PyCall

z = [rand(10, 100, 10^n) for n in 1:scale]

function from_julia(i)
	return z[i]
end

function to_julia(arr)
	return nothing
end

function bidirectional(arr)
	return arr
end