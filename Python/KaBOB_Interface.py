import logging
import warnings
from typing import List, Callable
import networkx as nx

from franz.openrdf.connect import ag_connect
from franz.openrdf.model import Literal, Statement, Value
from franz.openrdf.model import URI
from franz.openrdf.model.value import Resource
from franz.openrdf.repository.repository import Repository
from franz.openrdf.repository.repositoryconnection import RepositoryConnection
from franz.openrdf.sail.allegrographserver import AllegroGraphServer

import KaBOB_Constants
from MOPs import MOPs

logging.basicConfig(level=logging.DEBUG)


class InstanceAndSuperClassesException(Warning):
    pass


class KaBOBInterface:
    log = logging.getLogger('KaBOBInterface')

    KaBOB_IDs = "kabob_ids"

    def __init__(self, conn: RepositoryConnection, max_depth=None):
        self.max_depth = max_depth
        self.mops = MOPs()
        self.kabob = conn
        [conn.setNamespace(name, value) for name, value in KaBOB_Constants.NAMESPACE_ASSOCIATIONS.items()]
        self.role_fillers = {}

    def draw(self, layout: Callable=nx.spring_layout):
        self.mops.draw_mops(layout=layout)

    def mopify(self, mop: str or URI, depth: int=0) -> URI or Literal:
        node: URI or Literal = mop \
            if isinstance(mop, URI) or isinstance(mop, Literal) \
            else self.create_uri(mop)

        if not self.is_mopifyable(node):
            return node
        elif node in self.mops:
            return node
        elif not self.is_bio(node):
            self.log.warning("\t" * depth + "Trivial mopification of non-BIO-world node %s" % node)
            return self.create_kabob_mop(node, depth, is_trivial=True)
        # elif self.is_rdf_list(node):
        #     return self.rdf_to_list(node, depth)`
        else:
            return self.create_kabob_mop(node, depth)

    def create_kabob_mop(self, node: URI or Literal, depth: int, is_trivial: bool=False) -> URI or Literal:
        mop_name: str = self.instance_name(node) if self.is_bio_instance(node) else self.node_print_name(node)
        self.log.debug("\t" * depth + "> " + mop_name)
        if not is_trivial and (self.max_depth is None or depth < self.max_depth):
            superclasses = self.get_superclasses(node)
            parents = []
            if superclasses:
                for superclass in superclasses:
                    if not self.is_restriction(superclass):
                        parents.append(superclass)

            if parents and self.is_bio_instance(node):
                warnings.warn(str(mop_name) + " is an instance and a subClass")

            self.mops.add_frame(node, label=mop_name,
                                abstractions=[self.mopify(parent, depth + 1) for parent in parents])
            self.create_slots(node, depth + 1)
            # self.infer_inverse_relations(name, depth)

        else:
            self.mops.add_frame(node, label=mop_name)
        self.log.debug("\t" * depth + "< " + mop_name)

        return node

    def create_slots(self, main_node: Value, depth: int) -> None:
        equivalent_nodes = [main_node]  # + self.get_equivalent_classes(main_node)
        # self.mopsManager.add_slot(main_node, self.KaBOB_IDs, self.KaBOB_IDs, equivalent_nodes)

        for node in equivalent_nodes:
            superclasses = self.get_superclasses(node)
            if superclasses:
                for superclass in superclasses:
                    if self.is_restriction(superclass):
                        restriction = superclass
                        role = self.get_restriction_property(restriction)
                        self.mops.add_slot(main_node,
                                           role,
                                           self.get_role_name(role),
                                           self.mopify(self.get_restriction_value(restriction), depth))
            for edge in self.get_outgoing_edges(node):
                if edge.getURI() not in KaBOB_Constants.NOT_A_SLOT:
                    self.mops.add_slot(main_node,
                                       edge,
                                       self.get_role_name(edge),
                                       [self.mopify(filler, depth)
                                               for filler in self.agraph_get_objects(node, edge)])

    def is_bio_instance(self, node: URI) -> bool:
        return self.is_bio(node) and self.get_node_type(node)

    @staticmethod
    def is_bio(node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == KaBOB_Constants.get_namespace(KaBOB_Constants.BIO_NAMESPACE)

    @staticmethod
    def is_ice(node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == KaBOB_Constants.get_namespace(KaBOB_Constants.ICE_NAMESPACE)

    def instance_name(self, node: URI or Literal) -> str:
        return "%s - " % self.node_print_name(self.get_node_type(node))

    def node_print_name(self, node: URI or Literal or str) -> str:
        labels = [o.getLabel() for o in self.agraph_get_objects(s=node, p=KaBOB_Constants.LABEL) if
                  isinstance(o, Literal)]
        _id = self.agraph_get_object(s=node, p=KaBOB_Constants.ID)

        local_name = node
        if isinstance(node, URI):
            local_name = node.getLocalName()
        elif isinstance(node, Literal):
            node.getLabel()

        def find_lowercase_label(_labels):
            for label in _labels:
                if label.islower():
                    return label
            return False

        if labels:
            return str(find_lowercase_label(labels) or labels[0])
        if _id:
            return str(_id.getLabel())
            # return _id or part_to_string(node, format="concise")
        else:
            return str(local_name)

    def agraph_get_objects(self, s: URI or str, p: URI or str) -> List[URI or Literal]:
        s = self.convert_to_value(s)
        p = self.convert_to_value(p)
        statements = self.agraph_get_statements(s=s, p=p)
        return [] if not statements else [statement.getObject() for statement in statements]

    def convert_to_value(self, value: URI or str or Literal):
        value = value if not value or isinstance(value, URI) or isinstance(value, Literal) else self.create_uri(value)
        return value

    def agraph_get_statements(self, s: Value = None, p: URI = None, o: Value = None) -> List[Statement]:
        s = self.convert_to_value(s)
        p = self.convert_to_value(p)
        o = self.convert_to_value(o)
        with self.kabob.getStatements(subject=s, predicate=p, object=o) as statements:
            return statements.asList()

    def agraph_get_object(self, s: Value, p: URI) -> URI or Literal:
        objects = self.agraph_get_objects(s, p)
        return objects[0] if objects else None

    def agraph_get_subjects(self, o: URI or str, p: URI or str, full_statement: bool = False) -> List[Value or Literal]:
        o = self.convert_to_value(o)
        p = self.convert_to_value(p)
        statements = self.agraph_get_statements(o=o, p=p)
        return [] if not statements or full_statement else [statement.getSubject() for statement in statements]

    def agraph_get_subject(self, o, p):
        subjects = self.agraph_get_subjects(o, p)
        return subjects[0] if subjects else None

    def get_superclasses(self, node):
        return self.agraph_get_objects(s=node, p=KaBOB_Constants.SUBCLASSOF)

    def is_restriction(self, node):
        _type = self.get_node_type(node)
        return _type and _type.getURI() == KaBOB_Constants.get_full_uri(KaBOB_Constants.RESTRICTION)

    def get_node_type(self, node: Value) -> URI or Literal:
        return self.agraph_get_object(s=node, p=KaBOB_Constants.TYPE)

    def restriction_property(self, node):
        return self.agraph_get_object(s=node, p=KaBOB_Constants.RESTRICTION_PROPERTY)

    def create_uri(self, name: str) -> URI:
        namespace, local_name = self.split_name(name)
        return self.kabob.createURI(namespace=namespace, localname=local_name) if local_name else self.kabob.createURI(
            name)

    @staticmethod
    def split_name(name):
        """

        :type name: str
        """
        namespace, local_name = name.split(":")
        namespace = KaBOB_Constants.get_namespace(namespace)
        return (namespace, local_name) if namespace else (name, None)

    def bio(self, node: URI) -> Value:
        if self.is_ice(node):
            return self.ice_to_bio(node)
        else:
            subjects = self.agraph_get_subjects(o=node, p=KaBOB_Constants.DENOTES)
            for subject in subjects:
                if self.is_ice(subject):
                    return self.ice_to_bio(subject)

    def ice_to_bio(self, node: Value) -> Value:
        objects = self.agraph_get_objects(s=node, p=KaBOB_Constants.DENOTES)
        for _object in objects:
            if self.is_bio(_object):
                return _object

    def statement_to_slot(self, statement):
        pass

    # def infer_inverse_relations(self, mop, depth):
    #     """
    #
    #     :type depth: int
    #     :type mop: str
    #     """
    #     for slot in self:
    #         inverse_relation = self.get_inverse_relation(slot.role)
    #         if inverse_relation and self.mopsManager.is_mop(slot.filler):
    #             print("\t" * depth + "Adding inverse: %s %s %s" % (slot.filler, inverse_relation, mop))
    #             mop.add_slot(slot.filler, inverse_relation)

    # def get_inverse_relation(self, role: URI):
    #     if not role == self.KaBOB_IDs:
    #         edge = self.get_resource()
    #         inverse = edge and (self.agraph_get_object(s=edge, p=KaBOB_Constants.INVERSE_OF) or
    #                             self.agraph_get_subject(o=edge, p=KaBOB_Constants.INVERSE_OF))
    #         if inverse:
    #             return self.get_role_name(inverse)
    #         else:
    #             return None
    #     else:
    #         return None

    def rdf_list_p(self, node):
        """

        :type node: URI
        """
        _type = self.get_node_type(node)
        return _type and _type == KaBOB_Constants.LIST

    def rdf_to_list(self, node, depth, max_depth: int):
        first = self.agraph_get_object(s=node, p=KaBOB_Constants.FIRST)
        rest = self.agraph_get_object(s=node, p=KaBOB_Constants.REST)

        if first:
            return [self.mopify(first, depth + 1)] + [] \
                if rest == KaBOB_Constants.NIL else self.rdf_to_list(node, depth + 1, max_depth)
        else:
            self.log.warning("\t" * depth + "List has no node first: %s" % node)

    def mop_to_nodes(self, mop):
        return self.mops.get_filler(mop, self.KaBOB_IDs)

    # def lookup_mop(self, key):
    #     return self.find_mop(key) or (
    #             (self.is_upi(key) or self.get_upi(key, is_error=False)) and self.mopsManager.mops.get(key))

    def get_role_name(self, node: URI or Literal) -> str:
        return self.node_print_name(node)

    @staticmethod
    def is_mopifyable(node: URI) -> bool:
        return isinstance(node, Resource)

    def is_rdf_list(self, node):
        """

        :type node: URI
        """
        _type = self.get_node_type(node)
        return _type and _type == KaBOB_Constants.LIST

    def get_equivalent_classes(self, node: Value) -> List[Value]:
        return self.agraph_get_objects(s=node, p=KaBOB_Constants.EQUIVALENT_CLASS)

    def get_outgoing_edges(self, node: Value) -> List[URI]:
        """

        :type node: URI
        """
        return [statement.getPredicate() for statement in self.agraph_get_statements(s=node, p=None)]

    def get_incoming_edges(self, node):
        """

        :type node: URI
        """
        return self.agraph_get_subjects(o=node, p=None, full_statement=True)

    def get_restriction_property(self, restriction: URI or Literal) -> URI or Literal:
        return self.agraph_get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_PROPERTY)

    def get_restriction_value(self, restriction: Value):
        return self.agraph_get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_VALUE)

    def is_upi(self, key):
        pass

    def get_upi(self, key, is_error):
        pass

    def is_upi_type(self, node: URI, _type: str) -> bool:
        pass


