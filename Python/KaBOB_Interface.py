import logging
import warnings
from typing import List

from franz.openrdf.connect import ag_connect
from franz.openrdf.model import Literal, Statement, Value
from franz.openrdf.model import URI
from franz.openrdf.repository.repository import Repository
from franz.openrdf.repository.repositoryconnection import RepositoryConnection
from franz.openrdf.sail.allegrographserver import AllegroGraphServer

import KaBOB_Constants
from MOPs import MOPsManager

logging.basicConfig(level=logging.DEBUG)


class InstanceAndSuperClassesException(Warning):
    pass


class KaBOBInterface:
    log = logging.getLogger('KaBOBInterface')

    KaBOB_IDs = "kabob_ids"

    def __init__(self, conn: RepositoryConnection):
        self.BLANK_NODE = None
        self.RESOURCE = None
        self.mopsManager = MOPsManager()
        self.kabob = conn
        [conn.setNamespace(name, value) for name, value in KaBOB_Constants.NAMESPACE_ASSOCIATIONS.items()]
        self.role_fillers = {}

    def mopify(self, node: URI or str, depth: int, max_depth: int) -> str:
        node_to_mopify: URI or Literal = node \
            if isinstance(node, URI) or isinstance(node, Literal) \
            else self.create_uri(node)

        # if not self.is_mopifyable(node):
        #     return node
        # elif self.lookup_mop(node):
        #     return self.lookup_mop(node)
        # elif not self.is_bio(node):
        #     self.log.warning("Trivial mopification of non-BIO-world node %s" % node)
        #     return self.mopsManager.to_mop(node, True)
        # elif self.is_rdf_list(node):
        #     return self.rdf_to_list(node, depth)
        # else:
        return self.create_kabob_mop(node_to_mopify, depth, max_depth)

    def create_kabob_mop(self, node: URI, depth: int, max_depth) -> str:
        mop: str = self.instance_name(node) if self.is_bio_instance(node) else self.node_print_name(node)
        self.log.debug("\t" * depth + "Mopifying " + mop)
        if not depth or depth < max_depth:
            superclasses = self.get_superclasses(node)
            parents = []
            if superclasses:
                for superclass in superclasses:
                    if not self.is_restriction(superclass):
                        parents.append(superclass)

            if parents and self.is_bio_instance(node):
                warnings.warn(mop + " is an instance and a subClass")

            self.mopsManager.add_mop(mop, abstractions=[self.mopify(parent, depth + 1, max_depth)
                                                        for parent in parents])
            self.create_slots(mop, node, depth, max_depth)
            # self.infer_inverse_relations(name, depth)

            self.log.debug("\t" * depth + "Finished mopifying " + mop)

        return mop

    def create_slots(self, mop: str, main_node: Value, depth: int, max_depth: int) -> None:
        equivalent_nodes = [main_node]  # + self.get_equivalent_classes(main_node)
        self.mopsManager.add_slot(mop, self.KaBOB_IDs, equivalent_nodes)

        for node in equivalent_nodes:
            superclasses = self.get_superclasses(node)
            if superclasses:
                for superclass in superclasses:
                    if self.is_restriction(superclass):
                        restriction = superclass
                        self.mopsManager.add_slot(mop,
                                                  self.get_role_name(self.get_restriction_property(restriction)),
                                                  self.mopify(self.get_restriction_value(restriction), depth, max_depth)
                                                  )
            for edge in self.get_outgoing_edges(node):
                if edge not in KaBOB_Constants.NOT_A_SLOT:
                    self.mopsManager.add_slot(mop, self.get_role_name(edge.getPredicate()),
                                              [self.mopify(o, depth + 1, max_depth)
                                               for o in self.agraph_get_objects(node, edge.getPredicate())])

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

    def instance_name(self, node: Value) -> str:
        return "%s - " % self.node_print_name(self.get_node_type(node))

    def node_print_name(self, node: Value) -> str:
        labels = [o.getLabel() for o in self.agraph_get_objects(s=node, p=KaBOB_Constants.LABEL)]
        _id = self.agraph_get_object(s=node, p=KaBOB_Constants.ID)
        local_name = node.getLocalName() if isinstance(node, URI) \
            else node.getLabel() if isinstance(node, Literal) else node

        def find_lowercase_label(_labels):
            for label in _labels:
                if label.islower():
                    return label
            return False

        if labels:
            return find_lowercase_label(labels) or labels[0]
        if _id:
            return _id.getLabel()
            # return _id or part_to_string(node, format="concise")
        else:
            return local_name

    def agraph_get_objects(self, s: URI or str, p: URI or str) -> List[Value]:
        s = s if not s or isinstance(s, URI) or isinstance(s, Literal) else self.create_uri(s)
        p = p if not p or isinstance(p, URI) or isinstance(p, Literal) else self.create_uri(p)
        statements = self.agraph_get_statements(s=s, p=p)
        return [] if not statements else [statement.getObject() for statement in statements]

    def agraph_get_statements(self, s: Value = None, p: URI = None, o: Value = None) -> List[Statement]:
        with self.kabob.getStatements(subject=s, predicate=p, object=o) as statements:
            return statements.asList()

    def agraph_get_object(self, s: Value, p: URI) -> Value:
        objects = self.agraph_get_objects(s, p)
        return objects[0] if objects else None

    def agraph_get_subjects(self, o: URI or str, p: URI or str, full_statement: bool = False) -> List[Value]:
        o = o if not o or isinstance(o, URI) or isinstance(o, Literal) else self.create_uri(o)
        p = p if not p or isinstance(p, URI) or isinstance(p, Literal) else self.create_uri(p)
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

    def get_node_type(self, node: Value) -> Value:
        return self.agraph_get_object(s=node, p=KaBOB_Constants.TYPE)

    def role_name(self, node):
        return self.node_print_name(node)

    def restriction_property(self, node):

        return self.agraph_get_object(s=node, p=KaBOB_Constants.RESTRICTION_PROPERTY)

    def find_or_mopify(self, node, depth, max_depth: int):
        return node in self.mopsManager.abstraction_hierarchy or self.mopify(node, depth, max_depth)

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
        """

        :type node: URI
        """
        if self.is_ice(node):
            return self.ice_to_bio(node)
        else:
            subjects = self.agraph_get_subjects(o=node, p=KaBOB_Constants.DENOTES)
            for subject in subjects:
                if self.is_ice(subject):
                    return self.ice_to_bio(subject)

    def ice_to_bio(self, node: Value) -> Value:
        """

        :type node: URI
        """
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

    def get_inverse_relation(self, role):
        """

        :type role: URI
        """
        if not role == self.KaBOB_IDs:
            edge = self.get_resource()
            inverse = edge and (self.agraph_get_object(s=edge, p=KaBOB_Constants.INVERSE_OF) or
                                self.agraph_get_subject(o=edge, p=KaBOB_Constants.INVERSE_OF))
            if inverse:
                return self.get_role_name(inverse)
            else:
                return None
        else:
            return None

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
            return [self.mopify(first, depth + 1, max_depth)] + [] \
                if rest == KaBOB_Constants.NIL else self.rdf_to_list(node, depth + 1, max_depth)
        else:
            self.log.warning("\t" * depth + "List has no node first: %s" % node)

    def mop_to_nodes(self, mop):
        return self.mopsManager.get_filler(mop, self.KaBOB_IDs)

    # def lookup_mop(self, key):
    #     return self.find_mop(key) or (
    #             (self.is_upi(key) or self.get_upi(key, is_error=False)) and self.mopsManager.mops.get(key))

    def get_role_name(self, node: Value) -> str:
        return self.node_print_name(node)

    def is_mopifyable(self, node: URI) -> bool:
        return self.is_upi_type(node, self.RESOURCE) or self.is_upi_type(node, self.BLANK_NODE)

    def is_rdf_list(self, node):
        """

        :type node: URI
        """
        _type = self.get_node_type(node)
        return _type and _type == KaBOB_Constants.LIST

    def get_equivalent_classes(self, node: Value) -> List[Value]:
        return self.agraph_get_objects(s=node, p=KaBOB_Constants.EQUIVALENT_CLASS)

    def get_outgoing_edges(self, node: Value) -> List[Statement]:
        """

        :type node: URI
        """
        return self.agraph_get_statements(s=node, p=None)

    def get_incoming_edges(self, node):
        """

        :type node: URI
        """
        return self.agraph_get_subjects(o=node, p=None, full_statement=True)

    def get_restriction_property(self, restriction: Value) -> Value:
        return self.agraph_get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_PROPERTY)

    def get_restriction_value(self, restriction: Value):
        return self.agraph_get_object(s=restriction, p=KaBOB_Constants.RESTRICTION_VALUE)

    def get_resource(self) -> Value:
        return self.RESOURCE

    def is_upi(self, key):
        pass

    def get_upi(self, key, is_error):
        pass

    def is_upi_type(self, node: URI, _type: str) -> bool:
        pass


