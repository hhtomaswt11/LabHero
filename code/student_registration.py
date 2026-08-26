
import pygame
import pygame_menu

from async_menu import run_menu
from functions import animation_text_save
from options_values import mytheme
from save_load import save_file
from student_identity import validate_student_name


class StudentRegistrationMenu:
    """One-time student-name registration for a campaign."""

    def __init__(self, player, close_callback):
        self.player = player
        self.close_callback = close_callback
        self.display_surface = pygame.display.get_surface()

    async def update(self):
        candidate = {"name": None}

        entry = pygame_menu.Menu(
            "Student Registration",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        entry.add.label(
            "Before starting your missions, Dr. Alves needs to register your name.",
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

        result = {"confirmed": False}
        confirm = pygame_menu.Menu(
            "Confirm Student",
            1280,
            720,
            onclose=lambda: None,
            theme=mytheme,
        )
        confirm.add.label("Your name will be recorded as:")
        confirm.add.vertical_margin(15)
        confirm.add.label(candidate["name"], font_size=42)
        confirm.add.vertical_margin(15)
        confirm.add.label(
            "After confirmation, the name cannot be changed during this campaign.",
            max_char=-1,
            wordwrap=True,
        )

        def accept():
            if self.player.register_student_name(candidate["name"]):
                save_file(self.player.get_save_data())
                animation_text_save("Student name registered")
                result["confirmed"] = True
            confirm.disable()

        def go_back():
            confirm.disable()

        confirm.add.button("Confirm", accept)
        confirm.add.button("Back", go_back)
        await run_menu(confirm, self.display_surface)

        self.close_callback()
