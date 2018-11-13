from spectrum import logger


LOGGER = logger.logger(__name__)

def _info_log(message, *args, **kwargs):
    LOGGER.info(message, extra={'app':'elife-xpub'}, *args, **kwargs)

class PageObject:
    def __init__(self, driver):
        self._driver = driver

    def _input(self, css_selector, text, name=None):
        input_element = self._driver.find_element_by_css_selector(css_selector)
        if name:
            _info_log("Found %s input %s", name, css_selector)
        input_element.send_keys(text)


class XpubJavaScriptSession:
    CSS_LOGIN_BUTTON = 'button[data-test-id="login"]'
    CSS_PROFILE_MENU = 'button[data-test-id="profile-menu"]'

    def __init__(self, driver):
        self._driver = driver

    def login(self):
        login_button = self._driver.find_element_by_css_selector(self.CSS_LOGIN_BUTTON)
        _info_log("Found login button %s `%s`", self.CSS_LOGIN_BUTTON, login_button.text)
        login_button.click()
        _info_log("Clicked login button %s", self.CSS_LOGIN_BUTTON)
        profile_menu = self._driver.find_element_by_css_selector(self.CSS_PROFILE_MENU)
        _info_log("Found profile menu %s", self.CSS_PROFILE_MENU)
        profile_menu.click()
        _info_log("Clicked profile menu %s", self.CSS_PROFILE_MENU)

    def dashboard(self):
        dashboard_button = self._driver.find_element_by_link_text('Dashboard')
        dashboard_button.click()
        return XpubDashboardPage(self._driver)


class XpubDashboardPage(PageObject):
    CSS_NEW_SUBMISSION_BUTTON = 'button[data-test-id="desktop-new-submission"]'

    def create_initial_submission(self):
        new_submission_button = self._driver.find_element_by_css_selector(self.CSS_NEW_SUBMISSION_BUTTON)
        new_submission_button.click()
        return XpubInitialSubmissionAuthorPage(self._driver)


class XpubInitialSubmissionAuthorPage(PageObject):
    CSS_INPUT_FIRST_NAME = 'input[name="author.firstName"]'
    CSS_INPUT_LAST_NAME = 'input[name="author.lastName"]'
    CSS_INPUT_EMAIL = 'input[name="author.email"]'
    CSS_INPUT_AFFILIATION = 'input[name="author.aff"]'
    CSS_NEXT = 'button[data-test-id="next"]'

    def next(self):
        self._input(self.CSS_INPUT_FIRST_NAME, 'Josiah', 'first name')
        self._input(self.CSS_INPUT_LAST_NAME, 'Carberry', 'last name')
        self._input(self.CSS_INPUT_EMAIL, 'j.carberry@example.com', 'email')
        self._input(self.CSS_INPUT_AFFILIATION, 'Brown University', 'affiliation')
        next_button = self._driver.find_element_by_css_selector(self.CSS_NEXT)
        next_button.click()
