from spectrum import logger


LOGGER = logger.logger(__name__)

def _log(message, *args, **kwargs):
    LOGGER.info(message, extra={'app':'elife-xpub'}, *args, **kwargs)

class PageObject:
    def _input(self, css_selector, text, name=None):
        input_element = self._driver.find_element_by_css_selector(css_selector)
        if name:
            _log("Found %s input %s", name, self.CSS_INPUT_FIRST_NAME)
        input_element.send_keys(text)


class XpubJavaScriptSession:
    CSS_LOGIN_BUTTON = 'button[data-test-id="login"]'
    CSS_PROFILE_MENU = 'button[data-test-id="profile-menu"]'

    def __init__(self, driver):
        self._driver = driver

    def login(self):
        login_button = self._driver.find_element_by_css_selector(self.CSS_LOGIN_BUTTON)
        _log("Found login button %s `%s`", self.CSS_LOGIN_BUTTON, login_button.text)
        login_button.click()
        _log("Clicked login button %s", self.CSS_LOGIN_BUTTON)
        profile_menu = self._driver.find_element_by_css_selector(self.CSS_PROFILE_MENU)
        _log("Found profile menu %s", self.CSS_PROFILE_MENU)
        profile_menu.click()
        _log("Clicked profile menu %s", self.CSS_PROFILE_MENU)

    def dashboard(self):
        dashboard_button = self._driver.find_element_by_link_text('Dashboard')
        dashboard_button.click()
        return XpubDashboardPage(self._driver)


class XpubDashboardPage(PageObject):
    CSS_NEW_SUBMISSION_BUTTON = 'button[data-test-id="desktop-new-submission"]'

    def __init__(self, driver):
        self._driver = driver

    def create_initial_submission(self):
        new_submission_button = self._driver.find_element_by_css_selector(self.CSS_NEW_SUBMISSION_BUTTON)
        new_submission_button.click()
        return XpubInitialSubmissionAuthorPage(self._driver)


class XpubInitialSubmissionAuthorPage(PageObject):
    CSS_INPUT_FIRST_NAME = 'input[name="author.firstName"]'
    CSS_INPUT_LAST_NAME = 'input[name="author.lastName"]'

    def __init__(self, driver):
        self._driver = driver

    def next(self):
        self._input(self.CSS_INPUT_FIRST_NAME, 'Josiah', 'first name')
        self._input(self.CSS_INPUT_LAST_NAME, 'Carberry', 'last name')
        self._input(self.CSS_INPUT_EMAIL, 'j.carberry@example.com', 'email')
        self._input(self.CSS_INPUT_AFFILIATION, 'Brown University', 'affiliation')
        next_button = self._driver.find_element_by_css_selector('button[data-test-id="next"]')
        next_button.click()
