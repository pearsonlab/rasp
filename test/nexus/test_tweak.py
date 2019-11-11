import os
import yaml
import io
import filecmp

import logging; logger = logging.getLogger(__name__)
from src.nexus.tweak import Tweak 
from src.nexus.tweak import TweakModule
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
import visual.visual
import acquire.acquire
import process.process
import analysis.analysis

class createConfBasic(StoreDependentTestCase):

    def setUp(self):
        super(createConfBasic, self).setUp()
        self.tweak = Tweak()

    def test_actor(self):
        self.tweak.createConfig()
        self.assertEqual(self.tweak.actors['Processor'].packagename, 'process.process')

    def test_GUI(self):
        self.tweak.createConfig()
        self.assertEqual(self.tweak.gui.packagename, 'visual.visual')
        self.assertEqual(self.tweak.gui.classname, 'DisplayVisual')

    def test_connections(self):
        self.tweak.createConfig()
        self.assertEqual(self.tweak.connections['Acquirer.q_out'], ['Processor.q_in', 'Visual.raw_frame_queue'])

    def tearDown(self):
        super(createConfBasic, self).tearDown()


class FailCreateConf(StoreDependentTestCase):

    def setUp(self):
        super(FailCreateConf, self).setUp()
        self.tweak = Tweak()

    def MissingPackageorClass(self):
        cwd = os.getcwd()
        self.tweak.createConfig(configFile= 'test/repeated_actors.yaml')
        self.assertEqual(self.tweak.configFile, cwd+ 'test/MissingPackage.yaml')
        self.assertRaises(KeyError)
        #TODO: create repeated actor error

    def noactors(self):
        cwd = os.getcwd()
        self.tweak.createConfig(configFile= 'test/no_actor.yaml')
        self.assertRaises(KeyError)

    def tearDown(self):
        super(FailCreateConf)


#TODO: create config but with different config files