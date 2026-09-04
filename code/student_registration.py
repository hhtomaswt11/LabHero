
import pygame
import pygame_menu

from async_menu import run_menu
from functions import animation_text_save
from options_values import mytheme
from save_load import save_file
from student_identity import validate_student_name
from utils import get_resource_path
from campaign import CampaignContext, STUDENT_CAMPAIGN_MODES
from hint_system import (
    SCORE_BY_HINT_LEVEL,
    WRONG_ANSWER_PENALTY,
    initial_keys_for_campaign,
)


class StudentRegistrationMenu:
    """One-time student-name registration for a campaign."""

    def __init__(self, player, close_callback, campaign_changed_callback=None):
        self.player = player
        self.close_callback = close_callback
        self.campaign_changed_callback = campaign_changed_callback
        self.display_surface = pygame.display.get_surface()
        self.font_path = get_resource_path('font/LycheeSoda.ttf')

    async def update(self):
        candidate = {"name": None, "mode": None}

        entry = pygame_menu.Menu(
            "Student Registration",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        entry.add.label(
            "Before starting your missions, Dr. Melo needs to register your name.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.vertical_margin(15)
        normal_keys = initial_keys_for_campaign('normal')
        easy_keys = initial_keys_for_campaign('easy')
        entry.add.label(
            "Dr. Melo: Hint keys are limited, and the starting budget depends on your route.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.label(
            f"Normal starts with {normal_keys['bronze']} Bronze, {normal_keys['silver']} Silver, "
            f"and {normal_keys['gold']} Gold keys. Easy starts with {easy_keys['bronze']} Bronze, "
            f"{easy_keys['silver']} Silver, and {easy_keys['gold']} Gold keys.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.label(
            "Hint keys are limited. Unlocking a hint spends a key and lowers that mission's score.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.label(
            f"Mission score: {SCORE_BY_HINT_LEVEL[0]} points with no hints; then "
            f"{SCORE_BY_HINT_LEVEL[1]}, {SCORE_BY_HINT_LEVEL[2]}, or "
            f"{SCORE_BY_HINT_LEVEL[3]} points as you unlock the three hint levels.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.label(
            f"Every incorrect final-answer submission costs {WRONG_ANSWER_PENALTY} point too, "
            "including typos. Read the evidence carefully before you submit; a mission score can fall to 0.",
            max_char=-1,
            wordwrap=True,
        )
        entry.add.vertical_margin(25)
        name_widget = entry.add.text_input(
            "Full name: ",
            default="",
            maxchar=60,
            textinput_id="student_name",
        )
        error_label = entry.add.label("", font_color="firebrick")

        def review_name():
            valid, normalized, error = validate_student_name(name_widget.get_value())
            if not valid:
                error_label.set_title(error)
                return
            candidate["name"] = normalized
            entry.disable()

        def cancel_entry():
            entry.disable()

        entry.add.button("Review name", review_name)
        entry.add.button("Cancel", cancel_entry)
        await run_menu(entry, self.display_surface)

        if candidate["name"] is None:
            self.close_callback()
            return

        name_review = {"accepted": False}
        confirm_name = pygame_menu.Menu(
            "Confirm Student",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        confirm_name.add.label("Your name will be recorded as:")
        confirm_name.add.vertical_margin(15)
        confirm_name.add.label(candidate["name"], font_size=42, font_name=self.font_path)
        confirm_name.add.vertical_margin(15)
        confirm_name.add.label(
            "After final registration, the name cannot be changed during this campaign.",
            max_char=-1,
            wordwrap=True,
        )

        def accept_name():
            name_review["accepted"] = True
            confirm_name.disable()

        confirm_name.add.button("Confirm name", accept_name)
        confirm_name.add.button("Cancel", confirm_name.disable)
        await run_menu(confirm_name, self.display_surface)

        if not name_review["accepted"]:
            self.close_callback()
            return

        mode_menu = pygame_menu.Menu(
            "Choose Campaign Mode",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        mode_menu.add.label(
            "Choose the route for this campaign. The mode is locked after confirmation.",
            max_char=-1,
            wordwrap=True,
        )
        mode_menu.add.vertical_margin(20)
        mode_menu.add.label("Normal - full 40-mission campaign (maximum score: 200)")
        mode_menu.add.label("Easy - curated 11-mission classroom route, about 2 hours (maximum score: 55)")
        mode_menu.add.vertical_margin(25)

        def choose_mode(mode):
            if mode in STUDENT_CAMPAIGN_MODES:
                candidate["mode"] = mode
                mode_menu.disable()

        mode_menu.add.button("Normal", lambda: choose_mode("normal"))
        mode_menu.add.button("Easy", lambda: choose_mode("easy"))
        mode_menu.add.button("Cancel", mode_menu.disable)
        await run_menu(mode_menu, self.display_surface)

        if candidate["mode"] is None:
            self.close_callback()
            return

        context = CampaignContext(candidate["mode"])
        final = {"confirmed": False}
        final_menu = pygame_menu.Menu(
            "Confirm Campaign",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        final_menu.add.label(f"Student: {candidate['name']}", font_name=self.font_path)
        final_menu.add.label(f"Mode: {candidate['mode'].title()}")
        selected_keys = initial_keys_for_campaign(candidate['mode'])
        final_menu.add.label(
            f"Starting hint keys: {selected_keys['bronze']} Bronze / "
            f"{selected_keys['silver']} Silver / {selected_keys['gold']} Gold",
            max_char=-1,
            wordwrap=True,
        )
        final_menu.add.label(
            f"Missions: {context.mission_count}    Maximum score: {context.max_score}",
            max_char=-1,
            wordwrap=True,
        )
        final_menu.add.vertical_margin(20)
        final_menu.add.label(
            "Name and campaign mode cannot be changed after this confirmation.",
            max_char=-1,
            wordwrap=True,
        )

        def accept_campaign():
            if self.player.register_student_campaign(candidate["name"], candidate["mode"]):
                if self.campaign_changed_callback is not None:
                    self.campaign_changed_callback()
                save_file(self.player.get_save_data())
                animation_text_save(
                    f"{candidate['mode'].title()} campaign registered"
                )
                final["confirmed"] = True
            final_menu.disable()

        final_menu.add.button("Confirm campaign", accept_campaign)
        final_menu.add.button("Cancel", final_menu.disable)
        await run_menu(final_menu, self.display_surface)

        self.close_callback()
