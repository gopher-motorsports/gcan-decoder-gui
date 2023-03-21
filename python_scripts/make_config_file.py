# generates the general config file for the gui
# TODO: rewrite with for gophercan
import configparser

config = configparser.ConfigParser(allow_no_value=True)
# comments

with open('gui_config.ini', 'w') as configfile:
    config.write(configfile)