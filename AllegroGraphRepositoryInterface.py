import logging
import pickle
import shutil
import sys
import warnings
from typing import List, Callable, Dict, Set, Tuple
import networkx as nx

from franz.openrdf.connect import ag_connect
from franz.openrdf.model import Literal, Statement, Value
from franz.openrdf.model import URI
from franz.openrdf.repository.repositoryconnection import RepositoryConnection
from franz.openrdf.vocabulary import RDF, RDFS, OWL

from MOPs import MOPs

logging.basicConfig(level=logging.DEBUG)


class InstanceAndSuperClassesException(Warning):
    """
    Exception if an instance is also a superclass of another entity
    """
    pass


class Interface:
    log = logging.getLogger('Interface')

    HOST = "HOST"
    PORT = "PORT"
    USER = "USER"
    PASSWORD = "PASSWORD"
    CATALOG = "CATALOG"
    RELEASE = "RELEASE"
    INSTANCE_RELEASE = "INSTANCE_RELEASE"

    def __init__(self, credentials_file: str, max_depth=1000, cache_dir=None):
        """
        :param credentials_file: File containing the settings for accessing KaBOB
        :param max_depth: Maximum depth to mopify to. Maximum value is the systems set recursion limit
        :param cache_dir: Directory to save results to. Some methods cache results as they go
        :return: Self
        """
        self.NOT_A_SLOT = [RDF.TYPE, RDFS.SUBCLASSOF, RDFS.LABEL, OWL.EQUIVALENTCLASS]
        self.credentials_file = credentials_file
        self.mops = MOPs()

        self.conn: RepositoryConnection = None
        self.max_depth = min(max_depth, sys.getrecursionlimit())
        self.equivalent_classes: Dict[Value, Set(Value)] = dict()

        self.cache_dir = cache_dir
        self.cached_statements = {}

        # Attempt to load cached statements and mops
        if self.cache_dir:
            try:
                print("Reading cached statements")
                self.cached_statements = pickle.load(open("%s/statements.pickle" % self.cache_dir, "rb"))
                self.equivalent_classes: Dict = pickle.load(open("%s/equivalent_classes.pickle" % self.cache_dir, "rb"))

                print("Reading cached mops")
                self.mops: MOPs = pickle.load(open("%s/mops.pickle" % self.cache_dir, "rb"))
                print()
                # abstractions: nx.DiGraph = pickle.load(open("%s/abstractions.pickle" % self.cache_dir, "rb"))
                # self.mops.abstractions.add_nodes_from(abstractions.nodes(data=True))
                # self.mops.abstractions.add_edges_from(abstractions.edges(data=True))
                #
                # slots: nx.MultiDiGraph = pickle.load(open("%s/slots.pickle" % self.cache_dir, "rb"))
                # self.mops.slots.add_nodes_from(slots.nodes(data=True))
                # self.mops.slots.add_edges_from(slots.edges(data=True))
            except FileNotFoundError:
                pass

    def __enter__(self):
        """
        Called when initialized using a "with" statement. Loads cached items if available, and opens a connection to
        KaBOB using the credentials provided.
        :return: The interface
        """

        self.connect_to_repository()

        return self

    def get_credentials(self):
        credentials = {}

        # Read credentials file
        with open(self.credentials_file) as f:
            for line in f.readlines():
                key_value = line.strip().split(':')
                if len(key_value) == 2:
                    credentials[key_value[0]] = key_value[1]

        return credentials

    def connect_to_repository(self):
        credentials = self.get_credentials()

        # Open connection to KaBOB using provided credentials
        self.log.debug("Connecting to repository --" +
                       "host:'%s' port:%s" % (credentials[self.HOST], credentials[self.PORT]))
        self.conn = ag_connect(credentials[self.RELEASE],
                               host=credentials[self.HOST],
                               port=int(credentials[self.PORT]),
                               user=credentials[self.USER],
                               password=credentials[self.PASSWORD],
                               create=False,
                               clear=False)

        self.initialize_namespaces()
        self.initialize_relations()
        self.initialize_nodes()

    def initialize_namespaces(self):
        pass

    def initialize_relations(self):
        pass

    def initialize_nodes(self):
        pass

    def close(self):
        self.conn.close()

        self.log.debug("Closed KaBOB")

        if self.cache_dir:
            pickle.dump(self.cached_statements,
                        open("%s/statements.pickle" % self.cache_dir, "wb"))
            pickle.dump(self.equivalent_classes,
                        open("%s/equivalent_classes.pickle" % self.cache_dir, "wb"))
            pickle.dump(self.mops,
                        open("%s/mops.pickle" % self.cache_dir, "wb"))

    def __exit__(self, t, value, traceback):
        """
        Called when the "with" statement concludes. Safely closes connection to KaBOB and caches results
        :param t:
        :param value:
        :param traceback:
        :return: None
        """

        self.close()

    """
    SETTERS
    """

    def set_max_depth(self, max_depth: int) -> None:
        """
        Set the maximum mopification depth
        :param max_depth:
        :return: None
        """
        if max_depth > sys.getrecursionlimit():
            self.log.warning("Can't set max depth deeper than the system's maximum recursion limit."
                             "Please increase system's maximum recursion depth first (sys.setrecursionlimit(n))")
        self.max_depth = max_depth

    """
    VISUALIZATION
    """

    def draw(self, image_dir: str, layout: Callable = nx.spring_layout, size: float = None) -> None:
        """
        Draw mop structures using matplotlib. Creates three image files.
        :param image_dir: Directory to save image files to
        :param layout: NetworkX layout function
        :param size: Set image size to Size X Size
        :return: None
        """
        self.log.debug("Drawing graphs")
        self.mops.draw_mops(image_dir, layout=layout, size=size)

    """
    MOPIFICATION
    """

    def mopify_and_cache(self, nodes: List[str or URI], cache_every_iter: int = None, number_of_nodes_to_mopify=None,
                         separate_caches: bool = False):
        """
        Begin mopifying and caching results. Results are cached after each mop in mops has finished mopifying
        :param cache_every_iter:
        :param separate_caches: Specify whether cached mops should be saved separately
        :param nodes: List of nodes to mopify
        :param number_of_nodes_to_mopify: Number of nodes in mops to mopify
        :return: None
        """
        if self.cache_dir:
            count = 0
            for node in nodes:
                self.log.debug("**************************** Mopify %d ****************************" % count)
                if node not in self.mops.abstractions:
                    self.mopify(node, depth=0)

                    if cache_every_iter and count % cache_every_iter == 0:
                        self.log.debug("Caching results")
                        pickle.dump(self.mops, open("%s/mops.pickle" % self.cache_dir, "wb"))
                        if separate_caches:
                            shutil.copyfile("%s/mops.pickle" % self.cache_dir,
                                            "%s/mops_%d.pickle" % (self.cache_dir, count))

                count += 1
                if count > number_of_nodes_to_mopify:
                    break
            if not cache_every_iter:
                self.log.debug("Caching results")
                pickle.dump(self.mops, open("%s/mops.pickle" % self.cache_dir, "wb"))
                if separate_caches:
                    shutil.copyfile("%s/mops.pickle" % self.cache_dir,
                                    "%s/mops_%d.pickle" % (self.cache_dir, count))

        else:
            self.log.warning("Cache directory not set")

    def mopify(self, node: str or Value, depth: int = 0) -> Value or List[Value]:
        """
        Convert node to a mop and mopify its parents if it is a Bio World node
        :param node: A KaBOB node to mopify
        :param depth: Current mopification depth
        :return:
        """

        # Convert node to URI

        if node in self.mops.abstractions:  # No need to mopify if it has already been mopified
            return node
        else:
            is_trivial = self.is_node_trivial(node)
            if is_trivial:
                self.log.warning("\t" * depth + "Trivial mopification of non-BIO-world node %s" % node)
            mop_label, parents, slots, node_type, equivalent_class = self.parse_statements(node, is_trivial)

            if node_type == RDF.LIST:
                return self.get_list_from_rdf(node, depth)

            self.log.debug("\t" * depth + "> " + mop_label)
            self.create_kabob_mop(node, mop_label, parents, slots, node_type, equivalent_class, depth, is_trivial)
            self.log.debug("\t" * depth + "< " + mop_label)
            return equivalent_class

    def create_kabob_mop(self,
                         node: URI or Literal,
                         mop_label: str,
                         parents: List[Value],
                         slots: List[Tuple[Value, Value]],
                         node_type: Value,
                         equivalent_class: Value,
                         depth: int,
                         is_trivial: bool = False) -> None:
        """
        Adds the node to KaBOB's mops and mopifies its slots and parents if it is not a trivial node
        :param node: Node to be added as a mop
        :param mop_label: Label for the mop
        :param parents: Parents of the node
        :param slots: Tuples containing a role for the mop and a filler for the role
        :param node_type: Type of node
        :param equivalent_class: The equivalent class of the node
        :param depth:
        :param is_trivial:
        :return:
        """

        if parents and self.is_instance(node, node_type):
            warnings.warn("\t" * depth + str(mop_label) + " is an instance and a subClass")

        self.mops.add_frame(node, label=mop_label)

        if not is_trivial or depth < self.max_depth:
            # if equivalent_class == node:
            #     [self.mops.add_equivalent_frame(node, self.mopify(equivalent, depth=depth + 1))
            #      for equivalent in self.equivalent_classes[equivalent_class] if equivalent != node]
            # else:
            #     self.mops.add_equivalent_frame(node, equivalent_class)

            [self.mops.add_abstraction(equivalent_class,
                                       self.mopify(parent, depth=depth + 1)) for parent in parents]
            [self.mops.add_slot(equivalent_class,
                                role,
                                self.get_label(role),
                                self.mopify(filler, depth=depth + 1)) for role, filler in slots]

    def parse_statements(self, node: Value, is_trivial: bool) -> Tuple[
            str, List[Value], List[Tuple[Value, Value]], Value, Value]:
        """
        Parse triples with node as the subject
        :param node:
        :param is_trivial:
        :return:
        """
        parents: List[Value] = list()
        slots: List[Tuple[Value, Value]] = list()
        labels: List[str] = list()
        equivalent_class = None
        node_type = None

        node_statements = self.get_statements(node)

        for statement in node_statements:
            o = statement.getObject()
            p = statement.getPredicate()

            if not is_trivial:
                if p == RDFS.SUBCLASSOF:
                    # Here, we check to see if the parent is a restriction.
                    # If it is, we add it as a slot.
                    # Otherwise, we add it as a parent.
                    is_restriction, restriction_property, restriction_value = self.check_restriction(o)
                    if is_restriction:
                        slots.append((restriction_property, restriction_value))
                    else:
                        parents.append(o)

                elif p not in self.NOT_A_SLOT:
                    slots.append((p, o))

            if p == RDFS.LABEL and isinstance(o, Literal):
                labels.append(str(o.getLabel()))

            elif p == OWL.EQUIVALENTCLASS:
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

            elif p == RDF.TYPE:
                node_type = o

        if not equivalent_class:
            self.equivalent_classes[node] = {node}
            equivalent_class = node

        if self.is_instance(node, node_type):
            mop_label: str = self.get_instance_node_label(node, labels)
        else:
            mop_label: str = self.get_label(node, labels)

        return mop_label, parents, slots, node_type, equivalent_class

    def check_restriction(self, o):
        parent_statements = self.get_statements(o)
        is_restriction = False
        restriction_property = None
        restriction_value = None
        for parent_statement in parent_statements:
            parent_o = parent_statement.getObject()
            parent_p = parent_statement.getPredicate()
            if parent_p == RDF.TYPE:
                if parent_o == OWL.RESTRICTION:
                    is_restriction = True
            elif parent_p == OWL.ONPROPERTY:
                restriction_property = parent_o
            elif parent_p == OWL.SOMEVALUESFROM:
                restriction_value = parent_o
        return is_restriction, restriction_property, restriction_value

    """
    CHECKERS
    """

    def is_node_trivial(self, node: Value) -> bool:
        return False

    def is_instance(self, node: Value, node_type) -> bool:
        return node_type

    """
    GETTERS
    """

    def get_instance_node_label(self, node: URI or Literal, labels: List) -> str:
        return "%s - " % self.get_label(self.get_node_type(node), labels)

    def get_label(self, node: URI or Literal, labels: List = None) -> str:
        local_name = node
        if isinstance(node, URI):
            local_name = node.getLocalName()
        elif isinstance(node, Literal):
            local_name = node.getLabel()

        if not labels:
            labels = [str(o.getLabel()) for o in self.get_objects(node, RDFS.LABEL)]

        def find_lowercase_label(_labels):
            for label in _labels:
                if label.islower():
                    return label
            return False

        if labels:
            return find_lowercase_label(labels) or labels[0]
        else:
            return str(local_name)

    def get_objects(self, s: Value or None, p: URI or None) -> List[URI or Literal]:
        statements = self.get_statements(s=s, p=p)
        return [] if not statements else [statement.getObject() for statement in statements]

    def get_object(self, s: Value, p: URI) -> URI or Literal:
        objects = self.get_objects(s, p)
        return objects[0] if objects else None

    def get_subjects(self, o: Value, p: URI, full_statement: bool = False) -> List[Value or Literal]:
        statements = self.get_statements(o=o, p=p)
        return [] if not statements or full_statement else [statement.getSubject() for statement in statements]

    def get_subject(self, o: Value, p: URI):
        subjects = self.get_subjects(o, p)
        return subjects[0] if subjects else None

    def get_statements(self, s: Value = None, p: URI = None, o: Value = None) -> List[Statement]:
        statements = None
        if s and not p and not o:
            statements = self.cached_statements.get(s)
        if not statements:
            with self.conn.getStatements(subject=s, predicate=p, object=o) as statements:
                statements = statements.asList()
                if s and not p and not o:
                    self.cached_statements[s] = statements
        return statements

    def get_node_type(self, node: Value) -> URI or Literal:
        return self.get_object(s=node, p=RDF.TYPE)

    def get_list_from_rdf(self, node: URI or Literal, depth: int) -> List[URI or Literal]:
        first = self.get_object(s=node, p=RDF.FIRST)
        rest = self.get_object(s=node, p=RDF.REST)

        if first:
            if rest.getURI() == RDF.NIL:
                return [self.mopify(first, depth=depth + 1)]
            else:
                return [self.mopify(first, depth=depth + 1)] + self.get_list_from_rdf(rest, depth + 1)
        else:
            self.log.warning("\t" * depth + "List has no first: %s" % node)
            return []

    def get_equivalent_classes(self, node: Value) -> List[Value]:
        return self.get_objects(s=node, p=OWL.EQUIVALENTCLASS)
