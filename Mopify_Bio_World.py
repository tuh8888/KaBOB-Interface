import pickle
import shutil
import sys
import logging
import networkx as nx

from KaBOB_Interface import KaBOBInterface

log = logging.getLogger('mopify_kabob_world')


def mopify_bio_world(image_dir, pickle_dir, num_nodes=None):
    with KaBOBInterface("KaBOB_credentials.txt") as interface:

        try:
            mops = pickle.load(open("%s/mops.pickle" % pickle_dir, "rb"))
            interface.mops = mops
        except FileNotFoundError:
            pass

        bio_world = interface.get_bio_world(pickle_dir)

        # pickle.dump(interface.bio_world, open("%s/bio_world.pickle" % pickle_dir, "wb"))
        count = 0
        for node in bio_world:
            interface.mopify(node)

            log.debug("Caching results")
            pickle.dump(interface.mops, open("%s/mops.pickle" % pickle_dir, "wb"))
            shutil.copyfile("%s/mops.pickle" % pickle_dir, "%s/mops_%d.pickle" % (pickle_dir, count))

            count += 1
            if count == num_nodes:
                break

    log.debug("Drawing images")
    interface.draw(image_dir, layout=nx.fruchterman_reingold_layout, size=100)


if __name__ == "__main__":
    if len(sys.argv) == 4:
        image_folder = sys.argv[1]
        pickle_folder = sys.argv[2]
        val = int(sys.argv[3])
    else:
        if len(sys.argv) == 2:
            val = int(sys.argv[1])
        else:
            val = 100
        pickle_folder = "E:/Documents/KaBOB/pickles"
        image_folder = "E:/Documents/KaBOB/images"

    mopify_bio_world(image_folder, pickle_folder, num_nodes=val)
