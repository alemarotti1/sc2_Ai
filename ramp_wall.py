from distutils.command.build import build
from distutils.log import error
import os
import sys
from tabnanny import check


sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import random
from typing import List, Set, Tuple

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

from BuildingCommander import BuildingCommander
from ArmyCommander import ArmyCommander
from Controller import *


class RampWallBot(BotAI):

    def __init__(self):
        self.unit_command_uses_self_do = False
        #self.buildingCommander = BuildingCommander(self)

    game_time = 0
    needed_buildings = []
    needed_army = 0
    build_workers = False
    
    army_commanders : List[ArmyCommander] = []
    
    controller : Controller = None

    async def on_start(self):
        try:
            await self.chat_send("(glhf)")
            #get the enemy race
            er = self.enemy_race
            if er == Race.Zerg:
                self.controller = TVZController(self)
            elif er == Race.Terran:
                self.controller = TVTController(self)
            elif er == Race.Protoss:
                self.controller = TVPController(self)
            else:
                self.controller = RandomController(self)
            
            self.controller.on_start()
        except Exception as e:
            pass

    async def on_unit_created(self, unit: Unit):
        try:
            await self.controller.on_unit_created(unit)
        except Exception as e:
            pass

    
    async def on_building_construction_complete(self, unit: Unit):
        try:
            self.controller.on_building_construction_complete(unit)
        except Exception as e:
            pass
    async def on_step(self, iteration):
        # try:
        #     self.iteration = iteration
        #     self.controller.run(iteration=iteration)
        # except Exception as e:
        #     pass

        try:
            self.iteration = iteration
            await self.controller.run(iteration=iteration)

            if self.units(UnitTypeId.SCV).amount < 50 or 22 * self.units(UnitTypeId.SCV).amount < self.townhalls.amount:
                for townhall in self.townhalls.idle:
                    if self.can_afford(UnitTypeId.SCV):
                        townhall.train(UnitTypeId.SCV)

            # Raise depos when enemies are nearby
            for depo in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
                for unit in self.enemy_units:
                    if unit.distance_to(depo) < 15:
                        break
                else:
                    depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

            # Lower depos when no enemies are nearby
            for depo in self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
                for unit in self.enemy_units:
                    if unit.distance_to(depo) < 10:
                        depo(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                        break
        except Exception as e:
            print(e)
            pass

        # barracks_placement_position: Point2 = self.main_base_ramp.barracks_correct_placement

        # depots: Units = self.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

    



    def get_threats(self):
        try:
            return self.controller.threats
        except:
            return Units([], self)
        
        
        

    async def on_building_construction_started(self, unit: Unit):
        pass
        # print(f"Construction of building {unit} started at {unit.position}.")

    async def on_building_construction_complete(self, unit: Unit):
        pass
        # print(f"Construction of building {unit} completed at {unit.position}.")


    def draw_facing_units(self):
        """ Draws green box on top of selected_unit2, if selected_unit2 is facing selected_unit1 """
        pass


    def get_idle_workers(self):
        """ Returns a list of workers that are not carrying anything """
        try:
            return [unit for unit in self.workers.idle]
        except Exception as e:
            return []

    def add_worker(self, worker: Unit, target: Unit):
        """ Adds a worker to a building """
        try:
            for townhall in self.controller.assigned_workers:
                for mineral_patch in townhall["patches"]["mineral"]:
                    if mineral_patch == target:
                        townhall["workers"].append(worker)
                        return True
                for gas_patch in townhall["patches"]["gas"]:
                    if gas_patch == target:
                        townhall["workers"].append(worker)
                        return True
            return False
        except Exception as e:
            return False
    
    async def remove_worker(self, worker: Unit):
        try:
            await self.controller.remove_worker(worker)
        except Exception as e:
            pass
    def produce_workers(self, townhall: Unit):
        """ Produce a worker if not already producing"""
        try:
            if townhall.is_active:
                return False
            #check if townhall has enough minerals to produce a worker
            if self.minerals > 50:
                townhall.train(UnitTypeId.SCV)
                return True
            return False
        except:
            return False

    def worker_sauration(self):
        try:
            #check if every mining place is saturated
            mining_place = (self.townhalls.ready)|(self.gas_buildings.ready)
            surplus_workers = [place.surplus_harvesters for place in mining_place]

            for i in range(len(surplus_workers)):
                if surplus_workers[i] < 0:
                    done = False
                    idle_workers = self.get_idle_workers()
                    #check if the place has vespene gas
                    if mining_place[i].vespene_contents > 0:
                        if idle_workers:
                            idle_workers[0].gather(mining_place[i])
                            done = True
                    else:
                        #get the close mineral patch
                        local_minerals = [
                            mineral
                            for mineral in self.mineral_field if mineral.distance_to(mining_place[i]) <= 8
                        ]
                        if local_minerals:
                            if idle_workers:
                                idle_workers[0].gather(local_minerals[0])
                                done = True

                    if not done:
                        #get the closest townhall to the place
                        townhall = self.townhalls.closest_to(mining_place[i])
                        if (self.build_workers):
                            self.produce_workers(townhall)
        except Exception as e:
            print(e)
    
    def update_race(self, race:Race):
        controller : RandomController = self.controller
        self.controller = controller.update_race(race)
        print("race changed to ", race)
    
    async def available_army(self) -> Units:
        return await self.controller.available_army()

    async def start_producing_army(self):
        self.controller.start_producing = True
    



def main():
    map = random.choice(
        [
            # Most maps have 2 upper points at the ramp (len(self.main_base_ramp.upper) == 2)
            "AcropolisLE",
            "BlueshiftLE",
            "CeruleanFallLE",
            "KairosJunctionLE",
            "ParaSiteLE",
            "PortAleksanderLE",
            "StasisLE",
            "DarknessSanctuaryLE",
            "ParaSiteLE",  # Has 5 upper points at the main ramp
            "AcolyteLE",  # Has 4 upper points at the ramp to the in-base natural and 2 upper points at the small ramp
            "HonorgroundsLE",  # Has 4 or 9 upper points at the large main base ramp
        ]
    )

    map = "AcropolisLE"
    run_game(
        maps.get(map),
        [
            Bot(Race.Terran, RampWallBot()), 
            Computer(Race.Protoss, difficulty=Difficulty.Hard)
        ],
        realtime=False,
        save_replay_as="replay"
        
        # sc2_version="4.10.1",
    )






















if __name__ == "__main__":
    main()
