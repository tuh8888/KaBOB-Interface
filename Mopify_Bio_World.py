import logging
import pickle
import sys
import threading

from KaBOBInterface import KaBOBInterface

log = logging.getLogger('mopify_kabob_world')


def mopify_bio_world(image_dir, pickle_dir, num_nodes=None):
    with KaBOBInterface("KaBOB_credentials.txt", cache_dir=pickle_dir) as interface:

        bio_world = interface.get_bio_world()
        interface.mopify_and_cache(bio_world, number_of_nodes_to_mopify=num_nodes)

        # cache_thread = threading.Thread(target=cache_statements, args=(bio_world, bio_world_with_statements, interface, num_nodes, pickle_dir))
        # cache_statements(bio_world, bio_world_with_statements, interface, num_nodes, pickle_dir)

        # mopify_thread = threading.Thread(target=interface.mopify_and_cache, args=(bio_world, num_nodes))
        # mopify_statements(bio_world_with_statements, interface, num_nodes, pickle_dir)

        # cache_thread.start()
        # mopify_thread.start()

    # log.debug("Drawing images")
    # interface.draw(image_dir, layout=nx.fruchterman_reingold_layout, size=100)


def cache_statements(bio_world, bio_world_with_statements, interface, num_nodes, pickle_dir):
    count = 0
    for o in bio_world:
        if count == num_nodes:
            break
        if o not in bio_world_with_statements.keys():
            bio_world_with_statements[o] = interface.get_statements(o)
            if count % 100 == 0:
                log.debug("**************************** Cache %d ****************************" % count)
                pickle.dump(bio_world_with_statements,
                            open("%s/bio_world_with_statements.pickle" % pickle_dir, "wb"))
                # shutil.copyfile("%s/bio_world_with_statements.pickle" % pickle_dir, "%s/bio_world_with_statements_%d.pickle" % (pickle_dir, count))
        count += 1
    pickle.dump(bio_world_with_statements, open("%s/bio_world_with_statements.pickle" % pickle_dir, "wb"))


if __name__ == "__main__":
    if len(sys.argv) == 4:
        image_folder = sys.argv[1]
        pickle_folder = sys.argv[2]
        val = int(sys.argv[3])
    else:
        if len(sys.argv) == 2:
            val = int(sys.argv[1])
        else:
            val = 2
        pickle_folder = "E:/Documents/KaBOB/pickles"
        pickle_folder = "E:/Documents/Test"
        image_folder = "E:/Documents/KaBOB/images"

    mopify_bio_world(image_folder, pickle_folder, num_nodes=val)
