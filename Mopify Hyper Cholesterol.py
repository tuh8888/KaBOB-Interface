from Collapsing import Collapser
from KaBOBInterface import KaBOBInterface
import networkx as nx

project_dir = "Biology/Hyper Cholesterol"
credentials_file = "KaBOB/KaBOB Interface/KaBOB_credentials.txt"
hyper_cholesterol = "GO_0034383"
ldl = "ice:REACTOME_R-HSA-8964038"
REACTOME = "<http://ekw.ucdenver.edu/reactome_bio>"
mops = None
with KaBOBInterface(credentials_file) as interface:
    # bio_hyper_cholesterol = interface.get_bio_node(hyper_cholesterol)
    bio_ldl = interface.get_bio_node(ldl)

    statements_of_interest = []

    # hyper_cholesterol_statements_of_interest = interface.get_statements(s=bio_hyper_cholesterol)
    # hyper_cholesterol_statements_of_interest.extend(interface.get_statements(o=bio_hyper_cholesterol))

    # print("Hyper cholesterol is involved in %d statements of interest" % len(hyper_cholesterol_statements_of_interest))

    ldl_statements = interface.get_statements(s=bio_ldl)
    ldl_statements.extend(interface.get_statements(o=bio_ldl))

    print("LDL Clearance is involved in %d statements" % len(ldl_statements))

    statements_of_interest.extend(statements_of_interest)

    count = 0
    for statement in statements_of_interest:
        print("****** %d ******" % count)
        interface.mopify(statement.getSubject())
        interface.mopify(statement.getObject())
        count += 1

    mops = interface.mops


# mops.draw_mops(project_dir + "/images", layout=nx.spring_layout, size=50)


# collapser = Collapser(mops, bio_hyper_cholesterol)
# collapser.draw(project_dir + "/images")
