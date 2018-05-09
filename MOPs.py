import logging
import math
from typing import Callable

import matplotlib.pyplot as plt
import networkx as nx


class FrameNotAddedYetException(Exception):
    pass


class MOPs:
    log = logging.getLogger("MOPs")

    type_mop = "mop"
    type_instance = "instance"

    attribute_label = 'label'
    attribute_frame_type = 'frame_type'
    attribute_filler = 'filler'

    def __init__(self, **attr):
        super().__init__(**attr)
        self.abstractions = nx.DiGraph()
        self.slots = nx.MultiDiGraph()
        self.special_node_attributes = {}

    '''
    ADDERS
    '''

    def add_special_node_attribute(self, role, role_label):
        self.special_node_attributes[role] = role_label

    def add_frame(self, frame, label: str = None, frame_type: str = type_mop):
        if frame not in self.abstractions:
            self.abstractions.add_node(frame, label=label, frame_type=frame_type)

    def add_slot(self, frame, role, role_label, filler):
        if isinstance(filler, list):
            list_node = str(frame) + " " + str(role) + " - list"
            self.slots.add_node(list_node, label=list_node, list=filler)
            filler = list_node
            self.slots.add_edge(frame, filler, key=role, label=role_label)
        else:
            if role in self.special_node_attributes.keys():
                nx.set_node_attributes(self.abstractions,
                                       {frame: nx.get_node_attributes(self.abstractions, self.attribute_label)[filler]},
                                       self.special_node_attributes[role])
            else:
                self.slots.add_edge(frame, filler, key=role, label=role_label)

    # def add_equivalent_frame(self, frame, equivalent_frame):
    #     self.equivalents.add_edge(frame, equivalent_frame)

    def add_instance(self, label):
        return self.add_frame(label, frame_type=self.type_instance)

    def add_abstraction(self, frame, abstraction):
        if not self.is_abstraction(abstraction, frame):
            try:
                if self.is_abstraction(frame, abstraction):
                    raise AbstractionException(
                        nx.get_node_attributes(self.abstractions, self.attribute_label)[frame],
                        nx.get_node_attributes(self.abstractions, self.attribute_label)[abstraction])
                else:
                    self.abstractions.add_edge(frame, abstraction)
            except AbstractionException as ae:
                self.log.warning(ae.message)

    '''
    CHECKERS
    '''

    def is_abstraction(self, abstraction, specialization):
        if abstraction == specialization:
            return True

        if abstraction in self.abstractions and specialization in self.abstractions:
            return nx.has_path(self.abstractions, specialization, abstraction)
        else:
            return False

    def is_mop(self, frame):
        return nx.get_node_attributes(self.abstractions, self.attribute_frame_type)[frame] == self.type_mop

    def is_instance(self, frame):
        return nx.get_node_attributes(self.abstractions, self.attribute_frame_type)[frame] == self.type_instance

    # def has_slot(self, instance, role, filler):
    #     self.is_abstraction(filler, self.inherit_filler(instance, role))

    # def has_slots(self, instance, slots):
    #     for role, filler in slots.items():
    #         if not self.has_slot(instance, role, filler):
    #             return False
    #     return True

    def is_strict_abstraction(self, specialization, abstraction):
        return abstraction is not specialization and self.is_abstraction(abstraction, specialization)

    '''
    INHERITANCE
    '''

    # def inherit(self, mop, fn):
    #     for abstraction in self.get_all_abstractions(mop):
    #         if fn(abstraction) is not None:
    #             return abstraction
    #
    # def inherit_filler(self, frame, role):
    #     return self.inherit(frame,
    #                         lambda abstraction: self.slots.get_edge_data(abstraction, role)[self.attribute_filler])

    '''
    GETTERS
    '''

    def get_frame_label(self, frame):
        if frame in self.abstractions:
            return nx.get_node_attributes(self.abstractions, self.attribute_label)[frame]

    def get_edge_label(self, u, v):
        if self.slots.has_edge(u, v):
            return list(self.slots.get_edge_data(u, v))[0]

    def get_full_graph(self):
        # The order is important here since it needs to be a multidigraph
        full_graph = nx.MultiDiGraph()
        full_graph.add_nodes_from(self.abstractions.nodes(data=True))
        full_graph.add_edges_from(self.abstractions.edges)
        full_graph.add_edges_from(self.slots.edges(data=True))

        return full_graph

    # def get_instances(self, abstraction, slots):
    #     if self.is_instance(abstraction) and self.has_slots(abstraction, slots):
    #         return list(abstraction)
    #     else:
    #         return [instance for specialization in self.predecessors(abstraction)
    #                 for instance in self.get_instances(specialization, slots)]
    #
    # def get_root_frames(self):
    #     roots = []
    #     [roots.append(frame) for frame in self
    #      if self.successors(frame) is None]
    #     return roots
    #
    # def get_filler(self, mop, role) -> str:
    #     return self.get_edge_data(mop, role, self.attribute_filler)[0]

    '''
    REMOVERS
    '''

    def clear_frames(self):
        self.abstractions.clear()
        self.slots.clear()

    '''
    DRAWING
    '''

    def draw_mops(self, image_dir: str, layout: Callable = nx.spring_layout, size: float = None):
        self.log.debug("Drawing Mops")
        full_graph = self.get_full_graph()

        pos = layout(full_graph)

        self.draw_graph(full_graph, pos, "%s/full_graph.png" % image_dir, size=size)
        self.draw_graph(self.abstractions, pos, "%s/abstraction_hierarchy.png" % image_dir, size=size)
        self.draw_graph(self.slots, pos, "%s/slot_graph.png" % image_dir, size=size)

    def draw_graph(self, G: nx.Graph, pos, out_loc: str, size: float = None, node_labels=None, edge_labels=None):
        if G.nodes:
            if size is None:
                size = math.sqrt(G.number_of_nodes() * G.number_of_edges()) / 2
            if node_labels is None:
                node_labels = dict()
                for n, d in self.abstractions.nodes(data=True):
                    if n in G:
                        label = str(d.get(self.attribute_label, n))
                        # for key, value in d.items():
                        #     if key in self.special_node_attributes.values():
                        #         label += "\n%s" % str(value)
                        node_labels[n] = label
            if edge_labels is None:
                edge_labels = dict([((u, v), d[self.attribute_label]) for u, v, d in G.edges(data=True) if
                                    self.attribute_label in d.keys()])
            plt.figure(None, figsize=(size, size))

            nx.draw(G, pos, labels=node_labels, with_labels=True)
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

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
        node_attrs = nx.get_node_attributes(self.abstractions, self.attribute_frame_type)
        for frame_type in node_attrs.values():
            if frame_type not in frame_types:
                frame_types[frame_type] = 1
            else:
                frame_types[frame_type] += 1

        return frame_types

    def get_role_statistics(self):
        role_types = {}
        edge_attrs = nx.get_edge_attributes(self.slots, self.attribute_label)
        for role_type in edge_attrs.values():

            if role_type not in role_types:
                role_types[role_type] = 1
            else:
                role_types[role_type] += 1

        return role_types

    """
    COLLAPSING
    """




class AbstractionException(Exception):
    def __init__(self, specialization, abstraction):
        self.message = '%s can\'t be an abstraction of %s' % (specialization, abstraction)
