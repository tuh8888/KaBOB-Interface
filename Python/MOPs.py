import math

import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Callable


class MOPs(nx.MultiDiGraph):
    type_mop = "mop"
    type_instance = "instance"

    def __init__(self, **attr):
        super().__init__(**attr)

    '''
    ADDERS
    '''

    def add_frame(self, frame, label: str = None, frame_type: str = type_mop, abstractions: List = None):
        if frame not in self:
            self.add_node(frame, label=label, frame_type=frame_type)

        if abstractions is not None:
            if frame in abstractions:
                abstractions.remove(frame)
            self.update_abstractions(frame, abstractions)
            [self.add_edge(frame, abstraction) for abstraction in abstractions]

    def add_instance(self, label, abstractions=None):
        return self.add_frame(label, frame_type=self.type_instance, abstractions=abstractions)

    def add_slot(self, mop, role, role_label, fillers: str or List[str]) -> None:
        if mop != role:
            if not isinstance(fillers, list):
                fillers = [fillers]
            for filler in fillers:
                self.add_edge(mop, filler, filler=role, label=role_label)

    '''
    CHECKERS
    '''

    def is_mop(self, frame):
        return nx.get_node_attributes(self, 'frame_type')[frame] == self.type_mop

    def is_instance(self, frame):
        return nx.get_node_attributes(self, 'frame_type')[frame] == self.type_instance

    def has_slot(self, instance, role, filler):
        self.is_abstraction(filler, self.inherit_filler(instance, role))

    def has_slots(self, instance, slots):
        for role, filler in slots.items():
            if not self.has_slot(instance, role, filler):
                return False
        return True

    def is_abstraction(self, abstraction, specialization):
        if abstraction is specialization:
            return True
        specialization_abstractions = self.get_all_abstractions(specialization)
        if specialization_abstractions is not None:
            for spec_abstraction in specialization_abstractions:
                if abstraction is spec_abstraction:
                    return True

        return False

    def is_strict_abstraction(self, specialization, abstraction):
        return abstraction is not specialization and self.is_abstraction(abstraction, specialization)

    '''
    INHERITANCE
    '''

    def inherit(self, mop, fn):
        for abstraction in self.get_all_abstractions(mop):
            if fn(abstraction) is not None:
                return abstraction

    def inherit_filler(self, frame, role):
        return self.inherit(frame,
                            lambda abstraction: self.get_edge_data(abstraction, role)['filler'])

    def get_all_abstractions(self, frame):
        if frame is not None:
            immediate_parents = []
            if frame in self:
                immediate_parents = self.neighbors(frame)

            all_abstractions = list(immediate_parents)
            for parent in list(immediate_parents):
                all_abstractions.extend(self.get_all_abstractions(parent))

            return all_abstractions

    def unlink_abstraction(self, specialization, abstraction):
        self.remove_edge(specialization, abstraction)

    def unlink_old_abstractions(self, frame, old_abstractions, new_abstractions):
        for old_abstraction in list(old_abstractions):
            if old_abstraction not in new_abstractions:
                self.unlink_abstraction(frame, old_abstraction)

    def link_abstraction(self, specialization, abstraction):
        if self.is_abstraction(abstraction, specialization):
            return
        try:
            if self.is_abstraction(specialization, abstraction):
                raise AbstractionException(specialization, abstraction)
        except AbstractionException as err:
            print(err)
            return

        self.add_edge(specialization, abstraction)

    def link_new_abstractions(self, frame, old_abstractions, new_abstractions):
        for new_abstraction in new_abstractions:
            if new_abstraction not in old_abstractions:
                if frame == new_abstraction:
                    raise AbstractionException(frame, new_abstraction)
                else:
                    self.link_abstraction(frame, new_abstraction)

    def update_abstractions(self, frame, abstractions):
        old_abstractions = self.neighbors(frame)
        new_abstractions = set(abstractions)

        if old_abstractions != new_abstractions:
            self.unlink_old_abstractions(frame, old_abstractions, new_abstractions)
            self.link_new_abstractions(frame, old_abstractions, new_abstractions)

    '''
    GETTERS
    '''

    def get_instances(self, abstraction, slots):
        if self.is_instance(abstraction) and self.has_slots(abstraction, slots):
            return list(abstraction)
        else:
            return [instance for specialization in self.predecessors(abstraction)
                    for instance in self.get_instances(specialization, slots)]

    def get_root_frames(self):
        roots = []
        [roots.append(frame) for frame in self
         if self.successors(frame) is None]
        return roots

    '''
    REMOVERS
    '''

    def clear_frames(self):
        self.clear()

    def get_filler(self, mop, role) -> str:
        return self.get_edge_data(mop, role, 'filler')[0]

    '''
    DRAWING
    '''

    def draw_mops(self, layout: Callable=nx.spring_layout):
        self.draw_graph("images/full_graph.png", layout=layout)

        edges = ((u, v, k) for (u, v, k, filler) in self.edges(keys=True, data=True) if not filler)
        self.draw_graph("images/abstraction_hierarchy.png", edges=edges, layout=layout)

        edges = ((u, v, k) for (u, v, k, filler) in self.edges(keys=True, data=True) if filler)
        self.draw_graph("images/slot_graph.png", edges=edges, layout=layout)

    def draw_graph(self, out_loc: str, edges=None, layout: Callable=nx.spring_layout):

        if edges:
            g = self.edge_subgraph(edges)
        else:
            g = self

        size = math.sqrt(g.number_of_nodes() * g.number_of_edges()) / 2
        plt.figure(None, figsize=(size, size))

        labels = dict((n, d['label']) if 'label' in d.keys() else (n, n) for n, d in g.nodes(data=True))
        edge_labels = dict([((u, v), d['label']) for u, v, d in g.edges(data=True) if 'label' in d.keys()])

        pos = layout(g)
        nx.draw(g, pos, labels=labels, with_labels=True)
        nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels)

        plt.savefig(out_loc)
        plt.close()


class AbstractionException(Exception):
    def __init__(self, specialization, abstraction):
        self.message = '%s can\'t be an abstraction of %s' % (specialization, abstraction)
