from unittest import TestCase

from MOPs import MOPsManager


class TestMOPsManager(TestCase):
    def test_add_frame(self):
        manager = MOPsManager()

        manager.add_mop("thing")
        manager.add_mop("animate-thing", abstractions=["thing"])
        manager.add_mop("person", abstractions=["animate-thing"])
        manager.add_mop("dog", abstractions=["animate-thing"])
        manager.add_mop("male-person", abstractions=["person"])
        manager.add_mop("female-person", abstractions=["person"])
        manager.add_mop("circus-performer", abstractions=["animate-thing"])

        manager.add_instance("john-1", abstractions=["male-person", "circus-performer"])
        manager.add_instance("bob-3", abstractions=["male-person"])
        manager.add_instance("mary-0", abstractions=["female-person"])
        manager.add_instance("buddy-8", abstractions=["dog"])
        manager.add_mop("thing")

        # manager.show_frame("john-1", max_depth=4)
