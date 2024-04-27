from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import os
import subprocess


from selenium import webdriver
import selenium.common.exceptions as _exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import p06io

# Chromium drivers can be found here:
# http://chromedriver.storage.googleapis.com/index.html
# Firefox drivers can be found here:
# https://github.com/mozilla/geckodriver/releases


###########
# Website #
###########

class Website(object):
    """
    General class to interact with websites.
    """

    ############
    # __exit__ #
    ############

    def __exit__(self, *args):
        """
        General exit.
        """

        self.quit()

    ###########
    # __del__ #
    ###########

    def __del__(self):
        """
        General deletion.
        """

        self.quit()

    ############
    # __init__ #
    ############

    def __init__(self, browser="chromium", verbosity=0, driver_init=True):
        """
        General class to interact with websites.

        Parameters
        ----------
        browser : str, optional
            The default browser to use.
            Default is chromium.

        verbosity : int, optional
            The verbosity level.

        driver_init : boolean, optional
            Determines if the driver is initialised upon class init.
        """

        self.verbosity = verbosity
        self._browser = browser
        self._exceptions = _exceptions

        if driver_init:
            if self.verbosity > 0:
                print("Initialising the driver.")
            self._init_driver()
        else:
            if self.verbosity > 0:
                print("Skipping driver Initialisation.")

        self._loaded_page = None

    ########################
    # _get_browser_version #
    ########################

    def _get_browser_version(self):
        """
        Gets the browser version.

        Returns
        -------
        str
            The browser version.
        """

        cmd = [self._browser, "--version"]
        reply = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        output = reply.stdout.readlines()
        output = output[0].split()[1]

        # Convert for py2/3 compatibility
        if isinstance(output, bytes):
            output = output.decode("utf-8")

        return output

    ##################
    # _get_button_id #
    ##################

    def _get_button_id(self, name):
        """
        Get the button ID using the button name.

        Parameters
        ----------
        name : str
            The name of the button.

        Returns
        -------
        instance
            The button instance.
        """
        try:
            return self._driver.find_element_by_id(name)
        except _exceptions.NoSuchElementException:
            raise ValueError("No button found with this name.")

    ####################
    # _get_driver_path #
    ####################

    def _get_driver_path(self):
        """
        Determines the path of the gecko driver.

        Returns
        -------
        str
            The path of the gecko driver.
            If none can be found None is returned.
        """

        if self._browser == "firefox":
            driver = "geckodriver"
            version = "0.27"
        elif self._browser == "chromium":
            driver = "chromedriver"
            version = self._get_browser_version()
            version = ".".join(version.split(".")[:2])

        path = os.path.join(
            os.path.abspath(p06io.__path__[0]),
            "website/bin/{}/{}/{}".format(self._browser, version, driver)
        )

        # The driver needs to be add to the PATH environment variable.
        newpath = "{}:{}".format(
            os.getenv("PATH"),
            os.path.split(path)[0]
        )

        os.environ["PATH"] = newpath

        return path

    ################
    # _init_driver #
    ################

    def _init_driver(self):
        """
        Inits the selenium driver.
        """

        if self._browser == "firefox":
            from selenium.webdriver.firefox.options import Options
        elif self._browser == "chromium":
            from selenium.webdriver.chrome.options import Options

        options = Options()
        options.headless = True
        # options.add_argument('-headless')
        driver_path = self._get_driver_path()
        if driver_path is None:
            raise RuntimeError("The driver can not be found.")

        if self._browser == "firefox":
            self._driver = webdriver.Firefox(
                executable_path=driver_path,
                options=options
            )
        elif self._browser == "chromium":
            self._driver = webdriver.Chrome(
                executable_path=driver_path,
                options=options
            )

    ################
    # _wait_for_id #
    ################

    def _wait_for_id(self, name, timeout=5):
        """
        Waits for the ID to be available.

        Parameters
        ----------
        name : str
            The id name of the button to click.

        timeout : float, optional
            The timeout in seconds.

        Raises
        ------
        TimeoutException
            When the ID is not available before the timeout expires.
        """

        WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located((By.ID, name))
        )

    ######################
    # click_button_by_id #
    ######################

    def click_button_by_id(self, name, url=None):
        '''
        Clicks the button.

        Parameters
        ----------
        name : str
            The id name of the button to click.

        url : str, optional
            The url of the page the button is on.
            The currently loaded page is taken by default.
        '''

        self.load_page(url)
        self._wait_for_id(name)
        button = self._get_button_id(name)
        button.click()

    #############
    # load_page #
    #############

    def load_page(self, url):
        """
        Loads a page to enable page interaction.

        Parameters
        ----------
        url : str
            The page url.
        """

        if url is not None:
            self._driver.get(url)
            self._loaded_page = url

    ########
    # quit #
    ########

    def quit(self):
        """
        Closes the session.
        """

        if hasattr(self, "_driver"):
            self._driver.quit()
