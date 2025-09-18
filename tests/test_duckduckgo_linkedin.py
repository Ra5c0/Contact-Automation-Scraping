import unittest

from utils import find_first_linkedin_url


class DuckDuckGoLinkedInTests(unittest.TestCase):
    def test_company_url_from_redirect(self) -> None:
        hrefs = [
            "https://example.com/irrelevant",
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linkedin.com%2Fcompany%2Facme-labs%2F%3Ftrk%3Dpublic_profile",
        ]
        result = find_first_linkedin_url(hrefs, "linkedin.com/company")
        self.assertEqual(result, "https://www.linkedin.com/company/acme-labs/")

    def test_profile_url_from_direct_result(self) -> None:
        hrefs = [
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linkedin.com%2Ffeed/",
            "https://linkedin.com/in/jane-doe-42a19b?utm_source=duckduckgo",
        ]
        result = find_first_linkedin_url(hrefs, "linkedin.com/in")
        self.assertEqual(result, "https://www.linkedin.com/in/jane-doe-42a19b")

    def test_no_match_returns_none(self) -> None:
        hrefs = [
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com",
            "https://example.org",
        ]
        self.assertIsNone(find_first_linkedin_url(hrefs, "linkedin.com/company"))


if __name__ == "__main__":
    unittest.main()
