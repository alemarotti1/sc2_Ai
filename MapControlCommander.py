from __future__ import annotations
from typing import Dict, List, Set, TYPE_CHECKING

import string
from tokenize import group


import random
from matplotlib.style import available

import numpy as np

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from ramp_wall import RampWallBot 




class MapControlCommander:

    def run(self):
        pass
    