class OpenKaBOB:
    log = logging.getLogger('OpenKaBOB')

    def __init__(self):
        self.kabob = None
        self.kabob_repository = None

    def connect_to_kabob(self):
        self.log.debug("Connecting to AllegroGraph server --" +
                       "host:'%s' port:%s" % (KaBOB_Constants.HOST, KaBOB_Constants.PORT))
        kabob_server = AllegroGraphServer(KaBOB_Constants.HOST, KaBOB_Constants.PORT,
                                          KaBOB_Constants.USER, KaBOB_Constants.PASSWORD)

        if KaBOB_Constants.CATALOG in kabob_server.listCatalogs() or KaBOB_Constants.CATALOG == '':
            kabob_catalog = kabob_server.openCatalog(KaBOB_Constants.CATALOG)

            if KaBOB_Constants.RELEASE in kabob_catalog.listRepositories():
                mode = Repository.OPEN
                self.kabob_repository = kabob_catalog.getRepository(KaBOB_Constants.RELEASE, mode)
                self.kabob = self.kabob_repository.getConnection()

                # print('Repository %s is up!' % self.kabob_repository.getDatabaseName())
                # print('It contains %d statement(s).' % self.kabob.size())
            else:
                print('%s does not exist' % KaBOB_Constants.RELEASE)
                print("Available repositories in catalog '%s':" % kabob_catalog.getName())
                for repo_name in kabob_catalog.listRepositories():
                    print('  - ' + repo_name)

        else:
            print('%s does not exist' % KaBOB_Constants.CATALOG)
            print('Available catalogs:')
            for cat_name in kabob_server.listCatalogs():
                if not cat_name:
                    print('  - <root catalog>')
                else:
                    print('  - ' + str(cat_name))

    # Potentially better alternate method
    def alt_connect_to_kabob(self):
        self.kabob = ag_connect(KaBOB_Constants.RELEASE,
                                host=KaBOB_Constants.HOST,
                                port=KaBOB_Constants.PORT,
                                user=KaBOB_Constants.USER,
                                password=KaBOB_Constants.PASSWORD,
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
