"""Lightweight, spoiler-free mission guidance for student exploration.

The tracker deliberately derives its state from the existing campaign/save data
instead of introducing a second progression system.  It never stores anything
and never inspects mission evidence/answers; it only tells the player which
researcher owns the current/next mission.
"""

from campaign import normalize_mission_id

MISSION_TITLES = {
    '01': 'Into the Microbial World',
    '02': 'Restore Growth Without Glucose',
    '03': 'The Conditional Essentiality Screen',
    '04': 'Growth-Coupled Ethanol Production',
    '05': 'Context-Dependent Anaerobic Ethanol Design',
    '06': 'Controlled Multi-Knockout Challenge',
    '07': 'Objective Matters',
    '08': 'Constraint Impact on the Optimal Solution',
    '09': 'Integrated Environment-and-Gene Design',
    '10': 'Two-Gene Redundancy and Flux Redirection',
    '11': 'Anaerobic Secretion Fingerprint',
    '12': 'Constraint-Driven Succinate Byproducts',
    '13': 'Primary Objective and Flux Parsimony',
    '14': 'Byproduct Trade-off Screening',
    '15': 'Product-Growth Viability Audit',
    '16': 'Context-Dependent Carbon Rescue',
    '17': 'Essential Uptake Routes',
    '18': 'Binding Export Constraints',
    '19': 'Re-optimisation vs Minimal Adjustment',
    '20': 'Context-Specific Export Robustness',
    '21': 'Compensatory Flux Comparison',
    '22': 'Phenotype Equivalence Audit',
    '23': 'Nutrient Sensitivity Curve',
    '24': 'Export Capacity Thresholds',
    '25': 'Context-Dependent Gene Essentiality',
    '26': 'Genotype-Environment Interaction Curve',
    '27': 'Metabolic Bypass Rescue',
    '28': 'Bypass Dependency Mapping',
    '29': 'Isoenzyme Redundancy Screen',
    '30': 'Redundancy Breakdown Threshold',
    '31': 'Environmental Suppression Matrix',
    '32': 'Respiratory Complex Cut-Set',
    '33': 'Reference-State Adjustment Footprint',
    '34': 'Shared-Subunit Equivalence Audit',
    '35': 'E. coli Final Systems Certification',
    '36': 'Oxygen-Capped Fermentation Onset',
    '37': 'Fermentation Redundancy Cut Set',
    '38': 'Background-Dependent Compensation Audit',
    '39': 'Pathway Bypass Rescue',
    '40': 'Final Rescue Robustness Certification',
}


MISSION_RESEARCHERS = {
    **{mid: 'Dr. Martinez' for mid in ('01', '02')},
    **{mid: 'Dr. Silva' for mid in ('03', '04', '05')},
    '06': 'Dr. Carter',
    **{mid: 'Dr. Nova' for mid in ('07', '08', '09', '10')},
    **{mid: 'Dr. Almeida' for mid in ('11', '12', '13', '14', '15')},
    **{mid: 'Dr. Rio' for mid in ('16', '17', '18', '19', '20')},
    **{mid: 'Dr. Vega' for mid in ('21', '22')},
    **{mid: 'Dr. Luna' for mid in ('23', '24')},
    **{mid: 'Dr. Smith' for mid in ('25', '26')},
    **{mid: 'Dr. Ribeiro' for mid in ('27', '28')},
    **{mid: 'Dr. Li' for mid in ('29', '30', '31')},
    **{mid: 'Dr. Chen' for mid in ('32', '33', '34')},
    '35': 'Dr. Richter',
    '36': 'Vale',
    '37': 'Voss',
    '38': 'Umbra',
    '39': 'Morbus',
    '40': 'Mortis',
}


def _normalised_set(values):
    return {
        normalize_mission_id(value)
        for value in (values or ())
        if normalize_mission_id(value) is not None
    }


def build_quest_tracker_snapshot(player):
    """Return a small, read-only guidance snapshot for the current campaign.

    The active mission is the first campaign mission that is activated but not
    completed.  If none is active, the tracker points to the first incomplete
    mission in the selected route.  This works for both Normal and Easy without
    inventing fake completion for missions omitted by Easy mode.
    """
    context = player.get_campaign_context()
    sequence = tuple(context.mission_sequence or ())
    completed = _normalised_set(getattr(player, 'missions_completed', ()))
    activated = _normalised_set(getattr(player, 'missions_activated', ()))

    completed_in_mode = tuple(mid for mid in sequence if mid in completed)
    active_mission = next(
        (mid for mid in sequence if mid in activated and mid not in completed),
        None,
    )

    if active_mission is not None:
        researcher = MISSION_RESEARCHERS.get(active_mission, 'the mission researcher')
        return {
            'status': 'active',
            'mission_id': active_mission,
            'title': MISSION_TITLES.get(active_mission, f'Mission {active_mission}'),
            'researcher': researcher,
            'objective': (
                f'Follow the Mission {active_mission} briefing, complete the experiment, '
                f'then return to {researcher}.'
            ),
            'completed': len(completed_in_mode),
            'total': len(sequence),
            'mode': context.mode,
        }

    if context.is_campaign_complete(completed):
        return {
            'status': 'complete',
            'mission_id': None,
            'title': 'Campaign Complete',
            'researcher': None,
            'objective': 'All missions in this campaign are complete. Continue exploring freely.',
            'completed': len(completed_in_mode),
            'total': len(sequence),
            'mode': context.mode,
        }

    next_mission = next((mid for mid in sequence if mid not in completed), None)
    if next_mission is None:
        # Defensive fallback for malformed/migrated saves. The campaign-complete
        # branch above should normally handle this state.
        return {
            'status': 'complete',
            'mission_id': None,
            'title': 'Campaign Complete',
            'researcher': None,
            'objective': 'No further mission is available in this campaign.',
            'completed': len(completed_in_mode),
            'total': len(sequence),
            'mode': context.mode,
        }

    researcher = MISSION_RESEARCHERS.get(next_mission, 'the next researcher')
    if next_mission == context.first_mission:
        objective = (
            f'Speak with {researcher} in the first laboratory to begin Mission {next_mission}.'
        )
    else:
        objective = f'Speak with {researcher} to begin Mission {next_mission}.'

    return {
        'status': 'available',
        'mission_id': next_mission,
        'title': MISSION_TITLES.get(next_mission, f'Mission {next_mission}'),
        'researcher': researcher,
        'objective': objective,
        'completed': len(completed_in_mode),
        'total': len(sequence),
        'mode': context.mode,
    }


