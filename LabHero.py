import sys
import os
import asyncio
import copy

sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import pygame

from settings import *
from level import Level
from intro import Intro
from save_load import *
from functions import animation_text_save, drain_animations
from utils import *


class Game:
	def __init__(self):
		pygame.init()
		self.screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
		pygame.display.set_icon(pygame.image.load(get_resource_path('LabHero-icon.png')))
		pygame.display.set_caption('Lab Hero')
		self.clock = pygame.time.Clock()
		self.intro = Intro()
		self.web_autosave_elapsed = 0.0


	async def intro_run(self):
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					sys.exit()

				if pygame.key.get_pressed()[pygame.K_RETURN]:
					try:
						data = load_file(get_save_path('data'))
						self.level = Level(copy.deepcopy(data))
					except FileNotFoundError:
						self.level = Level(copy.deepcopy(DEFAULT_INVENTORY_2))
					await self.run()
				elif pygame.key.get_pressed()[pygame.K_SPACE]:
					# New Game is the one explicit action that must discard durable
					# browser progress. Back to Title and page refresh preserve it.
					if sys.platform == 'emscripten':
						clear_web_persistent_storage()
					else:
						for filename in ('data.txt', 'results.txt', 'simulation_file.txt'):
							path = get_save_path(filename)
							if os.path.exists(path):
								os.remove(path)
					self.level = Level(copy.deepcopy(DEFAULT_INVENTORY_2))
					self.web_autosave_elapsed = 0.0
					await self.run()

			self.intro.run()
			if self.intro.pending is not None:
				coro_factory = self.intro.pending
				self.intro.pending = None
				await coro_factory()
			pygame.display.update()
			await drain_animations()
			await asyncio.sleep(0)


	async def run(self):
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					animation_text_save('Saving Game', fullscreen=True)
					await drain_animations()
					save_file(self.level.player.get_save_data())
					pygame.quit()
					sys.exit()

			dt = self.clock.tick() / 1000
			await self.level.run(dt)

			# localStorage writes are synchronous and the main save is small.
			# A five-second web autosave keeps position/profile/reward progress
			# current even when the player refreshes or closes the tab. Mission
			# evidence artifacts are persisted immediately by save_load.py.
			if sys.platform == 'emscripten':
				self.web_autosave_elapsed += dt
				if self.web_autosave_elapsed >= 5.0:
					save_file(self.level.player.get_save_data())
					self.web_autosave_elapsed = 0.0

			pygame.display.update()
			await drain_animations()
			await asyncio.sleep(0)

			if self.level.player.restart_to_intro:
				pygame.mixer.stop()
				return


async def main():
	game = Game()
	await game.intro_run()


if __name__ == '__main__':
	asyncio.run(main())
