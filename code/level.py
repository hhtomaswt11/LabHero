import pygame 
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
from mission01 import Mission01
from mission02 import Mission02
from mission03 import Mission03
from mission06 import Mission06
from mission07 import Mission07
from mission11 import Mission11
from mission16 import Mission16
from mission21 import Mission21
from mission23 import Mission23
from mission25 import Mission25
from mission27 import Mission27
from mission29 import Mission29
from mission32 import Mission32
from mission35 import Mission35
from mission36 import Mission36
from mission37 import Mission37
from mission38 import Mission38
from mission39 import Mission39
from mission40 import Mission40
from dialogues import Dialogues
from save_load import save_file
from functions import *
from utils import *
from skins import SkinManager
from skin_menu import SkinSelectionMenu
from progression import is_model_unlocked

class Level:
	def __init__(self, load_game):

		# get the display surface
		self.display_surface = pygame.display.get_surface()

		# load the game
		self.load_game = load_game

		# sprite groups
		self.all_sprites = CameraGroup()
		self.collision_sprites = pygame.sprite.Group()
		self.tree_sprites = pygame.sprite.Group()
		self.interaction_sprites = pygame.sprite.Group()

		# Character skin system: load all skin sprite frames once.
		self.skin_manager = SkinManager()

		self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)
		self.setup()

		# MENUS
		self.menu_active = False
		self.desk_active = False
		self.yeast_simulator_active = False
		self.books_active = False
		self.ecoli_active = False
		self.talk_1_active = False
		self.talk_1 = Mission01(self.toggle_talk_1, self.player)
		self.talk_2_active = False
		self.talk_2 = Mission03(self.toggle_talk_2, self.player)
		self.talk_3_active = False
		self.talk_3 = Mission06(self.toggle_talk_3, self.player)
		self.talk_7_active = False
		self.talk_7 = Mission07(self.toggle_talk_7, self.player)
		self.talk_11_active = False
		self.talk_11 = Mission11(self.toggle_talk_11, self.player)
		self.talk_16_active = False
		self.talk_16 = Mission16(self.toggle_talk_16, self.player)
		self.talk_21_active = False
		self.talk_21 = Mission21(self.toggle_talk_21, self.player)
		self.talk_23_active = False
		self.talk_23 = Mission23(self.toggle_talk_23, self.player)
		self.talk_25_active = False
		self.talk_25 = Mission25(self.toggle_talk_25, self.player)
		self.talk_27_active = False
		self.talk_27 = Mission27(self.toggle_talk_27, self.player)
		self.talk_29_active = False
		self.talk_29 = Mission29(self.toggle_talk_29, self.player)
		self.talk_32_active = False
		self.talk_32 = Mission32(self.toggle_talk_32, self.player)
		self.talk_35_active = False
		self.talk_35 = Mission35(self.toggle_talk_35, self.player)
		self.talk_36_active = False
		self.talk_36 = Mission36(self.toggle_talk_36, self.player)
		self.talk_37_active = False
		self.talk_37 = Mission37(self.toggle_talk_37, self.player)
		self.talk_38_active = False
		self.talk_38 = Mission38(self.toggle_talk_38, self.player)
		self.talk_39_active = False
		self.talk_39 = Mission39(self.toggle_talk_39, self.player)
		self.talk_40_active = False
		self.talk_40 = Mission40(self.toggle_talk_40, self.player)
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
		self.skin_menu_active = False
		self.skin_menu = SkinSelectionMenu(self.skin_manager, self.player)
		self.skin_open_key_locked = False

		# sounds
		success_path = get_resource_path('audio/success.ogg')
		self.success = pygame.mixer.Sound(success_path) 
		self.success.set_volume(0.1)

		# music
		# self.music_bg = pygame.mixer.Sound(MUSIC_NAME)
		# self.music_bg.set_volume(0.07)
		# self.music_bg.play(loops = -1)

	def setup(self):
		
		map_path = get_resource_path('data/map_lb.tmx')
		tmx_data = load_pygame(map_path)
		surf_path = get_resource_path('graphics/world/ground_lb.png')

		# house
		for layer in ['HouseFloor', 'HouseFurnitureBottom']:
			for x, y, surf in tmx_data.get_layer_by_name(layer).tiles(): # 'HouseFurnitureBottom' mesmo nome que layers no programa Tiled
				Generic((x* TILE_SIZE, y* TILE_SIZE), surf, self.all_sprites, LAYERS['house bottom'])

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
			Water((x* TILE_SIZE, y* TILE_SIZE), water_frames, self.all_sprites)


		# Trees
		for obj in tmx_data.get_layer_by_name('Trees'):
			Tree(
				pos = (obj.x, obj.y),
				surf = obj.image,
				groups = [self.all_sprites, self.collision_sprites, self.tree_sprites],
				name = obj.name,
				player_add = self.player_add,
				all_sprites = self.all_sprites)

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
		for obj in tmx_data.get_layer_by_name('Player'):
			if obj.name == 'Start':
				self.player = Player(
					pos = (obj.x,obj.y),
					group = self.all_sprites,
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
					skin_manager = self.skin_manager
					# music = self.music_bg
					)
			
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

			# if obj.name == 'Oscar':
			# 	Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)

			# if obj.name == 'Vitor':
			# 	Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
				
			if obj.name == 'Coffee':
				Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)
			

		if carter_reveal_pos is not None:
			CarterRevealSprite(
				pos = carter_reveal_pos,
				groups = self.all_sprites,
				player = self.player)

		Generic(
			pos = (0,0),
			surf = pygame.image.load(surf_path).convert_alpha(),
			groups = self.all_sprites,
			z = LAYERS['ground'])

	def player_add(self, item):
		self.player.item_inventory[item] += 1
		self.success.play()

	def toggle_shop(self):
		self.menu_active = not self.menu_active

	def toggle_talk_1(self):
		self.talk_1_active = not self.talk_1_active

	def toggle_talk_2(self):
		self.talk_2_active = not self.talk_2_active
	
	def toggle_talk_3(self):
		self.talk_3_active = not self.talk_3_active

	def toggle_talk_7(self):
		self.talk_7_active = not self.talk_7_active

	def toggle_talk_11(self):
		self.talk_11_active = not self.talk_11_active

	def toggle_talk_16(self):
		self.talk_16_active = not self.talk_16_active

	def toggle_talk_21(self):
		self.talk_21_active = not self.talk_21_active

	def toggle_talk_23(self):
		self.talk_23_active = not self.talk_23_active

	def toggle_talk_25(self):
		self.talk_25_active = not self.talk_25_active

	def toggle_talk_27(self):
		self.talk_27_active = not self.talk_27_active

	def toggle_talk_29(self):
		self.talk_29_active = not self.talk_29_active

	def toggle_talk_32(self):
		self.talk_32_active = not self.talk_32_active

	def toggle_talk_35(self):
		self.talk_35_active = not self.talk_35_active

	def toggle_talk_36(self):
		self.talk_36_active = not self.talk_36_active

	def toggle_talk_37(self):
		self.talk_37_active = not self.talk_37_active

	def toggle_talk_38(self):
		self.talk_38_active = not self.talk_38_active

	def toggle_talk_39(self):
		self.talk_39_active = not self.talk_39_active

	def toggle_talk_40(self):
		self.talk_40_active = not self.talk_40_active

	def toggle_dialogue(self):
		self.dialogues_active = not self.dialogues_active

	def desk_menu(self):
		self.desk_active = not self.desk_active

	def yeast_simulator_menu(self):
		if not is_model_unlocked('yeast_iMM904', self.player.missions_completed):
			animation_text_save('Complete Mission 35 to unlock the yeast simulator.', time=2500)
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
			self.dialogues_active
		)

	def handle_skin_menu_shortcut(self):
		keys = pygame.key.get_pressed()
		c_pressed = keys[pygame.K_c]
		if c_pressed and not self.skin_open_key_locked and not self.any_modal_active():
			self.skin_menu.open()
			self.skin_menu_active = True
		self.skin_open_key_locked = c_pressed

	def plant_collision(self):
		if self.soil_layer.plant_sprites: # se houver plantas
			for plant in self.soil_layer.plant_sprites.sprites():
				if plant.harvestable and plant.rect.colliderect(self.player.hitbox): # se colidir com o player
					self.player_add(plant.plant_type)
					plant.kill()
					Particle(
						pos = plant.rect.topleft,
						surf = plant.image,
						groups = self.all_sprites,
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
		if self.menu_active:
			# self.menu.update()
			await self.menu.update()

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
			self.all_sprites.update(dt)
			self.plant_collision()

		


class CameraGroup(pygame.sprite.Group):
	def __init__(self):
		super().__init__()
		self.display_surface = pygame.display.get_surface()
		self.offset = pygame.math.Vector2()

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
		for sprite in sorted(self.sprites(), key=lambda sprite: (sprite.z, sprite.rect.centery)):
			if not sprite.rect.colliderect(view_rect):
				continue
			offset_rect = sprite.rect.copy()
			offset_rect.center -= self.offset
			self.display_surface.blit(sprite.image, offset_rect)


					# # analytics (só para visualizar melhor)
					# if sprite == player:
					# 	pygame.draw.rect(self.display_surface, 'red', offset_rect, 5)
					# 	hitbox_rect = player.hitbox.copy()
					# 	hitbox_rect.center = offset_rect.center
					# 	pygame.draw.rect(self.display_surface, 'green', hitbox_rect, 5)
					# 	target_pos = offset_rect.center + PLAYER_TOOL_OFFSET[player.status.split('_')[0]]
					# 	pygame.draw.circle(self.display_surface, 'blue', target_pos, 5)