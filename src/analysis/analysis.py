from nexus.actor import Actor, Spike, RunManager
from nexus.store import ObjectNotFoundError
from queue import Empty
import numpy as np
import time
import cv2
import colorsys

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SpontAnalysis(Actor):
    def __init__(self, *args):
        super().__init__(*args)

    def setup(self):
        self.frame = 0
        self.window = 500 #TODO: make user input, choose scrolling window for Visual
        self.C = None
        self.S = None
        self.Call = None
        self.Cx = None
        self.Cpop = None
        self.coords = None
        self.color = None

    def run(self):
        self.total_times = []
        self.timestamp = []

        with RunManager(self.name, self.fitModel, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)
        
        print('Analysis broke, avg time per frame: ', np.mean(self.total_times, axis=0))
        print('Analysis got through ', self.frame, ' frames')

    def fitModel(self):
        '''
        '''
        t = time.time()
        ids = None
        try:
            ids = self.q_in.get(timeout=0.0001)
            if ids is not None and ids[0]==1:
                print('analysis: missing frame')
                self.total_times.append(time.time()-t)
                self.q_out.put([1])
                raise Empty
            self.frame = ids[-1]
            (self.coordDict, self.image, self.S) = self.client.getList(ids[:-1])
            self.C = self.S
            self.coords = [o['coordinates'] for o in self.coordDict]
            
            # Compute model fit
            # Just do overall average activity for now
            self.fit()
            
            # Compute coloring of neurons for processed frame
            # Also rotate and stack as needed for plotting
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

    def fit(self):
        pass

    def putAnalysis(self):
        ''' Throw things to DS and put IDs in queue for Visual
        '''
        ids = []
        ids.append(self.client.put(self.Cx, 'Cx'+str(self.frame)))
        ids.append(self.client.put(self.Call, 'Call'+str(self.frame)))
        ids.append(self.client.put(self.Cpop, 'Cpop'+str(self.frame)))
        ids.append(self.client.put(None, 'tune'+str(self.frame)))
        ids.append(self.client.put(self.color, 'color'+str(self.frame)))
        ids.append(self.client.put(self.coordDict, 'analys_coords'+str(self.frame)))
        ids.append(self.frame)

        self.q_out.put(ids)

    def plotColorFrame(self):
        ''' Computes colored nicer background+components frame
        '''
        image = self.image
        color = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        color[...,3] = 255
            # color = self.color.copy() #TODO: don't stack image each time?
        if self.coords is not None:
            for i,c in enumerate(self.coords):
                #c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(color, ind, (255,255,255,50))
        return color

class MeanAnalysis(Actor):
    #TODO: Add additional error handling
    def __init__(self, *args):
        super().__init__(*args)

    def setup(self, param_file=None):
        '''
        '''
        np.seterr(divide='ignore')

        # TODO: same as behaviorAcquisition, need number of stimuli here. Make adaptive later
        self.num_stim = 21 
        self.frame = 0
        # self.curr_stim = 0 #start with zeroth stim unless signaled otherwise
        self.stim = {}
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

        np.savetxt('timing/analysis_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/analysisput_frame_time.txt', np.array(self.puttime))
        np.savetxt('timing/analysiscolor_frame_time.txt', np.array(self.colortime))
        np.savetxt('timing/analysis_timestamp.txt', np.array(self.timestamp))

        np.savetxt('analysis_estsAvg.txt', np.array(self.estsAvg))
        # np.savetxt('analysis_estsOn.txt', np.array(self.estsOn))
        # np.savetxt('analysis_estsOff.txt', np.array(self.estsOff))
        np.savetxt('analysis_proc_S.txt', np.array(self.S))
        # np.savetxt('analysis_spikeAvg.txt', np.array(self.spikeAvg))

    def runAvg(self):
        ''' Take numpy estimates and frame_number
            Create X and Y for plotting
        '''
        t = time.time()
        ids = None
        try: 
            sig = self.links['input_stim_queue'].get(timeout=0.0001)
            self.updateStim(sig)
        except Empty as e:
            pass #no change in input stimulus
        try:
            ids = self.q_in.get(timeout=0.0001)
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
            self.stimAvg()
            
            self.globalAvg = np.mean(self.estsAvg, axis=0)
            self.tune = [self.estsAvg, self.globalAvg]

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

    def putAnalysis(self):
        ''' Throw things to DS and put IDs in queue for Visual
        '''
        t = time.time()
        ids = []
        ids.append(self.client.put(self.Cx, 'Cx'+str(self.frame)))
        ids.append(self.client.put(self.Call, 'Call'+str(self.frame)))
        ids.append(self.client.put(self.Cpop, 'Cpop'+str(self.frame)))
        ids.append(self.client.put(self.tune, 'tune'+str(self.frame)))
        ids.append(self.client.put(self.color, 'color'+str(self.frame)))
        ids.append(self.client.put(self.coordDict, 'analys_coords'+str(self.frame)))
        ids.append(self.frame)

        self.q_out.put(ids)
        self.puttime.append(time.time()-t)

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
        
        polarAvg = np.array(estsAvg)
        # polarAvg[2] = np.sum(estsAvg[[9,11,15],:], axis=0)
        # polarAvg[1] = estsAvg[10, :]
        # polarAvg[0] = np.sum(estsAvg[[3,5,8],:], axis=0)
        # polarAvg[7] = estsAvg[12, :]
        # polarAvg[6] = np.sum(estsAvg[[13,17,18],:], axis=0)
        # polarAvg[5] = estsAvg[14, :]
        # polarAvg[4] = np.sum(estsAvg[[4,6,7],:], axis=0)
        # polarAvg[3] = estsAvg[16, :]
        
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
        if self.estsAvg[ind] is not None and np.sum(np.abs(self.estsAvg[ind]))>2:
            try:
                # trying sort and compare
                rel = self.estsAvg[ind]/np.max(self.estsAvg[ind])
                order = np.argsort(rel)
                if rel[order[-1]] - rel[order[-2]] > 0.2: #ensure strongish tuning
                    r, g, b = self.manual_Color(order[-1])
                    return (r, g, b) + (255,)
                else:
                    # print(order, rel)
                    return (255, 255, 255, 50)
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
            except Exception:
                print('inten is ', inten)
                print('estsAvg[i] is ', self.estsAvg[ind])
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