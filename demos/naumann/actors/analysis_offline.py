import time
import numpy as np
from scipy.linalg import norm
import matplotlib.pylab as plt
# import cupy as np

# @profile
def runModel(data):
    dh = p['hist_dim']
    N  = p['numNeurons']

    # nonlinearity (exp)
    f = np.exp

    expo = np.zeros((N,data['y'].shape[1]))
    # simulate the model for t samples (time steps)
    for j in np.arange(0,data['y'].shape[1]): 
        expo[:,j] = runModelStep(data['y'][:,j-dh:j], data['s'][:,j])
    
    # computed rates
    # try:
    rates = f(expo)
    # except:
    #     import pdb; pdb.set_trace()

    return rates

# @profile
def runModelStep(y, s):
    N  = p['numNeurons']
    dh = p['hist_dim']
    ds = p['stim_dim']

    # model parameters
    w = theta[:N*N].reshape((N,N))
    h = theta[N*N:N*(N+dh)].reshape((N,dh))
    b = theta[N*(N+dh):N*(N+dh+1)].reshape(N)
    k = theta[N*(N+dh+1):].reshape((N, ds))

    # data length in time
    t = y.shape[1]

    # expo = np.zeros(N)
    # for i in np.arange(0,N): # step through neurons
        # compute model firing rate
    # if t<1:
    hist = np.zeros(N)
    if t>0:
        # import pdb; pdb.set_trace()
        for i in np.arange(0,N): # step through neurons
            try:
                hist[i] = np.sum(np.flip(h[i,:], axis=0)*y[i,:])   
            except:
                import pdb; pdb.set_trace()
    if t>0:
        np.fill_diagonal(w, 0)
        weights = w @ y[:,-1]
    else:
        weights = np.zeros(N)

    stim = k @ s 
   
    expo = (b + hist + weights + stim)
    
    return expo

# @profile
def ll_grad(y, s):
    dh = p['hist_dim']
    dt = p['dt']
    N  = p['numNeurons']
    M  = y.shape[1] #params['numSamples'] #TODO: should be equal

    # run model at theta
    data = {}
    data['y'] = y
    data['s'] = s
    rhat = runModel(data)

    # #### print ll
    # ll_val = (np.sum(rhat) - np.sum(y*np.log(rhat+np.finfo(float).eps)))/(y.shape[1]*N**2)
    # print(ll_val)
    # rhat = rhat*dt

    # compute gradient
    grad = dict()

    # difference in computed rate vs. observed spike count
    rateDiff = (rhat - data['y'])

    # graident for baseline
    grad['b'] = np.sum(rateDiff, axis=1)/M

    # gradient for stim
    grad['k'] = rateDiff.dot(data['s'].T)/M

    # gradient for coupling terms
    yr = np.roll(data['y'], 1)
    #yr[0,:] = 0
    grad['w'] = rateDiff.dot(yr.T)/M #+ 2*np.abs(theta[:N*N].reshape((N,N)))/(N*N)
    ## ensure diagonals are zero
    np.fill_diagonal(grad['w'], 0)

    #d_abs(theta[:N*N].reshape((N,N)))
    
    # gradient for history terms
    grad['h'] = np.zeros((N,dh))
    #grad['h'][:,0] = rateDiff[:,0].dot(data['y'][:,0].T)/M
    for i in np.arange(0,N):
        for j in np.arange(0,dh):
            grad['h'][i,j] = np.sum(np.flip(data['y'],1)[i,:]*rateDiff[i,:])/M

    # flatten grad
    grad_flat = np.concatenate((grad['w'],grad['h'],grad['b'],grad['k']), axis=None).flatten()/N

    return grad_flat

# @profile
def ll(y, s, theta):
    eps = np.finfo(float).eps
    dh = p['hist_dim']
    dt = p['dt']
    N  = p['numNeurons']
    # run model at theta
    data = {}
    data['y'] = y
    data['s'] = s
    rhat = runModel(data)
    # try:
    #     rhat = rhat*dt
    # except FloatingPointError:
    #     print('FPE in rhat*dt; likely underflow')

    # model parameters
    # w = theta[:N*N].reshape((N,N))
    # h = theta[N*N:N*(N+dh)].reshape((N,dh))
    # b = theta[N*(N+dh):].reshape(N)

    # compute negative log-likelihood
    # include l1 or l2 penalty on weights
    # l2 = norm(w) #100*np.sqrt(np.sum(np.square(theta['w'])))
    # l1 = np.sum(np.sum(np.abs(w)))/(N*N)

    ll_val = (np.sum(rhat) - np.sum(y*np.log(rhat+eps)))/(y.shape[1]*N**2)  #+ l1

    return ll_val

