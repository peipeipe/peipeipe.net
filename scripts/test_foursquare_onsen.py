import unittest

from fetch_foursquare_checkins import (
    HOT_SPRING_CATEGORY_ID,
    NOT_ONSEN_FSQ_IDS,
    build_places_from_checkins,
    category_label_matches_onsen,
    comment_matches_onsen,
    merge_with_existing,
)


class OnsenCheckinsTest(unittest.TestCase):
    def checkin(self, timestamp, comment='', photo='photo', venue_id='hotel'):
        return {
            'createdAt': timestamp,
            'shout': comment,
            'photos': [photo],
            'venue': {
                'id': venue_id,
                'name': 'ホテル',
                'location': {'lat': 36, 'lng': 138},
                'categories': [{'id': 'hotel-category', 'name': 'ホテル'}],
            },
        }

    def test_comment_keywords(self):
        for comment in ['温泉あり', '日帰り温泉サウナ', '源泉かけ流し', '成分表: 第一源泉']:
            with self.subTest(comment=comment):
                self.assertTrue(comment_matches_onsen(comment))
        for comment in ['', '宿泊しました', '温泉なし', '温泉ではない', '温泉はありません']:
            with self.subTest(comment=comment):
                self.assertFalse(comment_matches_onsen(comment))

    def test_all_visits_and_photos_of_comment_identified_hotel(self):
        checkins = [self.checkin(300, '', 'new'), self.checkin(200, '温泉あり', 'sheet'),
                    self.checkin(100, '', 'old')]
        for items in [checkins, list(reversed(checkins))]:
            places = build_places_from_checkins(items, {HOT_SPRING_CATEGORY_ID}, onsen_only=True)
            self.assertEqual(len(places), 1)
            self.assertEqual(places[0]['checkin_count'], 3)
            self.assertEqual(set(places[0]['photos']), {'new', 'sheet', 'old'})
            self.assertEqual(places[0]['user_comment'], '温泉あり')
            self.assertNotIn('category_group', places[0])

    def test_normal_hotel_and_blacklisted_venue_are_excluded(self):
        items = [self.checkin(100), self.checkin(200, '温泉あり', venue_id=next(iter(NOT_ONSEN_FSQ_IDS)))]
        self.assertEqual(build_places_from_checkins(items, set(), onsen_only=True), [])

    def test_category_id_still_qualifies(self):
        item = self.checkin(100)
        item['venue']['categories'] = [{'id': HOT_SPRING_CATEGORY_ID, 'name': 'unknown'}]
        self.assertEqual(len(build_places_from_checkins([item], {HOT_SPRING_CATEGORY_ID}, True)), 1)

    def test_category_word_boundaries(self):
        for label in ['Spa', 'Bath House', 'Hot Spring', '浴場', 'スパ']:
            self.assertTrue(category_label_matches_onsen({'name': label}))
        for label in ['Event Space', 'Spanish Restaurant', 'ホテル']:
            self.assertFalse(category_label_matches_onsen({'name': label}))

    def test_retained_places_lose_legacy_groups_without_losing_history(self):
        existing = {'hotel': {'fsq_id': 'hotel', 'category_group': 'travel', 'photos': ['old']}}
        places, kept = merge_with_existing([], existing, None)
        self.assertEqual(kept, 1)
        self.assertEqual(places, [{'fsq_id': 'hotel', 'photos': ['old']}])
        self.assertIn('category_group', existing['hotel'])


if __name__ == '__main__':
    unittest.main()
