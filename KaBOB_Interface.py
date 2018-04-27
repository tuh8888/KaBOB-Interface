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


class KaBOBInterface:
    log = logging.getLogger('KaBOBInterface')

    def __init__(self, credentials_file: str, max_depth=1000, cache_dir=None):
        """
        :param credentials_file: File containing the settings for accessing KaBOB
        :param max_depth: Maximum depth to mopify to. Maximum value is the systems set recursion limit
        :param cache_dir: Directory to save results to. Some methods cache results as they go
        :return: Self
        """
        self.credentials_file = credentials_file
        self.mops = MOPs()
        self.bio_world = None
        self.kabob: RepositoryConnection = None
        self.max_depth = min(max_depth, sys.getrecursionlimit())
        self.equivalent_classes: Dict[Value, Set(Value)] = dict()

        self.cache_dir = cache_dir
        self.cached_statements = {}

        self.credentials = {}

        self.BIO = None
        self.ICE = None
        self.OBO = None
        self.OBOINOWL = None
        self.CCP_EXT = None
        self.CCP_BNODE = None
        self.NCBITAXON = None
        self.PART_OF = None
        self.HAS_PART = None
        self.DENOTES = None
        self.HAS_PARTICIPANT = None
        self.TRANSPORTS = None
        self.CAUSES = None
        self.XREF = None
        self.ID = None
        self.OBONAMESPACE = None
        self.DEFINITION = None
        self.EXACTSYNONYM = None
        self.HAS_RANK = None
        self.BP_root = None
        self.MF_root = None
        self.CC_root = None
        self.PRO_root = None
        self.localization_process = None
        self.binding_process = None
        self.interaction = None
        self.physical_association = None
        self.apoptotic_process = None
        self.p53 = None
        self.cytochrome_C = None
        self.CUSTOM_RELATIONS_TO_IGNORE = None
        self.NOT_A_SLOT = None

    def __enter__(self):
        """
        Called when initialized using a "with" statement. Loads cached items if available, and opens a connection to
        KaBOB using the credentials provided.
        :return: The interface
        """

        HOST = "HOST"
        PORT = "PORT"
        USER = "USER"
        PASSWORD = "PASSWORD"
        # noinspection PyUnusedLocal
        CATALOG = "CATALOG"
        RELEASE = "RELEASE"
        # noinspection PyUnusedLocal
        INSTANCE_RELEASE = "INSTANCE_RELEASE"

        # Attempt to load cached statements and mops
        if self.cache_dir:
            try:
                self.cached_statements = pickle.load(open("%s/statements.pickle" % self.cache_dir, "rb"))
                graph: nx.MultiDiGraph = pickle.load(open("%s/mops.pickle" % self.cache_dir, "rb"))
                self.mops.add_nodes_from(graph.nodes(data=True))
                self.mops.add_edges_from(graph.edges(data=True))
            except FileNotFoundError:
                pass

        # Read credentials file
        with open(self.credentials_file) as f:
            for line in f.readlines():
                key_value = line.strip().split(':')
                if len(key_value) == 2:
                    self.credentials[key_value[0]] = key_value[1]

        # Open connection to KaBOB using provided credentials
        self.log.debug("Connecting to KaBOB --" +
                       "host:'%s' port:%s" % (self.credentials[HOST], self.credentials[PORT]))
        self.kabob = ag_connect(self.credentials[RELEASE],
                                host=self.credentials[HOST],
                                port=int(self.credentials[PORT]),
                                user=self.credentials[USER],
                                password=self.credentials[PASSWORD],
                                create=False,
                                clear=False)

        self.initialize_nodes()

        return self

    def initialize_nodes(self):
        self.BIO = self.kabob.namespace('bio')
        self.ICE = self.kabob.namespace('ice')
        self.OBO = self.kabob.namespace("http://purl.obolibrary.org/obo/")
        self.OBOINOWL = self.kabob.namespace("http://www.geneontology.org/formats/oboInOwl#")
        self.CCP_EXT = self.kabob.namespace("http://ccp.ucdenver.edu/obo/ext/")
        self.CCP_BNODE = self.kabob.namespace("http://ccp.ucdenver.edu/bnode/")
        self.NCBITAXON = self.kabob.namespace("http://purl.obolibrary.org/obo/ncbitaxon#")

        self.PART_OF = self.OBO.BFO_0000050
        self.HAS_PART = self.OBO.BFO_0000051
        self.DENOTES = self.OBO.IAO_0000219
        self.HAS_PARTICIPANT = self.OBO.RO_0000057
        self.TRANSPORTS = self.OBO.RO_0002313
        self.CAUSES = self.OBO.RO_0003302
        self.XREF = self.OBOINOWL.hasDbXref
        self.ID = self.OBOINOWL.id
        self.OBONAMESPACE = self.OBOINOWL.hasOBONamespace
        self.DEFINITION = self.OBO.IAO_0000115
        self.EXACTSYNONYM = self.OBOINOWL.hasExactSynonym
        self.HAS_RANK = self.NCBITAXON.has_rank

        # KaBOB Nodes of Interest
        self.BP_root = self.OBO.GO_0008150
        self.MF_root = self.OBO.GO_0003674
        self.CC_root = self.OBO.GO_0005575
        self.PRO_root = self.OBO.PR_000000001
        self.localization_process = self.OBO.GO_0051179
        self.binding_process = self.OBO.GO_0005488
        self.interaction = self.OBO.MI_0000
        self.physical_association = self.OBO.MI_0915
        self.apoptotic_process = self.OBO.GO_0006915
        self.p53 = self.OBO.PR_P04637
        self.cytochrome_C = self.OBO.PR_P08574

        # Ignore these relations when making slots
        self.CUSTOM_RELATIONS_TO_IGNORE = [OWL.DISJOINTWITH,
                                           self.HAS_RANK,
                                           OWL.INTERSECTIONOF,
                                           self.kabob.createURI(namespace=RDF.NAMESPACE, localname='subClassOf')]
        self.NOT_A_SLOT = [RDF.TYPE,
                           RDFS.SUBCLASSOF,
                           RDFS.LABEL,
                           self.XREF,
                           self.ID,
                           self.DEFINITION,
                           self.EXACTSYNONYM,
                           RDFS.COMMENT,
                           self.OBONAMESPACE,
                           OWL.EQUIVALENTCLASS,
                           self.DENOTES] + self.CUSTOM_RELATIONS_TO_IGNORE

    def __exit__(self, t, value, traceback):
        """
        Called when the "with" statement concludes. Safely closes connection to KaBOB and caches results
        :param t:
        :param value:
        :param traceback:
        :return: None
        """
        self.kabob.close()

        self.log.debug("Closed KaBOB")

        if self.cache_dir:
            pickle.dump(self.cached_statements,
                        open("%s/statements.pickle" % self.cache_dir, "wb"))
            pickle.dump(self.mops,
                        open("%s/mops.pickle" % self.cache_dir, "wb"))

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
                if node not in self.mops:
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

        if node in self.mops:  # No need to mopify if it has already been mopified
            return node
        else:
            is_trivial = not self.is_bio(node)
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

        if parents and self.is_bio_instance(node, node_type):
            warnings.warn("\t" * depth + str(mop_label) + " is an instance and a subClass")

        self.mops.add_frame(node, label=mop_label)

        if not is_trivial or depth < self.max_depth:
            if equivalent_class == node:
                [self.mops.add_equivalent_frame(node, self.mopify(equivalent, depth=depth + 1))
                 for equivalent in self.equivalent_classes[equivalent_class] if equivalent != node]
            else:
                self.mops.add_equivalent_frame(node, equivalent_class)

            [self.mops.add_abstraction(equivalent_class,
                                       self.mopify(parent, depth=depth + 1)) for parent in parents]
            [self.mops.add_slot(equivalent_class,
                                role,
                                self.get_role_name(role),
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
                if p.getURI() == RDFS.SUBCLASSOF:
                    # Here, we check to see if the parent is a restriction.
                    # If it is, we add it as a slot.
                    # Otherwise, we add it as a parent.
                    is_restriction, restriction_property, restriction_value = self.check_restriction(o)
                    if is_restriction:
                        slots.append((restriction_property, restriction_value))
                    else:
                        parents.append(o)

                elif p.getURI() not in self.NOT_A_SLOT:
                    slots.append((p, o))

            if p.getURI() == RDFS.LABEL and isinstance(o, Literal):
                labels.append(str(o.getLabel()))

            elif p.getURI() == OWL.EQUIVALENTCLASS:
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

            elif p.getURI() == RDF.TYPE:
                node_type = o

        if not equivalent_class:
            self.equivalent_classes[node] = {node}
            equivalent_class = node

        if self.is_bio_instance(node, node_type):
            mop_label: str = self.get_instance_node_label(node, labels)
        else:
            mop_label: str = self.get_node_label(node, labels)

        return mop_label, parents, slots, node_type, equivalent_class

    def check_restriction(self, o):
        parent_statements = self.get_statements(o)
        is_restriction = False
        restriction_property = None
        restriction_value = None
        for parent_statement in parent_statements:
            parent_o = parent_statement.getObject()
            parent_p = parent_statement.getPredicate()
            if parent_p.getURI() == RDF.TYPE:
                if parent_o.getURI() == OWL.RESTRICTION:
                    is_restriction = True
            elif parent_p.getURI() == OWL.ONPROPERTY:
                restriction_property = parent_o
            elif parent_p.getURI() == OWL.SOMEVALUESFROM:
                restriction_value = parent_o
        return is_restriction, restriction_property, restriction_value

    """
    CHECKERS
    """

    def is_bio_instance(self, node: Value, node_type) -> bool:
        return self.is_bio(node) and node_type

    def is_bio(self, node: Value) -> bool:
        return isinstance(node, URI) and node.getNamespace() == self.BIO

    def is_ice(self, node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == self.ICE

    """
    GETTERS
    """

    def get_bio_world(self):
        if self.cache_dir:
            try:
                self.bio_world = pickle.load(open("%s/bio_world.pickle" % self.cache_dir, "rb"))
            except FileNotFoundError:
                self.log.warning("Collecting all bio world nodes")
                self.bio_world = self.get_objects(None, self.DENOTES)
                pickle.dump(self.bio_world, open("%s/bio_world.pickle" % self.cache_dir, "wb"))

            return self.bio_world

    def get_instance_node_label(self, node: URI or Literal, labels: List) -> str:
        return "%s - " % self.get_node_label(self.get_node_type(node), labels)

    @staticmethod
    def get_node_label(node: URI or Literal, labels: List) -> str:
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
            with self.kabob.getStatements(subject=s, predicate=p, object=o) as statements:
                statements = statements.asList()
                if s and not p and not o:
                    self.cached_statements[s] = statements
        return statements

    def get_node_type(self, node: Value) -> URI or Literal:
        return self.get_object(s=node, p=RDF.TYPE)

    def get_bio(self, node: URI) -> Value:
        if self.is_ice(node):
            return self.get_ice_to_bio(node)
        else:
            subjects = self.get_subjects(o=node, p=self.DENOTES)
            for subject in subjects:
                if self.is_ice(subject):
                    return self.get_ice_to_bio(subject)

    def get_ice_to_bio(self, node: Value) -> Value:
        objects = self.get_objects(s=node, p=self.DENOTES)
        for _object in objects:
            if self.is_bio(_object):
                return _object

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

    def get_role_name(self, node: URI or Literal) -> str:
        return self.get_node_label(node, self.get_labels(node))

    def get_labels(self, node: URI or Literal):
        return [str(o.getLabel()) for o in self.get_objects(node, RDFS.LABEL)]

    def get_equivalent_classes(self, node: Value) -> List[Value]:
        return self.get_objects(s=node, p=OWL.EQUIVALENTCLASS)
