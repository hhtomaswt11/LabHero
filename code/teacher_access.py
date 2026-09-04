"""Hidden title-screen Teacher Access UI and server-side authentication bridge.

No teacher secret is embedded in the Pygbag bundle.  In the browser the entered
credentials are sent only as an HTTP Basic Authorization header to the same-
origin ``/teacher-auth`` endpoint protected by nginx.  Desktop development may
optionally validate against LABHERO_TEACHER_USER/LABHERO_TEACHER_PASSWORD from
the local environment.
"""

import asyncio
import hmac
import os
import sys

import pygame
import pygame_menu

from async_menu import run_menu
from options_values import mytheme
from teacher_mode import (
    TEACHER_CAMPAIGN_MODES,
    build_teacher_request,
    teacher_missions_for_mode,
)


TEACHER_AUTH_ENDPOINT = "/teacher-auth"
DEFAULT_TEACHER_USER = "teacher"


def _release_teacher_text_input_focus_now():
    """Release pygame/Pygbag text-input focus before leaving the auth form.

    Pygbag bridges pygame text input through a hidden browser textarea.  If a
    pygame-menu form is disabled while that textarea is still focused, Firefox
    can repeatedly exchange focus/blur messages with the WASM runtime.  Do the
    release synchronously in the button callback, before the menu is disabled.
    """
    try:
        pygame.key.stop_text_input()
    except Exception:
        pass

    if sys.platform == "emscripten":
        try:
            from platform import window

            blur_active = window.eval(
                """(() => {
                    const active = document.activeElement;
                    if (active && typeof active.blur === 'function') active.blur();
                })"""
            )
            blur_active()
        except Exception:
            # Focus release is a browser-compatibility guard, not a reason to
            # make Teacher Access unusable if a browser lacks the bridge.
            pass


async def _settle_teacher_text_input_focus():
    """Give the browser two turns to process the blur before network I/O."""
    _release_teacher_text_input_focus_now()
    await asyncio.sleep(0)
    if sys.platform == "emscripten":
        await asyncio.sleep(0)


async def authenticate_teacher_credentials(username, password):
    """Return ``(ok, message)`` without persisting either credential.

    Web authentication is performed by nginx.  The JavaScript helper is built
    once by ``eval`` and receives credentials as function arguments, so user
    input is never interpolated into executable JavaScript source.
    """
    username = str(username or "").strip()
    password = str(password or "")
    if not username or not password:
        return False, "Enter the teacher username and password."

    if sys.platform == "emscripten":
        try:
            from platform import window

            # Do NOT await a JavaScript Promise directly from Pygbag/Pyodide.
            # In Firefox that bridge can stall after pygame-menu releases its
            # hidden textarea, leaving the submit button greyed out forever.
            # Start an ordinary asynchronous XMLHttpRequest in JavaScript, let
            # its callbacks update a tiny transient status object, and poll that
            # object cooperatively from Python while yielding to the browser.
            start_auth = window.eval(
                """((username, password, endpoint) => {
                    window.__labheroTeacherAuthStatus = -999;

                    try {
                        const raw = `${username}:${password}`;
                        const bytes = new TextEncoder().encode(raw);
                        let binary = '';
                        for (const byte of bytes) binary += String.fromCharCode(byte);
                        const token = btoa(binary);

                        const request = new XMLHttpRequest();
                        request.open('HEAD', endpoint, true);
                        request.timeout = 8000;
                        request.setRequestHeader('Authorization', `Basic ${token}`);
                        request.onload = () => {
                            window.__labheroTeacherAuthStatus = request.status;
                        };
                        request.onerror = () => {
                            window.__labheroTeacherAuthStatus = -1;
                        };
                        request.ontimeout = () => {
                            window.__labheroTeacherAuthStatus = 0;
                        };
                        request.onabort = () => {
                            window.__labheroTeacherAuthStatus = 0;
                        };
                        request.send();
                    } catch (error) {
                        window.__labheroTeacherAuthStatus = -1;
                    }
                })"""
            )
            poll_auth = window.eval(
                """(() => Number(
                    typeof window.__labheroTeacherAuthStatus === 'number'
                        ? window.__labheroTeacherAuthStatus
                        : -1
                ))"""
            )
            clear_auth = window.eval(
                """(() => { delete window.__labheroTeacherAuthStatus; })"""
            )

            start_auth(username, password, TEACHER_AUTH_ENDPOINT)
            status = -999
            # XMLHttpRequest has its own 8 s timeout.  The Python-side bound is
            # a second safety net in case a browser never dispatches callbacks.
            for _ in range(240):
                status = int(poll_auth())
                if status != -999:
                    break
                await asyncio.sleep(0.05)
            if status == -999:
                status = 0
            try:
                clear_auth()
            except Exception:
                pass
        except Exception:
            return False, "Teacher authentication service is unavailable."

        if status == 200:
            return True, ""
        if status == 401:
            return False, "Invalid teacher credentials."
        if status == 0:
            return False, "Teacher authentication timed out. Try again."
        if status == -1:
            return False, "Teacher authentication service is unavailable."
        return False, f"Teacher authentication failed (HTTP {status})."

    # Desktop Teacher Access is mainly for local development.  Keep credentials
    # outside the repository exactly as deploy.sh does for the Web deployment.
    expected_user = os.environ.get("LABHERO_TEACHER_USER", DEFAULT_TEACHER_USER)
    expected_password = os.environ.get("LABHERO_TEACHER_PASSWORD")
    if not expected_password:
        return False, (
            "Desktop Teacher Access needs LABHERO_TEACHER_PASSWORD in the environment."
        )
    valid = (
        hmac.compare_digest(username, str(expected_user))
        and hmac.compare_digest(password, str(expected_password))
    )
    return (True, "") if valid else (False, "Invalid teacher credentials.")


