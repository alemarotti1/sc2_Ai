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

    async def on_unit_created(self, unit: Unit):
        await self.controller.on_unit_created(unit)
    
    async def on_building_construction_complete(self, unit: Unit):
        self.controller.on_building_construction_complete(unit)

    async def on_step(self, iteration):
        # try:
        #     self.iteration = iteration
        #     self.controller.run(iteration=iteration)
        # except Exception as e:
        #     pass

        
        self.iteration = iteration
        await self.controller.run(iteration=iteration)

        for towhhall in self.townhalls.idle: 
            if towhhall.assigned_harvesters < 16:
                if self.can_afford(UnitTypeId.SCV):
                    towhhall.train(UnitTypeId.SCV)


        # if not self.army_commanders:
        #     self.army_commanders.append(ArmyCommander(self, "attack", [UnitTypeId.REAPER]))

        # self.buildingCommander.run()

        # self.worker_sauration()

        # for army_commander in self.army_commanders:
        #     army_commander.run()

        
        
        # #if barracks are ready and no reapers were build, train one reaper
        # if self.supply_left > 0 and self.units(UnitTypeId.REAPER).amount == 0:
        #     # Loop through all idle barracks
        #     for rax in self.structures(UnitTypeId.BARRACKS).idle:
        #         if self.can_afford(UnitTypeId.REAPER):
        #             rax.train(UnitTypeId.REAPER)


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


        # barracks_placement_position: Point2 = self.main_base_ramp.barracks_correct_placement

        # depots: Units = self.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

    



    def get_threats(self):
        return self.controller.threats

        
        
        

    async def on_building_construction_started(self, unit: Unit):
        print(f"Construction of building {unit} started at {unit.position}.")

    async def on_building_construction_complete(self, unit: Unit):
        print(f"Construction of building {unit} completed at {unit.position}.")


    def draw_facing_units(self):
        """ Draws green box on top of selected_unit2, if selected_unit2 is facing selected_unit1 """
        pass


    def get_idle_workers(self):
        """ Returns a list of workers that are not carrying anything """
        return [unit for unit in self.workers.idle]


    def add_worker(self, worker: Unit, target: Unit):
        """ Adds a worker to a building """
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
    
    async def remove_worker(self, worker: Unit):
        await self.controller.remove_worker(worker)
    
    def produce_workers(self, townhall: Unit):
        """ Produce a worker if not already producing"""
        if townhall.is_active:
            return False
        #check if townhall has enough minerals to produce a worker
        if self.minerals > 50:
            townhall.train(UnitTypeId.SCV)
            return True
        return False

    def worker_sauration(self):
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
    
    def update_race(self, race:Race):
        controller : RandomController = self.controller
        self.controller = controller.update_race(race)
        print("race changed to ", race)
    
    async def available_army(self) -> Units:
        return await self.controller.available_army()

    async def start_producing_army(self):
        self.controller.start_producing = True
    


# class BCRushBot(BotAI):
#     def select_target(self) -> Tuple[Point2, bool]:
#         """ Select an enemy target the units should attack. """
#         targets: Units = self.enemy_structures
#         if targets:
#             return targets.random.position, True

#         targets: Units = self.enemy_units
#         if targets:
#             return targets.random.position, True

#         if self.units and min([u.position.distance_to(self.enemy_start_locations[0]) for u in self.units]) < 5:
#             return self.enemy_start_locations[0].position, False

#         return self.mineral_field.random.position, False

#     async def on_step(self, iteration):
#         ccs: Units = self.townhalls
#         # If we no longer have townhalls, attack with all workers
#         if not ccs:
#             target, target_is_enemy_unit = self.select_target()
#             for unit in self.workers | self.units(UnitTypeId.BATTLECRUISER) | self.units(UnitTypeId.MARINE):
#                 if not unit.is_attacking:
#                     unit.attack(target)
#             return
#         else:
#             cc: Unit = ccs.furthest_to(self.game_info.map_center)

