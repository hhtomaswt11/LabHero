import pygame
from settings import *
from functions import *
from timers import Timer
import time
from math import ceil
from utils import *
from hint_system import HintSystem, create_reward_state


# Maximum distance advanced before checking collisions again.  Keeping this
# below the player hitbox dimensions prevents a low-FPS browser frame from
# jumping completely across a thin collision region (collision tunnelling).
MAX_COLLISION_STEP = 16.0


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
    def __init__(self, pos, group, collision_sprites, tree_sprites, interaction, soil_layer, toggle_shop, desk_menu, yeast_simulator, books, ecoli, inventory2, talk_1, talk_2, talk_3, talk_7, talk_11, talk_16, talk_21, talk_23, talk_25, talk_27, talk_29, talk_32, talk_35, talk_36, talk_37, talk_38, talk_39, talk_40, dialogues, skin_manager=None):
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
        self.character = None
        self.tree_sprites = tree_sprites
        self.interaction = interaction
        self.soil_layer = soil_layer

        	
        # music/audio
        # DEFAULT
        # self.music_bg = pygame.mixer.Sound(MUSIC_NAME)
        # self.music_bg.set_volume(0.07)
        # # self.music_bg.set_volume(0)
        # self.music_bg.play(loops = -1)


        # TURN OFF AUDIO
        self.music_bg = pygame.mixer.Sound(MUSIC_NAME)
        self.music_bg.set_volume(0)
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

    def get_player_state(self):
        facing = self._safe_facing(self.status)
        return {
            'scene': DEFAULT_SCENE_ID,
            'x': float(self.pos.x),
            'y': float(self.pos.y),
            'facing': facing,
            'status': self.status,
            'skin_id': self.current_skin_id
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


            # interaction
            if keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]:
                # timer for tool use
                self.timers['tool_use'].activate()
                self.direction = pygame.math.Vector2()
                self.frame_index = 0

                collided_interaction_sprite = pygame.sprite.spritecollide(self, self.interaction, False) # spritecollide(sprite, group, dokill)
                if collided_interaction_sprite:
                    if collided_interaction_sprite[0].name == 'Mission01':
                        self.talk_1()
                    elif collided_interaction_sprite[0].name == 'Mission02':
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

