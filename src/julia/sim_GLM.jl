module simGLM

using ForwardDiff
using StaticArrays
using LinearAlgebra: dot
using DelimitedFiles

function ll(theta, data, params)
    # theta is w, h, b, data is y
    M = size(data)[2] #params["numSamples"]
    N = params["numNeurons"]
    dt = params["dt"]
    dh = params["hist_dim"]

    expo = ones(eltype(theta), N, M)

    for j in range(dh,stop=M)
        expo[:,j] = runModelStep(theta, data[:, 1+j-dh:j], params)
    end

    rhat = dt.*exp.(expo)

    return (sum(rhat)+sum(data.*log.(rhat)))/M
end

function runModelStep(theta, data, params)
    M = params["numSamples"]
    N = params["numNeurons"]
    dh = params["hist_dim"]

    w = reshape(theta[1:N*N], N, N)
    h = reshape(theta[N*N+1:N*(N+dh)], N, dh)
    b = reshape(theta[N*(N+dh)+1:end], N)

    t = size(data)[2] # data length in time

    expo = zeros(eltype(theta), N)
    for i in range(1, stop=N)
        if t<1
            hist = 0
        elseif t<dh
            hist = sum(reverse(h,dims=2)[i,1:t].*data[i,1:t])
        else
            hist = sum(reverse(h,dims=2)[i,:].*data[i,t-dh+1:t])
        end
        
        if t<2
            weights = 0
        else
            weights = dot(w[i,:], data[:,t-1])
        end
        expo[i] = b[i]+hist+weights
    end

    return expo
end

function ll_grad(x, data, params)
    function wrapper(x)
        return ll(x, data, params)
    end
    return ForwardDiff.gradient(n->wrapper(n), x)
end


end