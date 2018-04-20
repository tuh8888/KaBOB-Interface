"""
Constants for KaBOB Interface
"""

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

SUBCLASSOF = 'rdfs:subClassOf'
LABEL = 'rdfs:label'
PART_OF = 'obo:BFO_0000050'
HAS_PART = 'obo:BFO_0000051'
DENOTES = 'obo:IAO_0000219'
HAS_PARTICIPANT = 'obo:RO_0000057'
TRANSPORTS = 'obo:RO_0002313'
CAUSES = 'obo:RO_0003302'
TYPE = 'rdf:type'
XREF = 'oboInOwl:hasDbXref'
ID = 'oboInOwl:id'
OBONAMESPACE = 'oboInOwl:hasOBONamespace'
DEFINITION = 'obo:IAO_0000115'
EXACTSYNONYM = 'oboInOwl:hasExactSynonym'
COMMENT = 'rdfs:comment'
EQUIVALENTCLASS = 'owl:equivalentClass'
RESTRICTION_PROPERTY = 'owl:onProperty'
RESTRICTION_VALUE = 'owl:someValuesFrom'
INVERSE_OF = 'owl:inverseOf'
RESTRICTION = 'owl:Restriction'
EQUIVALENT_CLASS = 'owl:equivalentClass'
FIRST = 'rdf:first'
REST = 'rdf:rest'
INTERSECTIONOF = 'owl:intersectionOf'
DISJOINTWITH = 'owl:disjointWith'
LIST = 'rdf:List'
NIL = 'rdf:nil'



def get_namespace(namespace):
    return NAMESPACE_ASSOCIATIONS.get(namespace)


def get_full_uri(concise_name):
    namespace, local_name = concise_name.split(':')
    return get_namespace(namespace) + local_name

# Ignore these relations when making slots

NOT_A_SLOT = [get_full_uri(TYPE),
              get_full_uri(SUBCLASSOF),
              get_full_uri(LABEL),
              get_full_uri(XREF),
              get_full_uri(ID),
              get_full_uri(DEFINITION),
              get_full_uri(EXACTSYNONYM),
              get_full_uri(COMMENT),
              get_full_uri(OBONAMESPACE),
              get_full_uri(EQUIVALENTCLASS),
              get_full_uri(DENOTES)]