#         if self.minerals > 500 and len(self.structures(UnitTypeId.COMMANDCENTER)) < 2:
#             if self.can_afford(UnitTypeId.COMMANDCENTER):
#                 await self.expand_now()

#         # Send all BCs to attack a target.
#         bcs: Units = self.units(UnitTypeId.BATTLECRUISER)
#         target, target_is_enemy_unit = self.select_target()
#         if bcs:
#             bc: Unit
#             for bc in bcs:
#                 # Order the BC to attack-move the target
#                 if target_is_enemy_unit and (bc.is_idle or bc.is_moving):
#                     bc.attack(target)
#                 # Order the BC to move to the target, and once the select_target returns an attack-target, change it to attack-move
#                 elif bc.is_idle:
#                     bc.move(target)

#         marines: Units = self.units(UnitTypeId.MARINE)
#         if marines.amount > 15 or target_is_enemy_unit:
#             for marine in marines:
#                 if target_is_enemy_unit and (marine.is_idle or marine.is_moving):
#                     marine.attack(target)
#                 elif marine.is_idle:
#                     marine.move(target)

#         # Build more SCVs until 22
#         for ccc in ccs:
#             if      self.can_afford(UnitTypeId.SCV) and ccc.is_idle \
#                 and self.supply_workers < 22 * len(self.structures(UnitTypeId.COMMANDCENTER)):
#                 ccc.train(UnitTypeId.SCV)

#         # Build more BCs
#         if self.structures(UnitTypeId.FUSIONCORE) and self.can_afford(UnitTypeId.BATTLECRUISER):
#             for sp in self.structures(UnitTypeId.STARPORT).idle:
#                 if sp.has_add_on:
#                     if not self.can_afford(UnitTypeId.BATTLECRUISER):
#                         break
#                     sp.train(UnitTypeId.BATTLECRUISER)
        
#         if self.structures(UnitTypeId.BARRACKS) and self.can_afford(UnitTypeId.MARINE)\
#             and (len(self.structures(UnitTypeId.COMMANDCENTER)) >= 2 or self.minerals > 500):
#             for sp in self.structures(UnitTypeId.BARRACKS).idle:
#                 if not self.can_afford(UnitTypeId.MARINE):
#                     break
#                 sp.train(UnitTypeId.MARINE)

#         # Build more supply depots
#         if self.supply_left < 6 and self.supply_used >= 14 and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
#             if self.can_afford(UnitTypeId.SUPPLYDEPOT):
#                 await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 12))

#         # Build barracks if we have none
#         if self.tech_requirement_progress(UnitTypeId.BARRACKS) == 1:
#             if not self.structures(UnitTypeId.BARRACKS):
#                 if self.can_afford(UnitTypeId.BARRACKS):
#                     await self.build(UnitTypeId.BARRACKS, near=cc.position.towards(self.game_info.map_center, 10))

#             # Build refineries
#             elif self.structures(UnitTypeId.BARRACKS) and self.gas_buildings.amount < 2 * len(self.structures(UnitTypeId.COMMANDCENTER)):
#                 if self.can_afford(UnitTypeId.REFINERY):
#                     vgs: Units = self.vespene_geyser.closer_than(20, cc)
#                     for vg in vgs:
#                         if self.gas_buildings.filter(lambda unit: unit.distance_to(vg) < 1):
#                             break

#                         worker: Unit = self.select_build_worker(vg.position)
#                         if worker is None:
#                             break

#                         worker.build(UnitTypeId.REFINERY, vg)
#                         break

#             elif len(self.structures(UnitTypeId.BARRACKS)) < 2:
#                 if self.can_afford(UnitTypeId.BARRACKS):
#                     await self.build(UnitTypeId.BARRACKS, near=cc.position.towards(self.game_info.map_center, 12))

