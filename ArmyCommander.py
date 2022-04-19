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
        self.assigned_army = Units([], self.ramp_wall_bot)
        
        


    async def run(self):
        await self.get_units()
        print("assigned army: ",self.assigned_army)

    async def get_units(self):
        if self.ramp_wall_bot.iteration % 10 != 0:
            return
        army : Units = await self.ramp_wall_bot.available_army()
        for unit in army:
            id_unit_necessities = [id["unit"] for id in self.unity_necessities]
            
            if unit.type_id.name in id_unit_necessities:
                self.unity_necessities[unit.type_id]["acquired"] += 1
                self.assigned_army.append(unit)
                army.remove(unit)
                
        
    
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
            {"unit" : "SIEGETANK", "amount": 3, "source": UnitTypeId.FACTORY},
            {"unit" : "WIDOWMINE", "amount": 2, "source": UnitTypeId.FACTORY},
            {"unit" : "RAVEN", "amount": 1, "source": UnitTypeId.STARPORT},
            {"unit" : "MARINE", "amount": 15, "source": UnitTypeId.BARRACKS},
            {"unit" : "GHOST", "amount": 5, "source": UnitTypeId.BARRACKS},
            {"unit" : "MEDIVAC", "amount": 2, "source": UnitTypeId.STARPORT},
            {"unit" : "LIBERATOR", "amount": 2, "source": UnitTypeId.STARPORT},
            {"unit" : "BATTLECRUISER", "amount" : 3, "source": UnitTypeId.STARPORT},
            {"unit" : "GHOST", "amount": 5, "source": UnitTypeId.BARRACKS},
            {"unit" : "MARINE", "amount": "fill", "source": UnitTypeId.BARRACKS},


        ],
        "rebuild" : True
    },
    "AntiAir" : {
        "MinSupply": 6,
        "army" : [
            {"unit": "CYCLONE", "amount": 2, "source": UnitTypeId.FACTORY},
            {"unit": "RAVEN", "amount": 1, "source": UnitTypeId.STARPORT},
            {"unit": "VIKINGFIGHTER", "amount": "fill", "source": UnitTypeId.STARPORT},
        ],
        "rebuild" : True
    },
    "ScoutHarass" : {
        "MinSupply": 9,
        "army" : [
            {"unit": "HELLION", "amount": 2, "source": UnitTypeId.FACTORY},
            {"unit": "REAPER", "amount": 3, "source": UnitTypeId.BARRACKS},
        ],
        "rebuild" : False
    },
    "PreventExpansion" : {
        "MinSupply": 4,
        "army" : [
            {"unit": "WIDOWMINE", "amount": 2, "source": UnitTypeId.FACTORY},
        ],
        "rebuild" : False
    },
    "MapControl": {
        "MinSupply": 5,
        "army" : [
            {"unit": "MARINE", "amount": 5, "source": UnitTypeId.BARRACKS},
        ],
        "rebuild" : True
    }
}

