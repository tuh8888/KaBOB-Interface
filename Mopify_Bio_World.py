import logging
import sys

from KaBOBInterface import KaBOBInterface

log = logging.getLogger('mopify_kabob_world')


def mopify_bio_world(pickle_dir, num_nodes=None):
    with KaBOBInterface("KaBOB_credentials.txt", cache_dir=pickle_dir) as interface:

        bio_world = interface.get_bio_world()
        interface.mopify_and_cache(bio_world, number_of_nodes_to_mopify=num_nodes)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        pickle_folder = sys.argv[1]
        val = int(sys.argv[2])
    else:
        if len(sys.argv) == 2:
            val = int(sys.argv[1])
        else:
            val = 1000
        pickle_folder = "E:/Documents/KaBOB/pickles"

    mopify_bio_world(pickle_folder, num_nodes=val)