class QuestTrackerOverlay:
    """Small Q/Esc exploration overlay; no pygame-menu or nested event loop."""

    def __init__(self, player):
        import pygame

        from settings import SCREEN_HEIGHT, SCREEN_WIDTH
        from utils import get_resource_path

        self.player = player
        self.display_surface = pygame.display.get_surface()
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font_title = pygame.font.Font(font_path, 42)
        self.font_heading = pygame.font.Font(font_path, 29)
        self.font_body = pygame.font.Font(font_path, 25)
        self.font_small = pygame.font.Font(font_path, 20)
        self.key_locks = {
            pygame.K_q: False,
            pygame.K_ESCAPE: False,
        }

    def open(self):
        import pygame

        keys = pygame.key.get_pressed()
        for key in self.key_locks:
            self.key_locks[key] = keys[key]

    def _pressed_once(self, key):
        import pygame

        keys = pygame.key.get_pressed()
        pressed = keys[key]
        once = pressed and not self.key_locks.get(key, False)
        self.key_locks[key] = pressed
        return once

    def update(self):
        """Return ``close`` when Q or Esc is newly pressed."""
        import pygame

        q_pressed = self._pressed_once(pygame.K_q)
        escape_pressed = self._pressed_once(pygame.K_ESCAPE)
        return 'close' if q_pressed or escape_pressed else None

    def _wrap_text(self, text, max_width):
        words = str(text).split()
        lines = []
        current = ''
        for word in words:
            candidate = word if not current else f'{current} {word}'
            if self.font_body.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw_hint(self, show_final_results=False):
        """Persistent exploration shortcuts shown during free movement."""
        import pygame

        entries = [
            'Q  Quest Tracker',
            'E  Inventory',
        ]
        if show_final_results:
            entries.append('F  Final Results')

        rendered = [self.font_small.render(entry, False, 'white') for entry in entries]
        width = max(item.get_width() for item in rendered)
        line_height = max(item.get_height() for item in rendered)
        panel_height = 12 + len(rendered) * line_height + (len(rendered) - 1) * 6 + 12
        panel = pygame.Rect(0, 0, width + 20, panel_height)
        panel.topright = (self.screen_width - 16, 14)

        hint = pygame.Surface(panel.size, pygame.SRCALPHA)
        hint.fill((0, 0, 0, 155))
        self.display_surface.blit(hint, panel.topleft)

        y = panel.y + 12
        for rendered_text in rendered:
            self.display_surface.blit(
                rendered_text,
                rendered_text.get_rect(centerx=panel.centerx, top=y),
            )
            y += line_height + 6

    def draw(self):
        import pygame

        snapshot = build_quest_tracker_snapshot(self.player)

        dim = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 105))
        self.display_surface.blit(dim, (0, 0))

        panel = pygame.Rect(190, 170, 900, 360)
        pygame.draw.rect(self.display_surface, (242, 242, 236), panel, border_radius=10)
        pygame.draw.rect(self.display_surface, (40, 40, 40), panel, 4, border_radius=10)

        title = self.font_title.render('Quest Tracker', False, 'black')
        self.display_surface.blit(title, (panel.x + 30, panel.y + 22))

        progress = self.font_small.render(
            f"{snapshot['mode'].title()}  |  Progress: {snapshot['completed']} / {snapshot['total']}",
            False,
            (70, 70, 70),
        )
        self.display_surface.blit(progress, (panel.right - progress.get_width() - 30, panel.y + 35))

        if snapshot['status'] == 'active':
            section = 'Current Mission'
            mission_line = f"Mission {snapshot['mission_id']} - {snapshot['title']}"
            next_label = 'Next step'
        elif snapshot['status'] == 'available':
            section = 'No mission active'
            mission_line = f"Next: Mission {snapshot['mission_id']} - {snapshot['title']}"
            next_label = 'Next objective'
        else:
            section = 'Campaign Complete'
            mission_line = snapshot['title']
            next_label = 'Status'

        section_surf = self.font_heading.render(section, False, (30, 95, 90))
        self.display_surface.blit(section_surf, (panel.x + 34, panel.y + 95))

        mission_surf = self.font_body.render(mission_line, False, 'black')
        self.display_surface.blit(mission_surf, (panel.x + 34, panel.y + 138))

        label_surf = self.font_heading.render(next_label, False, (30, 95, 90))
        self.display_surface.blit(label_surf, (panel.x + 34, panel.y + 190))

        y = panel.y + 232
        for line in self._wrap_text(snapshot['objective'], panel.width - 68):
            body = self.font_body.render(line, False, 'black')
            self.display_surface.blit(body, (panel.x + 34, y))
            y += 31

        controls = self.font_small.render('Q / Esc  close', False, (70, 70, 70))
        self.display_surface.blit(controls, (panel.x + 34, panel.bottom - 35))
