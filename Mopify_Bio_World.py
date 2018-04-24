import pickle
import shutil
import sys
import logging
import networkx as nx

from KaBOB_Interface import OpenKaBOB, KaBOBInterface

log = logging.getLogger('mopify_kabob_world')


def mopify_bio_world(pickle_dir, num_nodes=None):
    with OpenKaBOB("KaBOB_credentials.txt") as kabob:

        try:
            interface = pickle.load(open("%s/interface.pickle" % pickle_dir, "rb"))
            interface.kabob = kabob
        except FileNotFoundError:
            interface = KaBOBInterface(kabob)

        interface.mopify_bio_world(pickle_dir, num_nodes=num_nodes)
        pickle.dump(interface.bio_world, open("%s/bio_world.pickle" % pickle_dir, "wb"))

    log.warning("Caching results")
    # pickle.dump(interface, open("%s/interface.pickle" % pickle_dir, "wb"))
    # shutil.copyfile("%s/interface.pickle" % pickle_dir, "%s/interface_%d.pickle" % (pickle_dir, num_nodes))

    log.warning("Drawing images")
    interface.draw(layout=nx.fruchterman_reingold_layout, size=100)
    # pickle.dump(interface, open("pickles/interface_%d.pickle" % num_nodes, "wb"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        val = int(sys.argv[2])
        pickle_folder = sys.argv[1]
    else:
        val = 200
        pickle_folder = "E:/Documents/pickles"
    mopify_bio_world(pickle_folder, num_nodes=val)
