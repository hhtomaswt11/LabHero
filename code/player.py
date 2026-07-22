import pygame
from settings import *
from functions import *
from timers import Timer
import time
from utils import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, group, collision_sprites, tree_sprites, interaction, soil_layer, toggle_shop, desk_menu, books, ecoli, inventory2, talk_1, talk_2, talk_3, talk_7, talk_11, talk_16, talk_21, talk_26, dialogues, skin_manager=None):
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
            self.player_state
        ) = self._unpack_save_data(inventory2)
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
        self.talk_26 = talk_26
        self.desk_menu = desk_menu
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
        """Read both old and new save formats.

        Old format:
        [player_name, results, missions_activated, missions_completed]

        New format:
        [player_name, results, missions_activated, missions_completed, player_state]
        """
        data = data or DEFAULT_INVENTORY_2

        player_name = data[0] if len(data) > 0 else DEFAULT_INVENTORY_2[0]
        results = data[1] if len(data) > 1 else []
        missions_activated = data[2] if len(data) > 2 else []
        missions_completed = data[3] if len(data) > 3 else []
        player_state = data[4] if len(data) > 4 and isinstance(data[4], dict) else DEFAULT_PLAYER_STATE.copy()

        return player_name, results, missions_activated, missions_completed, player_state

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
        """Centralized save payload used by all save_file calls."""
        return [
            self.player_name,
            self.results,
            self.missions_activated,
            self.missions_completed,
            self.get_player_state()
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
        if not self.skin_manager.is_unlocked(skin_id):
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
                    elif collided_interaction_sprite[0].name == 'Mission26':
                        self.talk_26()
                    elif collided_interaction_sprite[0].name == 'Desk':
                        animation_text_save('... please wait ...', time=100)
                        self.desk_menu()
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
        
        # horizontal movement
        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self.collision('horizontal')

        # vertical movement
        self.pos.y += self.direction.y * self.speed * dt
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

