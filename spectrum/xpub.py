from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from spectrum import logger


LOGGER = logger.logger(__name__)

def _info_log(message, *args, **kwargs):
    LOGGER.info(message, extra={'app':'elife-xpub'}, *args, **kwargs)

class PageObject:
    def __init__(self, driver):
        self._driver = driver

    # TODO: transform into XpubInput object?
    def _send_input_to(self, css_selector, text, name=None):
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

    def populate_required_fields(self):
        self._send_input_to(self.CSS_INPUT_FIRST_NAME, 'Josiah', 'first name')
        self._send_input_to(self.CSS_INPUT_LAST_NAME, 'Carberry', 'last name')
        self._send_input_to(self.CSS_INPUT_EMAIL, 'j.carberry@example.com', 'email')
        self._send_input_to(self.CSS_INPUT_AFFILIATION, 'Brown University', 'affiliation')

    def next(self):
        XpubNextButton(self._driver).follow()
        return XpubInitialSubmissionFilesPage(self._driver)

class XpubInitialSubmissionFilesPage(PageObject):
    CSS_EDITOR_COVER_LETTER = '#coverLetter [contentEditable=true]'
    CSS_INPUT_MANUSCRIPT = '[data-test-id=upload]>input'
    CSS_UPLOAD_INSTRUCTIONS = 'p[data-test-conversion="completed"]'

    def populate_required_fields(self):
        self._send_input_to(self.CSS_EDITOR_COVER_LETTER, 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.', 'cover letter')
        self._send_input_to(self.CSS_INPUT_MANUSCRIPT, '/templates/elife-xpub/initial-submission.pdf', 'manuscript file')
        self._wait_for_upload_and_conversion()

    def next(self):
        XpubNextButton(self._driver).follow()
        return XpubInitialSubmissionSubmissionPage(self._driver)

    def _wait_for_upload_and_conversion(self):
        instructions = self._driver.find_element_by_css_selector(self.CSS_UPLOAD_INSTRUCTIONS)
        LOGGER.info("Found instructions: %s", instructions.text)

class XpubInitialSubmissionSubmissionPage(PageObject):
    def populate_required_fields(self):
        self._send_input_to('[name="meta.title"]', 'My title', 'title')
        # unstable selectors follow: https://github.com/elifesciences/elife-xpub/issues/1041
        self._driver.find_element_by_css_selector('[role=listbox] button').click()
        # multiple elements, pick the first one
        self._driver.find_element_by_css_selector('[role=option]').click()
        # subject area menu
        subject_area = self._driver.find_element_by_css_selector('label[for="subject-area-select"]')
        subject_area.click()
        subject_area_input = self._driver.find_element_by_css_selector('input#subject-area-select')
        subject_area_input.send_keys(Keys.ARROW_DOWN)
        subject_area_input.send_keys(Keys.ENTER)

    def next(self):
        XpubNextButton(self._driver).follow()
        return XpubInitialSubmissionEditorsPage(self._driver)


class XpubInitialSubmissionEditorsPage(PageObject):
    CSS_SUGGEST_SENIOR_EDITORS_BUTTON = '[data-test-id="suggested-senior-editors"] button'
    CSS_SUGGEST_REVIEWING_EDITORS_BUTTON = '[data-test-id="suggested-reviewing-editors"] button'
    CSS_SUGGEST_REVIEWER_NAME_TEMPLATE = 'input[name="suggestedReviewers.{index}.name"]'
    CSS_SUGGEST_REVIEWER_EMAIL_TEMPLATE = 'input[name="suggestedReviewers.{index}.email"]'

    def populate_required_fields(self):
        self._driver.find_element_by_css_selector(self.CSS_SUGGEST_SENIOR_EDITORS_BUTTON).click()
        picker = XpubPeoplePicker(self._driver)
        picker.choose_some(2)

        self._driver.find_element_by_css_selector(self.CSS_SUGGEST_REVIEWING_EDITORS_BUTTON).click()
        picker = XpubPeoplePicker(self._driver)
        picker.choose_some(2)

        for index in range(0, 3):
            self._send_input_to(self.CSS_SUGGEST_REVIEWER_NAME_TEMPLATE.format(index=index), 'Reviewer %d' % index)
            self._send_input_to(self.CSS_SUGGEST_REVIEWER_EMAIL_TEMPLATE.format(index=index), 'reviewer%d@example.com' % index)

    def next(self):
        XpubNextButton(self._driver).follow()
        return XpubInitialSubmissionDisclosurePage(self._driver)


class XpubInitialSubmissionDisclosurePage(PageObject):
    CSS_SUBMITTER_SIGNATURE = 'input[name="submitterSignature"]'
    CSS_DISCLOSURE_CONSENT = 'input[name="disclosureConsent"]'
    CSS_SUBMIT = 'button[data-test-id="submit"]'
    CSS_CONFIRM = 'button[data-test-id="accept"]'

    def acknowledge(self):
        self._send_input_to(self.CSS_SUBMITTER_SIGNATURE, 'Josiah Carberry')
        # need to click on the parent <label>
        # TODO: add logs or wrap in object
        self._driver.find_element_by_css_selector(self.CSS_DISCLOSURE_CONSENT).find_element_by_xpath('..').click()

    def submit(self):
        self._driver.find_element_by_css_selector(self.CSS_SUBMIT).click()
        self._driver.find_element_by_css_selector(self.CSS_CONFIRM).click()
        print()
        WebDriverWait(self._driver, 10).until(lambda driver: self._on_thank_you())

    def _on_thank_you(self):
        return self._driver.find_element_by_css_selector('h1').text == 'Thank you'


class XpubNextButton():
    CSS_NEXT = 'button[data-test-id="next"]'

    def __init__(self, driver):
        self._element = driver.find_element_by_css_selector(self.CSS_NEXT)

    def follow(self):
        self._element.click()


class XpubPeoplePicker():
    CSS_PEOPLE_PICKER = '[data-test-id="people-picker-body"]'
    CSS_PERSON_POD_BUTTON = '[data-test-id="person-pod-button"]'
    CSS_ADD_BUTTON = '[data-test-id="people-picker-add"]'
    TIMEOUT_CLOSING = 10

    def __init__(self, driver):
        self._driver = driver
        self._picker = self._find_picker()
        self._add = driver.find_element_by_css_selector(self.CSS_ADD_BUTTON)

    def _find_picker(self):
        return self._driver.find_element_by_css_selector(self.CSS_PEOPLE_PICKER)

    def choose_some(self, quantity):
        buttons = self._picker.find_elements_by_css_selector(self.CSS_PERSON_POD_BUTTON)
        for button in range(0, quantity):
            buttons[button].click()
        self._add.click()
        # seem to be needlessly slow, stopping for several seconds after the picker has disappeared
        WebDriverWait(self._driver, self.TIMEOUT_CLOSING).until_not(lambda driver: self._find_picker().is_displayed())
