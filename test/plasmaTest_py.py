import multiprocessing as mp 
import subprocess


def startStore():
    subprocess.Popen(['plasma_store', '-s', '/tmp/store','-m', str(1000000000)])


if __name__ == '__main__':
    p1 = mp.Process(target=startStore)
    p1.start()
    p1.join()