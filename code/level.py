import pygame 
from bisect import bisect_left, bisect_right
from settings import *
from player import Player
from sprites import *
import pytmx
from pytmx.util_pygame import load_pygame # pytmx map loader
from soil import *
# from menu import *
from menu_2 import *
from window import Window
from books import Books
from ecoli import Ecoli
from dialogues import Dialogues
from save_load import save_file
from functions import *
from utils import *
from skins import SkinManager
from skin_menu import SkinSelectionMenu
from progression import is_model_unlocked
from campaign import CampaignContext
from student_registration import StudentRegistrationMenu
from easy_mission_npc import EasyMissionNPC
from final_results import FinalResultsMenu
from teacher_mission_launcher import TeacherMissionLauncher

class Level:
	def __init__(self, load_game, teacher_target_mission=None, teacher_preview=False):

		# get the display surface
		self.display_surface = pygame.display.get_surface()

		# load the game
		self.load_game = load_game
		self.teacher_target_mission = teacher_target_mission
		self.teacher_preview = bool(teacher_preview or teacher_target_mission is not None)
		self.teacher_launch_pending = teacher_target_mission is not None
		self.teacher_open_key_locked = False
		self.campaign_context = CampaignContext(mode='normal')

		# sprite groups
		self.all_sprites = CameraGroup()
		# Only sprites with real per-frame behaviour belong here. Static map
		# sprites stay in all_sprites for drawing but no longer receive thousands
		# of unnecessary Sprite.update() dispatches in the browser.
		self.dynamic_sprites = pygame.sprite.Group()
		self.collision_sprites = pygame.sprite.Group()
		self.tree_sprites = pygame.sprite.Group()
		self.interaction_sprites = pygame.sprite.Group()
		self.progression_gate_sprites = pygame.sprite.Group()

		# Character skin system: load all skin sprite frames once.
		self.skin_manager = SkinManager()

		self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)
		self.setup()
		# Teacher Preview is orthogonal to Normal/Easy campaign mode.  The Player
		# keeps the selected student route so mission-specific Easy branches remain
		# faithful, while this flag controls preview-only UI/behaviour.
		self.player.teacher_preview = self.teacher_preview
		self.player.teacher_target_mission = self.teacher_target_mission
		# Transient Teacher control signal. Never persisted in student/teacher
		# save data; Game consumes it only when switching isolated previews.
		self.player.teacher_switch_request = None
		if self.teacher_preview:
			font_path = get_resource_path('font/LycheeSoda.ttf')
			self.teacher_banner_font = pygame.font.Font(font_path, 24)
			self.teacher_banner_small_font = pygame.font.Font(font_path, 19)
		else:
			self.teacher_banner_font = None
			self.teacher_banner_small_font = None

		# MENUS
		self.menu_active = False
		self.desk_active = False
		self.yeast_simulator_active = False
		self.books_active = False
		self.ecoli_active = False
		self.talk_1_active = False
		self.talk_1 = None
		self.talk_2_active = False
		self.talk_2 = None
		self.talk_3_active = False
		self.talk_3 = None
		self.talk_7_active = False
		self.talk_7 = None
		self.talk_11_active = False
		self.talk_11 = None
		self.talk_16_active = False
		self.talk_16 = None
		self.talk_21_active = False
		self.talk_21 = None
		self.talk_23_active = False
		self.talk_23 = None
		self.talk_25_active = False
		self.talk_25 = None
		self.talk_27_active = False
		self.talk_27 = None
		self.talk_29_active = False
		self.talk_29 = None
		self.talk_32_active = False
		self.talk_32 = None
		self.talk_35_active = False
		self.talk_35 = None
		self.talk_36_active = False
		self.talk_36 = None
		self.talk_37_active = False
		self.talk_37 = None
		self.talk_38_active = False
		self.talk_38 = None
		self.talk_39_active = False
		self.talk_39 = None
		self.talk_40_active = False
		self.talk_40 = None
		self.menu = Menu(self.player, self.toggle_shop)
		self.window = Window(self.desk_menu, self.player, model_id='ecoli_core')
		# The large iMM904 UI is created only when the unlocked computer is
		# actually opened.  This keeps pre-Mission-35 startup light and mirrors
		# the future browser flow, where model-specific assets should be loaded
		# on demand rather than at initial page load.
		self.yeast_window = None
		self.books = Books(self.read_books)
		self.ecoli = Ecoli(self.see_ecoli)
		self.dialogues = Dialogues(self.toggle_dialogue, self.player)
		self.dialogues_active = False
		self.student_registration_active = False
		self.student_registration = StudentRegistrationMenu(
			self.player,
			self.toggle_student_registration,
			self.refresh_campaign_context,
		)
		# STUDENT.2 final results are opened automatically once the selected
		# campaign's actual final mission is complete.
		self.final_results_active = False
		self.final_results = FinalResultsMenu(self.player, self.close_final_results)
		# After campaign completion, F can reopen the final-results screen.
		# The lock prevents a held key from reopening the menu repeatedly.
		self.final_results_open_key_locked = False
		self.teacher_launcher = (
			TeacherMissionLauncher(self.player, self.teacher_target_mission)
			if self.teacher_target_mission is not None else None
		)
		self.skin_menu_active = False
		self.skin_menu = SkinSelectionMenu(self.skin_manager, self.player)
		self.skin_open_key_locked = False
		# Track modal -> map transitions. If a modal was confirmed with ENTER,
		# the same held key must not trigger a nearby world interaction.
		self._map_modal_was_active = False

		# sounds
		success_path = get_resource_path('audio/success.ogg')
		self.success = pygame.mixer.Sound(success_path) 
		self.success.set_volume(0.1)

		# music
		# self.music_bg = pygame.mixer.Sound(MUSIC_NAME)
		# self.music_bg.set_volume(0.07)
		# self.music_bg.play(loops = -1)

	@staticmethod
	def _optional_tmx_layer(tmx_data, name):
		"""Return an optional Tiled layer; old maps remain valid."""
		try:
			return tmx_data.get_layer_by_name(name)
		except (ValueError, KeyError):
			return None

	def _setup_progression_gates(self, tmx_data):
		"""Create gates from optional Tiled object layer ``ProgressionGates``."""
		layer = self._optional_tmx_layer(tmx_data, 'ProgressionGates')
		if layer is None:
			return

		for obj in layer:
			properties = getattr(obj, 'properties', {}) or {}
			required_mission = properties.get('unlock_after')
			if required_mission is None:
				raise ValueError(
					f"Progression gate {getattr(obj, 'name', '<unnamed>')!r} "
					"is missing Tiled property 'unlock_after'"
				)

			surf = getattr(obj, 'image', None)
			if surf is None:
				width = max(1, round(float(getattr(obj, 'width', TILE_SIZE) or TILE_SIZE)))
				height = max(1, round(float(getattr(obj, 'height', TILE_SIZE) or TILE_SIZE)))
				surf = pygame.Surface((width, height), pygame.SRCALPHA)

			ProgressionGate(
				pos=(obj.x, obj.y),
				surf=surf,
				groups=[self.all_sprites, self.dynamic_sprites,
						self.collision_sprites, self.progression_gate_sprites],
				player=self.player,
				campaign_context=self.campaign_context,
				required_mission=required_mission,
				name=getattr(obj, 'name', None),
			)

	def setup(self):
		
		map_path = get_resource_path('data/map_lb.tmx')
		tmx_data = load_pygame(map_path)
		surf_path = get_resource_path('graphics/world/ground_lb.png')

		# HouseFloor + HouseFurnitureBottom are large, completely static tile
		# layers. Keep their exact pytmx surfaces/positions/order, but do not
		# allocate 1409 Sprite objects or include them in the global per-frame
		# sort. CameraGroup draws this pre-sorted layer directly at the same z.
		house_bottom_tiles = []
		house_bottom_order = 0
		for layer in ['HouseFloor', 'HouseFurnitureBottom']:
			for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
				rect = surf.get_rect(topleft = (x * TILE_SIZE, y * TILE_SIZE))
				house_bottom_tiles.append((rect.centery, house_bottom_order, surf, rect))
				house_bottom_order += 1
		self.all_sprites.set_house_bottom_tiles(house_bottom_tiles)

		for layer in ['HouseWalls', 'HouseFurnitureMiddle', 'HouseFurnitureTop']:
			for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
				Generic((x* TILE_SIZE, y* TILE_SIZE), surf, self.all_sprites, LAYERS['main'])

		# Fence
		for x, y, surf in tmx_data.get_layer_by_name('Fence').tiles():
			Generic((x* TILE_SIZE, y* TILE_SIZE), surf, [self.all_sprites, self.collision_sprites], LAYERS['main'])

		# Water
		water_frames_path = get_resource_path('graphics/water')
		water_frames = import_folder(water_frames_path)
		for x, y, surf in tmx_data.get_layer_by_name('Water').tiles():
			Water((x* TILE_SIZE, y* TILE_SIZE), water_frames, [self.all_sprites, self.dynamic_sprites])


		# Trees
		for obj in tmx_data.get_layer_by_name('Trees'):
			Tree(
				pos = (obj.x, obj.y),
				surf = obj.image,
				groups = [self.all_sprites, self.collision_sprites, self.tree_sprites],
				name = obj.name,
				player_add = self.player_add,
				all_sprites = self.all_sprites,
				dynamic_sprites = self.dynamic_sprites)

		# Wildflowers
		for obj in tmx_data.get_layer_by_name('Decoration'):
			WildFlower((obj.x, obj.y), obj.image, [self.all_sprites, self.collision_sprites])

		# collision tiles 
		for x, y, surf in tmx_data.get_layer_by_name('Collision').tiles(): # no mapa tem tiles definidos como collision (como water, house, etc.)
			Generic((x * TILE_SIZE, y * TILE_SIZE), pygame.Surface((TILE_SIZE, TILE_SIZE)), self.collision_sprites) # apenas neste grupo porque não queremos mostrar estes tiles, apenas colidir

		# Player
		# Keep the post-Mission-06 Carter reveal anchored to the current
		# Tiled interaction object instead of the coordinates of an older map.
		carter_reveal_pos = None
		golden_egg_obj = None
		for obj in tmx_data.get_layer_by_name('Player'):
			if obj.name == 'Start':
				self.player = Player(
					pos = (obj.x,obj.y),
					group = [self.all_sprites, self.dynamic_sprites],
					collision_sprites = self.collision_sprites,
					tree_sprites = self.tree_sprites,
					interaction = self.interaction_sprites,
					soil_layer = self.soil_layer,
					toggle_shop = self.toggle_shop,
					desk_menu = self.desk_menu,
					yeast_simulator = self.yeast_simulator_menu,
					books = self.read_books,
					ecoli = self.see_ecoli,
					# inventory = self.load_game,
					inventory2 = self.load_game,
					talk_1 = self.toggle_talk_1,
					talk_2 = self.toggle_talk_2,
					talk_3 = self.toggle_talk_3,
					talk_7 = self.toggle_talk_7,
					talk_11 = self.toggle_talk_11,
					talk_16 = self.toggle_talk_16,
					talk_21 = self.toggle_talk_21,
					talk_23 = self.toggle_talk_23,
					talk_25 = self.toggle_talk_25,
					talk_27 = self.toggle_talk_27,
					talk_29 = self.toggle_talk_29,
					talk_32 = self.toggle_talk_32,
					talk_35 = self.toggle_talk_35,
					talk_36 = self.toggle_talk_36,
					talk_37 = self.toggle_talk_37,
					talk_38 = self.toggle_talk_38,
					talk_39 = self.toggle_talk_39,
					talk_40 = self.toggle_talk_40,
					dialogues = self.toggle_dialogue,
					student_registration = self.toggle_student_registration,
					skin_manager = self.skin_manager
					# music = self.music_bg
					)
				# EASY.1A: rebuild the campaign policy from the persisted player
				# mode before progression gates are instantiated later in setup().
				self.campaign_context = CampaignContext(mode=self.player.campaign_mode)

			if obj.name == 'GoldenEgg':
				golden_egg_obj = obj
			
			if obj.name == 'Mission01':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
			
			if obj.name == 'Mission02':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission03':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
				carter_reveal_pos = (obj.x, obj.y)

			if obj.name == 'Mission07':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission11':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission16':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission21':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission23':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission25':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission27':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission29':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mission32':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Final':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
			
			if obj.name == 'Desk':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Vale':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Voss':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Umbra':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Morbus':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Mortis':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'YeastSimulator':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
			
			if obj.name == 'Books':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Ecoli':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)	

			if obj.name in ('Sequeira', 'Pacheco', 'Nuno', 'Fernanda', 'Emanuel', 'Alexandre', 'Capela', 'Marta', 'Oscar', 'Miguel'):
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			if obj.name == 'Alves':
				# Start NPC: the Tiled tile object resolves to start.png.
				if getattr(obj, 'image', None) is not None:
					Generic(
						(obj.x, obj.y),
						obj.image,
						[self.all_sprites, self.collision_sprites],
						LAYERS['main'],
					)
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			# if obj.name == 'Oscar':
			# 	Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			# if obj.name == 'Vitor':
			# 	Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
				
			if obj.name == 'Coffee':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

		# The Golden Egg is authored as a tile object on the Player layer. It is
		# deliberately not a collision object: players can walk up to it, press
		# ENTER nearby, collect its one-time reward and then it disappears.
		if (
			golden_egg_obj is not None
			and not getattr(self.player, 'golden_egg_collected', False)
		):
			GoldenEgg(
				pos=(golden_egg_obj.x, golden_egg_obj.y),
				surf=golden_egg_obj.image,
				groups=[self.all_sprites, self.dynamic_sprites],
				player=self.player,
			)
			interaction_padding = 32
			Interaction(
				(
					golden_egg_obj.x - interaction_padding,
					golden_egg_obj.y - interaction_padding,
				),
				(
					golden_egg_obj.width + (interaction_padding * 2),
					golden_egg_obj.height + (interaction_padding * 2),
				),
				self.interaction_sprites,
				'GoldenEgg',
			)

		# Gates are created after Player has loaded missions_completed from save.
		self._setup_progression_gates(tmx_data)

		if carter_reveal_pos is not None:
			CarterRevealSprite(
				pos = carter_reveal_pos,
				groups = [self.all_sprites, self.dynamic_sprites],
				player = self.player)

		Generic(
			pos = (0,0),
			surf = pygame.image.load(surf_path).convert(),
			groups = self.all_sprites,
			z = LAYERS['ground'])

	def refresh_campaign_context(self):
		"""Synchronise Level/gates after the one-time Normal/Easy registration."""
		self.campaign_context = CampaignContext(mode=self.player.campaign_mode)
		for gate in self.progression_gate_sprites.sprites():
			gate.campaign_context = self.campaign_context
			gate.sync_with_progression()

	def player_add(self, item):
		self.player.item_inventory[item] += 1
		self.success.play()

	def toggle_shop(self):
		self.menu_active = not self.menu_active

	def toggle_talk_1(self):
		if not self.talk_1_active and self.talk_1 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_1 = EasyMissionNPC(self.toggle_talk_1, self.player, '01')
			else:
				from mission01 import Mission01
				self.talk_1 = Mission01(self.toggle_talk_1, self.player)
		self.talk_1_active = not self.talk_1_active

	def toggle_talk_2(self):
		if not self.talk_2_active and self.talk_2 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_2 = EasyMissionNPC(self.toggle_talk_2, self.player, '03')
			else:
				from mission03 import Mission03
				self.talk_2 = Mission03(self.toggle_talk_2, self.player)
		self.talk_2_active = not self.talk_2_active
	
	def toggle_talk_3(self):
		if not self.talk_3_active and self.talk_3 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_3 = EasyMissionNPC(self.toggle_talk_3, self.player, '06')
			else:
				from mission06 import Mission06
				self.talk_3 = Mission06(self.toggle_talk_3, self.player)
		self.talk_3_active = not self.talk_3_active

	def toggle_talk_7(self):
		if not self.talk_7_active and self.talk_7 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_7 = EasyMissionNPC(self.toggle_talk_7, self.player, '07')
			else:
				from mission07 import Mission07
				self.talk_7 = Mission07(self.toggle_talk_7, self.player)
		self.talk_7_active = not self.talk_7_active

	def toggle_talk_11(self):
		if not self.talk_11_active and self.talk_11 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_11 = EasyMissionNPC(self.toggle_talk_11, self.player, '13')
			else:
				from mission11 import Mission11
				self.talk_11 = Mission11(self.toggle_talk_11, self.player)
		self.talk_11_active = not self.talk_11_active

	def toggle_talk_16(self):
		if not self.talk_16_active and self.talk_16 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_16 = EasyMissionNPC(self.toggle_talk_16, self.player, '18')
			else:
				from mission16 import Mission16
				self.talk_16 = Mission16(self.toggle_talk_16, self.player)
		self.talk_16_active = not self.talk_16_active

	def toggle_talk_21(self):
		if not self.talk_21_active and self.talk_21 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_21 = EasyMissionNPC(self.toggle_talk_21, self.player, '21')
			else:
				from mission21 import Mission21
				self.talk_21 = Mission21(self.toggle_talk_21, self.player)
		self.talk_21_active = not self.talk_21_active

	def toggle_talk_23(self):
		if not self.talk_23_active and self.talk_23 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_23 = EasyMissionNPC(self.toggle_talk_23, self.player, '23')
			else:
				from mission23 import Mission23
				self.talk_23 = Mission23(self.toggle_talk_23, self.player)
		self.talk_23_active = not self.talk_23_active

	def toggle_talk_25(self):
		if not self.talk_25_active and self.talk_25 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_25 = EasyMissionNPC(self.toggle_talk_25, self.player, '25')
			else:
				from mission25 import Mission25
				self.talk_25 = Mission25(self.toggle_talk_25, self.player)
		self.talk_25_active = not self.talk_25_active

	def toggle_talk_27(self):
		if not self.talk_27_active and self.talk_27 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_27 = EasyMissionNPC(self.toggle_talk_27, self.player, '27')
			else:
				from mission27 import Mission27
				self.talk_27 = Mission27(self.toggle_talk_27, self.player)
		self.talk_27_active = not self.talk_27_active

	def toggle_talk_29(self):
		if not self.talk_29_active and self.talk_29 is None:
			from mission29 import Mission29
			self.talk_29 = Mission29(self.toggle_talk_29, self.player)
		self.talk_29_active = not self.talk_29_active

	def toggle_talk_32(self):
		if not self.talk_32_active and self.talk_32 is None:
			from mission32 import Mission32
			self.talk_32 = Mission32(self.toggle_talk_32, self.player)
		self.talk_32_active = not self.talk_32_active

	def toggle_talk_35(self):
		if not self.talk_35_active and self.talk_35 is None:
			from mission35 import Mission35
			self.talk_35 = Mission35(self.toggle_talk_35, self.player)
		self.talk_35_active = not self.talk_35_active

	def toggle_talk_36(self):
		if not self.talk_36_active and self.talk_36 is None:
			if getattr(self.player, 'campaign_mode', 'normal') == 'easy':
				self.talk_36 = EasyMissionNPC(self.toggle_talk_36, self.player, '36')
			else:
				from mission36 import Mission36
				self.talk_36 = Mission36(self.toggle_talk_36, self.player)
		self.talk_36_active = not self.talk_36_active

	def toggle_talk_37(self):
		if not self.talk_37_active and self.talk_37 is None:
			from mission37 import Mission37
			self.talk_37 = Mission37(self.toggle_talk_37, self.player)
		self.talk_37_active = not self.talk_37_active

	def toggle_talk_38(self):
		if not self.talk_38_active and self.talk_38 is None:
			from mission38 import Mission38
			self.talk_38 = Mission38(self.toggle_talk_38, self.player)
		self.talk_38_active = not self.talk_38_active

	def toggle_talk_39(self):
		if not self.talk_39_active and self.talk_39 is None:
			from mission39 import Mission39
			self.talk_39 = Mission39(self.toggle_talk_39, self.player)
		self.talk_39_active = not self.talk_39_active

	def toggle_talk_40(self):
		if not self.talk_40_active and self.talk_40 is None:
			from mission40 import Mission40
			self.talk_40 = Mission40(self.toggle_talk_40, self.player)
		self.talk_40_active = not self.talk_40_active

	def toggle_dialogue(self):
		self.dialogues_active = not self.dialogues_active

	def toggle_student_registration(self):
		self.student_registration_active = not self.student_registration_active

	def should_show_final_results(self):
		return (
			not self.teacher_preview
			and self.player.name_confirmed
			and not self.player.final_results_seen
			and self.campaign_context.is_campaign_complete(self.player.missions_completed)
		)

	def can_reopen_final_results(self):
		"""Return whether the completed campaign summary may be reopened with F."""
		return (
			not self.teacher_preview
			and self.player.name_confirmed
			and self.campaign_context.is_campaign_complete(self.player.missions_completed)
		)

	def close_final_results(self):
		self.final_results_active = False
		if not self.player.final_results_seen:
			self.player.final_results_seen = True
			save_file(self.player.get_save_data())

	def handle_final_results_shortcut(self):
		"""Reopen Final Results with F, but only after campaign completion."""
		keys = pygame.key.get_pressed()
		f_pressed = keys[pygame.K_f]

		# Re-arm only after the key is released, so holding F cannot immediately
		# reopen the menu after the player closes it.
		if not f_pressed:
			self.final_results_open_key_locked = False
			return

		if (
			not self.final_results_open_key_locked
			and self.can_reopen_final_results()
			and not self.any_modal_active()
			and not self.skin_menu_active
		):
			self.final_results_active = True

		self.final_results_open_key_locked = True

	def desk_menu(self):
		self.desk_active = not self.desk_active

	def yeast_simulator_menu(self):
		if not is_model_unlocked('yeast_iMM904', self.player.missions_completed, self.campaign_context):
			required = self.campaign_context.progression_milestone_for('35') or '35'
			animation_text_save(f'Complete Mission {required} to unlock the yeast simulator.', time=2500)
			return
		if self.yeast_window is None:
			animation_text_save('Loading yeast simulator...', time=250)
			self.yeast_window = Window(self.yeast_simulator_menu, self.player, model_id='yeast_iMM904')
		self.yeast_simulator_active = not self.yeast_simulator_active

	def read_books(self):
		self.books_active = not self.books_active

	def see_ecoli(self):
		self.ecoli_active = not self.ecoli_active

	def any_modal_active(self):
		return (
			self.menu_active or
			self.desk_active or
			self.yeast_simulator_active or
			self.books_active or
			self.ecoli_active or
			self.talk_1_active or
			self.talk_2_active or
			self.talk_3_active or
			self.talk_7_active or
			self.talk_11_active or
			self.talk_16_active or
			self.talk_21_active or
			self.talk_23_active or
			self.talk_25_active or
			self.talk_27_active or
			self.talk_29_active or
			self.talk_32_active or
			self.talk_35_active or
			self.talk_36_active or
			self.talk_37_active or
			self.talk_38_active or
			self.talk_39_active or
			self.talk_40_active or
			self.dialogues_active or
			self.student_registration_active or
			self.final_results_active
		)

	def suppress_enter_after_modal_close(self):
		"""Require an ENTER release when control returns from any modal UI."""
		modal_active = self.any_modal_active() or self.skin_menu_active
		if self._map_modal_was_active and not modal_active:
			self.player.block_interaction_until_enter_release()
		self._map_modal_was_active = modal_active

	def handle_teacher_mission_shortcut(self):
		if self.teacher_launcher is None or not self.teacher_preview:
			return
		keys = pygame.key.get_pressed()
		t_pressed = keys[pygame.K_t]
		if t_pressed and not self.teacher_open_key_locked and not self.any_modal_active() and not self.skin_menu_active:
			self.teacher_launch_pending = True
		self.teacher_open_key_locked = t_pressed

	def draw_teacher_preview_banner(self):
		"""Render a small persistent reminder without obscuring world interaction."""
		if not self.teacher_preview or self.teacher_banner_font is None:
			return
		mode = self.player.campaign_mode.upper()
		target = self.teacher_target_mission or '--'
		panel = pygame.Surface((620, 66), pygame.SRCALPHA)
		panel.fill((0, 0, 0, 185))
		self.display_surface.blit(panel, (12, 12))
		line1 = self.teacher_banner_font.render(
			f'TEACHER PREVIEW - {mode} - MISSION {target}', True, 'white'
		)
		line2 = self.teacher_banner_small_font.render(
			'Student save is isolated. T reopens target; M can change mission.',
			True,
			'white',
		)
		self.display_surface.blit(line1, (24, 18))
		self.display_surface.blit(line2, (24, 49))

	def handle_skin_menu_shortcut(self):
		keys = pygame.key.get_pressed()
		e_pressed = keys[pygame.K_e]
		if e_pressed and not self.skin_open_key_locked and not self.any_modal_active() and not self.skin_menu_active:
			self.skin_menu.open()
			self.skin_menu_active = True
		self.skin_open_key_locked = e_pressed

	def plant_collision(self):
		if self.soil_layer.plant_sprites: # se houver plantas
			for plant in self.soil_layer.plant_sprites.sprites():
				if plant.harvestable and plant.rect.colliderect(self.player.hitbox): # se colidir com o player
					self.player_add(plant.plant_type)
					plant.kill()
					Particle(
						pos = plant.rect.topleft,
						surf = plant.image,
						groups = [self.all_sprites, self.dynamic_sprites],
						z = LAYERS['main']
					)
					x = plant.rect.centerx // TILE_SIZE
					y = plant.rect.centery // TILE_SIZE
					self.soil_layer.grid[y][x].remove('P')

	def reset(self):
		#save game
		save_file(self.player.get_save_data())

		# plants
		self.soil_layer.update_plants()

		# trees
		for tree in self.tree_sprites.sprites():
			for apple in tree.apple_sprites.sprites():
				apple.kill()
			tree.create_fruit()


	async def run(self,dt): #delta time

		# drawing logic
		self.display_surface.fill('black')
		self.all_sprites.custom_draw(self.player)
		self.draw_teacher_preview_banner()

		# A menu may have just closed using ENTER. Re-arm map interaction only
		# after RETURN/KP_ENTER are physically released.
		self.suppress_enter_after_modal_close()

		# TEACHER.1 opens the requested mission menu immediately and lets the
		# professor reopen it with T without walking back through NPC chains.
		if (
			self.teacher_launch_pending
			and self.teacher_launcher is not None
			and not self.any_modal_active()
			and not self.skin_menu_active
		):
			self.teacher_launch_pending = False
			await self.teacher_launcher.update()
			return

		self.handle_teacher_mission_shortcut()
		if self.teacher_launch_pending:
			return

		# Once the campaign is complete, F provides a persistent way to reopen
		# the final-results screen after the one-shot automatic presentation.
		self.handle_final_results_shortcut()

		# Open the summary only after every mission/dialogue/menu has closed.
		# This makes M36 (Easy) and M40 (Normal) completion feel immediate while
		# avoiding nested pygame-menu loops inside a mission screen.
		if (
			not self.final_results_active
			and not self.skin_menu_active
			and not self.any_modal_active()
			and self.should_show_final_results()
		):
			self.final_results_active = True

		if self.skin_menu_active:
			result = self.skin_menu.update()
			self.skin_menu.draw()
			if result in ('confirm', 'cancel'):
				self.skin_menu_active = False
			return

		self.handle_skin_menu_shortcut()
		if self.skin_menu_active:
			self.skin_menu.draw()
			return

		#updates
		if self.final_results_active:
			await self.final_results.update()

		elif self.menu_active:
			# self.menu.update()
			await self.menu.update()

		elif self.student_registration_active:
			await self.student_registration.update()

		elif self.talk_1_active:
			await self.talk_1.update()

		elif self.talk_2_active:
			await self.talk_2.update()

		elif self.talk_3_active:
			await self.talk_3.update()

		elif self.talk_7_active:
			await self.talk_7.update()

		elif self.talk_11_active:
			await self.talk_11.update()

		elif self.talk_16_active:
			await self.talk_16.update()

		elif self.talk_21_active:
			await self.talk_21.update()

		elif self.talk_23_active:
			await self.talk_23.update()

		elif self.talk_25_active:
			await self.talk_25.update()

		elif self.talk_27_active:
			await self.talk_27.update()

		elif self.talk_29_active:
			await self.talk_29.update()

		elif self.talk_32_active:
			await self.talk_32.update()

		elif self.talk_35_active:
			await self.talk_35.update()

		elif self.talk_36_active:
			await self.talk_36.update()

		elif self.talk_37_active:
			await self.talk_37.update()

		elif self.talk_38_active:
			await self.talk_38.update()

		elif self.talk_39_active:
			await self.talk_39.update()

		elif self.talk_40_active:
			await self.talk_40.update()

		elif self.desk_active:
			await self.window.update()

		elif self.yeast_simulator_active:
			if self.yeast_window is not None:
				await self.yeast_window.update()
			else:
				self.yeast_simulator_active = False

		elif self.books_active:
			await self.books.update()

		elif self.ecoli_active:
			await self.ecoli.update()

		elif self.dialogues_active:
			self.dialogues.choosing_character(self.player.character)
			self.dialogues.update()

		else:
			self.dynamic_sprites.update(dt)
			self.plant_collision()

		


