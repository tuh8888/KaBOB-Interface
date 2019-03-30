from KaBOBInterface import KaBOBInterface
from franz.openrdf.model import URI
from franz.openrdf.vocabulary import RDFS
import networkx as nx

REACTOME = "<http://ekw.ucdenver.edu/reactome_bio>"


def get_reactome_label(interface: KaBOBInterface, node: URI):
    denoters = [statement.getSubject() for statement in interface.get_statements(p=interface.DENOTES, o=node)]
    for d in denoters:
        labels = interface.get_statements(s=d, p=RDFS.LABEL)
        if labels:
            return labels[0].getObject().getLabel()


def mopify_reactome():
    with KaBOBInterface("KaBOB/KaBOB Interface/KaBOB_credentials.txt", cache_dir="E:/Documents/KaBOB/REACTOME/pickles") as interface:
        reactome_statements = interface.conn.getStatements(predicate=interface.DENOTES, contexts=REACTOME)
        i = 0
        for statement in reactome_statements:
            print("*************%d*****************" % i)
            i += 1
            o = statement.getObject()

            o_label = get_reactome_label(interface, o)

            interface.mopify(o)
            nx.set_node_attributes(interface.mops.abstractions, {o: o_label}, name=interface.mops.attribute_label)
            if i == 100:
                break


if __name__ == "__main__":
    mopify_reactome()
