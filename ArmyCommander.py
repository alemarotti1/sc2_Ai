from __future__ import annotations
from typing import Dict, List, Set, TYPE_CHECKING

import string
from tokenize import group


import random
from matplotlib import units
from matplotlib.style import available

import numpy as np

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
import time


if TYPE_CHECKING:
    from ramp_wall import RampWallBot 




class ArmyCommander:
    action = {}
    def __init__(self, ramp_wall_bot : RampWallBot, objective : str, enemy_race : Race, mode : str):
        self.ramp_wall_bot :RampWallBot = ramp_wall_bot
        self.objective : str  = objective
        self.available_supply = Objectives[objective]["MinSupply"]
        self.unity_necessities : List[UnitTypeId] = Objectives[objective]["army"]
        for unit in self.unity_necessities:
            unit["acquired"] = 0
        self.done : bool = False
        self.enemy_race : Race = enemy_race
        self.assigned_army = Units([], self.ramp_wall_bot)
        self.assigned_army_tags = set()
        self.mode = mode
        self.targets = None
        self.phase = None
        
    async def update_army(self):
        # self.assigned_army = Units([], self.ramp_wall_bot)
        # for unit_tag in self.assigned_army_tags.copy():
        #     unit = self.ramp_wall_bot.units.find_by_tag(unit_tag)
        #     if unit:
        #         self.assigned_army.append(unit)
        #     else:
        #         self.assigned_army_tags.remove(unit_tag)
        
        # print("getting army")
        # print (self.assigned_army)
        
        # for unit_necessity in self.unity_necessities:
        #     unit_necessity["acquired"] = self.assigned_army.of_type(UnitTypeId[unit_necessity["unit"]]).amount
        self.assigned_army = Units([], self.ramp_wall_bot)
        for unit_tag in self.assigned_army_tags.copy():
            unit = self.ramp_wall_bot.units.find_by_tag(unit_tag)
            if unit:
                self.assigned_army.append(unit)
            else:
                self.assigned_army_tags.remove(unit_tag)
   


    async def run(self):
        if self.targets is None:
            bases = self.ramp_wall_bot.expansion_locations_list
            self.targets = sorted(bases, key=lambda x: x.distance_to(self.ramp_wall_bot.start_location), reverse=True)
        
        
        if self.ramp_wall_bot.iteration % 10 != 0:    
            await self.get_units()
            await self.update_army()
        await self.act()

    async def get_units(self):
        if self.objective!="MainArmy":
            return
        army = await self.ramp_wall_bot.available_army()
        
        self.assigned_army_tags = set([unit.tag for unit in army])



        
    
    def group(self, units : Units, destination: Point2):
        grouped = True
        for unit in units:
            if unit.distance_to(destination) > 10:
                unit.move(destination, queue=True)
                grouped = False
        
        return grouped

    
    async def attack(self):
        bases = self.ramp_wall_bot.expansion_locations_list
        bases = sorted(bases, key=lambda x: x.distance_to(self.ramp_wall_bot.start_location), reverse=True)
        for base in bases:
            for unit in self.assigned_army:
                unit.attack(base, queue=True)
        


    async def defend(self):
        threats = self.ramp_wall_bot.enemy_units
        if not threats:
            if not self.ramp_wall_bot.townhalls:
                return
            closest_th : Point2 = self.ramp_wall_bot.townhalls.closest_to(self.ramp_wall_bot.enemy_start_locations[0]).position
            for unit in self.assigned_army:
                if unit.type_id not in [UnitTypeId.WIDOWMINE, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED, UnitTypeId.LIBERATOR]:
                    unit.attack(closest_th.towards(self.targets[0], 13))
                else:
                    
                    if unit.type_id == UnitTypeId.WIDOWMINE:
                        unit.move(closest_th.towards_with_random_angle(self.ramp_wall_bot.enemy_start_locations[0], 20))
                        unit(AbilityId.BURROWDOWN_WIDOWMINE, queue=True)
                        return

                    unit.attack(closest_th.towards(self.targets[0], 8))
                    if unit.type_id == UnitTypeId.SIEGETANK:
                        unit(AbilityId.SIEGEMODE_SIEGEMODE, queue=True)
                    if unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                        unit.hold_position(queue=True)
                    if unit.type_id == UnitTypeId.LIBERATOR:
                        print(await self.ramp_wall_bot.get_available_abilities(unit))
                        unit(AbilityId.LIBERATORMORPHTOAG_LIBERATORAGMODE, queue=True)
        else:
            for unit in self.assigned_army:
                pos = self.ramp_wall_bot.enemy_units.closest_to(unit).position
                if unit.type_id not in [UnitTypeId.WIDOWMINE, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED, UnitTypeId.LIBERATOR, UnitTypeId.RAVEN]:
                    unit.attack(pos.towards(unit.position, max(unit.ground_range, unit.air_range)+0.5))
                else:
                    if unit.type_id == UnitTypeId.SIEGETANK:
                        unit.move(pos.towards(unit.position,13))
                        unit(AbilityId.SIEGEMODE_SIEGEMODE, queue=True)
                    if unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                        unit.hold_position(queue=True)
                    if unit.type_id == UnitTypeId.LIBERATOR:
                        print(await self.ramp_wall_bot.get_available_abilities(unit))
                        unit(AbilityId.LIBERATORMORPHTOAG_LIBERATORAGMODE, queue=True)
                    if unit.type_id == UnitTypeId.RAVEN:
                        for threat in threats:
                            self.goalIt = self.ramp_wall_bot.iteration + 300
                            if(self.ramp_wall_bot.iteration >= self.goalIt and not(threat.has_buff(BuffId.RAVENSHREDDERMISSILEARMORREDUCTION))):
                                point = {"x": 0, "y": 0}
                                point["x"] += threat.position.x
                                point["y"] += threat.position.y
                                available_abilities = await self.ramp_wall_bot.get_available_abilities(unit)
                                if AbilityId.EFFECT_ANTIARMORMISSILE in available_abilities:
                                    unit.move(pos.towards(Point2((point["x"], point["y"])),10))
                                    unit(AbilityId.EFFECT_ANTIARMORMISSILE, queue=True)
                        
    
    async def harass(self):
        if not self.phase:
            self.phase = "defend"
        
        hellions = self.assigned_army.of_type(UnitTypeId.HELLION)
        reapers = self.assigned_army.of_type(UnitTypeId.REAPER)
        if self.phase=="defend" and (hellions.amount == 2 and reapers.amount == 3):
            self.phase = "move"
            
        pos1 = self.targets[1].towards(self.ramp_wall_bot.start_location, 30)
        pos2 = self.targets[5].towards(self.ramp_wall_bot.start_location, 5)


        if self.phase == "move":
            if self.group(hellions, pos1) and self.group(reapers,pos2):
                self.phase = "harass"
        
        if self.phase == "harass":
            if self.ramp_wall_bot.enemy_units.amount < 0:
                for hellion in hellions:
                    hellion.move(self.targets[1])
                for reaper in reapers:
                    reaper.move(self.targets[0])
            else:
                for hellion in hellions:
                    enemy_units = self.ramp_wall_bot.enemy_units
                    enemy_structures = self.ramp_wall_bot.enemy_structures
                    #enemy units - enemy structures
                    enemy_units_minus_structures = enemy_units - enemy_structures
                    print(enemy_units_minus_structures)
                    hellion.move(self.targets[1])
                for reaper in reapers:
                    reaper.move(self.targets[0])
        
        
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
    
    async def act(self):
        if self.mode == "attack":
            await self.attack()
        elif self.mode == "defend":
            await self.defend()
        elif self.mode == "harass":
            await self.harass()







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
            {"unit" : "MARINE", "amount": "fill", "source": UnitTypeId.BARRACKS}
        ],
        "rebuild" : True
    },
    "AntiAir" : {
        "MinSupply": 8,
        "army" : [
            {"unit": "CYCLONE", "amount": 2, "source": UnitTypeId.FACTORY},
            {"unit": "RAVEN", "amount": 1, "source": UnitTypeId.STARPORT},
            {"unit": "VIKINGFIGHTER", "amount": "fill", "source": UnitTypeId.STARPORT}
        ],
        "rebuild" : True
    },
    "ScoutHarass" : {
        "MinSupply": 9,
        "army" : [
            
            {"unit": "REAPER", "amount": 3, "source": UnitTypeId.BARRACKS},
            {"unit": "HELLION", "amount": 2, "source": UnitTypeId.FACTORY}
        ],
        "rebuild" : False
    },
    "PreventExpansion" : {
        "MinSupply": 4,
        "army" : [
            {"unit": "WIDOWMINE", "amount": 2, "source": UnitTypeId.FACTORY}
        ],
        "rebuild" : False
    },
    "MapControl": {
        "MinSupply": 5,
        "army" : [
            {"unit": "MARINE", "amount": 5, "source": UnitTypeId.BARRACKS}
        ],
        "rebuild" : True
    }
}