class OpenKaBOB:
    log = logging.getLogger('OpenKaBOB')
    HOST = "HOST"
    PORT = "PORT"
    USER = "USER"
    PASSWORD = "PASSWORD"
    CATALOG = "CATALOG"
    RELEASE = "RELEASE"
    INSTANCE_RELEASE = "INSTANCE_RELEASE"

    def __init__(self, credentials_file):
        self.kabob = None
        self.kabob_repository = None
        self.credentials = {}
        with open(credentials_file) as f:
            for line in f.readlines():
                key_value = line.strip().split(':')
                if len(key_value) == 2:
                    self.credentials[key_value[0]] = key_value[1]

    def connect_to_kabob(self):
        self.log.debug("Connecting to AllegroGraph server --" +
                       "host:'%s' port:%s" % (self.credentials[self.HOST], self.credentials[self.PORT]))
        kabob_server = AllegroGraphServer(self.credentials[self.HOST], int(self.credentials[self.PORT]),
                                          self.credentials[self.USER], self.credentials[self.PASSWORD])

        if self.credentials[self.CATALOG] in kabob_server.listCatalogs() or self.credentials[self.CATALOG] == '':
            kabob_catalog = kabob_server.openCatalog(self.credentials[self.CATALOG])

            if self.credentials[self.RELEASE] in kabob_catalog.listRepositories():
                mode = Repository.OPEN
                self.kabob_repository = kabob_catalog.getRepository(self.credentials[self.RELEASE], mode)
                self.kabob = self.kabob_repository.getConnection()

                # print('Repository %s is up!' % self.kabob_repository.getDatabaseName())
                # print('It contains %d statement(s).' % self.kabob.size())
            else:
                print('%s does not exist' % self.credentials[self.RELEASE])
                print("Available repositories in catalog '%s':" % kabob_catalog.getName())
                for repo_name in kabob_catalog.listRepositories():
                    print('  - ' + repo_name)

        else:
            print('%s does not exist' % self.credentials[self.CATALOG])
            print('Available catalogs:')
            for cat_name in kabob_server.listCatalogs():
                if not cat_name:
                    print('  - <root catalog>')
                else:
                    print('  - ' + str(cat_name))

    # Potentially better alternate method
    def alt_connect_to_kabob(self):
        self.kabob = ag_connect(self.credentials[self.RELEASE],
                                host=self.credentials[self.HOST],
                                port=int(self.credentials[self.PORT]),
                                user=self.credentials[self.USER],
                                password=self.credentials[self.PASSWORD],
                                create=False,
                                clear=False)

        print('Statements in KaBOB:', self.kabob.size())

    def close_kabob(self):
        self.kabob.close()
        self.kabob_repository.shutDown()
        self.log.debug("Closed %s" % self.kabob_repository.getDatabaseName())

    def __enter__(self):
        self.connect_to_kabob()
        return self.kabob

    def __exit__(self, t, value, traceback):
        self.close_kabob()
