import logging
import pickle
import warnings
from typing import List, Callable, Dict, Set, Tuple
import networkx as nx

from franz.openrdf.connect import ag_connect
from franz.openrdf.model import Literal, Statement, Value
from franz.openrdf.model import URI
from franz.openrdf.model.value import Resource
from franz.openrdf.repository.repositoryconnection import RepositoryConnection

import KaBOB_Constants
from MOPs import MOPs

logging.basicConfig(level=logging.DEBUG)


class InstanceAndSuperClassesException(Warning):
    pass


class KaBOBInterface:
    log = logging.getLogger('KaBOBInterface')

    HOST = "HOST"
    PORT = "PORT"
    USER = "USER"
    PASSWORD = "PASSWORD"
    CATALOG = "CATALOG"
    RELEASE = "RELEASE"
    INSTANCE_RELEASE = "INSTANCE_RELEASE"

    KaBOB_IDs = "kabob_ids"

    def __init__(self, credentials_file: str, max_depth=1000):
        self.credentials_file = credentials_file
        self.mops = MOPs()
        self.bio_world = None
        self.kabob: RepositoryConnection = None
        self.max_depth = max_depth
        self.equivalent_classes: Dict[Value, Set(Value)] = dict()

    def __enter__(self):
        self.credentials = {}

        with open(self.credentials_file) as f:
            for line in f.readlines():
                key_value = line.strip().split(':')
                if len(key_value) == 2:
                    self.credentials[key_value[0]] = key_value[1]

        self.log.debug("Connecting to AllegroGraph server --" +
                       "host:'%s' port:%s" % (self.credentials[self.HOST], self.credentials[self.PORT]))
        self.kabob = ag_connect(self.credentials[self.RELEASE],
                                host=self.credentials[self.HOST],
                                port=int(self.credentials[self.PORT]),
                                user=self.credentials[self.USER],
                                password=self.credentials[self.PASSWORD],
                                create=False,
                                clear=False)

        return self

    def __exit__(self, t, value, traceback):
        self.kabob.close()

        self.log.debug("Closed AllegroGraph server --" +
                       "host:'%s' port:%s" % (self.credentials[self.HOST], self.credentials[self.PORT]))

    """
    SETTERS
    """

    def set_max_depth(self, max_depth: int):
        self.max_depth = max_depth

    """
    VISUALIZATION
    """

    def draw(self, image_dir, layout: Callable = nx.spring_layout, size: float = None):
        self.log.debug("Drawing graphs")
        self.mops.draw_mops(image_dir, layout=layout, size=size)

    """
    MOPIFICATION
    """

    def mopify(self, mop: str or URI, depth: int = 0, statements=None) -> URI or Literal or List[URI or Literal]:
        node: URI or Literal = mop \
            if isinstance(mop, URI) or isinstance(mop, Literal) \
            else self.create_uri(mop)

        if not self.is_mopifyable(node):
            return node
        elif node in self.mops:
            return node
        elif not self.is_bio(node):
            self.log.warning("\t" * depth + "Trivial mopification of non-BIO-world node %s" % node)
            return self.create_kabob_mop(node, statements, depth, is_trivial=True)
        else:
            return self.create_kabob_mop(node, statements, depth)

    def create_kabob_mop(self, node: URI or Literal, node_statements: List, depth: int,
                         is_trivial: bool = False) -> URI or Literal:

        parents: List[Tuple[Value, List]] = list()
        slots: List[URI or Literal, str, URI or Literal] = list()
        labels: List[str] = list()

        if not node_statements:
            node_statements = self.get_statements(node)

        equivalent_class = None
        node_type = None
        for statement in node_statements:
            o = statement.getObject()
            p = statement.getPredicate()

            if p.getURI() == KaBOB_Constants.SUBCLASSOF:
                parent_statements = self.get_statements(o)
                is_restriction = False
                restriction_property = None
                restriction_value = None
                for parent_statement in parent_statements:
                    parent_o = parent_statement.getObject()
                    parent_p = parent_statement.getPredicate()
                    if parent_p.getURI() == KaBOB_Constants.TYPE:
                        if parent_o.getURI() == KaBOB_Constants.RESTRICTION:
                            is_restriction = True
                    elif parent_p.getURI() == KaBOB_Constants.RESTRICTION_PROPERTY:
                        restriction_property = parent_o
                    elif parent_p.getURI() == KaBOB_Constants.RESTRICTION_VALUE:
                        restriction_value = parent_o
                if is_restriction:
                    role = restriction_property
                    role_label = self.get_role_name(restriction_property)
                    slots.append((role, role_label, self.mopify(restriction_value, depth + 1)))
                else:
                    parents.append((o, parent_statements))

            elif p.getURI() == KaBOB_Constants.LABEL and isinstance(o, Literal):
                labels.append(str(o.getLabel()))

            elif p.getURI() == KaBOB_Constants.EQUIVALENT_CLASS:
                if not equivalent_class:
                    for key, classes in self.equivalent_classes.items():
                        if o in classes:
                            equivalent_class = key
                            classes.add(node)
                            break
                        if node in classes:
                            equivalent_class = key
                            classes.add(o)
                            break
                    if not equivalent_class:
                        self.equivalent_classes[node] = {node}
                        equivalent_class = node
                else:
                    self.equivalent_classes[equivalent_class].add(o)

            elif p.getURI() not in KaBOB_Constants.NOT_A_SLOT:
                slots.append((p, self.get_role_name(p), o))
            elif p.getURI() == KaBOB_Constants.TYPE:
                node_type = o

        if node_type == KaBOB_Constants.LIST:
            return self.get_list_from_rdf(node, depth)

        if not equivalent_class:
            self.equivalent_classes[node] = {node}
            equivalent_class = node

        mop_name: str = self.get_instance_node_label(node, labels) if self.is_bio_instance(node, node_type) \
            else self.get_node_label(
            node, labels)

        self.log.debug("\t" * depth + "> " + mop_name)

        if not is_trivial and depth < self.max_depth:
            if parents and self.is_bio_instance(node, node_type):
                warnings.warn(str(mop_name) + " is an instance and a subClass")

            self.mops.add_frame(node, label=mop_name)

            if equivalent_class == node:
                [self.mops.add_equivalent_frame(node, self.mopify(equivalent, depth + 1)) for equivalent in
                 self.equivalent_classes[equivalent_class] if equivalent != node]
            else:
                self.mops.add_equivalent_frame(node, equivalent_class)

            [self.mops.add_abstraction(equivalent_class, self.mopify(parent, depth + 1, statements=parent_statements))
             for parent, parent_statements in parents]
            [self.mops.add_slot(equivalent_class, role, role_name, self.mopify(filler, depth + 1)) for
             role, role_name, filler in slots]
        else:
            self.mops.add_frame(node, label=mop_name)

        self.log.debug("\t" * depth + "< " + mop_name)

        return equivalent_class

    def create_uri(self, name: str) -> URI:
        namespace, local_name = KaBOB_Constants.split_name(name)
        return self.kabob.createURI(namespace=namespace, localname=local_name) if local_name else self.kabob.createURI(
            name)

    """
    CHECKERS
    """

    def is_bio_instance(self, node: URI, node_type) -> bool:
        return self.is_bio(node) and node_type

    @staticmethod
    def is_bio(node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == KaBOB_Constants.get_namespace(KaBOB_Constants.BIO_NAMESPACE)

    @staticmethod
    def is_ice(node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == KaBOB_Constants.get_namespace(KaBOB_Constants.ICE_NAMESPACE)

    # def is_restriction(self, node):
    #     _type = self.get_node_type(node)
    #     return _type and _type.getURI() == KaBOB_Constants.RESTRICTION

    # def is_rdf_list(self, node: URI or Literal) -> bool:
    #     _type = self.get_node_type(node)
    #     return _type and _type.getURI() == KaBOB_Constants.LIST

    @staticmethod
    def is_mopifyable(node: URI) -> bool:
        return isinstance(node, Resource)

    """
    GETTERS
    """

    def get_bio_world(self, pickle_dir):
        try:
            self.bio_world = pickle.load(open("%s/bio_world.pickle" % pickle_dir, "rb"))
        except FileNotFoundError:
            self.log.warning("Collecting all bio world nodes")
            self.bio_world = self.get_objects(None, KaBOB_Constants.DENOTES)
            pickle.dump(self.bio_world, open("%s/bio_world.pickle" % pickle_dir, "wb"))

        return self.bio_world

    def get_instance_node_label(self, node: URI or Literal, labels: List) -> str:
        return "%s - " % self.get_node_label(self.get_node_type(node), labels)

    @staticmethod
    def get_node_label(node: URI or Literal or str, labels: List) -> str:
        local_name = node
        if isinstance(node, URI):
            local_name = node.getLocalName()
        elif isinstance(node, Literal):
            local_name = node.getLabel()

        def find_lowercase_label(_labels):
            for label in _labels:
                if label.islower():
                    return label
            return False

        if labels:
            return find_lowercase_label(labels) or labels[0]
        else:
            return str(local_name)

    def get_objects(self, s: URI or str, p: URI or str) -> List[URI or Literal]:
        s = self.get_value_from_str(s)
        p = self.get_value_from_str(p)
        statements = self.get_statements(s=s, p=p)
        return [] if not statements else [statement.getObject() for statement in statements]

    def get_object(self, s: Value, p: URI) -> URI or Literal:
        objects = self.get_objects(s, p)
        return objects[0] if objects else None

    def get_subjects(self, o: URI or str, p: URI or str, full_statement: bool = False) -> List[Value or Literal]:
        o = self.get_value_from_str(o)
        p = self.get_value_from_str(p)
        statements = self.get_statements(o=o, p=p)
        return [] if not statements or full_statement else [statement.getSubject() for statement in statements]

    def get_subject(self, o, p):
        subjects = self.get_subjects(o, p)
        return subjects[0] if subjects else None

    def get_statements(self, s: Value = None, p: URI = None, o: Value = None) -> List[Statement]:
        s = self.get_value_from_str(s)
        p = self.get_value_from_str(p)
        o = self.get_value_from_str(o)
        with self.kabob.getStatements(subject=s, predicate=p, object=o) as statements:
            return statements.asList()

    def get_value_from_str(self, value: URI or str or Literal):
        value = value if not value or isinstance(value, URI) or isinstance(value, Literal) else self.create_uri(value)
        return value

    def get_node_type(self, node: Value) -> URI or Literal:
        return self.get_object(s=node, p=KaBOB_Constants.TYPE)

    def get_bio(self, node: URI) -> Value:
        if self.is_ice(node):
            return self.get_ice_to_bio(node)
        else:
            subjects = self.get_subjects(o=node, p=KaBOB_Constants.DENOTES)
            for subject in subjects:
                if self.is_ice(subject):
                    return self.get_ice_to_bio(subject)

    def get_ice_to_bio(self, node: Value) -> Value:
        objects = self.get_objects(s=node, p=KaBOB_Constants.DENOTES)
        for _object in objects:
            if self.is_bio(_object):
                return _object

    def get_list_from_rdf(self, node: URI or Literal, depth: int) -> List[URI or Literal]:
        first = self.get_object(s=node, p=KaBOB_Constants.FIRST)
        rest = self.get_object(s=node, p=KaBOB_Constants.REST)

        if first:
            if rest.getURI() == KaBOB_Constants.NIL:
                return [self.mopify(first, depth + 1)]
            else:
                return [self.mopify(first, depth + 1)] + self.get_list_from_rdf(rest, depth + 1)
        else:
            self.log.warning("\t" * depth + "List has no first: %s" % node)
            return []

    def get_role_name(self, node: URI or Literal) -> str:
        return self.get_node_label(node, self.get_labels(node))

    def get_labels(self, node: URI or Literal):
        return [str(o.getLabel()) for o in self.get_objects(node, KaBOB_Constants.LABEL)]

    def get_equivalent_classes(self, node: Value) -> List[Value]:
        return self.get_objects(s=node, p=KaBOB_Constants.EQUIVALENT_CLASS)

    def get_outgoing_edges(self, node: Value) -> List[URI]:
        return [statement.getPredicate() for statement in self.get_statements(s=node, p=None)]

    def get_incoming_edges(self, node):
        return self.get_subjects(o=node, p=None, full_statement=True)

    def get_restriction_property(self, restriction: URI or Literal) -> URI or Literal:
        return self.get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_PROPERTY)

    def get_restriction_value(self, restriction: Value):
        return self.get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_VALUE)
