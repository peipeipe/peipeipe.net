import unittest

from extract_onsen_composition import PROMPT, clean_springs
from fetch_foursquare_checkins import extract_composition_hint, merge_place
from merge_onsen_composition import build_entries, merge_places, normalize_place


class MultiSpringCompositionTest(unittest.TestCase):
    def setUp(self):
        self.photos = {
            1: {
                "index": 1,
                "fsq_id": "venue-1",
                "place_name": "二源泉の施設",
                "address": "長野県",
                "date": "2026-09-01",
                "photo_url": "https://example.com/first.jpg",
            },
            2: {
                "index": 2,
                "fsq_id": "venue-1",
                "place_name": "二源泉の施設",
                "address": "長野県",
                "date": "2026-09-01",
                "photo_url": "https://example.com/second.jpg",
            },
        }
        self.group = {
            "name": "二源泉の施設",
            "photos": list(self.photos.values()),
        }

    def test_extracts_each_spring_with_its_own_photo(self):
        result = {
            "is_composition": True,
            "springs": [
                {"photo_indexes": [1], "spring_name": "第一源泉", "ph": 7.4},
                {"photo_indexes": [2], "spring_name": "第二源泉", "ph": 9.0},
            ],
        }

        springs = clean_springs(result, self.group)

        self.assertEqual([spring["spring_name"] for spring in springs], ["第一源泉", "第二源泉"])
        self.assertEqual([spring["photo_indexes"] for spring in springs], [[1], [2]])

    def test_build_and_merge_keep_two_springs_under_one_place(self):
        extracted = {
            "places": [{
                "springs": [
                    {"photo_indexes": [1], "spring_name": "第一源泉", "ph": 7.4},
                    {"photo_indexes": [2], "spring_name": "第二源泉", "ph": 9.0},
                ],
            }],
        }

        incoming, used_urls = build_entries(extracted, self.photos)
        places = merge_places([], incoming)

        self.assertEqual(len(places), 1)
        self.assertEqual(len(places[0]["springs"]), 2)
        self.assertEqual(places[0]["springs"][1]["source_photos"], ["https://example.com/second.jpg"])
        self.assertEqual(used_urls, {"https://example.com/first.jpg", "https://example.com/second.jpg"})

    def test_legacy_flat_place_is_normalized(self):
        place = normalize_place({
            "fsq_id": "venue-1",
            "name": "旧形式",
            "spring_name": "第一源泉",
            "ph": 7.4,
        })

        self.assertEqual(place["fsq_id"], "venue-1")
        self.assertEqual(place["springs"], [{"spring_name": "第一源泉", "ph": 7.4}])

    def test_different_named_springs_are_not_merged_when_a_photo_is_shared(self):
        existing = [{
            "fsq_id": "venue-1",
            "name": "一枚に二源泉が写る施設",
            "springs": [{
                "spring_name": "第一源泉",
                "source_photos": ["https://example.com/shared.jpg"],
            }],
        }]
        incoming = [{
            "fsq_id": "venue-1",
            "name": "一枚に二源泉が写る施設",
            "springs": [{
                "spring_name": "第二源泉",
                "source_photos": ["https://example.com/shared.jpg"],
            }],
        }]

        places = merge_places(existing, incoming)

        self.assertEqual([spring["spring_name"] for spring in places[0]["springs"]], ["第一源泉", "第二源泉"])

    def test_checkin_comment_can_supply_a_composition_hint(self):
        shout = "茶褐色のお湯。\n成分表: 第一源泉 / 第二源泉"

        self.assertEqual(extract_composition_hint(shout), "第一源泉 / 第二源泉")

    def test_composition_hint_survives_a_later_checkin_without_a_marker(self):
        existing = {"last_checkin_at": "2026-09-01", "composition_hint": "第一源泉 / 第二源泉"}
        fresh = {"last_checkin_at": "2026-09-02", "user_comment": "また来た", "photos": []}

        merged = merge_place(existing, fresh, photo_limit=None)

        self.assertEqual(merged["composition_hint"], "第一源泉 / 第二源泉")

    def test_prompt_distinguishes_analysis_completion_from_document_date(self):
        self.assertIn('analyzed_on は「分析終了年月日」', PROMPT)
        self.assertIn("分析書右上の発行日・作成日", PROMPT)
        self.assertIn("調査及び試験年月日", PROMPT)


if __name__ == "__main__":
    unittest.main()
