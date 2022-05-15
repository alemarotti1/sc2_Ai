from __future__ import annotations
import abc
from distutils.command.build import build
from statistics import mode

from typing import Dict, List, Set, TYPE_CHECKING

import string
from tokenize import group


import random

import numpy as np
from pkg_resources import working_set

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
####
from sc2.ids.effect_id import EffectId #used for finding ground based abilities
###
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units


from BuildingCommander import BuildingCommander


if TYPE_CHECKING:
    from ramp_wall import RampWallBot 

from ArmyCommander import ArmyCommander
from MapControlCommander import MapControlCommander






#create a class that will be the base class for all controllers
class Controller(metaclass=abc.ABCMeta):

    bot : RampWallBot = None
    assigned_workers = []
    worker_pool = Units([], bot)
    worker_necessities = []
    threats : Units = None
    MapControlCommander = MapControlCommander()
    army_commanders : List[ArmyCommander] = []
    start_producing = False
    army_tag = {}
    
    
    @abc.abstractmethod
    def __init__(self, bot : RampWallBot) -> None:
        pass

    @abc.abstractmethod
    async def run(self, iteration):
        pass

    @abc.abstractmethod
    async def on_start(self):
        pass

    @abc.abstractmethod
    async def available_army(self) -> Units:
        pass

    @abc.abstractmethod
    async def used_army(self) -> Units:
        pass

    
    async def assign_workers(self):
        await self.bot.distribute_workers(1)
        for townhall in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND):
            townhalls = self.bot.townhalls
            th = sorted(townhalls, key=lambda x: x.assigned_harvesters)[0]
            if townhall.energy > 50:
                townhall(AbilityId.CALLDOWNMULE_CALLDOWNMULE, self.bot.mineral_field.closest_to(th))
        # if self.bot.build_workers:
        #     self.bot.worker_sauration()
        return
        self.worker_necessities = self.worker_needs()
        #if there are workers that need to be assigned, assign them
        print(self.worker_necessities)
        for necessity in self.worker_necessities:
            if len(self.worker_pool) > 0:
                worker : Unit = self.worker_pool.closest_to(necessity)
                worker.gather(necessity, queue=True)
                self.worker_pool.remove(worker)
                for mineral in self.assigned_workers[0]["patches"]["mineral"]:
                    if mineral["patch"] == necessity:
                        mineral["worker"].append(worker)
            elif self.bot.build_workers:
                th : Unit = self.bot.townhalls.closest_to(necessity)
                if self.bot.supply_left > 0 and self.bot.can_afford(UnitTypeId.SCV) and ((th.build_progress > 0.9 and th.orders==1) or th.noqueue):
                    th.train(UnitTypeId.SCV, queue=True)

    async def worker_needs(self):
        worker_necessities = []
        for townhall in self.assigned_workers:
            for gas in townhall["patches"]["gas"]:
                patch : Unit = gas["patch"]
                if len(gas["worker"]) <= 3:
                    worker_necessities.append(patch)
                if len(gas["worker"]) >3: 
                    worker = gas["worker"][0]
                    if worker.is_carrying_resource:
                        worker.return_resource(townhall["townhall"], queue=True)
                    gas["worker"].remove(worker)
                


            for mineral_patch in townhall["patches"]["mineral"]:
                patch : Unit = mineral_patch["patch"] 
                if len(mineral_patch["worker"]) <= 3:
                    worker_necessities.append(patch)
                if len(mineral_patch["worker"]) >3:
                    worker = mineral_patch["worker"][0]
                    if worker.is_carrying_resource:
                        worker.return_resource(townhall["townhall"], queue=True)
                    mineral_patch["worker"].remove(worker)
        return worker_necessities


    async def gathering_boost(self):
        for townhall in self.assigned_workers:
            for mineral_patch in townhall["patches"]["mineral"]:
                for worker in mineral_patch["worker"]:
                    w : Unit = worker
                    if w.is_carrying_resource and len(w.orders<6):
                        mineral_location = mineral_patch["patch"].position*0.95 + townhall.position*0.05
                        w.move(mineral_location, queue=True)
                        w.gather(mineral_patch["mineral"], queue=True)
                        w.return_resource(townhall, queue=True)

        

    async def gathering_places(self):
        #get all the townhalls
        townhalls = self.bot.townhalls
        return_val = []
        #get the minerals and geysers related to the townhalls
        for townhall in townhalls:
            gases = self.bot.gas_buildings.closer_than(10, townhall)
            minerals = self.bot.mineral_field.closer_than(10, townhall)
            return_val.append({
                    "townhall":townhall, 
                    "patches": {
                        "mineral":[ 
                            {"patch": mineral, "worker": Units([], self.bot)} for mineral in minerals
                        ],
                        
                        "gas":[ 
                            {"patch": gas, "worker": Units([], self.bot)} for gas in gases
                        ]
                    }
                })
        
        
        return return_val

    async def on_unit_created(self, unit:Unit):
        if unit.type_id == UnitTypeId.SCV:
            self.worker_pool.append(unit)
        elif unit.type_id in [UnitTypeId.MARINE, UnitTypeId.REAPER, UnitTypeId.MARAUDER, UnitTypeId.GHOST, UnitTypeId.HELLION, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED, UnitTypeId.THOR, UnitTypeId.CYCLONE, UnitTypeId.WIDOWMINE, UnitTypeId.WIDOWMINEBURROWED, UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT , UnitTypeId.MEDIVAC, UnitTypeId.RAVEN, UnitTypeId.BANSHEE, UnitTypeId.BATTLECRUISER, UnitTypeId.AUTOTURRET, UnitTypeId.LIBERATOR]:
            print(unit.type_id, " created")
            army : Units = await self.available_army()
            army.append(unit)
    
    async def on_building_construction_complete(self, unit:Unit):
        if unit.type_id == UnitTypeId.COMMANDCENTER:
            self.assigned_workers.append({
                "townhall": unit,
                "patches": {
                    "mineral":[
                        {"patch": mineral, "worker": Units([], self.bot)} for mineral
                        in self.bot.mineral_field.closer_than(10, unit)
                    ],
                }
            })
        elif unit.type_id == UnitTypeId.REFINERY:
            closest_townhall = self.bot.townhalls.closest_to(unit)
            for townhall in self.assigned_workers:
                if townhall["townhall"] == closest_townhall:
                    townhall["patches"]["gas"].append({"patch": unit, "worker": Units([], self.bot)})
    
    async def remove_worker(self, worker : Unit):
        for townhall in self.assigned_workers:
            for mineral_patch in townhall["patches"]["mineral"]:
                if worker in mineral_patch["worker"]:
                    mineral_patch["worker"].remove(worker)
                    return
            for gas_patch in townhall["patches"]["gas"]:
                if worker in gas_patch["worker"]:
                    gas_patch["worker"].remove(worker)
                    return

    async def find_threats(self):
        t = Units([], self.bot)
        for base in self.bot.townhalls:
            threats = self.bot.enemy_units.closer_than(30, base)
            if threats.amount > 0:
                t.extend(threats)
                print(f"Threats found at {base.position}")
        self.threats = t
    
    async def refresh_army_tag(self):
        self.army_tag = { unit.tag: unit for unit in self.all_units }
    
    async def produce_army(self):
        for a in self.army_commanders:
            army_commander : ArmyCommander = a
            needed_army = army_commander.unity_necessities
            fill : List[dict] = []
            for unity in needed_army:
                if unity["amount"] is "fill":
                    fill.append(unity)
                    continue 

                if not unity["acquired"]<unity["amount"]:
                    continue
                
                await self.produce_unit(unity)
                
            for unit in fill:
                if self.bot.can_afford(UnitTypeId[unit["unit"]]):
                    u = unit.copy()
                    u["amount"] = u["acquired"]+1
                    await self.produce_unit(u)

    async def produce_unit(self, unity):
        for structure in self.bot.structures(unity["source"]).idle:
            abilities = await self.bot.get_available_abilities(structure)
            for ability in abilities:
                if unity["unit"] not in str(ability):
                    continue
                if self.bot.can_afford(UnitTypeId[unity["unit"]]):
                    structure.train(UnitTypeId[unity["unit"]])

                    if structure.has_reactor and self.bot.can_afford(UnitTypeId[unity["unit"]]) and unity["acquired"]+1<unity["amount"] :
                        structure.train(UnitTypeId[unity["unit"]])

    
        

