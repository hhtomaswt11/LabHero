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
from teacher_mode import get_teacher_request, build_teacher_save_data
from teacher_access import TeacherAccessMenu


class Game:
	def __init__(self):
		pygame.init()
		self.screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
		pygame.display.set_icon(pygame.image.load(get_resource_path('LabHero-icon.png')))
		pygame.display.set_caption('LabHero')
		self.clock = pygame.time.Clock()
		self.intro = Intro()
		self.teacher_access = TeacherAccessMenu(self.screen)
		self.web_autosave_elapsed = 0.0
		self.teacher_request = get_teacher_request()
		self.teacher_preview_active = False


	async def run_teacher_preview(self, request):
		"""Run an authenticated Teacher session with isolated mission previews.

		A professor may switch targets from Settings without returning to the
		title screen or authenticating again. Every switch still rebuilds a fresh
		teacher save payload and clears the disposable teacher namespace, so one
		preview cannot leak evidence into the next and student progress remains
		untouched.
		"""
		set_save_namespace('teacher')
		self.teacher_preview_active = True
		self.web_autosave_elapsed = 0.0
		current_request = request
		try:
			while current_request is not None:
				mission_id = current_request['mission_id']
				campaign_mode = current_request.get('campaign_mode', 'normal')

				# A mission switch is a new preview, not a continuation of the
				# previous teacher evidence state.
				clear_active_persistent_storage()
				clear_memstore()
				self.level = Level(
					copy.deepcopy(build_teacher_save_data(mission_id, campaign_mode)),
					teacher_target_mission=mission_id,
					teacher_preview=True,
				)
				await self.run()

				# Settings can request another canonical Normal/Easy target. If no
				# switch was requested, run() returned because the professor chose
				# Exit Teacher Preview and we go back to the title screen.
				current_request = getattr(
					self.level.player,
					'teacher_switch_request',
					None,
				)
		finally:
			clear_active_persistent_storage()
			set_save_namespace(None)
			clear_memstore()
			self.teacher_preview_active = False
			self.web_autosave_elapsed = 0.0


	async def intro_run(self):
		# Protected teacher URLs/CLI flags remain a direct administrative fallback.
		# The normal user-facing teacher entry is hidden behind SHIFT+T below.
		if self.teacher_request is not None:
			await self.run_teacher_preview(self.teacher_request)
			self.teacher_request = None

		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					sys.exit()

				if event.type != pygame.KEYDOWN:
					continue

				# A fresh campaign destroys the current save, so SPACE is deliberately
				# a two-step action.  While the confirmation card is open, only a
				# second SPACE confirms and ESC cancels back to the untouched title.
				if self.intro.new_game_confirmation_pending:
					if event.key == pygame.K_ESCAPE:
						self.intro.cancel_new_game_confirmation()
					elif event.key == pygame.K_SPACE:
						self.intro.cancel_new_game_confirmation()
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
					continue

				if event.key == pygame.K_RETURN:
					try:
						data = load_file(get_save_path('data'))
						self.level = Level(copy.deepcopy(data))
					except FileNotFoundError:
						self.level = Level(copy.deepcopy(DEFAULT_INVENTORY_2))
					await self.run()
				elif event.key == pygame.K_SPACE:
					self.intro.request_new_game_confirmation()
				elif event.key == pygame.K_t and (event.mod & pygame.KMOD_SHIFT):
					# Hidden teacher access is intentionally available only from the title
					# screen.  It cannot replace a live student's runtime state mid-mission.
					request = await self.teacher_access.update()
					if request is not None:
						await self.run_teacher_preview(request)

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
			if sys.platform == 'emscripten' and not self.teacher_preview_active:
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
