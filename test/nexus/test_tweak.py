import os
import yaml
import io
import filecmp

import logging; logger = logging.getLogger(__name__)
from src.nexus.tweak import Tweak 
from src.nexus.tweak import TweakModule
from unittest import TestCase
from test.test_utils import StoreDependentTestCase

class createConf(StoreDependentTestCase):

    def setUp(self):
        super(createConf, self).setUp()
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
        super(createConf, self).tearDown()

#TODO: create config but with different config files