def updateTheta(theta, m, v, newN):
    ''' TODO: Currently terribly inefficient growth
        Probably initialize large and index into it however many N we have
    '''
    N  = p['numNeurons']
    dh = p['hist_dim']
    ds = p['stim_dim']

    old_w = theta[:N*N].reshape((N,N))
    old_h = theta[N*N:N*(N+dh)].reshape((N,dh))
    old_b = theta[N*(N+dh):N*(N+dh+1)].reshape(N)
    old_k = theta[N*(N+dh+1):].reshape((N, ds))

    m_w = m[:N*N].reshape((N,N))
    m_h = m[N*N:N*(N+dh)].reshape((N,dh))
    m_b = m[N*(N+dh):N*(N+dh+1)].reshape(N)
    m_k = m[N*(N+dh+1):].reshape((N, ds))

    v_w = v[:N*N].reshape((N,N))
    v_h = v[N*N:N*(N+dh)].reshape((N,dh))
    v_b = v[N*(N+dh):N*(N+dh+1)].reshape(N)
    v_k = v[N*(N+dh+1):].reshape((N, ds))

    p["numNeurons"] = newN

    w = np.zeros((newN,newN))
    w[:N, :N] = old_w
    h = np.zeros((newN,dh))
    h[:N, :] = old_h
    b = np.zeros(newN)
    b[:N] = old_b
    k = np.zeros((newN,ds))
    k[:N, :] = old_k
    theta = np.concatenate((w,h,b,k), axis=None).flatten()

    w = np.zeros((newN,newN))
    w[:N, :N] = m_w
    h = np.zeros((newN,dh))
    h[:N, :] = m_h
    b = np.zeros(newN)
    b[:N] = m_b
    k = np.zeros((newN,ds))
    k[:N, :] = m_k
    m = np.concatenate((w,h,b,k), axis=None).flatten().copy()

    w = np.zeros((newN,newN))
    w[:N, :N] = v_w
    h = np.zeros((newN,dh))
    h[:N, :] = v_h
    b = np.zeros(newN)
    b[:N] = v_b
    k = np.zeros((newN,ds))
    k[:N, :] = v_k
    v = np.concatenate((w,h,b,k), axis=None).flatten().copy()
    
    return theta, m, v

if __name__=="__main__":
    # load data
    # import numpy
    C = np.loadtxt(open('output_snap/ests_C_frame2875.txt', 'rb'), delimiter=' ')
    stim = np.loadtxt(open('output_snap/stims.txt', 'rb'), delimiter=' ')[:,:2875]
    
    # C = np.asarray(C)
    # stim = np.asarray(stim)

    online = False

    # import pdb; pdb.set_trace()
    if not online:
        N = C.shape[0]
        w = np.zeros((N,N)) 
        h = np.zeros((N,4)) 
        k = np.zeros((N,8))
        b = np.zeros(N)
        theta = np.concatenate((w,h,b,k), axis=None).flatten()
        p = {'numNeurons': N, 'hist_dim': 4, 'numSamples': 1, 'dt': 0.5, 'stim_dim': 8}

        i = 0
        max_iter=500
        step = 0.05
        while i<max_iter:
            # timer = time.time()
            print(ll(C[:,-200:], stim[:,-200:], theta))
            # print('--------- Time: ', time.time() - timer)
            theta -= step*ll_grad(C[:,-200:], stim[:,-200:])
            i+=1
            step /= 1.001

            # if i in [10,50,100,200,300,400]:

            #     w = theta[:N*N].reshape((N,N))

            #     import matplotlib.pylab as plt

            #     plt.imshow(w)
            #     plt.show(block=True)

            #     import pdb; pdb.set_trace()

        ## save data for online comparison
        w = theta[:N*N].reshape((N,N))
        np.savetxt('offline_w_200iter.txt', w)

    
    ## OR simulate online analysis
    if online:
        w0 = np.loadtxt(open('offline_w_1000iter.txt', 'rb'))

        N = 20
        M = C.shape[1]
        w = np.zeros((N,N)) 
        h = np.zeros((N,4)) 
        k = np.zeros((N,8))
        b = np.zeros(N)
        theta = np.concatenate((w,h,b,k), axis=None).flatten()
        p = {'numNeurons': N, 'hist_dim': 4, 'numSamples': 1, 'dt': 0.5, 'stim_dim': 8}

        first_online = (C!=0).argmax(axis=1) # when we first see the neuron

        # step = 5e-4
        loglike = []
        diff = []
        ##for adam
        beta1 = 0.9
        beta2 = 0.999
        m = np.zeros_like(theta)
        v = np.zeros_like(theta)

        for i in np.arange(100,M):

            num_Neuro_online = np.count_nonzero(first_online<i)
            neurons = np.nonzero(first_online<i)
            #TODO TODO: not accurate picture of when we saw each neuron

            if p["numNeurons"] < num_Neuro_online: #check for more neurons
                theta, m, v = updateTheta(theta, m, v, num_Neuro_online)
                N = p["numNeurons"]

            p["numSamples"] = i

            if i<200:
                y_step = C[neurons,:i]
                stim_step = stim[:, :i]
            else:
                y_step =  C[neurons,i-200:i]
                stim_step = stim[:, i-200:i]
            y_step = np.where(np.isnan(y_step), 0, y_step)
            y_step = np.squeeze(y_step)

            ll_i = ll(y_step, stim_step, theta)
            loglike.append(ll_i)

            w = theta[:N*N].reshape((N,N))
            wcf = np.zeros_like(w0)
            wcf[:N,:N] = w
            wdiff = w0 - wcf
            mse = np.sum(wdiff**2)/N**2
            diff.append(mse)

            print(i, N, ll_i, mse)
            
            it = 0
            step = 0.005
            while it<5:
                ## using adam
                # m = beta1*m + (1-beta1)*grad
                # v = beta2*v + (1-beta2)*grad**2
                # m_hat = m/(1-np.power(beta1,it+1))
                # v_hat = v/(1-np.power(beta2,it+1))
                # theta -= step*m_hat / (np.sqrt(v_hat)+np.finfo(float).eps)
                
                ## using SGD
                grad = ll_grad(y_step, stim_step)
                theta -= step*grad
                step /= 1.001

                it+=1

        loglike = np.array(loglike)
        diff = np.array(diff)
        plt.plot(loglike)
        plt.plot(diff)
        plt.show()

    import pdb; pdb.set_trace()