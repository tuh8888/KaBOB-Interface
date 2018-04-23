from unittest import TestCase

from KaBOB_Interface import KaBOBInterface, OpenKaBOB


class TestKaBOBInterface(TestCase):
    p53 = "obo:PR_P04637"
    p53_label_expected = "cellular tumor antigen p53 (human)"

    def test_node_print_name(self):
        with OpenKaBOB("KaBOB_credentials.txt") as kabob:
            interface = KaBOBInterface(kabob)

            p53_label = interface.node_print_name(self.p53, interface.get_labels(self.p53))

            if p53_label != self.p53_label_expected:
                self.fail("Label for p53 was %s but should have been %s" % (p53_label, self.p53_label_expected))

    def test_mopify(self):
        with OpenKaBOB("KaBOB_credentials.txt") as kabob:
            interface = KaBOBInterface(kabob, max_depth=2)

            bio_p53 = interface.bio(interface.create_uri(self.p53))

            interface.mopify(bio_p53)

            interface.draw()
