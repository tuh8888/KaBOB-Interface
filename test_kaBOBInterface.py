from unittest import TestCase

from KaBOB_Interface import KaBOBInterface


class TestKaBOBInterface(TestCase):
    p53_label_expected = "cellular tumor antigen p53 (human)"

    def test_node_print_name(self):
        with KaBOBInterface("KaBOB_credentials.txt") as interface:
            p53 = interface.OBO.PR_P04637
            p53_label = interface.get_mop_label(p53, interface.get_labels(p53))

            if p53_label != self.p53_label_expected:
                self.fail("Label for p53 was %s but should have been %s" % (p53_label, self.p53_label_expected))

    def test_mopify(self):
        with KaBOBInterface("KaBOB_credentials.txt") as interface:
            p53 = interface.OBO.PR_P04637
            bio_p53 = interface.get_bio(p53)

            interface.mopify(bio_p53)
