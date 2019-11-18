import os
import yaml
import io
import filecmp

import logging; logger = logging.getLogger(__name__)
from src.nexus.tweak import Tweak 
from src.nexus.tweak import TweakModule
from unittest import TestCase
from test.test_utils import StoreDependentTestCase
from src.nexus.tweak import RepeatedActorError
import visual.visual
import acquire.acquire
import process.process
import analysis.analysis
from inspect import signature

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
        self.tweak.createConfig(configFile= 'test/config/repeated_actors.yaml')
        self.assertEqual(self.tweak.configFile, cwd+ 'test/config/MissingPackage.yaml')
        self.assertRaises(KeyError)
        #TODO: create repeated actor error

    def noactors(self):
        cwd = os.getcwd()
        self.tweak.createConfig(configFile= 'test/config/no_actor.yaml')
        self.assertRaises(AttributeError)

    def repeatedActor(self):
        cwd  = os.getcwd()
        self.tweak.createConfig(configFile= 'test/config/repeated_actors')
        self.assertRaises(RepeatedActorError)

    def tearDown(self):
        super(FailCreateConf)


class testPackageClass(StoreDependentTestCase):

    def setUp(self):
        super(testPackageClass, self).setUp()
        self.tweak = Tweak()

    def badpackage(self):
        cwd = os.getcwd()
        self.tweak.createConfig(configFile= 'test/config/bad_package.yaml')
        self.assertRaises(ModuleNotFoundError)

    def badclass(self):
        cwd = os.getcwd()
        self.tweak.createConfig(configFile= 'test/config/bad_class.yaml')
        self.assertRaises(ImportError)

    def tearDown(self):
        super(testPackageClass)

class testArgs(StoreDependentTestCase):

    def setUp(self):
        super(testArgs, self).setUp()
        self.tweak= Tweak()

    

    def tearDown(self):
        super(testArgs)

#TODO: create config but with different config files