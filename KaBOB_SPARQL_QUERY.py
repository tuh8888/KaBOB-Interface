import AllegroGraphRepositoryInterface
from franz.openrdf.query.query import QueryLanguage
from franz.openrdf.repository.repositoryconnection import RepositoryConnection
from franz.openrdf.vocabulary import OWL, RDF, RDFS
import uuid


class KaBOBSPARQLQuery:

    def __init__(self, interface: AllegroGraphRepositoryInterface):
        self.interface = interface
        self.triples = []
        self.selections = []

    def make_query_string(self):
        query_string = "SELECT"
        for selection in self.selections:
            query_string += " ?"
            query_string += selection

        query_string += " WHERE{\n"
        contains_unbound_var = [True for _ in self.selections]
        for triple in self.triples:
            if isinstance(triple, tuple):
                query_string += "\t%s %s %s .\n" % triple
                for i, (is_unbound, selection) in enumerate(zip(contains_unbound_var, self.selections)):
                    if "?" + selection in triple:
                        contains_unbound_var[i] = False
            else:
                query_string += "\t%s\n" % triple

        if True in contains_unbound_var:
            raise Exception("Contains unbound variable")

        query_string += "}"

        return query_string

    def make_triple(self, s, p, o):
        self.triples.append(("?%s" % s if isinstance(s, str) else str(s),
                             "?%s" % p if isinstance(p, str) else str(p),
                             "?%s" % o if isinstance(o, str) else str(o)
                             ))

    def apply_restriction(self, svf, op, targets):
        restriction_var = "restriction_" + uuid.uuid4().hex[:6].upper()
        self.make_triple(restriction_var, OWL.SOMEVALUESFROM, svf)
        self.make_triple(restriction_var, OWL.ONPROPERTY, op)
        self.make_triple(restriction_var, RDF.TYPE, OWL.RESTRICTION)
        for target in targets:
            self.make_triple(target, RDFS.SUBCLASSOF, restriction_var)

    def run(self, conn:RepositoryConnection):
        query_string = self.make_query_string()
        print("Query:\n%s" % query_string)
        print()

        tuple_query = conn.prepareTupleQuery(QueryLanguage.SPARQL, query_string)
        result = tuple_query.evaluate()
        print("Number of results: %d" % len(result))

        return result

    def set_selections(self, selections):
        self.selections = selections

    def add_filter(self, s, p, o):
        self.triples.append("filter (%s %s %s)" % ("?%s" % s if isinstance(s, str) else str(s),
                                                   str(p),
                                                   "?%s" % o if isinstance(o, str) else str(o)))

