import logging
import pickle

from KaBOB_SPARQL_QUERY import KaBOBSPARQLQuery
from franz.openrdf.model import URI
from franz.openrdf.model import Value
from franz.openrdf.vocabulary import RDF, RDFS, OWL

from AllegroGraphRepositoryInterface import Interface


class KaBOBInterface(Interface):
    log = logging.getLogger('KaBOBInterface')

    BIO = ICE = OBO = OBOINOWL = CCP_EXT = CCP_BNODE = NCBITAXON = PART_OF = HAS_PART = DENOTES = HAS_PARTICIPANT = \
        TRANSPORTS = CAUSES = XREF = ID = OBONAMESPACE = DEFINITION = EXACTSYNONYM = BP_root = MF_root = \
        CC_root = PRO_root = localization_process = binding_process = interaction = physical_association = \
        apoptotic_process = p53 = cytochrome_C = CUSTOM_RELATIONS_TO_IGNORE = NOT_A_SLOT = DC = DCTERMS = ERR = FN = \
        FOAF = FTI = KEYWORD = ND = NDFN = SKOS = XS = XSD = drugbank_identifier = reactome_identifier = None

    def __init__(self, credentials_file: str, max_depth=1000, cache_dir=None):
        super().__init__(credentials_file, max_depth=max_depth, cache_dir=cache_dir)
        self.bio_world = None

    def initialize_namespaces(self):
        self.BIO = self.conn.namespace("http://ccp.ucdenver.edu/kabob/bio/")
        self.CCP_BNODE = self.conn.namespace("http://ccp.ucdenver.edu/bnode/")
        self.CCP_EXT = self.conn.namespace("http://ccp.ucdenver.edu/obo/ext/")
        self.DC = self.conn.namespace("http://purl.org/dc/elements /11/")
        self.DCTERMS = self.conn.namespace("http://purl.org/dc/terms/")
        self.ERR = self.conn.namespace("http://www.w3.org/2005/xqt-errors#")
        self.FN = self.conn.namespace("http://www.w3.org/2005 /xpath-functions#")
        self.FOAF = self.conn.namespace("http://xmlns.com/foaf /01/")
        self.FTI = self.conn.namespace("http://franz.com/ns/allegrograph/2.2/textindex/")
        self.ICE = self.conn.namespace("http://ccp.ucdenver.edu/kabob/ice/")
        self.KEYWORD = self.conn.namespace("http://franz.com/ns/keyword#")
        self.ND = self.conn.namespace("http://franz.com/ns/allegrograph/5.0/geo/nd#")
        self.NDFN = self.conn.namespace("http://franz.com/ns/allegrograph/5.0/geo/nd/fn#")
        self.OBOINOWL = self.conn.namespace("http://www.geneontology.org/formats/oboInOwl#")
        self.SKOS = self.conn.namespace("http://www.w3.org/2004/02/skos/core#")
        self.XS = self.conn.namespace("http://www.w3.org/2001/XMLSchema#")
        self.XSD = self.conn.namespace("http://www.w3.org/2001/XMLSchema#")

        self.OBO = self.conn.namespace("http://purl.obolibrary.org/obo/")

    def initialize_relations(self):
        super(KaBOBInterface, self).initialize_relations()
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

        HAS_RANK = self.get_node("ncbitaxon#has_rank")
        ONLY_IN_TAXON = self.get_bio_node(self.OBO.RO_0002160)

        CUSTOM_RELATIONS_TO_IGNORE = [OWL.DISJOINTWITH,
                                      HAS_RANK,
                                      OWL.INTERSECTIONOF,
                                      self.conn.createURI(namespace=RDF.NAMESPACE, localname='subClassOf'),
                                      self.XREF, self.ID, self.DEFINITION,
                                      self.EXACTSYNONYM, RDFS.COMMENT, self.OBONAMESPACE,
                                      self.DENOTES]

        self.mops.add_special_node_attribute(ONLY_IN_TAXON, self.get_label(ONLY_IN_TAXON))

        self.NOT_A_SLOT.extend(CUSTOM_RELATIONS_TO_IGNORE)

    def initialize_nodes(self):
        super(KaBOBInterface, self).initialize_relations()
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
        self.drugbank_identifier = self.CCP_EXT.IAO_EXT_0001309
        self.reactome_identifier = self.CCP_EXT.IAO_EXT_0001643



    """
    CHECKERS
    """

    def is_instance(self, node: Value, node_type) -> bool:
        return self.is_bio(node) and node_type

    def is_bio(self, node: Value) -> bool:
        return isinstance(node, URI) and node.getNamespace() == self.BIO.__class__.getNamespace()

    def is_ice(self, node: Value) -> bool:
        return isinstance(node, URI) and \
               node.getNamespace() == self.ICE.__class__.getNamespace()

    def is_node_trivial(self, node: Value):
        return not self.is_bio(node)

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

    def get_bio_node(self, node: URI or str) -> Value:
        if isinstance(node, str):
            node = self.get_node(node)
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

    def get_node(self, node_name: str):
        split_node_name = node_name.split(":")
        node = None
        if len(split_node_name) < 2:
            node = getattr(self.OBO, node_name)
        else:
            namespace, local_name = split_node_name
            if hasattr(self, namespace.upper()):
                namespace = getattr(self, namespace.upper())
                node = getattr(namespace, local_name)

        return node

    def get_drugbank_drug(self, drugbank_id):
        return self.get_bio_node("ice:DRUGBANK_" + drugbank_id)

    def get_drug_targets(self, drug_bank_id):
        drug = self.get_drugbank_drug(drug_bank_id)
        binding = self.get_bio_node("GO_0005488")
        has_participant = self.get_bio_node(self.HAS_PARTICIPANT)
        inheres_in = self.get_bio_node("RO_0000052")

        drug_sc = "drug_sc"
        inheres = "inheres"
        interaction = "interaction"
        target_sc = "target_sc"
        target = "target"

        selections = [target]

        query = KaBOBSPARQLQuery(self)

        query.make_triple(drug_sc, RDFS.SUBCLASSOF, drug)
        query.apply_restriction(svf=drug_sc, op=has_participant, targets=[interaction])
        query.apply_restriction(svf=drug_sc, op=inheres_in, targets=[inheres])
        query.make_triple(interaction, RDFS.SUBCLASSOF, binding)
        query.apply_restriction(svf=target_sc, op=has_participant, targets=[interaction])
        query.make_triple(target_sc, RDFS.SUBCLASSOF, target)

        query.add_filter(target, "!=", drug)

        query.set_selections(selections)

        result = query.run(self.conn)

        return [binding_set.getValue(selection) for binding_set in result for selection in selections]

    def mopify_pathway(self, pathway_node):
        # immediately_preceded_by_uri = "ice:RO_0002087"
        # immediately_preceded_by_bio = self.get_bio_node(immediately_preceded_by_uri)

        proper_part_restr = self.get_subjects(p=self.ONCLASS, o=pathway_node)
        bcr1 = self.get_subjects(p=RDFS.SUBCLASSOF, o=proper_part_restr)
        self.mopify(pathway_node)
        [self.mopify(bcr) for bcr in bcr1]

    def get_all_drugs(self):
        db_id_scs = self.get_subjects(o=self.drugbank_identifier, p=RDFS.SUBCLASSOF)
        return [self.get_bio_node(db_id_sc) for db_id_sc in db_id_scs]

    def get_all_pathways(self):
        reactome_ice_id = "reactome_ice_id"
        pathway = "pathway"
        selections = [pathway]

        query = KaBOBSPARQLQuery(self)
        query.make_triple(reactome_ice_id, RDFS.SUBCLASSOF, self.reactome_identifier)
        query.make_triple(reactome_ice_id, self.DENOTES, pathway)
        query.set_selections(selections)

        result = query.run(self.conn)
        return [binding_set.getValue(selection) for binding_set in result for selection in selections]


def test_with_lipitor():
    with KaBOBInterface("KaBOB_credentials.txt") as interface:
        lipitor = "DB01076"
        targets = interface.get_drug_targets(lipitor)
        for target in targets:
            print(target)


if __name__ == "__main__":
    test_with_lipitor()