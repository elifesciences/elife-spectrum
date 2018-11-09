from spectrum import logger


LOGGER = logger.logger(__name__)

def _log(self, message, *args, **kwargs):
    LOGGER.info(message, extra={'app':'elife-xpub'}, *args, **kwargs)


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


class XpubDashboardPage:
    CSS_NEW_SUBMISSION_BUTTON = 'button[data-test-id="desktop-new-submission"]'

    def __init__(self, driver):
        self._driver = driver

    def create_initial_submission(self):
        new_submission_button = self._driver.find_element_by_css_selector(self.CSS_NEW_SUBMISSION_BUTTON)
        new_submission_button.click()
        return XpubInitialSubmissionAuthorPage(self._driver)


class XpubInitialSubmissionAuthorPage:
    def __init__(self, driver):
        self._driver = driver

    def next(self):
        first_name = self._driver.find_element_by_css_selector('input[name="author.firstName"]')
        first_name.send_keys("Josiah")
        last_name = self._driver.find_element_by_css_selector('input[name="author.lastName"]')
        last_name.send_keys("Carberry")
        email = self._driver.find_element_by_css_selector('input[name="author.email"]')
        email.send_keys("j.carberry@example.com")
        aff = self._driver.find_element_by_css_selector('input[name="author.aff"]')
        aff.send_keys("Brown University")

        next_button = self._driver.find_element_by_css_selector('button[data-test-id="next"]')
        next_button.click()