########################################################################################################################

class TVZController(Controller):
    def __init__(self, bot):
        self.bot = bot
        self.game_started = False
        self.needed_army = 0
        self.build_workers = False
        self.army_commanders = []
        self.controller = None
        self.buildingCommander : BuildingCommander = BuildingCommander(self.bot, self.bot.enemy_race)
        self.midgame_comanders_created = False
        self.army = Units([], self.bot)
        self.assigned_army = Units([], self.bot)


        

    async def run(self, iteration):
        self.refresh_army_tag()
        await self.find_threats()
        await self.buildingCommander.run()
        await self.assign_workers()
        await self.gathering_boost()
        await self.produce_army()
        for army_commander in self.army_commanders:
            await army_commander.run()

        if self.buildingCommander.objective == "midgame" and not self.midgame_comanders_created:
            self.army_commanders.append(ArmyCommander(self.bot, "ScoutHarass", Race.Protoss, mode="harass"))
            self.army_commanders.append(ArmyCommander(self.bot, "MainArmy", Race.Protoss, mode="defend"))
            self.midgame_comanders_created = True

        if self.bot.supply_army>90 and self.army_commanders[2].mode!="attack":
            self.army_commanders[2].mode = "attack"
        

    async def on_start(self):
        #self.army_commanders.append(ArmyCommander(self, "attack", [UnitTypeId.REAPER]))
        self.worker_pool = self.bot.workers
        self.assigned_workers = self.gathering_places()
    
    async def available_army(self) -> Units:
        return self.army
    
    async def used_army(self) -> Units:
        return self.assigned_army
    







