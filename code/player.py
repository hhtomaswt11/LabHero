import pygame
from settings import *
from functions import *
from timers import Timer
import time
from math import ceil
from utils import *
from hint_system import (
    HintSystem,
    create_reward_state,
    golden_egg_gold_reward_for_campaign,
)
from student_identity import infer_name_confirmed, validate_student_name
from save_load import save_file
from campaign import (
    CampaignContext,
    STUDENT_CAMPAIGN_MODES,
    normalize_campaign_mode,
)


# Maximum distance advanced before checking collisions again.  Keeping this
# below the player hitbox dimensions prevents a low-FPS browser frame from
# jumping completely across a thin collision region (collision tunnelling).
MAX_COLLISION_STEP = 16.0

MISSION_START_INTERACTIONS = {
    'Mission01', 'Mission02', 'Mission03', 'Mission07', 'Mission11',
    'Mission16', 'Mission21', 'Mission23', 'Mission25', 'Mission27',
    'Mission29', 'Mission32', 'Final', 'Vale', 'Voss', 'Umbra', 'Morbus',
    'Mortis',
}



def _movement_substep_plan(distance, max_step=MAX_COLLISION_STEP):
    """Return (number_of_steps, distance_per_step) for one movement axis.

    Normal 60 FPS movement stays a single step.  Long browser frames are split
    into several small advances so collision checks cover the path travelled,
    not only the final position.
    """
    distance = float(distance)
    if distance == 0.0:
        return 0, 0.0
    steps = max(1, ceil(abs(distance) / float(max_step)))
    return steps, distance / steps

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, group, collision_sprites, tree_sprites, interaction, soil_layer, toggle_shop, desk_menu, yeast_simulator, books, ecoli, inventory2, talk_1, talk_2, talk_3, talk_7, talk_11, talk_16, talk_21, talk_23, talk_25, talk_27, talk_29, talk_32, talk_35, talk_36, talk_37, talk_38, talk_39, talk_40, dialogues, student_registration, skin_manager=None):
        super().__init__(group)

        self.skin_manager = skin_manager
        self.current_skin_id = getattr(skin_manager, 'default_skin_id', 'default')
        self.import_assets()
        self.status = 'down_idle'
        self.frame_index = 0

        #general setup
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center = pos)
        self.z = LAYERS['main']

        # Canonical map spawnpoint. Keep the Tiled ``Start`` position supplied
        # by Level before a persisted save is allowed to restore the player
        # elsewhere. Settings -> Back to Spawnpoint always returns here, so
        # moving the Start object in Tiled automatically updates the feature.
        self.spawnpoint = pygame.math.Vector2(pos)

        # movement 
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 750

        # collision
        self.hitbox = self.rect.copy().inflate((-126,-70)) # tuplo w,h
        self.collision_sprites = collision_sprites

        # Área de interação independente da hitbox
        self.interaction_area = pygame.Rect(25,25, 50, 50)  # Tamanho pequeno para detectar objetos próximos

        # timers
        self.timers = {
            'tool_use': Timer(350, self.use_tool)
        }

        # ENTER interaction release guard.  Player interaction historically
        # used pygame.key.get_pressed(), so the same physical ENTER that
        # confirmed/closed another screen could leak into the first map frame
        # and immediately trigger a nearby NPC/simulator/coffee interaction.
        # Start locked so ENTER used on the title-screen Continue action must be
        # released once before it can interact with the map.
        self.interaction_enter_locked = True

        self.item_inventory = DEFAULT_INVENTORY[0]

        (
            self.player_name,
            self.results,
            self.missions_activated,
            self.missions_completed,
            self.player_state,
            reward_state
        ) = self._unpack_save_data(inventory2)
        self.hint_system = HintSystem(reward_state)
        self.reward_state = self.hint_system.state
        self.name_confirmed = infer_name_confirmed(
            self.player_name,
            self.missions_activated,
            self.missions_completed,
            self.player_state,
            DEFAULT_INVENTORY_2[0],
        )
        # Campaign mode lives inside player_state so the six-field save schema
        # remains unchanged. Historic saves have no key and therefore migrate
        # safely to Normal.
        self.campaign_mode = normalize_campaign_mode(
            self.player_state.get('campaign_mode', 'normal')
            if isinstance(self.player_state, dict) else 'normal'
        )
        self.final_results_seen = bool(
            self.player_state.get('final_results_seen', False)
            if isinstance(self.player_state, dict) else False
        )
        self.golden_egg_collected = bool(
            self.player_state.get('golden_egg_collected', False)
            if isinstance(self.player_state, dict) else False
        )
        self._apply_player_state(self.player_state)

        # web-only: when True, the outer LabHero.run() loop breaks back to intro_run()
        self.restart_to_intro = False

        # interaction
        self.toggle_shop = toggle_shop
        self.talk_1 = talk_1
        self.talk_2 = talk_2
        self.talk_3 = talk_3
        self.talk_7 = talk_7
        self.talk_11 = talk_11
        self.talk_16 = talk_16
        self.talk_21 = talk_21
        self.talk_23 = talk_23
        self.talk_25 = talk_25
        self.talk_27 = talk_27
        self.talk_29 = talk_29
        self.talk_32 = talk_32
        self.talk_35 = talk_35
        self.talk_36 = talk_36
        self.talk_37 = talk_37
        self.talk_38 = talk_38
        self.talk_39 = talk_39
        self.talk_40 = talk_40
        self.desk_menu = desk_menu
        self.yeast_simulator = yeast_simulator
        self.books = books
        self.ecoli = ecoli
        self.dialogues = dialogues
        self.student_registration = student_registration
        self.character = None
        self.tree_sprites = tree_sprites
        self.interaction = interaction
        self.soil_layer = soil_layer

        	
        # music/audio
        # Keep the runtime level aligned with the Settings slider default.
        self.music_bg = pygame.mixer.Sound(MUSIC_NAME)
        self.music_bg.set_volume(
            (DEFAULT_MUSIC_VOLUME_PERCENT / 100.0) * MUSIC_VOLUME_SCALE
        )
        self.music_bg.play(loops = -1)

        coffee_path = get_resource_path('audio/coffee.ogg')
        self.coffee = pygame.mixer.Sound(coffee_path)
        self.coffee.set_volume(0.05)


    def _unpack_save_data(self, data):
        """Read historic saves and the current six-field save format.

        Pre-P.1 saves have no reward_state. Existing completed missions in those
        saves are marked legacy-unscored because their historic hint usage is
        unknowable. A New Game has no completed missions, so it naturally starts
        with a fresh 15/10/5 key inventory and no legacy entries.
        """
        data = data or DEFAULT_INVENTORY_2

        player_name = data[0] if len(data) > 0 else DEFAULT_INVENTORY_2[0]
        results = data[1] if len(data) > 1 else []
        missions_activated = data[2] if len(data) > 2 else []
        missions_completed = data[3] if len(data) > 3 else []
        player_state = data[4] if len(data) > 4 and isinstance(data[4], dict) else DEFAULT_PLAYER_STATE.copy()

        if len(data) > 5 and isinstance(data[5], dict):
            reward_state = data[5]
        else:
            reward_state = create_reward_state(legacy_completed=missions_completed)

        return (
            player_name,
            results,
            missions_activated,
            missions_completed,
            player_state,
            reward_state,
        )

    def _safe_facing(self, facing):
        facing = str(facing or 'down').split('_')[0]
        return facing if facing in ('up', 'down', 'left', 'right') else 'down'

    def _apply_player_state(self, player_state):
        """Place the player at the saved position/orientation when possible."""
        if not isinstance(player_state, dict):
            return

        # The project currently has one playable scene. If a future save points
        # to a different scene, keep the normal spawn point instead of placing
        # the player in the wrong map.
        if player_state.get('scene', DEFAULT_SCENE_ID) != DEFAULT_SCENE_ID:
            return

        x = player_state.get('x')
        y = player_state.get('y')
        if x is not None and y is not None:
            try:
                self.pos.update(float(x), float(y))
                self.rect.center = (round(self.pos.x), round(self.pos.y))
                self.hitbox.center = self.rect.center
            except (TypeError, ValueError):
                pass

        facing = self._safe_facing(player_state.get('facing') or player_state.get('status'))
        saved_status = str(player_state.get('status') or f'{facing}_idle')

        if saved_status not in self.animations:
            saved_status = f'{facing}_idle'
        if saved_status not in self.animations:
            saved_status = 'down_idle'

        # Load as idle so the player appears facing the same direction but does
        # not resume mid-step.
        if not saved_status.endswith('_idle'):
            saved_status = f'{self._safe_facing(saved_status)}_idle'

        self.status = saved_status
        self.frame_index = 0
        self.image = self.animations[self.status][self.frame_index]

        saved_skin_id = player_state.get('skin_id')
        if saved_skin_id:
            self.set_skin(saved_skin_id)

        self.update_interaction_area()
        self.get_target_pos()

    def return_to_spawnpoint(self):
        """Return safely to the canonical Tiled Start position.

        This changes only the player's map position/orientation. Campaign
        progress, rewards, skin and every other save field remain untouched.
        """
        if not hasattr(self, 'spawnpoint'):
            return False

        self.pos.update(self.spawnpoint.x, self.spawnpoint.y)
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.hitbox.center = self.rect.center
        self.direction.update(0, 0)

        # A deterministic idle facing mirrors a fresh New Game at Start and
        # avoids carrying a mid-walk animation across the teleport.
        if 'down_idle' in self.animations:
            self.status = 'down_idle'
        else:
            facing = self._safe_facing(self.status)
            idle_status = f'{facing}_idle'
            if idle_status in self.animations:
                self.status = idle_status
        self.frame_index = 0
        if self.status in self.animations and self.animations[self.status]:
            self.image = self.animations[self.status][0]

        self.character = None
        self.update_interaction_area()
        self.get_target_pos()
        return True


    def get_campaign_context(self):
        """Return the current campaign policy without duplicating progression rules."""
        return CampaignContext(mode=self.campaign_mode)

    def is_mission_in_campaign(self, mission_id):
        return self.get_campaign_context().includes_mission(mission_id)

    def is_mission_unlocked(self, mission_id):
        return self.get_campaign_context().is_mission_unlocked(
            mission_id, self.missions_completed
        )

    def get_player_state(self):
        facing = self._safe_facing(self.status)
        return {
            'scene': DEFAULT_SCENE_ID,
            'x': float(self.pos.x),
            'y': float(self.pos.y),
            'facing': facing,
            'status': self.status,
            'skin_id': self.current_skin_id,
            'name_confirmed': bool(self.name_confirmed),
            'campaign_mode': self.campaign_mode,
            'final_results_seen': bool(self.final_results_seen),
            'golden_egg_collected': bool(self.golden_egg_collected)
        }

    def get_save_data(self):
        """Centralized six-field save payload used by all save_file calls.

        Mission completion already funnels through this method across all 40
        missions. During the staged rollout, only missions whose hint UI is
        integrated may score; earlier completions become legacy-unscored rather
        than receiving an unverifiable 5/5.
        """
        self.hint_system.sync_completed_missions(self.missions_completed)
        self.reward_state = self.hint_system.state
        return [
            self.player_name,
            self.results,
            self.missions_activated,
            self.missions_completed,
            self.get_player_state(),
            self.hint_system.to_dict()
        ]



    def collect_golden_egg(self):
        """Collect the one-time Golden Egg reward while the campaign can use it.

        Once the selected campaign is complete, hint keys have no remaining
        mission-scoring purpose.  In that case the easter egg stays visible and
        uncollected so the late discovery gets a small narrative response rather
        than consuming a now-useless reward.
        """
        if self.golden_egg_collected:
            return False

        if self.get_campaign_context().is_campaign_complete(self.missions_completed):
            animation_text_save(
                'Too late! You should have found me before finishing the campaign. What a shame!',
                time=3600,
            )
            return False

        reward = golden_egg_gold_reward_for_campaign(self.campaign_mode)
        self.golden_egg_collected = True
        self.hint_system.award_keys('gold', reward)
        self.reward_state = self.hint_system.state
        save_file(self.get_save_data())
        animation_text_save(
            f'Golden Egg discovered! You found {reward} Gold Key'
            f'{"s" if reward != 1 else ""}.',
            time=3200,
        )
        return True

    def register_student_campaign(self, value, campaign_mode):
        """Atomically lock student identity and student-facing campaign mode.

        Registration is only allowed before a campaign has started.  This keeps
        both the name and Normal/Easy route immutable for the lifetime of the
        save while preserving historic saves that were already registered.
        """
        if self.name_confirmed or self.missions_activated or self.missions_completed:
            return False
        valid, normalized, _error = validate_student_name(value)
        mode = normalize_campaign_mode(campaign_mode)
        if not valid or mode not in STUDENT_CAMPAIGN_MODES:
            return False
        self.player_name = normalized
        self.campaign_mode = mode
        # New campaigns receive a route-sized hint budget.  This happens only
        # during the one-time pre-mission registration, so no existing campaign
        # scores/hints are retroactively altered.
        self.hint_system.set_campaign_initial_keys(mode)
        self.reward_state = self.hint_system.state
        self.name_confirmed = True
        return True

    def register_student_name(self, value):
        """Backwards-compatible Normal registration helper used by older tests/code."""
        return self.register_student_campaign(value, self.campaign_mode)

    def use_tool(self):
        for tree in self.tree_sprites.sprites():
            if tree.rect.collidepoint(self.target_pos):
                tree.damage()
       

    def get_target_pos(self):
        self.target_pos = self.rect.center + PLAYER_TOOL_OFFSET[self.status.split('_')[0]] # status[0] (direção do jogador) para identificar o a posição da ferramenta no dict

    
        
    def import_assets(self):
        if self.skin_manager is not None:
            self.animations = self.skin_manager.get_animations(self.current_skin_id)
            return

        # Fallback used only if Player is created without SkinManager.
        self.animations = {'up': [], 'down': [], 'left': [], 'right': [],
                           'right_idle': [], 'left_idle': [], 'up_idle': [], 'down_idle': []}
        
        for animation in self.animations.keys():
            path_1 = get_resource_path('graphics/character/')
            full_path = path_1 + animation
            self.animations[animation] = import_folder(full_path)

    def set_skin(self, skin_id):
        if self.skin_manager is None or not self.skin_manager.is_valid_skin(skin_id):
            return False
        if not self.skin_manager.is_unlocked(skin_id, self.missions_completed):
            return False

        center = self.rect.center if hasattr(self, 'rect') else None
        self.current_skin_id = skin_id
        self.animations = self.skin_manager.get_animations(skin_id)

        if self.status not in self.animations:
            self.status = 'down_idle'
        self.frame_index = 0
        self.image = self.animations[self.status][self.frame_index]

        if center is not None:
            self.rect = self.image.get_rect(center=center)
            self.hitbox.center = self.rect.center
            self.update_interaction_area()
            self.get_target_pos()
        return True
    
    def animate(self, dt):
        self.frame_index += 4 * dt
        if self.frame_index >= len(self.animations[self.status]):
            self.frame_index = 0
        self.image = self.animations[self.status][int(self.frame_index)]

    def block_interaction_until_enter_release(self):
        """Ignore map ENTER interactions until RETURN/KP_ENTER are released.

        Menus may use ENTER to confirm a choice while Player.update() is paused.
        Level calls this guard when returning from a modal so that confirmation
        key cannot be reused as a world interaction on the next frame.
        """
        self.interaction_enter_locked = True

    def _interaction_enter_pressed_once(self, keys):
        """Return True only for a fresh map-interaction ENTER press."""
        enter_pressed = bool(keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER])
        if not enter_pressed:
            self.interaction_enter_locked = False
            return False
        if self.interaction_enter_locked:
            return False
        self.interaction_enter_locked = True
        return True

    def update_interaction_area(self):
        # Posiciona a área de interação ligeiramente à frente do jogador com base na direção
        if self.status.startswith('up'):
            self.interaction_area.midbottom = self.hitbox.midtop
        elif self.status.startswith('down'):
            self.interaction_area.midtop = self.hitbox.midbottom
        elif self.status.startswith('left'):
            self.interaction_area.midright = self.hitbox.midleft
        elif self.status.startswith('right'):
            self.interaction_area.midleft = self.hitbox.midright

    def input(self):

        self.update_interaction_area()

        keys = pygame.key.get_pressed()

        if not self.timers['tool_use'].active:
            
            # directions
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.direction.y = -1
                self.status = 'up'

            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.direction.y = 1
                self.status = 'down'
            else:
                self.direction.y = 0

            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.direction.x = 1
                self.status = 'right'

            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.direction.x = -1
                self.status = 'left'
            else:
                self.direction.x = 0
            
            if keys[pygame.K_m]:
                self.toggle_shop()

            # MENUS (ATALHOS PARA TESTES)

            # if keys[pygame.K_k]:
            #     self.desk_menu()
            
            # if keys[pygame.K_b]:
            #     self.books()

            # if keys[pygame.K_t]:
            #     self.talk_2()


            # interaction: edge-triggered and release-gated so ENTER used
            # to leave another screen cannot leak into the world interaction.
            if self._interaction_enter_pressed_once(keys):
                # timer for tool use
                self.timers['tool_use'].activate()
                self.direction = pygame.math.Vector2()
                self.frame_index = 0

                collided_interaction_sprite = pygame.sprite.spritecollide(self, self.interaction, False) # spritecollide(sprite, group, dokill)
                if collided_interaction_sprite:
                    interaction_name = collided_interaction_sprite[0].name
                    if interaction_name in MISSION_START_INTERACTIONS and not self.name_confirmed:
                        animation_text_save(
                            'Please register your name with Dr. Alves before starting missions.'
                        )
                    elif (
                        interaction_name in MISSION_START_INTERACTIONS
                        and not self.get_campaign_context().interaction_is_available(interaction_name)
                    ):
                        animation_text_save(
                            'This researcher is not part of your Easy campaign route.',
                            time=2500,
                        )
                    elif interaction_name == 'Alves':
                        if self.name_confirmed:
                            self.character = 'Alves'
                            self.dialogues()
                        else:
                            self.student_registration()
                    elif interaction_name == 'Mission01':
                        self.talk_1()
                    elif interaction_name == 'Mission02':
                        self.talk_2()
                    elif collided_interaction_sprite[0].name == 'Mission03':
                        self.talk_3()
                    elif collided_interaction_sprite[0].name == 'Mission07':
                        self.talk_7()
                    elif collided_interaction_sprite[0].name == 'Mission11':
                        self.talk_11()
                    elif collided_interaction_sprite[0].name == 'Mission16':
                        self.talk_16()
                    elif collided_interaction_sprite[0].name == 'Mission21':
                        self.talk_21()
                    elif collided_interaction_sprite[0].name == 'Mission23':
                        self.talk_23()
                    elif collided_interaction_sprite[0].name == 'Mission25':
                        self.talk_25()
                    elif collided_interaction_sprite[0].name == 'Mission27':
                        self.talk_27()
                    elif collided_interaction_sprite[0].name == 'Mission29':
                        self.talk_29()
                    elif collided_interaction_sprite[0].name == 'Mission32':
                        self.talk_32()
                    elif collided_interaction_sprite[0].name == 'Final':
                        self.talk_35()
                    elif collided_interaction_sprite[0].name == 'Vale':
                        self.talk_36()
                    elif collided_interaction_sprite[0].name == 'Voss':
                        self.talk_37()
                    elif collided_interaction_sprite[0].name == 'Umbra':
                        self.talk_38()
                    elif collided_interaction_sprite[0].name == 'Morbus':
                        self.talk_39()
                    elif collided_interaction_sprite[0].name == 'Mortis':
                        self.talk_40()
                    elif interaction_name == 'GoldenEgg':
                        if self.collect_golden_egg():
                            collided_interaction_sprite[0].kill()
                    elif collided_interaction_sprite[0].name == 'Desk':
                        animation_text_save('... please wait ...', time=100)
                        self.desk_menu()
                    elif collided_interaction_sprite[0].name == 'YeastSimulator':
                        self.yeast_simulator()
                    elif collided_interaction_sprite[0].name == 'Books':
                        self.books()
                    elif collided_interaction_sprite[0].name == 'Ecoli':
                        self.ecoli()
                    else:
                        # Deteta colisão apenas com objetos dentro da área de interação
                        for sprite in self.interaction:
                            if self.interaction_area.colliderect(sprite.hitbox):
                                if sprite.name == 'Coffee':
                                    self.coffee.play()
                                    self.speed = 900
                                if sprite.name in ('Sequeira', 'Pacheco', 'Nuno', 'Fernanda', 'Emanuel', 'Alexandre', 'Capela', 'Marta', 'Oscar', 'Miguel'):
                                    self.character = sprite.name
                                    self.dialogues() # add variable with name character to change message and id
                                    
    def get_status(self):
        # if player not moving add idle
        if self.direction.magnitude() == 0:
            self.status = self.status.split('_')[0] + '_idle'

        # tool use
        if self.timers['tool_use'].active:
            self.status = self.status.split('_')[0] # + '_' + self.selected_tool

    def update_timers(self):
        for timer in self.timers.values():
            timer.update()
        
    def move(self, dt):
        # normalize vector (diagonal speed same as horizontal/vertical speed)
        if self.direction.magnitude() > 0:
            self.direction = self.direction.normalize()

        # A slow browser frame can represent tens or even hundreds of pixels of
        # movement at once.  Checking collisions only at the final position can
        # therefore skip completely over a thin wall.  Split each axis into
        # bounded advances and keep the existing axis-separated collision rules
        # after every advance.
        horizontal_distance = self.direction.x * self.speed * dt
        horizontal_steps, horizontal_step = _movement_substep_plan(horizontal_distance)
        for _ in range(horizontal_steps):
            self.pos.x += horizontal_step
            self.hitbox.centerx = round(self.pos.x)
            self.rect.centerx = self.hitbox.centerx
            self.collision('horizontal')

        vertical_distance = self.direction.y * self.speed * dt
        vertical_steps, vertical_step = _movement_substep_plan(vertical_distance)
        for _ in range(vertical_steps):
            self.pos.y += vertical_step
            self.hitbox.centery = round(self.pos.y)
            self.rect.centery = self.hitbox.centery
            self.collision('vertical')

    def collision(self, direction):
        for sprite in self.collision_sprites.sprites():
            if hasattr(sprite, 'hitbox'):
                if sprite.hitbox.colliderect(self.hitbox):
                    if direction == 'horizontal':
                        if self.direction.x > 0: #moving right
                            self.hitbox.right = sprite.hitbox.left
                        if self.direction.x < 0: #moving left
                            self.hitbox.left = sprite.hitbox.right
                        self.rect.centerx = self.hitbox.centerx
                        self.pos.x = self.hitbox.centerx

                    if direction == 'vertical':
                        if self.direction.y > 0: #moving down
                            self.hitbox.bottom = sprite.hitbox.top
                        if self.direction.y < 0: #moving up
                            self.hitbox.top = sprite.hitbox.bottom
                        self.rect.centery = self.hitbox.centery
                        self.pos.y = self.hitbox.centery

    def update(self, dt):
        self.input()
        self.get_status()
        self.update_timers()
        self.get_target_pos()
        self.move(dt)
        self.animate(dt)