class CameraGroup(pygame.sprite.Group):
	def __init__(self):
		super().__init__()
		self.display_surface = pygame.display.get_surface()
		self.offset = pygame.math.Vector2()

		# Static z=house-bottom tiles are kept outside this Sprite group. Their
		# surfaces and rects still come directly from pytmx, so rendering stays
		# pixel-identical while the global sort contains ~1400 fewer objects.
		self.house_bottom_tiles = []
		self.house_bottom_centers = []
		self.house_bottom_max_half_height = 0

	def set_house_bottom_tiles(self, tiles):
		self.house_bottom_tiles = sorted(tiles, key=lambda item: (item[0], item[1]))
		self.house_bottom_centers = [item[0] for item in self.house_bottom_tiles]
		self.house_bottom_max_half_height = max(
			(rect.height + 1) // 2 for _, _, _, rect in self.house_bottom_tiles
		) if self.house_bottom_tiles else 0

	def _draw_house_bottom(self, view_rect):
		if not self.house_bottom_tiles:
			return

		# The tiles are sorted once at setup by the exact same Y key used by
		# CameraGroup. Bisect narrows the frame work to rows that can intersect
		# the 1280x720 camera, then the normal Rect test handles X clipping.
		margin = self.house_bottom_max_half_height
		start = bisect_left(self.house_bottom_centers, view_rect.top - margin)
		stop = bisect_right(self.house_bottom_centers, view_rect.bottom + margin)
		for index in range(start, stop):
			_, _, surf, rect = self.house_bottom_tiles[index]
			if not rect.colliderect(view_rect):
				continue
			offset_rect = rect.copy()
			offset_rect.center -= self.offset
			self.display_surface.blit(surf, offset_rect)

	def custom_draw(self, player):
		self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
		self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2

		# Preserve the exact old draw order (z layer first, then Y position),
		# but sort the sprite list only once instead of once per layer.  Also
		# avoid issuing blits for the many map sprites that are outside the
		# current camera viewport; this matters noticeably in the WASM build.
		view_rect = pygame.Rect(
			int(self.offset.x),
			int(self.offset.y),
			SCREEN_WIDTH,
			SCREEN_HEIGHT
		)
		house_bottom_drawn = False
		for sprite in sorted(self.sprites(), key=lambda sprite: (sprite.z, sprite.rect.centery)):
			# There are no other z=house-bottom sprites in the current project.
			# Draw the extracted static layer at the same point in the z stack.
			if not house_bottom_drawn and sprite.z > LAYERS['house bottom']:
				self._draw_house_bottom(view_rect)
				house_bottom_drawn = True

			if not sprite.rect.colliderect(view_rect):
				continue
			offset_rect = sprite.rect.copy()
			offset_rect.center -= self.offset
			self.display_surface.blit(sprite.image, offset_rect)

		if not house_bottom_drawn:
			self._draw_house_bottom(view_rect)


					# # analytics (só para visualizar melhor)
					# if sprite == player:
					# 	pygame.draw.rect(self.display_surface, 'red', offset_rect, 5)
					# 	hitbox_rect = player.hitbox.copy()
					# 	hitbox_rect.center = offset_rect.center
					# 	pygame.draw.rect(self.display_surface, 'green', hitbox_rect, 5)
					# 	target_pos = offset_rect.center + PLAYER_TOOL_OFFSET[player.status.split('_')[0]]
					# 	pygame.draw.circle(self.display_surface, 'blue', target_pos, 5)