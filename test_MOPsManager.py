from unittest import TestCase

from MOPs import MOPs


class TestMOPsManager(TestCase):
    def test_add_frame(self):
        manager = MOPs()

        manager.add_frame("thing")
        manager.add_frame("animate-thing", abstractions=["thing"])
        manager.add_frame("person", abstractions=["animate-thing"])
        manager.add_frame("dog", abstractions=["animate-thing"])
        manager.add_frame("male-person", abstractions=["person"])
        manager.add_frame("female-person", abstractions=["person"])
        manager.add_frame("circus-performer", abstractions=["animate-thing"])

        manager.add_instance("john-1", abstractions=["male-person", "circus-performer"])
        manager.add_instance("bob-3", abstractions=["male-person"])
        manager.add_instance("mary-0", abstractions=["female-person"])
        manager.add_instance("buddy-8", abstractions=["dog"])
        manager.add_frame("thing")

        # manager.show_frame("john-1", max_depth=4)
