import unittest

from generate_onsen_composition_pr import build_report


class OnsenCompositionPrReportTest(unittest.TestCase):
    def setUp(self):
        self.before = {
            "stats": {
                "places": 1,
                "springs": 1,
                "composition_photos": 1,
                "not_composition_photos": 4,
                "unreadable_photos": 0,
            },
            "places": [{
                "fsq_id": "existing",
                "name": "既存温泉",
                "springs": [{"spring_name": "既存源泉", "ph": 7.0}],
            }],
        }
        self.after = {
            "stats": {
                "places": 2,
                "springs": 2,
                "composition_photos": 3,
                "not_composition_photos": 5,
                "unreadable_photos": 1,
            },
            "places": self.before["places"] + [{
                "fsq_id": "new-place",
                "name": "新しい温泉",
                "address": "長野県",
                "checkin_date": "2026-09-03",
                "springs": [{
                    "confidence": "medium",
                    "spring_name": "新源泉",
                    "spring_quality": "ナトリウム−塩化物温泉",
                    "source_temp_c": 42.5,
                    "ph": 7.4,
                    "dissolved_solids_mg_kg": 1234,
                    "cations": [
                        {"name": "カルシウムイオン", "mg_kg": 20},
                        {"name": "ナトリウムイオン", "mg_kg": 400},
                    ],
                    "anions": [{"name": "塩化物イオン", "mg_kg": 500}],
                    "notes": "一部に反射あり",
                    "source_photos": ["https://example.com/photo?a=1&b=2"],
                }],
            }],
        }

    def test_report_contains_composition_photo_and_review_information(self):
        title, body = build_report(self.before, self.after, "[OK] 新源泉")

        self.assertEqual(title, "温泉成分表を更新: 新しい温泉")
        self.assertIn("| 新規施設 | 1 |", body)
        self.assertIn("| 要注意（信頼度 medium / low） | 1 |", body)
        self.assertIn("ナトリウムイオン 400mg/kg", body)
        self.assertIn("新しい温泉 新源泉 根拠写真 1", body)
        self.assertIn("https://example.com/photo?a=1&amp;b=2", body)
        self.assertIn("> 注意: 一部に反射あり", body)
        self.assertIn("[OK] 新源泉", body)
        self.assertIn("| 成分表ではなかった写真 | 5（+1） |", body)
        self.assertIn("- [ ] 写真と泉質名・源泉名が一致している", body)

    def test_existing_spring_lists_changed_fields(self):
        after = {
            **self.before,
            "places": [{
                "fsq_id": "existing",
                "name": "既存温泉",
                "springs": [{"spring_name": "既存源泉", "ph": 7.2}],
            }],
        }

        title, body = build_report(self.before, after)

        self.assertEqual(title, "温泉成分表を更新: 既存温泉")
        self.assertIn("## 更新: 既存温泉", body)
        self.assertIn("変更項目: pH", body)
        self.assertIn("| 更新した既存源泉 | 1 |", body)

    def test_no_composition_result_gets_an_explanatory_title(self):
        after = {
            **self.before,
            "stats": {**self.before["stats"], "not_composition_photos": 5},
        }

        title, body = build_report(self.before, after)

        self.assertEqual(title, "温泉写真の解析結果（成分表なし）")
        self.assertIn("追加・更新できる温泉分析書はありませんでした", body)
        self.assertIn("| 成分表ではなかった写真 | 5（+1） |", body)


if __name__ == "__main__":
    unittest.main()
