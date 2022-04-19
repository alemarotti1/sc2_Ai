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
from sqlalchemy import true


if TYPE_CHECKING:
    from ramp_wall import RampWallBot 




class ArmyCommander:
    action = {}
    def __init__(self, ramp_wall_bot : RampWallBot, objective : str, enemy_race : Race):
        self.ramp_wall_bot :RampWallBot = ramp_wall_bot
        self.objective : str  = objective
        self.available_supply = Objectives[objective]["MinSupply"]
        self.unity_necessities : List[UnitTypeId] = Objectives[objective]["army"]
        for unit in self.unity_necessities:
            unit["acquired"] = 0
        self.done : bool = False
        self.enemy_race : Race = enemy_race
        
        


    async def run(self):
        #
        # self.action[self.objective]()
        print ("unidades do exercito", await self.ramp_wall_bot.available_army())
        
    
    def group(self, destination: Point2):
        grouped = true
        army = [unit for unit in self.army]
        for unit in range(len(army)-1):
            if army[unit+1].distance_to(army[unit]) > 10:
                army[unit+1].move(army[unit])
                grouped = False
        
        return grouped

    
    def attack(self):
        if not hasattr(self, "moving"):
            self.moving = False
        if not hasattr(self, "grouped"):
            self.grouped = False

        army : Units = Units([], self.ramp_wall_bot)
        forces = self.ramp_wall_bot.units
        temp = self.unity_necessities.copy()
        if not self.done:
            for unit in temp:
                for force in forces:
                    if force.type_id == unit:
                        army.append(force)
                        temp.remove(unit)
            if len(temp) != 0:
                return
            self.army = army
        

        if not self.moving:
            enemy_base = self.ramp_wall_bot.enemy_start_locations[0]
            self.group(self.army.first.position)

            enemy_base = self.ramp_wall_bot.enemy_start_locations[0]
            
            unity_group_location = self.mean_point(self.army)

            destination = enemy_base
            move = Point2((destination.x-unity_group_location.x, destination.y-unity_group_location.y))
            size = np.linalg.norm(move)
            move.x, move.y = move.x*5/size, move.y*5/size

            destination = Point2((unity_group_location.x+move.x, unity_group_location.y+move.y))
            destination1 = Point2((unity_group_location.x*0.8, unity_group_location.y-move.y))



        
        
        for unit in self.army:
            #if there is an enemy worker in range, attack it
            workers = [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
            enemies = self.ramp_wall_bot.enemy_units.filter(lambda unit: unit.can_attack_ground)
            if unit.distance_to(destination) < 10:
                enemies_can_attack: Units = enemies.filter(lambda unit: unit.type_id in workers)
                if len(enemies_can_attack) > 0:
                    unit.attack(enemies_can_attack.closest_to(unit))
            else:
                unit.move(destination)


            
    def mean_point(units: Units):
        point = {"x": 0, "y": 0}
        total = 0
        for unit in units:
            point["x"] += unit.position.x
            point["y"] += unit.position.y
            total += 1
        point["x"] = point["x"]/total
        point["y"] = point["y"]/total
        return Point2((point["x"], point["y"]))











Objectives = {
    "MainArmy" : {
        "MinSupply": 0,
        "army" : [
            {"unit" : "SIEGETANK", "amount": 3},
            {"unit" : "WIDOWMINE", "amount": 2},
            {"unit" : "RAVEN", "amount": 1},
            {"unit" : "MARINE", "amount": 15},
            {"unit" : "GHOST", "amount": 5},
            {"unit" : "MEDIVAC", "amount": 2},
            {"unit" : "LIBERATOR", "amount": 2},
            {"unit" : "BATTLECRUISER", "amount" : 3},
            {"unit" : "GHOST", "amount": 5},
            {"unit" : "MARINE", "amount": "fill"}


        ],
        "rebuild" : True
    },
    "AntiAir" : {
        "MinSupply": 6,
        "army" : [
            {"unit": "CYCLONE", "amount": 2},
            {"unit": "RAVEN", "amount": 1},
            {"unit": "VIKINGFIGHTER", "amount": "fill"}
        ],
        "rebuild" : True
    },
    "ScoutHarass" : {
        "MinSupply": 9,
        "army" : [
            {"unit": "HELLION", "amount": "2"},
            {"unit": "REAPER", "amount": "3"}
        ],
        "rebuild" : False
    },
    "PreventExpansion" : {
        "MinSupply": 4,
        "army" : [
            {"unit": "WIDOWMINE", "amount": "2"}
        ],
        "rebuild" : False
    },
    "MapControl": {
        "MinSupply": 5,
        "army" : [
            {"unit": "MARINE", "amount": "5"}
        ],
        "rebuild" : True
    }
}

