from unittest import TestCase

from MOPs import MOPs


class TestMOPsManager(TestCase):
    def test_add_frame(self):
        manager = MOPs()

        manager.add_frame("thing")

        manager.add_frame("animate-thing")
        manager.add_abstraction("animate-thing", "thing")

        manager.add_frame("person")
        manager.add_abstraction("person", "animate-thing")

        manager.add_frame("dog")
        manager.add_abstraction("dog", "animate-thing")

        manager.add_frame("male-person")
        manager.add_abstraction("male-person", "person")

        manager.add_frame("female-person")
        manager.add_abstraction("female-person", "person")

        manager.add_frame("circus-performer")
        manager.add_abstraction("circus-performer", "animate-thing")

        manager.add_instance("john-1")
        manager.add_abstraction("john-1", "male-person")
        manager.add_abstraction("john-1", "circus-performer")

        manager.add_instance("bob-3")
        manager.add_abstraction("bob-3", "male-person")

        manager.add_instance("mary-0")
        manager.add_abstraction("mary-0", "female-person")

        manager.add_instance("buddy-8")
        manager.add_abstraction("buddy-8", "dog")

        manager.add_frame("thing")

        manager.draw_mops()