class TeacherAccessMenu:
    """Collect Teacher credentials once, then reuse that in-memory session.

    Authentication is intentionally session-only: it is never written to
    localStorage/save files and disappears on page refresh/restart.  This keeps
    repeated classroom mission jumps convenient without embedding a secret or
    creating a durable browser login.
    """

    def __init__(self, display_surface):
        self.display_surface = display_surface
        self.session_authenticated = False

    def end_session(self):
        """Forget the transient Teacher authentication for this page/runtime."""
        self.session_authenticated = False

    async def update(self):
        error_message = ""
        username_default = DEFAULT_TEACHER_USER

        while True:
            selection = {
                "mode": None,
                "cancelled": False,
                "logout": False,
            }
            menu = pygame_menu.Menu(
                "Teacher Access",
                1280,
                720,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
            )
            menu.add.label(
                "Private teacher preview. Student progress is never loaded or modified.",
                max_char=-1,
                wordwrap=True,
            )
            menu.add.label(
                "Use the same mission number the student sees. Easy keeps canonical IDs (01, 03, 06, ...).",
                max_char=-1,
                wordwrap=True,
                font_size=24,
            )
            menu.add.vertical_margin(15)

            # Every Teacher Access form contains at least the mission-number
            # text input. A previous Teacher form/switch deliberately stops text
            # input before leaving Pygbag, so re-arm it on every fresh form.
            try:
                pygame.key.start_text_input()
            except Exception:
                pass

            username_widget = None
            password_widget = None
            if self.session_authenticated:
                menu.add.label(
                    "Teacher session authenticated for this page. Choose another preview without signing in again.",
                    max_char=-1,
                    wordwrap=True,
                    font_size=24,
                    font_color=(40, 120, 40),
                )
            else:
                username_widget = menu.add.text_input(
                    "Username: ",
                    default=username_default,
                    maxchar=64,
                    textinput_id="teacher_username",
                )
                password_widget = menu.add.text_input(
                    "Password: ",
                    default="",
                    maxchar=128,
                    password=True,
                    textinput_id="teacher_password",
                )

            mission_widget = menu.add.text_input(
                "Mission number: ",
                default="1",
                maxchar=2,
                input_type=pygame_menu.locals.INPUT_INT,
                textinput_id="teacher_mission",
            )
            menu.add.label(
                error_message,
                max_char=-1,
                wordwrap=True,
                font_color="firebrick",
                font_size=24,
            )
            menu.add.vertical_margin(10)

            def close_form():
                # Capture values while widgets are alive, then release the
                # browser textarea before disabling pygame-menu.
                if username_widget is not None:
                    selection["username"] = str(
                        username_widget.get_value() or ""
                    ).strip()
                else:
                    selection["username"] = DEFAULT_TEACHER_USER

                if password_widget is not None:
                    selection["password"] = str(
                        password_widget.get_value() or ""
                    )
                else:
                    selection["password"] = ""

                selection["mission"] = mission_widget.get_value()
                _release_teacher_text_input_focus_now()
                menu.disable()

            def choose(mode):
                selection["mode"] = mode
                close_form()

            def cancel():
                selection["cancelled"] = True
                close_form()

            def logout():
                selection["logout"] = True
                close_form()

            menu.add.button("Open Normal Preview", lambda: choose("normal"))
            menu.add.button("Open Easy Preview", lambda: choose("easy"))
            if self.session_authenticated:
                menu.add.button(
                    "End Teacher Session",
                    logout,
                    background_color=(150, 60, 60),
                )
            menu.add.button("Cancel", cancel, background_color=(70, 70, 70))

            await run_menu(menu, self.display_surface)
            await _settle_teacher_text_input_focus()

            if selection["logout"]:
                self.end_session()
                return None
            if selection["cancelled"] or selection["mode"] not in TEACHER_CAMPAIGN_MODES:
                return None

            mode = selection["mode"]
            username = selection.get("username", "")
            password = selection.get("password", "")
            mission_value = selection.get("mission", "")
            request = build_teacher_request(mission_value, mode, source="title")
            if request is None:
                available = ", ".join(teacher_missions_for_mode(mode))
                error_message = (
                    f"Mission {mission_value} is not part of the {mode.title()} route. "
                    f"Available missions: {available}."
                )
                username_default = username or DEFAULT_TEACHER_USER
                continue

            # One successful server-side authentication unlocks only this
            # in-memory TeacherAccessMenu instance. It is not persisted and
            # therefore disappears on page reload/restart.
            if self.session_authenticated:
                return request

            ok, error_message = await authenticate_teacher_credentials(
                username, password
            )
            # Drop the Python-side reference immediately after the request.
            selection["password"] = ""
            password = ""
            if ok:
                self.session_authenticated = True
                return request
            username_default = username or DEFAULT_TEACHER_USER
