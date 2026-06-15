import unittest
from types import SimpleNamespace

from logic.coach_engine import VolleyballPostureEvaluator, calculate_angle


def point(x, y, visibility=1.0):
    return SimpleNamespace(x=x, y=y, visibility=visibility)


def body_points_for_knee_angle(left_ankle, right_ankle):
    return {
        "lewe_biodro": point(0.0, 0.0),
        "lewe_kolano": point(0.0, 1.0),
        "lewa_kostka": left_ankle,
        "prawe_biodro": point(1.0, 0.0),
        "prawe_kolano": point(1.0, 1.0),
        "prawa_kostka": right_ankle,
        "lewy_nadgarstek": point(0.45, 1.2),
        "prawy_nadgarstek": point(0.55, 1.2),
        "lewy_lokiec": point(0.35, 1.0),
        "prawy_lokiec": point(0.65, 1.0),
        "lewe_ramie": point(0.0, 0.7),
        "prawe_ramie": point(1.0, 0.7),
    }


class CalculateAngleTest(unittest.TestCase):
    def test_returns_right_angle(self):
        angle = calculate_angle(point(1, 0), point(0, 0), point(0, 1))

        self.assertAlmostEqual(angle, 90.0)

    def test_returns_straight_angle(self):
        angle = calculate_angle(point(-1, 0), point(0, 0), point(1, 0))

        self.assertAlmostEqual(angle, 180.0)

    def test_normalizes_reflex_angle(self):
        angle = calculate_angle(point(1, 0), point(0, 0), point(0, -1))

        self.assertAlmostEqual(angle, 90.0)


class VolleyballPostureEvaluatorTest(unittest.TestCase):
    def evaluator_for_knee_tests(self):
        return VolleyballPostureEvaluator(
            ema_alpha=1.0,
            knee_low_on=0.0,
            knee_low_off=0.0,
            elbow_warn_on=0.0,
            elbow_warn_off=0.0,
            hands_warn_on=10.0,
            hands_warn_off=10.0,
            platform_warn_on=-10.0,
            platform_warn_off=-10.0,
        )

    def test_warns_when_knees_are_too_straight(self):
        evaluator = self.evaluator_for_knee_tests()
        points = body_points_for_knee_angle(point(0.0, 2.0), point(1.0, 2.0))

        correct, message, score = evaluator.evaluate(points)

        self.assertFalse(correct)
        self.assertIn("Ugnij kolana", message)
        self.assertLess(score, 100)

    def test_accepts_bent_knees_when_other_warnings_are_disabled(self):
        evaluator = self.evaluator_for_knee_tests()
        points = body_points_for_knee_angle(point(0.8, 1.0), point(0.2, 1.0))

        correct, message, score = evaluator.evaluate(points)

        self.assertTrue(correct)
        self.assertEqual(message, "Dobra platforma do odbicia dolnego")
        self.assertEqual(score, 100)


if __name__ == "__main__":
    unittest.main()