########################################################################################################################


class TVPController(Controller):
    def __init__(self, bot):
        self.bot = bot
        self.game_started = False
        self.needed_army = 0
        self.build_workers = False
        self.army_commanders = []
        self.controller = None
        self.buildingCommander : BuildingCommander = BuildingCommander(self.bot, self.bot.enemy_race)
        self.midgame_comanders_created = False
        self.army = Units([], self.bot)
        self.assigned_army = Units([], self.bot)


        

    async def run(self, iteration):
        self.refresh_army_tag()
        await self.find_threats()
        await self.buildingCommander.run()
        await self.assign_workers()
        await self.gathering_boost()
        await self.produce_army()
        for army_commander in self.army_commanders:
            await army_commander.run()

        if self.buildingCommander.objective == "midgame" and not self.midgame_comanders_created:
            self.army_commanders.append(ArmyCommander(self.bot, "AntiAir", Race.Protoss, mode="defend"))
            self.army_commanders.append(ArmyCommander(self.bot, "ScoutHarass", Race.Protoss, mode="harass"))
            self.army_commanders.append(ArmyCommander(self.bot, "MainArmy", Race.Protoss, mode="defend"))
            
            self.midgame_comanders_created = True
        if self.bot.supply_army>90 and self.army_commanders[2].mode!="attack":
            self.army_commanders[2].mode = "attack"

    async def on_start(self):
        #self.army_commanders.append(ArmyCommander(self, "attack", [UnitTypeId.REAPER]))
        self.worker_pool = self.bot.workers
        self.assigned_workers = self.gathering_places()
    
    async def available_army(self) -> Units:
        return self.army
    
    async def used_army(self) -> Units:
        return self.assigned_army
    


########################################################################################################################


class TVTController(Controller):
    def __init__(self, bot):
        self.bot = bot
        self.game_started = False
        self.needed_army = 0
        self.build_workers = False
        self.army_commanders = []
        self.controller = None
        self.buildingCommander : BuildingCommander = BuildingCommander(self.bot, self.bot.enemy_race)
        self.midgame_comanders_created = False
        self.army = Units([], self.bot)
        self.assigned_army = Units([], self.bot)


        

    async def run(self, iteration):
        self.refresh_army_tag()
        await self.find_threats()
        await self.buildingCommander.run()
        await self.assign_workers()
        await self.gathering_boost()
        await self.produce_army()
        for army_commander in self.army_commanders:
            await army_commander.run()

        if self.buildingCommander.objective == "midgame" and not self.midgame_comanders_created:
            self.army_commanders.append(ArmyCommander(self.bot, "AntiAir", Race.Protoss, mode="defend"))
            self.army_commanders.append(ArmyCommander(self.bot, "ScoutHarass", Race.Protoss, mode="harass"))
            self.army_commanders.append(ArmyCommander(self.bot, "MainArmy", Race.Protoss, mode="defend"))
            self.midgame_comanders_created = True
        
        if self.bot.supply_army>90 and self.army_commanders[2].mode!="attack":
            self.army_commanders[2].mode = "attack"


    async def on_start(self):
        self.worker_pool = self.bot.workers
        self.assigned_workers = self.gathering_places()
    
    async def available_army(self) -> Units:
        return self.army
    
    async def used_army(self) -> Units:
        return self.assigned_army
    

########################################################################################################################


class RandomController(Controller):
    def __init__(self, bot):
        self.bot = bot
        self.game_started = False
        self.needed_army = 0
        self.build_workers = False
        self.army_commanders : List(ArmyCommander) = []
        self.buildingCommander : BuildingCommander = BuildingCommander(self.bot, self.bot.enemy_race)
        self.army = Units([], self.bot)
        self.assigned_army = Units([], self.bot)

    async def run(self, iteration):
        self.assign_workers()
        self.gathering_boost()
        self.buildingCommander.run()
        for army_commander in self.army_commanders:
            await army_commander.run()

    async def on_start(self):
        #self.army_commanders.append(ArmyCommander(self, "attack", [UnitTypeId.REAPER]))
        self.worker_pool = self.bot.workers
        self.assigned_workers = self.gathering_places()
    
    async def update_race(self, race:Race) -> Controller:
        temp : Controller = None
        step = self.buildingCommander.step
        if race is Race.Terran:
            temp = TVTController(self.bot)
            temp.buildingCommander = self.buildingCommander
        elif race is Race.Protoss:
            temp = TVPController(self.bot)
            temp.buildingCommander = self.buildingCommander
        elif race is Race.Zerg:
            temp = TVZController(self.bot)
            temp.buildingCommander = self.buildingCommander
        else:
            raise Exception("Erro ao identificar a raça")

        temp.buildingCommander.enemy_race = race
        temp.buildingCommander.step = step
        return temp
    
    async def available_army(self) -> Units:
        return self.army
    
    async def used_army(self) -> Units:
        return self.assigned_army