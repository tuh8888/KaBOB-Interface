from unittest import TestCase

from KaBOB_Interface import KaBOBInterface


class TestKaBOBInterface(TestCase):
    p53 = "obo:PR_P04637"
    p53_label_expected = "cellular tumor antigen p53 (human)"

    def test_node_print_name(self):
        with KaBOBInterface("KaBOB_credentials.txt") as interface:
            p53_label = interface.get_mop_label(self.p53, interface.get_labels(self.p53))

            if p53_label != self.p53_label_expected:
                self.fail("Label for p53 was %s but should have been %s" % (p53_label, self.p53_label_expected))

    def test_mopify(self):
        with KaBOBInterface("KaBOB_credentials.txt") as interface:
            # interface.set_max_depth(2)
            bio_p53 = interface.get_bio(interface.create_uri(self.p53))

            interface.mopify(bio_p53)


            interface.draw()
