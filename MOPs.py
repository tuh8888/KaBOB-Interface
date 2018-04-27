import logging
import math
from typing import Callable

import matplotlib.pyplot as plt
import networkx as nx


class FrameNotAddedYetException(Exception):
    pass


class MOPs(nx.MultiDiGraph):
    log = logging.getLogger("MOPs")
    type_mop = "mop"
    type_instance = "instance"
    abstraction = 'abstraction'
    equivalent = 'equivalent'

    def __init__(self, **attr):
        super().__init__(**attr)
        self.abstraction_hierarchy = nx.MultiDiGraph()

    '''
    ADDERS
    '''

    def add_frame(self, frame, label: str = None, frame_type: str = type_mop):
        if frame not in self:
            self.add_node(frame, label=label, frame_type=frame_type)

    def add_slot(self, frame, role, role_label, filler):
        if isinstance(filler, list):
            list_node = str(frame) + " " + str(role) + " - list"
            self.add_node(list_node, label=list_node, list=filler)
            filler = list_node
        self.add_edge(frame, filler, key=role, label=role_label)

    def add_equivalent_frame(self, frame, equivalent_frame):
        self.add_edge(frame, equivalent_frame, key=self.equivalent, label=self.equivalent)

    def add_instance(self, label):
        return self.add_frame(label, frame_type=self.type_instance)

    def add_abstraction(self, frame, abstraction):
        if frame in self.get_abstraction_hierarchy():
            if not self.is_abstraction(abstraction, frame):
                try:
                    if self.is_abstraction(frame, abstraction):
                        raise AbstractionException(nx.get_node_attributes(self, "label")[frame],
                                                   nx.get_node_attributes(self, "label")[abstraction])
                    else:
                        self.add_edge(frame, abstraction, key=self.abstraction)
                        self.get_abstraction_hierarchy().add_edge(frame, abstraction, key=self.abstraction)
                except AbstractionException as ae:
                    self.log.warning(ae.message)

        else:
            self.get_abstraction_hierarchy().add_edge(frame, abstraction, key=self.abstraction)
            self.add_edge(frame, abstraction, key=self.abstraction)

    '''
    CHECKERS
    '''

    def is_abstraction(self, abstraction, specialization):
        if abstraction == specialization:
            return True

        if abstraction in self.get_abstraction_hierarchy() and specialization in self.get_abstraction_hierarchy():
            return nx.has_path(self.get_abstraction_hierarchy(), specialization, abstraction)
        else:
            return False
        # specialization_abstractions = self.get_all_abstractions(specialization)
        # if specialization_abstractions:
        #     for spec_abstraction in specialization_abstractions:
        #         if abstraction is spec_abstraction:
        #             return True
        # return False

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

    '''
    GETTERS
    '''

    def get_all_abstractions(self, frame):
        immediate_parents = self.get_abstractions(frame)

        all_abstractions = list(immediate_parents)
        for parent in list(immediate_parents):
            all_abstractions.extend(self.get_all_abstractions(parent))

        return all_abstractions

    def get_abstractions(self, frame):
        return [neighbor for neighbor in self.neighbors(frame) if self.has_edge(frame, neighbor, key=self.abstraction)]

    def get_abstraction_hierarchy(self):
        if not self.abstraction_hierarchy:
            edges = ((u, v, k) for (u, v, k) in self.edges(keys=True) if k == self.abstraction)
            # abstraction_hierarchy = self.edge_subgraph(edges)
            self.abstraction_hierarchy.add_edges_from(edges)
        return self.abstraction_hierarchy

    def get_slot_graph(self):
        edges = ((u, v, k) for (u, v, k) in self.edges(data=True, keys=True) if k != self.abstraction and k != self.equivalent)
        return self.edge_subgraph(edges)

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

    def get_filler(self, mop, role) -> str:
        return self.get_edge_data(mop, role, 'filler')[0]

    '''
    REMOVERS
    '''

    def clear_frames(self):
        self.clear()

    '''
    DRAWING
    '''

    def draw_mops(self, image_dir: str, layout: Callable = nx.spring_layout, size: float = None):
        self.log.debug("Drawing Mops")
        pos = layout(self)
        self.draw_graph(self, pos, "%s/full_graph.png" % image_dir, size=size)
        self.draw_graph(self.get_abstraction_hierarchy(), pos, "%s/abstraction_hierarchy.png" % image_dir, size=size)
        self.draw_graph(self.get_slot_graph(), pos, "%s/slot_graph.png" % image_dir, size=size)

    @staticmethod
    def draw_graph(g, pos, out_loc: str, size: float = None):
        if g.nodes:
            if size is None:
                size = math.sqrt(g.number_of_nodes() * g.number_of_edges()) / 2
            plt.figure(None, figsize=(size, size))

            labels = dict((n, d['label']) if 'label' in d.keys() else (n, n) for n, d in g.nodes(data=True))
            edge_labels = dict([((u, v), d['label']) for u, v, d in g.edges(data=True) if 'label' in d.keys()])

            nx.draw(g, pos, labels=labels, with_labels=True)
            nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels)

            plt.savefig(out_loc)
            plt.close()

    """
    Statistics
    """

    def get_statistics(self):
        node_statistics = self.get_frame_statistics()
        edge_statistics = self.get_role_statistics()

        return node_statistics, edge_statistics

    def get_frame_statistics(self):
        frame_types = {}
        node_attrs = nx.get_node_attributes(self, "frame_type")
        for frame_type in node_attrs.values():
            if frame_type not in frame_types:
                frame_types[frame_type] = 1
            else:
                frame_types[frame_type] += 1

        return frame_types

    def get_role_statistics(self):
        role_types = {}
        edge_attrs = nx.get_edge_attributes(self, "label")
        for role_type in edge_attrs.values():

            if role_type not in role_types:
                role_types[role_type] = 1
            else:
                role_types[role_type] += 1

        return role_types


class AbstractionException(Exception):
    def __init__(self, specialization, abstraction):
        self.message = '%s can\'t be an abstraction of %s' % (specialization, abstraction)
