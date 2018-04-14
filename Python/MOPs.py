import networkx as nx
from typing import List


class MOPsManager:
    type_mop = "mop"
    type_instance = "instance"

    def __init__(self):
        self.abstraction_hierarchy = nx.DiGraph()
        self.slot_graph = nx.MultiDiGraph()

    '''
    ADDERS
    '''

    def add_mop(self, name, frame_type=type_mop, abstractions=None, slots=None):
        """
        Note that nodes point to their parents

        :param name:
        :type name: string
        :type frame_type: string
        :type slots: dict
        :type abstractions: list
        """
        self.abstraction_hierarchy.add_node(name, frame_type=frame_type)

        if abstractions is not None:
            if name in abstractions:
                abstractions.remove(name)
            self.update_abstractions(name, abstractions)
            [self.abstraction_hierarchy.add_edge(name, abstraction) for abstraction in abstractions]

        if slots is not None:
            for role, filler in slots.items():
                self.slot_graph.add_edge(name, role, filler=filler)

    def add_instance(self, name, abstractions=None, slots=None, _id=None):
        return self.add_mop(name, frame_type=self.type_instance, abstractions=abstractions, slots=slots)

    '''
    CHECKERS
    '''

    def is_mop(self, name):
        return nx.get_node_attributes(self.abstraction_hierarchy, 'frame_type')[name] == self.type_mop

    def is_instance(self, name):
        return nx.get_node_attributes(self.abstraction_hierarchy, 'frame_type')[name] == self.type_instance

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

    '''
    INHERITANCE
    '''

    def inherit(self, name, fn):
        for abstraction in self.get_all_abstractions(name):
            if fn(abstraction) is not None:
                return abstraction

    def inherit_filler(self, name, role):
        return self.inherit(name, lambda abstraction: self.slot_graph.get_edge_data(abstraction, role)['filler'])

    def get_all_abstractions(self, name):
        if name is not None:
            immediate_parents = []
            if name in self.abstraction_hierarchy:
                immediate_parents = self.abstraction_hierarchy.neighbors(name)

            all_abstractions = list(immediate_parents)
            for parent in list(immediate_parents):
                all_abstractions.extend(self.get_all_abstractions(parent))

            return all_abstractions

    def unlink_abstraction(self, specialization, abstraction):
        self.abstraction_hierarchy.remove_edge(specialization, abstraction)

    def unlink_old_abstractions(self, name, old_abstractions, new_abstractions):
        for old_abstraction in list(old_abstractions):
            if old_abstraction not in new_abstractions:
                self.unlink_abstraction(name, old_abstraction)

    def link_abstraction(self, specialization, abstraction):
        if self.is_abstraction(abstraction, specialization):
            return
        try:
            if self.is_abstraction(specialization, abstraction):
                raise AbstractionException(specialization, abstraction)
        except AbstractionException as err:
            print(err)
            return

        self.abstraction_hierarchy.add_edge(specialization, abstraction)

    def link_new_abstractions(self, name, old_abstractions, new_abstractions):
        for new_abstraction in new_abstractions:
            if new_abstraction not in old_abstractions:
                if name == new_abstraction:
                    raise AbstractionException(name, new_abstraction)
                else:
                    self.link_abstraction(name, new_abstraction)

    def update_abstractions(self, name, abstractions):
        old_abstractions = self.abstraction_hierarchy.neighbors(name)
        new_abstractions = set(abstractions)

        if old_abstractions != new_abstractions:
            self.unlink_old_abstractions(name, old_abstractions, new_abstractions)
            self.link_new_abstractions(name, old_abstractions, new_abstractions)

    '''
    GETTERS
    '''

    def get_instances(self, abstraction, slots):
        if self.is_instance(abstraction) and self.has_slots(abstraction, slots):
            return list(abstraction)
        else:
            return [instance for specialization in self.abstraction_hierarchy.predecessors(abstraction)
                    for instance in self.get_instances(specialization, slots)]

    def get_root_frames(self):
        roots = []
        [roots.append(frame) for frame in self.abstraction_hierarchy
         if self.abstraction_hierarchy.successors(frame) is None]
        return roots

    '''
    REMOVERS
    '''

    def clear_frames(self):
        self.abstraction_hierarchy.clear()
        self.slot_graph.clear()

    def is_strict_abstraction(self, specialization, abstraction):
        return abstraction is not specialization and self.is_abstraction(abstraction, specialization)

    # def show_frame(self, name_or_frame, max_depth=2):
    #     self.pretty_print_frame_info(name_or_frame, 0, max_depth)
    #
    # def pretty_print_frame_info(self, x, depth, max_depth):
    #     if frame in self.abstraction_hierarchy and depth != max_depth:
    #         self.pretty_print_frame_name(frame, depth)
    #         self.pretty_print_frame_type(frame, depth)
    #         self.pretty_print_frame_abstractions(frame, depth, max_depth)
    #         if isinstance(frame, MOP):
    #             self.pretty_print_frame_slots(frame, depth, max_depth)
    #
    # @staticmethod
    # def pretty_print_frame_name(frame, depth):
    #     print("\t" * depth + "NAME %s" % frame.name)
    #
    # @staticmethod
    # def pretty_print_frame_type(frame, depth):
    #     print("\t" * depth + "TYPE %s" % type(frame))
    #
    # def pretty_print_frame_abstractions(self, frame, depth, max_depth):
    #     for abstraction in frame.abstractions:
    #         name = abstraction.name if isinstance(abstraction, Frame) else abstraction
    #         print("\t" * depth + "ISA %s" % name)
    #         self.pretty_print_frame_info(abstraction, depth + 1, max_depth)
    #
    # def pretty_print_frame_slots(self, mop, depth, max_depth):
    #     for slot in mop.slots.values():
    #         print("\t" * depth + "ROLE %s" % slot.role)
    #         if isinstance(slot.filler, Frame):
    #             self.pretty_print_frame_info(slot.filler, depth + 1, max_depth)
    #         else:
    #             print("\t" * depth + "FILLER %s" % slot.filler)
    #
    # def to_mop(self, x, create=False):
    #     if self.is_mop(x):
    #         return self.mops.get(x)
    #     if create:
    #         return MOP(name=x)
    def add_slot(self, mop: str, role: str, fillers: str or List[str]) -> None:
        for filler in fillers:
            self.abstraction_hierarchy.add_edge(mop, role, filler=filler)

    def get_filler(self, mop, role) -> str:
        return self.slot_graph.get_edge_data(mop, role, 'filler')[0]


