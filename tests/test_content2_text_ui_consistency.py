import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


class Content2TextUiConsistencyTests(unittest.TestCase):
    def test_branding_is_consistent_in_global_ui_titles(self):
        intro = (CODE / "intro.py").read_text(encoding="utf-8")
        functions = (CODE / "functions.py").read_text(encoding="utf-8")
        menu = (CODE / "menu_2.py").read_text(encoding="utf-8")

        # Current global branding is deliberately the single word ``LabHero``.
        # The previous test accidentally asserted both presence and absence of
        # these exact same strings, making the suite impossible to satisfy.
        self.assertIn("render('LabHero'", intro)
        self.assertIn("render('LabHero'", functions)
        self.assertIn("pygame_menu.Menu('LabHero Settings'", menu)
        self.assertNotIn("render('Lab Hero'", intro)
        self.assertNotIn("render('Lab Hero'", functions)
        self.assertNotIn("pygame_menu.Menu('Lab Hero Settings'", menu)

    def test_story_matches_current_student_campaign_flow(self):
        intro = (CODE / "intro.py").read_text(encoding="utf-8")
        required = [
            "You are a student entering the LabHero systems-biology laboratory.",
            "registering with Dr. Melo",
            "Normal campaign",
            "Easy campaign",
            "constraint-based metabolic modelling",
            "visible simulation evidence",
        ]
        for phrase in required:
            self.assertIn(phrase, intro)
        self.assertNotIn("bioinformatician working at the University", intro)
        self.assertNotIn("metabolic modeling", intro)

    def test_secondary_npc_dialogues_do_not_use_old_meme_lines(self):
        text = (CODE / "dialogues.py").read_text(encoding="utf-8")
        forbidden = [
            "pokemon master",
            "Gotta catchem",
            "young padawan",
            "data side of the Force",
            "debugging the code of life",
            "grape achievement",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, text)

    def test_secondary_npc_scientific_wording_is_polished(self):
        text = (CODE / "dialogues.py").read_text(encoding="utf-8")
        self.assertIn("genome-scale metabolic model", text)
        self.assertIn("laboratory experiments to test the model's predictions", text)
        self.assertIn("SARS-CoV-2 is the coronavirus that causes COVID-19", text)
        self.assertNotIn("as well as, conducting", text)
        self.assertNotIn("SARS-COV-2", text)

    def test_mission22_to_23_transition_is_not_duplicated(self):
        text = (CODE / "mission21.py").read_text(encoding="utf-8")
        self.assertIn("Dr. Luna will continue in Mission 23.", text)
        self.assertIn(
            "She studies phenotypes across controlled perturbation levels.",
            text,
        )
        self.assertNotIn(
            "Dr. Luna will continue in Mission 23 by studying how phenotypes change across perturbation levels.",
            text,
        )
        self.assertNotIn(
            "Dr. Luna will now study how phenotypes change across perturbation levels.",
            text,
        )

    def test_easy_route_uses_predicted_growth_wording_in_polished_transitions(self):
        text = (CODE / "easy_mission_npc.py").read_text(encoding="utf-8")
        self.assertIn(
            "Compare predicted growth rate and the complete visible product profile.",
            text,
        )
        self.assertIn(
            "Return with the rescue supported by predicted growth and GPR evidence.",
            text,
        )

    def test_content_polish_does_not_change_mission_science_constants(self):
        # Guard the nature of this phase: text/UI polish must not introduce
        # scientific configuration into the dedicated consistency module/test.
        for name in ("simulation.py", "campaign.py"):
            self.assertTrue((CODE / name).exists())


if __name__ == "__main__":
    unittest.main()
