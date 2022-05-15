from __future__ import annotations
from distutils.command.build import build
from msilib.schema import Upgrade
from typing import List, Set, TYPE_CHECKING

import string
from tokenize import group


import random

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
from sqlalchemy import false, true


if TYPE_CHECKING:
    from ramp_wall import RampWallBot
    from ArmyCommander import ArmyCommander


class BuildingCommander:
    action = {}
    def __init__(self, ramp_wall_bot : RampWallBot, enemy_race : Race):
        self.ramp_wall_bot :RampWallBot = ramp_wall_bot
        self.objective : str  = "opening"
        self.done : bool = False
        self.step = 0
        self.enemy_race : Race = enemy_race
        self.expanded_times = 1

        self.action["opening"] = self.opening
        self.action["midgame"] = self.midgame

    async def run(self):
        await self.action[self.objective]()

        if(self.ramp_wall_bot.supply_workers>66):
            self.ramp_wall_bot.build_workers = False

    async def opening(self):
        if self.step == 0:
            #get the main base
            bases = self.ramp_wall_bot.townhalls
            if bases:
                base = bases.first
                self.step += 1
                bases = self.ramp_wall_bot.townhalls
                base.train(UnitTypeId.SCV, queue=True)
                return

        depot_placement_positions: Set[Point2] = self.ramp_wall_bot.main_base_ramp.corner_depots
        depots: Units = self.ramp_wall_bot.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})
        # Filter locations close to finished supply depots
        if depots:
            depot_placement_positions: Set[Point2] = { d for d in depot_placement_positions if depots.closest_distance_to(d) > 1 }

        if self.step == 1 and self.ramp_wall_bot.iteration>20:
            depots_copy = depot_placement_positions.copy()
            depot = depots_copy.pop()
            #get all workers not carrying minerals
            builders = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals)
            self.builder = builders.closest_to(depot)
            self.builder.move(depot)
            if self.ramp_wall_bot.can_afford(UnitTypeId.SUPPLYDEPOT):
                self.builder.build(UnitTypeId.SUPPLYDEPOT, depot)
                self.step += 1
                self.ramp_wall_bot.build_workers = True


                if self.enemy_race not in [Race.Terran, Race.Protoss, Race.Zerg]:
                    workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals and not unit.is_constructing_scv)
                    worker = random.choice(workers)
                    point1, point2 = self.scout_pos()
                    worker.move(point1)
                    worker.move(point2, queue=True)
                    mineral : Unit = self.ramp_wall_bot.mineral_field.closest_to(self.ramp_wall_bot.townhalls.first)
                    worker.gather(mineral, queue=True)
                    self.scout = True
            return
        
        if self.step == 2:
            if self.enemy_race not in [Race.Terran, Race.Protoss, Race.Zerg]:
                pass
            barracks_placement_position: Point2 = self.ramp_wall_bot.main_base_ramp.barracks_correct_placement
            if self.ramp_wall_bot.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED }).ready:
                if self.ramp_wall_bot.can_afford(UnitTypeId.BARRACKS):
                    self.builder.build(UnitTypeId.BARRACKS, barracks_placement_position)
                    self.step += 1
                return
        
        if self.step == 3:
            #take gas
            if self.ramp_wall_bot.can_afford(UnitTypeId.REFINERY):
                #get the closest gas to the base
                target_gas: Unit = self.ramp_wall_bot.vespene_geyser.closest_to(self.ramp_wall_bot.townhalls.first)
                #get the closest worker to the gas
                builders = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals)
                worker = builders.closest_to(target_gas)
                #build a refinery
                if worker:
                    worker.build(UnitTypeId.REFINERY, target_gas)
                    self.step += 1
                return
        
        if self.step == 4:
            #when scout spotted the enemy base and the variable scout exists
            if self.ramp_wall_bot.enemy_units.exists and hasattr(self, "scout"):
                self.ramp_wall_bot.update_race(self.ramp_wall_bot.enemy_units.first.race)
                delattr(self, "scout")

            #saturate gas
            if self.ramp_wall_bot.structures(UnitTypeId.REFINERY).ready:
                refinery = self.ramp_wall_bot.structures(UnitTypeId.REFINERY).ready.first
                if refinery:
                    needed_workers = max(refinery.surplus_harvesters*(-1), 0)
                    workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals and not unit.is_constructing_scv).closest_n_units(refinery, needed_workers-1)
                    for worker in workers:
                        worker.gather(self.ramp_wall_bot.structures(UnitTypeId.REFINERY).first)
                        await self.ramp_wall_bot.remove_worker(worker)
                        self.ramp_wall_bot.add_worker(worker, refinery)
                    self.step += 1
                return
        
        if self.step == 5:
            depots_copy = depot_placement_positions.copy()
            depot = depots_copy.pop()
            #get all workers not carrying minerals
            builders = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals)
            self.builder = builders.closest_to(depot)
            self.builder.move(depot)
            if self.ramp_wall_bot.can_afford(UnitTypeId.SUPPLYDEPOT):
                self.builder.build(UnitTypeId.SUPPLYDEPOT, depot)

                sorted_expansion_points = sorted(self.ramp_wall_bot.expansion_locations_list, key=lambda p: p.distance_to(self.ramp_wall_bot.townhalls.first))
                closest_expansion_point = sorted_expansion_points[1]

                self.builder.move(closest_expansion_point, queue=True)
                self.step += 1
            elif len(depots_copy)>0:
                self.step +=1
            return
        
        if self.step == 6:
            self.step = 0
            self.objective = "midgame"
            print("trying to move on")
            return
        
    async def midgame(self):
        if self.enemy_race is Race.Terran:
            await self.midgame_terran()
        elif self.enemy_race is Race.Protoss:
            await self.midgame_protoss()
        elif self.enemy_race is Race.Zerg:
            await self.midgame_zerg()
        else:
            raise Exception("error at identifying enemy race")
         
    


    async def midgame_terran(self):

        if self.step == 0:
            if self.ramp_wall_bot.can_afford(UnitTypeId.COMMANDCENTER):
                expansion_points : List[Point2] = self.ramp_wall_bot.expansion_locations_list
                sorted_expansion_points = sorted(expansion_points, key=lambda p: p.distance_to(self.ramp_wall_bot.townhalls[-1]))
                closest_expansion_point = sorted_expansion_points[self.expanded_times]

                self.builder.build(UnitTypeId.COMMANDCENTER, closest_expansion_point, queue=True)
                self.expanded_times += 1
                self.step += 1

        if self.step >= 1:
            end = True

            if len(self.ramp_wall_bot.structures(UnitTypeId.FACTORY)) < 1:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.FACTORY):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.structures(UnitTypeId.BARRACKS).first.position, 20, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.FACTORY, position)

            if len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)) > 0 and \
               len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKSTECHLAB)) == 0 and \
               len(self.ramp_wall_bot.structures(UnitTypeId.FACTORY)) > 0:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.TECHLAB):
                    self.ramp_wall_bot.structures(UnitTypeId.BARRACKS).first(AbilityId.BUILD_TECHLAB_BARRACKS)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)) > 0 and \
               len(self.ramp_wall_bot.structures(UnitTypeId.STARPORT)) < 1:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.STARPORT):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.structures(UnitTypeId.BARRACKS).first.position, 20, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.STARPORT, position)

            if len(self.ramp_wall_bot.structures(UnitTypeId.FACTORY)) > 0 and \
               len(self.ramp_wall_bot.structures(UnitTypeId.FACTORYTECHLAB)) == 0:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.TECHLAB):
                    self.ramp_wall_bot.structures(UnitTypeId.FACTORY).first(AbilityId.BUILD_TECHLAB_FACTORY)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKSTECHLAB)) > 0:
                if self.ramp_wall_bot.minerals > 200 and self.ramp_wall_bot.vespene > 200:
                    self.ramp_wall_bot.structures(UnitTypeId.BARRACKSTECHLAB).first(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK)
                else:
                    end = False

            if end and self.step == 1:
                self.step += 1
        
        if self.step >= 2:

            end = True

            if len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)) == 1:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.BARRACKS):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.structures(UnitTypeId.BARRACKS).first.position, 20, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.BARRACKS, position)

            if len(self.ramp_wall_bot.structures(UnitTypeId.FACTORY)) == 1:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.FACTORY):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.structures(UnitTypeId.FACTORY).first.position, 15, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.FACTORY, position)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.STARPORT)) == 1:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.STARPORT):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.structures(UnitTypeId.STARPORT).first.position, 15, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.STARPORT, position)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)) == 2 and \
               not self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)[1].has_add_on:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.REACTOR):
                    self.ramp_wall_bot.structures(UnitTypeId.BARRACKS)[1](AbilityId.BUILD_REACTOR_BARRACKS)

            if len(self.ramp_wall_bot.structures(UnitTypeId.FACTORY)) == 2 and \
               not self.ramp_wall_bot.structures(UnitTypeId.FACTORY)[1].has_add_on:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.REACTOR):
                    self.ramp_wall_bot.structures(UnitTypeId.FACTORY)[1](AbilityId.BUILD_REACTOR_FACTORY)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.STARPORT)) == 2 and \
               len(self.ramp_wall_bot.structures(UnitTypeId.STARPORTTECHLAB)) == 0:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.TECHLAB):
                    self.ramp_wall_bot.structures(UnitTypeId.STARPORT).first(AbilityId.BUILD_TECHLAB_STARPORT)
            
            if len(self.ramp_wall_bot.structures(UnitTypeId.STARPORT)) == 2 and \
               not self.ramp_wall_bot.structures(UnitTypeId.STARPORT)[1].has_add_on:
                end = False
                if self.ramp_wall_bot.can_afford(UnitTypeId.REACTOR):
                    self.ramp_wall_bot.structures(UnitTypeId.STARPORT)[1](AbilityId.BUILD_REACTOR_STARPORT)

            if end and self.step == 2:
                self.step += 1

        if self.step >= 3:

            mineralFields = 0
            expansion_points : List[Point2] = self.ramp_wall_bot.expansion_locations_list
            sorted_expansion_points = sorted(expansion_points, key=lambda p: p.distance_to(self.ramp_wall_bot.townhalls.first))
            for position in sorted_expansion_points[:self.expanded_times]:
                mineralFields += len(self.ramp_wall_bot.mineral_field.closer_than(10, position))

            if 2 * mineralFields < self.ramp_wall_bot.units(UnitTypeId.SCV).amount - 10:
                if self.ramp_wall_bot.can_afford(UnitTypeId.COMMANDCENTER):
                    closest_expansion_point = sorted_expansion_points[self.expanded_times]
                    builders = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals and not unit.is_constructing_scv)

                    self.builder = builders.closest_to(closest_expansion_point)

                    if self.builder and self.ramp_wall_bot.enemy_units.closer_than(10, closest_expansion_point).amount == 0:
                        self.builder.build(UnitTypeId.COMMANDCENTER, closest_expansion_point)
                        self.expanded_times += 1

                        if self.step == 3:
                            self.step += 1
        
        if self.step >= 4:
            if self.ramp_wall_bot.structures(UnitTypeId.ARMORY).amount == 0:
                if self.ramp_wall_bot.can_afford(UnitTypeId.ARMORY):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.townhalls.first.position, 15, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.ARMORY, position)
            
            if self.ramp_wall_bot.structures(UnitTypeId.ENGINEERINGBAY).amount == 0:
                if self.ramp_wall_bot.can_afford(UnitTypeId.ENGINEERINGBAY):
                    position : Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.COMMANDCENTER, self.ramp_wall_bot.townhalls.first.position, 15, placement_step=3)
                    if position:
                        workers = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
                        worker = workers.closest_to(position)
                        if worker:
                            worker.build(UnitTypeId.ENGINEERINGBAY, position)

            AbilitiesEB = [AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,
                           AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,
                           AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,
                           AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,
                           AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,
                           AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3]
            AbilitiesAR = [AbilityId.ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL1,
                           AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1,
                           AbilityId.ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL2,
                           AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL1,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL2,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2,
                           AbilityId.ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL3,
                           AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL3,
                           AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3,
                           ]

            for building in [UnitTypeId.ARMORY, UnitTypeId.ENGINEERINGBAY] if self.enemy_race == Race.Protoss else [UnitTypeId.ENGINEERINGBAY, UnitTypeId.ARMORY]:
                if self.ramp_wall_bot.structures(building).idle.amount > 0:
                    for ability in AbilitiesAR if building == UnitTypeId.ARMORY else AbilitiesEB:
                        if self.ramp_wall_bot.minerals > 300 and self.ramp_wall_bot.vespene > 300:
                            avaliable: List[AbilityId] = await self.ramp_wall_bot.get_available_abilities(self.ramp_wall_bot.structures(building).first)
                            if ability in avaliable:
                                self.ramp_wall_bot.structures(building).first(ability)
                                break

        for cc in self.ramp_wall_bot.townhalls(UnitTypeId.COMMANDCENTER).idle:
            if(self.ramp_wall_bot.can_afford(UnitTypeId.ORBITALCOMMAND)) and cc.position in self.ramp_wall_bot.expansion_locations_list:
                cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

        if self.expanded_times >= 2:
            if self.ramp_wall_bot.can_afford(UnitTypeId.REFINERY) and \
               len(self.ramp_wall_bot.structures(UnitTypeId.REFINERY)) < 2 * self.ramp_wall_bot.townhalls.amount and \
               self.ramp_wall_bot.vespene < 500:
                #get the closest gas to the base
                if self.ramp_wall_bot.townhalls:
                    for cc in self.ramp_wall_bot.townhalls:
                        for target_gas in self.ramp_wall_bot.vespene_geyser.closer_than(10, cc):
                            #get the closest worker to the gas
                            builders = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_minerals and not unit.is_constructing_scv)
                            worker = builders.closest_to(target_gas)
                            #build a refinery
                            if worker:
                                worker.build(UnitTypeId.REFINERY, target_gas, queue=True)
        

        if (self.ramp_wall_bot.supply_left < 9 and self.ramp_wall_bot.townhalls and self.ramp_wall_bot.supply_used >= 20
            and self.ramp_wall_bot.can_afford(UnitTypeId.SUPPLYDEPOT) and self.ramp_wall_bot.already_pending(UnitTypeId.SUPPLYDEPOT) < 1
        ):
            workers: Units = self.ramp_wall_bot.workers.filter(lambda unit: not unit.is_carrying_resource and not unit.is_constructing_scv)
            # If workers were found
            if workers:
                worker: Unit = workers.furthest_to(workers.center)
                location: Point2 = await self.ramp_wall_bot.find_placement(UnitTypeId.SUPPLYDEPOT, worker.position, placement_step=3)
                # If a placement location was found
                if location:
                    # Order worker to build exactly on that location
                    worker.build(UnitTypeId.SUPPLYDEPOT, location)
        



    midgame_protoss = midgame_terran
    
    midgame_zerg = midgame_protoss 




    def scout_pos(self):
        #queue a scout after the refinery is built
        enemy_base = self.ramp_wall_bot.enemy_start_locations[0]
        my_base : Point2 = self.ramp_wall_bot.start_location
        diference = Point2(((enemy_base.x - my_base.x), (enemy_base.y - my_base.y)))
        #do a 10 degree rotation
        point1 = Point2((diference.x*np.cos(np.pi/36) - diference.y*np.sin(np.pi/36), diference.x*np.sin(np.pi/36) + diference.y*np.cos(np.pi/36)))

        #do a -10 degree rotation
        point2 = Point2((diference.x*np.cos(-np.pi/36) - diference.y*np.sin(-np.pi/36), diference.x*np.sin(-np.pi/36) + diference.y*np.cos(-np.pi/36)))

        destination1 = Point2((point1.x + my_base.x, point1.y + my_base.y))
        destination2 = Point2((point2.x + my_base.x, point2.y + my_base.y))

        location = self.ramp_wall_bot.get_next_expansion()

        return destination1, destination2