#             # Build factory if we dont have one
#             if self.tech_requirement_progress(UnitTypeId.FACTORY) == 1:
#                 factories: Units = self.structures(UnitTypeId.FACTORY)
#                 if not factories:
#                     if self.can_afford(UnitTypeId.FACTORY):
#                         await self.build(UnitTypeId.FACTORY, near=cc.position.towards(self.game_info.map_center, 8))
#                 # Build starport once we can build starports, up to 2
#                 elif (
#                     factories.ready
#                     and self.structures.of_type({UnitTypeId.STARPORT, UnitTypeId.STARPORTFLYING}).ready.amount +
#                     self.already_pending(UnitTypeId.STARPORT) < 2
#                 ):
#                     if self.can_afford(UnitTypeId.STARPORT):
#                         await self.build(
#                             UnitTypeId.STARPORT,
#                             near=cc.position.towards(self.game_info.map_center, 15).random_on_distance(8),
#                         )

#         def starport_points_to_build_addon(sp_position: Point2) -> List[Point2]:
#             """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
#             addon_offset: Point2 = Point2((2.5, -0.5))
#             addon_position: Point2 = sp_position + addon_offset
#             addon_points = [
#                 (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
#             ]
#             return addon_points

#         # Build starport techlab or lift if no room to build techlab
#         sp: Unit
#         for sp in self.structures(UnitTypeId.STARPORT).ready.idle:
#             if not sp.has_add_on and self.can_afford(UnitTypeId.STARPORTTECHLAB):
#                 addon_points = starport_points_to_build_addon(sp.position)
#                 if all(
#                     self.in_map_bounds(addon_point) and self.in_placement_grid(addon_point)
#                     and self.in_pathing_grid(addon_point) for addon_point in addon_points
#                 ):
#                     sp.build(UnitTypeId.STARPORTTECHLAB)
#                 else:
#                     sp(AbilityId.LIFT)

#         def starport_land_positions(sp_position: Point2) -> List[Point2]:
#             """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
#             land_positions = [(sp_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
#             return land_positions + starport_points_to_build_addon(sp_position)

#         # Find a position to land for a flying starport so that it can build an addon
#         for sp in self.structures(UnitTypeId.STARPORTFLYING).idle:
#             possible_land_positions_offset = sorted(
#                 (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
#                 key=lambda point: point.x**2 + point.y**2,
#             )
#             offset_point: Point2 = Point2((-0.5, -0.5))
#             possible_land_positions = (sp.position.rounded + offset_point + p for p in possible_land_positions_offset)
#             for target_land_position in possible_land_positions:
#                 land_and_addon_points: List[Point2] = starport_land_positions(target_land_position)
#                 if all(
#                     self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos)
#                     and self.in_pathing_grid(land_pos) for land_pos in land_and_addon_points
#                 ):
#                     sp(AbilityId.LAND, target_land_position)
#                     break

#         # Show where it is flying to and show grid
#         unit: Unit
#         for sp in self.structures(UnitTypeId.STARPORTFLYING).filter(lambda unit: not unit.is_idle):
#             if isinstance(sp.order_target, Point2):
#                 p: Point3 = Point3((*sp.order_target, self.get_terrain_z_height(sp.order_target)))
#                 self.client.debug_box2_out(p, color=Point3((255, 0, 0)))

#         # Build fusion core
#         if self.structures(UnitTypeId.STARPORT).ready:
#             if self.can_afford(UnitTypeId.FUSIONCORE) and not self.structures(UnitTypeId.FUSIONCORE):
#                 await self.build(UnitTypeId.FUSIONCORE, near=cc.position.towards(self.game_info.map_center, 8))

#         # Saturate refineries
#         for refinery in self.gas_buildings:
#             if refinery.assigned_harvesters < refinery.ideal_harvesters:
#                 worker: Units = self.workers.closer_than(10, refinery)
#                 if worker:
#                     worker.random.gather(refinery)

#         # Send workers back to mine if they are idle
#         for scv in self.workers.idle:
#             scv.gather(self.mineral_field.closest_to(ccs.closest_to(self.game_info.map_center)))





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
            Computer(Race.Protoss, Difficulty.Hard)
        ],
        realtime=True,
        save_replay_as="replay"
        
        # sc2_version="4.10.1",
    )






















if __name__ == "__main__":
    main()
