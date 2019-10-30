
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.actor import Actor, RunManager, AsyncRunManager, Spike
from src.nexus.store import Limbo
from multiprocessing import Process
import numpy as np
from pyarrow.lib import ArrowIOError
import pickle
import pyarrow.plasma as plasma
import asyncio
from queue import Empty
import time
from typing import Awaitable, Callable
import traceback
from nexus.store import ObjectNotFoundError
import pickle
from queue import Queue


#TODO: write actor unittests

#setStore
class Actor_setStore(StoreDependentTestCase):

    def setUp(self):
        super(Actor_setStore, self).setUp()
        self.actor = Actor('test')
        self.limbo = Limbo()

    def test_setStore(self):
        limbo = self.limbo
        actor = self.actor
        actor.setStore(limbo.client)
        self.assertEqual(actor.client, limbo.client)

    def tearDown(self):
        super(Actor_setStore, self).tearDown()

class RunManager_setup(StoreDependentTestCase):

    def setUp(self):
        super(RunManager_setup, self).setUp()
        self.actor=Actor('test')
        self.isSetUp= False;

    def run_setup(self):
        self.isSetUp= True

    def runMethod(self):
        self.assertTrue(self.isSetUp)

    def test_runManager(self):
        q_sig= Queue()
        q_sig.put('setup')
        q_sig.put('run')
        q_sig.put('quit')
        q_comm= Queue()
        self.RunManager= RunManager('test', self.runMethod, self.run_setup, q_sig, q_comm)



# Nicole :
## setLinks and getLinks
class Actor_setLinks(StoreDependentTestCase):

    def setUp(self):
        super(Actor_setLinks, self).setUp()
        self.actor = Actor('test')

    def test_setLinks(self):
        links = {'1': 'one'}
        actor = self.actor
        actor.setLinks(limbo.client)
        self.assertEqual(links['1'], actor.getLinks()['1'])
        self.assertEqual(links, actor.getLinks())

    def tearDown(self):
        super(Actor_setLinks, self).tearDown()

# setLinkOut and getLinks
class Actor_setLinkOut(StoreDependentTestCase):

    def setUp(self):
        super(Actor_setLinkOut, self).setUp()
        self.actor = Actor('test')

    def test_setLinkOut(self):
        actor = self.actor
        q = ['one', 'two', 'three']
        actor.setLinkOut(q)
        self.assertEqual(q, actor.getLinks()['q_out'])


    def tearDown(self):
        super(Actor_setLinkOut, self).tearDown()

# setLinkIn and getLinks
class Actor_setLinkIn(StoreDependentTestCase):

    def setUp(self):
        super(Actor_setLinkIn, self).setUp()
        self.actor = Actor('test')

    def test_setLinkIn(self):
        actor = self.actor
        q = ['one', 'two', 'three']
        actor.setLinkIn(q)
        self.assertEqual(q, actor.getLinks()['q_in'])

    def tearDown(self):
        super(Actor_setLinkIn, self).tearDown()

# Daniel :
## addLink

## getLinks

## setUp

## run



#changePriority -> not unit testable?


# Run manager
