from unittest import TestCase
from Walker import *
from networkx import MultiDiGraph
from logging import Logger


class TestWalk(TestCase):
    log = Logger("TestWalk")

    def test_walk(self):
        A = Automata(None, [1, 2, 3], [])
        A.add_transition(1, 3)
        A.add_transition(3, 2)
        G = MultiDiGraph()
        G.add_edge("a", "b", filler=1)
        G.add_edge("b", "c", filler=2)
        G.add_edge("b", "d", filler=3)
        G.add_edge("d", "e", filler=2)

        walker = EdgeWalker(G, A, 'filler', ["e"])
        self.log.warning("Path: " + str(walker.walk("a")))
