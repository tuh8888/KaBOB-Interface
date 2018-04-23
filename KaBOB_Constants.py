"""
Constants for KaBOB Interface
"""


def get_namespace(namespace):
    return NAMESPACE_ASSOCIATIONS.get(namespace)


def get_full_uri(concise_name):
    namespace, local_name = concise_name.split(':')
    return get_namespace(namespace) + local_name


""""
NAMESPACES
"""

BIO_NAMESPACE = 'bio'
ICE_NAMESPACE = 'ice'

NAMESPACE_ASSOCIATIONS = {'rdfs': "http://www.w3.org/2000/01/rdf-schema#",
                          'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                          'owl': "http://www.w3.org/2002/07/owl#",
                          'obo': "http://purl.obolibrary.org/obo/",
                          'oboInOwl': "http://www.geneontology.org/formats/oboInOwl#",
                          'ccp.ext': "http://ccp.ucdenver.edu/obo/ext/",
                          'ccp.bnode': "http://ccp.ucdenver.edu/bnode/",
                          'ice': "http://ccp.ucdenver.edu/kabob/ice/",
                          'bio': "http://ccp.ucdenver.edu/kabob/bio/"}

"""
RELATIONS
"""

NIL = get_full_uri('rdf:nil')
SUBCLASSOF = get_full_uri('rdfs:subClassOf')
LABEL = get_full_uri('rdfs:label')
PART_OF = get_full_uri('obo:BFO_0000050')
HAS_PART = get_full_uri('obo:BFO_0000051')
DENOTES = get_full_uri('obo:IAO_0000219')
HAS_PARTICIPANT = get_full_uri('obo:RO_0000057')
TRANSPORTS = get_full_uri('obo:RO_0002313')
CAUSES = get_full_uri('obo:RO_0003302')
TYPE = get_full_uri('rdf:type')
XREF = get_full_uri('oboInOwl:hasDbXref')
ID = get_full_uri('oboInOwl:id')
OBONAMESPACE = get_full_uri('oboInOwl:hasOBONamespace')
DEFINITION = get_full_uri('obo:IAO_0000115')
EXACTSYNONYM = get_full_uri('oboInOwl:hasExactSynonym')
COMMENT = get_full_uri('rdfs:comment')
EQUIVALENTCLASS = get_full_uri('owl:equivalentClass')
RESTRICTION_PROPERTY = get_full_uri('owl:onProperty')
RESTRICTION_VALUE = get_full_uri('owl:someValuesFrom')
INVERSE_OF = get_full_uri('owl:inverseOf')
RESTRICTION = get_full_uri('owl:Restriction')
EQUIVALENT_CLASS = get_full_uri('owl:equivalentClass')
FIRST = get_full_uri('rdf:first')
REST = get_full_uri('rdf:rest')
INTERSECTIONOF = get_full_uri('owl:intersectionOf')
DISJOINTWITH = get_full_uri('owl:disjointWith')
LIST = get_full_uri('rdf:List')

# Ignore these relations when making slots

NOT_A_SLOT = [TYPE,
              SUBCLASSOF,
              LABEL,
              XREF,
              ID,
              DEFINITION,
              EXACTSYNONYM,
              COMMENT,
              OBONAMESPACE,
              EQUIVALENTCLASS,
              DENOTES]
