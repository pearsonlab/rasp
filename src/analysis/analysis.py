from nexus.module import Module, Spike, RunManager
from nexus.store import ObjectNotFoundError
from queue import Empty
from scipy.sparse import csc_matrix
from skimage.measure import find_contours
import numpy as np
import time
import cv2
import colorsys

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Analysis(Module):
    '''Abstract class for the analysis module
    Performs additional computations on the extracted
    neural activity from the processor module
    '''
    #def putAnalysis(self):
    #    # Update the DS with analysis
    #    raise NotImplementedError


class MeanAnalysis(Analysis):
    def __init__(self, *args):
        super().__init__(*args)

    def setup(self, param_file=None):
        '''
        '''
        # TODO: same as behaviorAcquisition, need number of stimuli here. TODO: make adaptive later
        self.num_stim = 21 
        self.frame = 0
        self.flag = False
        self.curr_stim = 0 #start with zeroth stim unless signaled otherwise
        self.stimInd = []
        self.stim = {}
        self.onoff = []
        self.window = 200 #TODO: make user input, choose scrolling window for Visual
        self.A = None
        self.C = None
        self.Call = None
        self.Cx = None
        self.Cpop = None
        self.coords = None
        self.updateCoordsTime = []
        self.color = None

    def run(self):
        self.total_times = []
        self.puttime = []
        self.colortime = []
        self.stimtime = []
        self.timestamp = []

        np.seterr(divide='raise')

        with RunManager(self.name, self.runAvg, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)
        
        print('Analysis broke, avg time per frame: ', np.mean(self.total_times))
        print('Analysis broke, avg time per put analysis: ', np.mean(self.puttime))
        print('Analysis broke, avg time per color frame: ', np.mean(self.colortime))
        print('Analysis broke, avg time per stim avg: ', np.mean(self.stimtime))
        print('Analysis got through ', self.frame, ' frames')

        np.savetxt('timing/analysis_frame_time.txt', np.array(self.total_times))
        np.savetxt('timing/analysis_timestamp.txt', np.array(self.timestamp))
        np.savetxt('analysis_estsAvg.txt', np.array(self.estsAvg))
        np.savetxt('analysis_estsOn.txt', np.array(self.estsOn))
        np.savetxt('analysis_estsOff.txt', np.array(self.estsOff))
        np.savetxt('analysis_proc_C.txt', np.array(self.C))
        np.savetxt('analysis_spikeAvg.txt', np.array(self.spikeAvg))


    def runAvg(self):
        ''' Take numpy estimates and frame_number
            Create X and Y for plotting
        '''
        t = time.time()
        try: 
            sig = self.links['input_stim_queue'].get(timeout=0.0001)
            self.updateStim(sig)
        except Empty as e:
            pass #no change in input stimulus
            #TODO: other errors
        try:
            #TODO: add error handling for if we received some but not all of these
            ids = self.q_in.get(timeout=0.0001)
            (self.C, self.coordDict, self.image, self.S) = self.client.getList(ids) #res

            self.coords = [o['coordinates'] for o in self.coordDict]

            # Keep internal running count 
            # self.frame += 1 #DANGER
            self.frame = self.C.shape[1]
            # From the input_stim_queue update the current stimulus (once per frame)
            #DANGER FIXME TODO Use a timestamp here
            
            # Compute tuning curves based on input stimulus
            # Just do overall average activity for now
            self.stimAvg()
            
            self.globalAvg = np.mean(self.estsAvg, axis=0)
            self.tune = [self.estsAvg, self.globalAvg]

            # Compute coloring of neurons for processed frame
            # Also rotate and stack as needed for plotting
            if self.frame % 2 == 0: #TODO: move to viz, but we don't need to compute this 30 times/sec
                self.color = self.plotColorFrame()

            if self.frame >= self.window:
                window = self.window
            else:
                window = self.frame

            if self.C.shape[1]>0:
                self.Cpop = np.nanmean(self.C[:,self.frame-window:self.frame], axis=0)
                self.Cx = np.arange(0,self.Cpop.size)+(self.frame-window)
                self.Call = self.C[:,self.frame-window:self.frame]
            
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
        # if(self.curr_stim != stim[0][0]):
        #     logger.info('Changed stimulus: '+str(whichStim))
        # self.curr_stim = stim[0][0]
        # self.onoff_stim = (1 if abs(stim[0][1]) > 1 else 0)

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

        self.q_out.put(ids)
        #print('time put analysis: ', time.time()-t)
        self.puttime.append(time.time()-t)
        #self.q_comm.put([self.frame])

    def stimAvg(self):
        ests = self.C
        S = self.S
        t = time.time()
        estsAvg = [np.zeros(ests.shape[0])]*self.num_stim
        spikeAvg = [np.zeros(ests.shape[0])]*self.num_stim
        estsStd = [np.zeros(ests.shape[0])]*self.num_stim
        onStim = [np.zeros(ests.shape[0])]*self.num_stim
        offStim = [np.zeros(ests.shape[0])]*self.num_stim
        for s,l in self.stim.items():
            if 'on' in l.keys() and 'off' in l.keys():
                onInd = np.array(l['on'])
                offInd = np.array(l['off'])
                try:
                    on = np.mean(ests[:,onInd], axis=1)
                    spikeOn = np.mean(S[:,onInd], axis=1)
                    onS = np.std(ests[:,onInd], axis=1)
                    off = np.mean(ests[:,offInd], axis=1)
                    spikeOff = np.mean(S[:,offInd], axis=1)
                    offS = np.std(ests[:,offInd], axis=1)
                    tmp = (on / off) - 1
                    tmpS = np.sqrt(np.square(onS)+np.square(offS))
                    estsAvg[int(s)] = tmp
                    estsStd[int(s)] = tmpS
                    onStim[int(s)] = on
                    offStim[int(s)] = off
                    try:
                        spikeAvg[int(s)] = spikeOn/spikeOff - 1
                    except FloatingPointError:
                        spikeAvg[int(s)] = spikeOn
                except IndexError:
                    pass
            else:
                estsAvg[int(s)] = np.zeros(ests.shape[0])
                estsStd[int(s)] = np.zeros(ests.shape[0])
                onStim[int(s)] = np.zeros(ests.shape[0])
                offStim[int(s)] = np.zeros(ests.shape[0])
                spikeAvg[int(s)] = np.zeros(ests.shape[0])
        self.estsAvg = np.transpose(np.array(estsAvg))
        self.estsStd = np.transpose(np.array(estsStd))
        self.estsOn = np.transpose(np.array(onStim))
        self.estsOff = np.transpose(np.array(offStim))
        self.spikeAvg = np.transpose(np.array(spikeAvg))
        self.estsAvg = np.where(np.isnan(self.estsAvg), 0, self.estsAvg)
        self.stimtime.append(time.time()-t)

    def plotColorFrame(self):
        ''' Computes colored nicer background+components frame
        '''
        t = time.time()
        image = self.image
        color = np.stack([image, image, image, image], axis=-1).astype(np.uint8).copy()
        color[...,3] = 255
        if self.coords is not None:
            for i,c in enumerate(self.coords):
                #c = np.array(c)
                ind = c[~np.isnan(c).any(axis=1)].astype(int)
                cv2.fillConvexPoly(color, ind, self._tuningColor(i, color[ind[:,1], ind[:,0]]))

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
        if self.estsAvg[ind] is not None:
            try:
                h = np.nanargmax(self.estsAvg[ind])*36/360
                intensity = 1- np.mean(inten[0][0])/255.0
                r, g, b, = colorsys.hls_to_rgb(h, intensity, 0.8)
                r, g, b = [x*255.0 for x in (r, g, b)]
                return (r, g, b)+ (intensity*150,)
            except ValueError:
                return (255,255,255,0)
        else:
            return (255,255,255,0)