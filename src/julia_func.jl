# test.jl
import Statistics: mean

function test(x)
	result = zeros(10)
	for i in 1:10
		result[i] = mean(x[i, :, :])
	end
	return result
end