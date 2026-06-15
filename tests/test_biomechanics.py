import unittest

from logic.biomechanics import fuzja_sensorow


class SensorFusionTest(unittest.TestCase):
    def test_rewards_ready_position_when_ball_is_not_detected(self):
        result = fuzja_sensorow(
            {"typ_odbicia": None, "pilka_wykryta": False},
            {"kat_kolana": 120.0, "komunikat_kolana": "Pozycja niska, prawidlowa"},
        )

        self.assertEqual(result["ocena_fuzji"], 30)
        self.assertIn("Dobra pozycja", result["komunikat_fuzji"])
        self.assertFalse(result["brak_pracy_nog"])

    def test_scores_perfect_lower_pass_contact(self):
        result = fuzja_sensorow(
            {
                "typ_odbicia": "DOLNE",
                "pilka_wykryta": True,
                "nadgarstki_zlaczone": True,
                "kat_lokcia_l": 150.0,
            },
            {
                "kolana_proste": False,
                "kat_kolana": 120.0,
                "zamach_wykryty": True,
                "komunikat_kolana": "Pozycja niska, prawidlowa",
            },
        )

        self.assertEqual(result["ocena_fuzji"], 100)
        self.assertEqual(result["typ_odbicia"], "DOLNE")
        self.assertFalse(result["brak_pracy_nog"])
        self.assertIn("Doskonałe odbicie", result["komunikat_fuzji"])

    def test_flags_contact_with_straight_knees(self):
        result = fuzja_sensorow(
            {
                "typ_odbicia": "DOLNE",
                "pilka_wykryta": True,
                "nadgarstki_zlaczone": True,
            },
            {
                "kolana_proste": True,
                "kat_kolana": 179.0,
                "zamach_wykryty": False,
                "komunikat_kolana": "Zbyt wysoka pozycja",
            },
        )

        self.assertTrue(result["brak_pracy_nog"])
        self.assertEqual(result["ocena_fuzji"], 42)
        self.assertIn("bardziej zaangażować nogi", result["komunikat_fuzji"])


if __name__ == "__main__":
    unittest.main()

