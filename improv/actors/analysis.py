import time
import cv2
import numpy as np
from queue import Empty

from improv.actor import Actor, Spike, RunManager
from improv.store import ObjectNotFoundError

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MeanAnalysis(Actor):
    #TODO: Add additional error handling
    def __init__(self, *args):
        super().__init__(*args)

    def setup(self, param_file=None):
        ''' Set custom parameters here
            Can also be done by e.g. loading them in from 
            a configuration file. #TODO
        '''
        np.seterr(divide='ignore')

        self.num_stim = 21 
        self.frame = 0
        self.stim = {}
        self.stimStart = {}
        self.window = 500 #TODO: make user input, choose scrolling window for Visual
        self.C = None
        self.S = None
        self.Call = None
        self.Cx = None
        self.Cpop = None
        self.coords = None
        self.color = None
        self.runMean = None
        self.runMeanOn = None
        self.runMeanOff = None
        self.lastOnOff = None
        self.recentStim = [0]*self.window

    def run(self):
        self.total_times = []
        self.puttime = []
        self.colortime = []
        self.stimtime = []
        self.timestamp = []

        with RunManager(self.name, self.runAvg, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)
        
        print('Analysis broke, avg time per frame: ', np.mean(self.total_times, axis=0))
        print('Analysis broke, avg time per put analysis: ', np.mean(self.puttime))
        print('Analysis broke, avg time per color frame: ', np.mean(self.colortime))
        print('Analysis broke, avg time per stim avg: ', np.mean(self.stimtime))
        print('Analysis got through ', self.frame, ' frames')

        np.savetxt('output/timing/analysis_frame_time.txt', np.array(self.total_times))
        np.savetxt('output/timing/analysisput_frame_time.txt', np.array(self.puttime))
        np.savetxt('output/timing/analysiscolor_frame_time.txt', np.array(self.colortime))
        np.savetxt('output/timing/analysis_timestamp.txt', np.array(self.timestamp))

        np.savetxt('output/final/analysis_tuning_curves.txt', np.array(self.polarAvg))

    def runAvg(self):
        ''' Take numpy estimates and frame_number
            Create X and Y for plotting
        '''
        t = time.time()
        ids = None
        try: 
            sig = self.links['input_stim_queue'].get(timeout=0.0001)
            self.updateStim_start(sig)
        except Empty as e:
            pass #no change in input stimulus
        try:
            ids = self.q_in.get(timeout=0.0001)
            ids = [id[0] for id in ids]
            if ids is not None and ids[0]==1:
                print('analysis: missing frame')
                self.total_times.append(time.time()-t)
                self.q_out.put([1])
                raise Empty
            # t = time.time()
            self.frame = ids[-1]
            (self.coordDict, self.image, self.S) = self.client.getList(ids[:-1])
            self.C = self.S
            self.coords = [o['coordinates'] for o in self.coordDict]
            
            # Compute tuning curves based on input stimulus
            # Just do overall average activity for now
            self.stimAvg_start()
            
            self.globalAvg = np.mean(self.estsAvg[:,:8], axis=0)
            self.tune = [self.estsAvg[:,:8], self.globalAvg]

            # Compute coloring of neurons for processed frame
            # Also rotate and stack as needed for plotting
            # TODO: move to viz, but we don't need to compute this 30 times/sec
            self.color = self.plotColorFrame()

            if self.frame >= self.window:
                window = self.window
            else:
                window = self.frame

            if self.C.shape[1]>0:
                self.Cpop = np.nanmean(self.C, axis=0)
                self.Cx = np.arange(0,self.Cpop.size)+(self.frame-window)
                self.Call = self.C #already a windowed version #[:,self.frame-window:self.frame]
            
            self.putAnalysis()
            self.timestamp.append([time.time(), self.frame])
            self.total_times.append(time.time()-t)
        except ObjectNotFoundError:
            logger.error('Estimates unavailable from store, droppping')
        except Empty as e:
            pass
        except Exception as e:
            logger.exception('Error in analysis: {}'.format(e))

    def updateStim(self, stim):
        ''' Recevied new signal from some Acquirer to change input stimulus
            [possibly other action items here...? Validation?]
        '''
        # stim in format dict frame_num:[n, on/off]
        frame = list(stim.keys())[0]
        whichStim = stim[frame][0]

        # stim is dict with stimID as key and lists for indexing on/off into that stim
        # length is number of frames
        if whichStim not in self.stim.keys():
            self.stim.update({whichStim:{}})
        if abs(stim[frame][1])>1 :
            if 'on' not in self.stim[whichStim].keys():
                self.stim[whichStim].update({'on':[]})
            self.stim[whichStim]['on'].append(frame)
        else:
            if 'off' not in self.stim[whichStim].keys():
                self.stim[whichStim].update({'off':[]})
            self.stim[whichStim]['off'].append(frame)

        # also store which stim is active for each frame, up to a recent window
        self.recentStim[frame%self.window] = whichStim

    def updateStim_start(self, stim):
        frame = list(stim.keys())[0]
        whichStim = stim[frame][0]
        if whichStim not in self.stimStart.keys():
            self.stimStart.update({whichStim:[]})
        if abs(stim[frame][1])>1 :
            curStim = 1 #on
        else:
            curStim = 0 #off
        if self.lastOnOff is None:
            self.lastOnOff = curStim
        elif self.lastOnOff == 0 and curStim == 1: #was off, now on
            self.stimStart[whichStim].append(frame)
            print('Stim ', whichStim, ' started at ', frame)
        
        self.lastOnOff = curStim
        

    def putAnalysis(self):
        ''' Throw things to DS and put IDs in queue for Visual
        '''
        t = time.time()
        ids = []
        ids.append([self.client.put(self.Cx, 'Cx'+str(self.frame)), 'Cx'+str(self.frame)])
        ids.append([self.client.put(self.Call, 'Call'+str(self.frame)), 'Call'+str(self.frame)])
        ids.append([self.client.put(self.Cpop, 'Cpop'+str(self.frame)), 'Cpop'+str(self.frame)])
        ids.append([self.client.put(self.tune, 'tune'+str(self.frame)), 'tune'+str(self.frame)])
        ids.append([self.client.put(self.color, 'color'+str(self.frame)), 'color'+str(self.frame)])
        ids.append([self.client.put(self.coordDict, 'analys_coords'+str(self.frame)), 'analys_coords'+str(self.frame)])
        ids.append([self.frame, str(self.frame)])

        self.put(ids, save= [False, False, False, False, False, True, False])

        self.puttime.append(time.time()-t)

    def stimAvg_start(self):
        ests = self.S #ests = self.C
        ests_num = ests.shape[1]
        t = time.time()
        polarAvg = [np.zeros(ests.shape[0])]*12
        estsAvg = [np.zeros(ests.shape[0])]*self.num_stim
        for s,l in self.stimStart.items():
            l = np.array(l)
            if l.size>0:
                onInd = np.array([np.arange(o+5,o+15) for o in np.nditer(l)]).flatten()
                onInd = onInd[onInd<ests_num]
                offInd = np.array([np.arange(o-10,o-1) for o in np.nditer(l)]).flatten() #TODO replace
                offInd = offInd[offInd>=0]
                offInd = offInd[offInd<ests_num]
                try:
                    if onInd.size>0:
                        onEst = np.mean(ests[:,onInd], axis=1)
                    else:
                        onEst = np.zeros(ests.shape[0])
                    if offInd.size>0:
                        offEst = np.mean(ests[:,offInd], axis=1)
                    else:
                        offEst = np.zeros(ests.shape[0])
                    try:
                        estsAvg[int(s)] = onEst #(onEst / offEst) - 1
                    except FloatingPointError:
                        print('Could not compute on/off: ', onEst, offEst)
                        estsAvg[int(s)] = onEst
                    except ZeroDivisionError:
                        estsAvg[int(s)] = np.zeros(ests.shape[0])
                except FloatingPointError: #IndexError:
                    logger.error('Index error ')
                    print('int s is ', int(s))
            # else:
            #     estsAvg[int(s)] = np.zeros(ests.shape[0])

        estsAvg = np.array(estsAvg)
        polarAvg[2] = estsAvg[9,:] #np.sum(estsAvg[[9,11,15],:], axis=0)
        polarAvg[1] = estsAvg[10, :]
        polarAvg[0] = estsAvg[3, :] #np.sum(estsAvg[[3,5,8],:], axis=0)
        polarAvg[7] = estsAvg[12, :]
        polarAvg[6] = estsAvg[13, :] #np.sum(estsAvg[[13,17,18],:], axis=0)
        polarAvg[5] = estsAvg[14, :]
        polarAvg[4] = estsAvg[4, :] #np.sum(estsAvg[[4,6,7],:], axis=0)
        polarAvg[3] = estsAvg[16, :]

        # for color summation
        polarAvg[8] = estsAvg[5, :]
        polarAvg[9] = estsAvg[6, :]
        polarAvg[10] = estsAvg[7, :]
        polarAvg[11] = estsAvg[8, :]
        
        self.estsAvg = np.abs(np.transpose(np.array(polarAvg)))
        self.estsAvg = np.where(np.isnan(self.estsAvg), 0, self.estsAvg)
        self.estsAvg[self.estsAvg == np.inf] = 0
        self.stimtime.append(time.time()-t)

    def stimAvg(self):
        ests = self.S #ests = self.C
        ests_num = ests.shape[1]
        # S = self.S
        t = time.time()
        polarAvg = [np.zeros(ests.shape[0])]*8
        estsAvg = [np.zeros(ests.shape[0])]*self.num_stim

        if self.runMeanOn is None:
            self.runMeanOn = [np.zeros(ests.shape[0])]*self.num_stim
        if self.runMeanOff is None:
            self.runMeanOff = [np.zeros(ests.shape[0])]*self.num_stim
        if self.runMean is None:
            self.runMean = [np.zeros(ests.shape[0])]*self.num_stim

        if self.frame > 0: #self.window: #recompute entire mean
            for s,l in self.stim.items():
                if 'on' in l.keys() and 'off' in l.keys():
                    onInd = np.array(l['on'])
                    onInd = onInd[onInd<ests_num]
                    offInd = np.array(l['off'])
                    offInd = offInd[offInd<ests_num]
                    try:
                        on = np.mean(ests[:,onInd], axis=1)
                        off = np.mean(ests[:,offInd], axis=1)
                        try:
                            estsAvg[int(s)] = (on / off) - 1
                        except FloatingPointError:
                            print('Could not compute on/off: ', on, off)
                            estsAvg[int(s)] = on
                    except IndexError:
                        logger.error('Index error ')
                        print('int s is ', int(s))
                else:
                    estsAvg[int(s)] = np.zeros(ests.shape[0])
        else:
            # keep running mean as well as recalc mean for possible updates
            # ests only contains self.window number of most recent frames
            # running mean of last newest frame, recalc mean of all more recent frames
            for s,l in self.stim.items():
                print(s, l)
                if 'on' in l.keys() and 'off' in l.keys():
                    onInd = np.array(l['on'])
                    offInd = np.array(l['off'])
                    # print('onInd ', onInd)
                    # print('offInd ', offInd)
                    try:
                        if self.frame == onInd[-1]:
                            self.runMeanOn[int(s)] += np.mean(ests[:, onInd[-1]], axis=1)
                        elif self.frame == offInd[-1]:
                            self.runMeanOff[int(s)] += np.mean(ests[:, offInd[-1]], axis=1)
                        on = np.mean(ests[:,onInd[:-1]], axis=1)
                        off = np.mean(ests[:,offInd[:-1]], axis=1)
                        try:
                            estsAvg[int(s)] = (on / off) - 1
                        except FloatingPointError:
                            estsAvg[int(s)] = on
                    except IndexError:
                        pass
                else:
                    estsAvg[int(s)] = np.zeros(ests.shape[0])
        
        estsAvg = np.array(estsAvg)
        polarAvg[2] = estsAvg[9,:] #np.sum(estsAvg[[9,11,15],:], axis=0)
        polarAvg[1] = estsAvg[10, :]
        polarAvg[0] = estsAvg[3, :] #np.sum(estsAvg[[3,5,8],:], axis=0)
        polarAvg[7] = estsAvg[12, :]
        polarAvg[6] = estsAvg[13, :] #np.sum(estsAvg[[13,17,18],:], axis=0)
        polarAvg[5] = estsAvg[14, :]
        polarAvg[4] = estsAvg[4, :] #np.sum(estsAvg[[4,6,7],:], axis=0)
        polarAvg[3] = estsAvg[16, :]

        # for color summation
        polarAvg[8] = estsAvg[5, :]
        polarAvg[9] = estsAvg[6, :]
        polarAvg[10] = estsAvg[7, :]
        polarAvg[11] = estsAvg[8, :]
        
        self.estsAvg = np.abs(np.transpose(np.array(polarAvg)))
        self.estsAvg = np.where(np.isnan(self.estsAvg), 0, self.estsAvg)
        self.estsAvg[self.estsAvg == np.inf] = 0
        #self.estsAvg = np.clip(self.estsAvg*4, 0, 4)
        self.stimtime.append(time.time()-t)

    def plotColorFrame(self):
        ''' Computes colored nicer background+components frame
        '''
        t = time.time()
        image = self.image
        color = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        color[...,3] = 255
            # color = self.color.copy() #TODO: don't stack image each time?
        if self.coords is not None:
            for i,c in enumerate(self.coords):
                #c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(color, ind, self._tuningColor(i, color[ind[:,1], ind[:,0]]))

        # TODO: keep list of neural colors. Compute tuning colors and IF NEW, fill ConvexPoly. 

        # if self.image.shape[0] < self.image.shape[1]:
        #         self.flip = True
        #         raw = raw.T
        # else:
        #     np.swapaxes(color,0,1)
        #TODO: user input for rotating frame? See Visual class
        #print('time plotColorFrame ', time.time()-t)
        self.colortime.append(time.time()-t)
        return color

    def _tuningColor(self, ind, inten):
        ''' ind identifies the neuron by number
        '''
        if self.estsAvg[ind] is not None: # and np.sum(np.abs(self.estsAvg[ind]))>2:
            try:
                # trying sort and compare
                # rel = self.estsAvg[ind]/np.max(self.estsAvg[ind])
                # order = np.argsort(rel)
                # if rel[order[-1]] - rel[order[-2]] > 0.2: #ensure strongish tuning
                    # r, g, b = self.manual_Color(order[-1])
                    # return (r, g, b) + (255,)
                # else:
                #     # print(order, rel)
                #     return (255, 255, 255, 50)

                # trying summation coloring
                return self.manual_Color_Sum(self.estsAvg[ind])
                
                # below is old method
                # tc = np.nanargmax(self.estsAvg[ind])
                # r, g, b = self.manual_Color(tc)
                # # h = (np.nanargmax(self.estsAvg[ind])*45)/360
                # # intensity = 1 - np.mean(inten[0][0])/255.0
                # # r, g, b, = colorsys.hls_to_rgb(h, intensity, 1)
                # # r, g, b = [x*255.0 for x in (r, g, b)]
                # return (r, g, b) + (255,) #(intensity*255,)
            except ValueError:
                return (255,255,255,0)
            # except Exception:
                # print('inten is ', inten)
                # print('estsAvg[i] is ', self.estsAvg[ind])
        else:
            return (255,255,255,50) #0)

    def manual_Color(self, x):
        if x==0:
            return 240, 122, 5
        elif x==1:
            return 181, 240, 5
        elif x==2:
            return 5, 240, 5
        elif x==3:
            return 5, 240, 181
        elif x==4:
            return 5, 122, 240
        elif x==5:
            return 64, 5, 240
        elif x==6:
            return 240, 5, 240
        elif x==7:
            return 240, 5, 64
        else:
            logger.error('No idea what color!')    

    def manual_Color_Sum(self, x):
        ''' x should be length 12 array for coloring
        '''
        # r, g, b = 0, 0, 0
        # r, g, b = r, g, b + x[0]*(1, 0.25, 0)
        # r, g, b = r, g, b + x[1]*(0.75, 1, 0)
        # r, g, b = r, g, b + x[2]*(0, 1, 0)
        # r, g, b = r, g, b + x[3]*(0, 0.75, 1)
        # r, g, b = r, g, b + x[4]*(0, 0.25, 1)
        # r, g, b = r, g, b + x[5]*(0.25, 0, 1)
        # r, g, b = r, g, b + x[6]*(1, 0, 1)
        # r, g, b = r, g, b + x[7]*(1, 0, 0.25)

        # r, g, b = r, g, b + x[8]*(1, 0, 0)
        # r, g, b = r, g, b + x[9]*(0, 0, 1)
        # r, g, b = r, g, b + x[10]*(0, 0, 1)
        # r, g, b = r, g, b + x[11]*(1, 0, 0)

        r = x[0]*1 + x[1]*0.75 + x[2]*0 + x[3]*0 + x[4]*0 + x[5]*0.25 + \
            x[6]*1 + x[7]*1 + x[8]*1 + x[9]*0 + x[10]*0 + x[11]*1 

        g = x[0]*0.25 + x[1]*1 + x[2]*1 + x[3]*0.75 + x[4]*0.25 + x[5]*0 + \
            x[6]*0 + x[7]*0 + x[8]*0 + x[9]*0 + x[10]*0 + x[11]*0 

        b = x[0]*0 + x[1]*0 + x[2]*0 + x[3]*1 + x[4]*1 + x[5]*1 + \
            x[6]*1 + x[7]*0.25 + x[8]*0 + x[9]*1 + x[10]*1 + x[11]*0 

        blend = 0.3
        thresh = 0.1

        maxVal = np.max(np.array([r, g, b]))

        if maxVal > 0:
            r /= maxVal
            g /= maxVal
            b /= maxVal
        #     if r > blend*maxVal:
        #         r = blend*maxVal
        #     if g>blend*maxVal:
        #         g = blend*maxVal
        #     if b>blend*maxVal:
        #         b = blend*maxVal
        if r<thresh:
            r=0
        if g<thresh:
            g=0
        if b<thresh:
            b=0
        r*=255
        g*=255
        b*=255

        if r>0 or g>0 or b>0:
            return (r, g, b, 255)       
        else:
            return (255, 255, 255, 50)
