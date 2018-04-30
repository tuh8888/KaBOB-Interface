from unittest import TestCase

from KaBOBInterface import KaBOBInterface


class TestKaBOBInterface(TestCase):
    p53_label_expected = "cellular tumor antigen p53 (human)"

    def test_node_print_name(self):
        with KaBOBInterface("KaBOB_credentials.txt") as kabob:
            p53 = kabob.OBO.PR_P04637
            p53_label = kabob.get_mop_label(p53)

            if p53_label != self.p53_label_expected:
                self.fail("Label for p53 was %s but should have been %s" % (p53_label, self.p53_label_expected))

    def test_mopify(self):
        with KaBOBInterface("KaBOB_credentials.txt") as kabob:
            p53 = kabob.OBO.PR_P04637
            bio_p53 = kabob.get_bio_node(p53)

            kabob.mopify(bio_p53)