class AbstractionException(Exception):
    def __init__(self, specialization, abstraction):
        self.message = '%s can\'t be an abstraction of %s' % (specialization, abstraction)


# class Slot:
#     role = ""
#     filler = ""
#     constraint = ""
#
#     def __init__(self, role, filler, constraint):
#         self.constraint = constraint
#         self.filler = filler
#         self.role = role
#
#
# class Frame(nx.):
#
#     def __init__(self, name):
#         self.name = name
#         self.abstractions = set()
#         self.slots = {}
#
#     def add_abstraction(self, abstraction):
#         self.abstractions.add(abstraction)
#
#     def add_slot(self, role, filler, constraint=None):
#         """
#         :type role: franz.openrdf.model.URI
#         :type filler: franz.openrdf.model.URI
#         :type constraint: str
#         """
#         if self.slots.get(role):
#             self.add_filler(role, filler, constraint)
#         else:
#             self.slots[role] = [Slot(role, filler, constraint)]
#
#     def add_filler(self, role, filler, constraint):
#         for slot in self.slots[role]:
#             if slot.filler == filler:
#                 return
#             else:
#                 self.slots[role].append(Slot(role, filler, constraint))
#
#     def __str__(self):
#         return "frame -> name: %s abstractions: %s" % (self.name, self.abstractions)
#
#     def get_filler(self, role):
#         slot = self.slots.get(role)
#         if slot:
#             return slot.filler
#
#
# class MOP(Frame):
#
#     def __init__(self, name):
#         super().__init__(name)
#         self.specializations = set()
#
#     def add_specialization(self, specialization):
#         self.specializations.add(specialization)
#
#
# class Instance(Frame):
#
#     def __init__(self, name):
#         super().__init__(name)
