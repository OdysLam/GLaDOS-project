# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re
from pyvirtualdisplay import Display
import pyvirtualdisplay


#add code to run on rpi
class Latest(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.base_url = "http://user@192.168.1.1"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_la(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        # ERROR: Caught exception [ERROR: Unsupported command [selectFrame | navigation | ]]
        driver.get("http://192.168.1.1/maintenance/tools_system.htm")
        # ERROR: Caught exception [ERROR: Unsupported command [selectWindow | name=main | ]]
        driver.find_element_by_name("Restart").click()
        self.assertRegexpMatches(self.close_alert_and_get_its_text(), r"^Are you sure you want restart system[\s\S]$")
    
    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException as e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
        display.stop()

if __name__ == "__main__":
    display = Display(visible=0, size=(800, 600))
    display.start()
    unittest.main()