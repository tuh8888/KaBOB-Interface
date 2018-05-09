import copy

import networkx as nx
from logging import Logger


class AcceptStateReached(Exception):
    pass


class TransitionDoesNotExist(Exception):
    pass


class Automata(nx.DiGraph):

    def __init__(self, start_state, states, accept_states, **attr):
        super().__init__(**attr)

        for state in states:
            self.add_node(state)

        self.accept_states = accept_states
        self.current_state = start_state

    def add_transition(self, start, end):
        self.add_edge(start, end)

    def transition(self, next_state):
        if self.has_edge(self.current_state, next_state) or self.current_state is None:
            self.current_state = next_state
            return self.current_state


class Walker:
    log = Logger("Walk")

    def __init__(self, G: nx.MultiDiGraph, query: Automata):
        self.G: nx.MultiDiGraph = G
        self.query = query

    def walk(self, start):
        return dfs(self.G, start, [], self.is_exit, self.can_step, self.query)

    def can_step(self, start, neighbor):
        return self.query.transition(neighbor)

    def is_exit(self, neighbor):
        return neighbor in self.query.accept_states


class EdgeWalker(Walker):
    def __init__(self, G: nx.MultiDiGraph, query: Automata, attribute_name, accept_nodes):
        super().__init__(G, query)
        self.attribute_name = attribute_name
        self.accept_nodes = accept_nodes

    def can_step(self, start, neighbor):
        if self.G.has_edge(start, neighbor):
            return self.query.transition(self.get_edge_attribute(start, neighbor))

    def get_edge_attribute(self, start, neighbor):
        for key, attribute in nx.get_edge_attributes(self.G, self.attribute_name).items():
            u, v, key = key
            if u == start and v == neighbor:
                return attribute

    def is_exit(self, neighbor):
        return neighbor in self.accept_nodes


def dfs(G, state, path, is_exit, can_step, query: Automata):
    path.append(state)
    if is_exit(state):
        return path
    for neighbor in G.successors(state):
        if neighbor not in path and can_step(state, neighbor):
            neighbor_path = dfs(G, neighbor, list(path), is_exit, can_step, copy.deepcopy(query))
            if neighbor_path is not None:
                return neighbor_path
