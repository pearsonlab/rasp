
from unittest import TestCase
from test.test_utils import StoreDependentTestCase, ActorDependentTestCase
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
class Actor_setStore(ActorDependentTestCase):

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

class Actor_addLink(ActorDependentTestCase):

    def setUp(self):
        super(Actor_addLink, self).setUp()
        self.actor=Actor('test')

    def test_addLink(self):
        links = {'1': 'one', '2': 'two'}
        self.actor.setLinks(links)
        newName= '3'
        newLink= 'three'
        self.actor.addLink(newName, newLink)
        links.update({'3': 'three'})
        self.assertEqual(self.actor.getLinks()['3'], 'three')
        self.assertEqual(self.actor.getLinks(), links)

    def tearDown(self):
        super(Actor_addLink, self).tearDown()

class RunManager_setupRun(ActorDependentTestCase):

    def setUp(self):
        super(RunManager_setupRun, self).setUp()
        self.actor=Actor('test')
        self.isSetUp= False;
        self.runNum=0

    def test_runManager(self):
        q_sig= Queue()
        q_sig.put('setup')
        q_sig.put('run') #runs after this signal
        q_sig.put('pause') 
        q_sig.put('resume') #runs again after this signal
        q_sig.put('quit')
        q_comm= Queue()
        with RunManager('test', self.runMethod, self.run_setup, q_sig, q_comm) as rm:
            print(rm)
        self.assertEqual(self.runNum, 2)
        self.assertTrue(self.isSetUp)

    def tearDown(self):
        super(RunManager_setupRun, self).tearDown()



class Actor_setLinks(ActorDependentTestCase):

    def setUp(self):
        super(Actor_setLinks, self).setUp()
        self.actor = Actor('test')
        self.limbo=Limbo()

    def test_setLinks(self):
        links = {'1': 'one'}
        actor = self.actor
        actor.setLinks(links)
        self.assertEqual(links['1'], actor.getLinks()['1'])
        self.assertEqual(links, actor.getLinks())

    def tearDown(self):
        super(Actor_setLinks, self).tearDown()

class Actor_setLinkOut(ActorDependentTestCase):

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

class Actor_setLinkIn(ActorDependentTestCase):

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

