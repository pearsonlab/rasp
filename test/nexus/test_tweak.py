import os
import yaml
import io

import logging; logger = logging.getLogger(__name__)
from src.nexus.tweak import Tweak 
from src.nexus.tweak import TweakModule
from unittest import TestCase
from test.test_utils import StoreDependentTestCase

class createConf(StoreDependentTestCase):

    def setUp(self):
        super(createConf, self).setUp()
        self.tweak = Tweak()

    def test_conf(self):
        self.tweak.createConfig()
        self.assertEqual(self.tweak.actors['Processor'].packagename, 'process.process')

    def test_GUI(self):
        self.tweak.createConfig()
        self.assertEqual(self.tweak.gui.packagename, 'visual.visual')

    def tearDown(self):
        super(createConf, self).tearDown()

#TODO: create config but with different config files
