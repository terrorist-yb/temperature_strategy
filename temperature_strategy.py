# -*- coding: utf-8 _*_

###############################################################################
# Copyright (C), 2018, TP-LINK Technologies Co., Ltd.
#
# Author: wuyangbo_w9477
# History:
# 1, 2018-01-17, wuyangbo, first create:temperature strategy validation tool
###############################################################################
import visa
import time
import logging
import xml.etree.ElementTree as ET


class NTC(object):
    '''ntc model'''

    def __init__(self, resistance, temperature):
        '''create dictionary: ntc resistance vs temperature'''
        self.resistance_vs_temperature_table = dict(zip(temperature, resistance))

    def get_resistance(self, temperature):
        '''look up table to get resistance'''
        return self.resistance_vs_temperature_table[temperature]


class DCSource(object):
    '''dc source operation model'''

    def __init__(self, dev):
        '''create gpib instrument instance using visa lib'''
        try:
            if not dev.__class__.__name__ in ['GPIBInstrument']:
                raise ValueError
        except ValueError:
            print 'Instrument instantiation failed!'
            exit()
        self.dev = dev

    def initialize(self, ntc_voltage):
        '''initialize configuration'''

        # reset device
        self.dev.write('*rst; status:preset; *cls')
        # decouple the output ports
        self.dev.write('instrument:couple:output:state none')
        # set protection voltage
        self.dev.write("voltage:protection:level 4;state on")
        # set output1 voltage as 3.8V, for powering on the mobile
        self.dev.write("voltage1 3.8")
        # enable the output 1
        self.dev.write("output1 on")
        # set output2 voltage according to ntc_voltage
        self.set_voltage(ntc_voltage)
        # enable the output 2
        self.dev.write("output2 on")
        # enable panel display
        self.dev.write("display on")
        # display channel info
        self.dev.write("display:channel 2")

    def set_voltage(self, ntc_voltage):
        '''output2 is used as simulating ntc'''

        self.dev.write("voltage2 %.3f" % ntc_voltage)


def preprocess():
    '''create instances for testcase'''

    # get configuration from XML
    config_tree = ET.parse('config.xml')
    root = config_tree.getroot()
    formula = compile(root.find('circuit').text, '', 'eval')
    t_delay = float(root.find('delay').text)

    # create ntc instance
    temperature = []
    resistance = []
    for item in root.iter('ntc'):
        temperature.append(int(item.attrib['temperature']))
        resistance.append(round(float(item.attrib['resistance']), 4))
    ntc = NTC(resistance, temperature)

    # create dc_source instance
    rm = visa.ResourceManager('visa32.dll')
    dev_list = rm.list_resources()
    dev = rm.open_resource(dev_list[0])
    dc_source = DCSource(dev)

    return formula, ntc, dc_source, t_delay


def change_temperature(ntc, dc_source, formula, temperature_init, temperature_end, t_delay):
    '''simulate temperature gradient change '''

    if temperature_init < temperature_end:
        direction = 1
    else:
        direction = -1

    for temperature in range(temperature_init, temperature_end+direction, direction):
        r = ntc.get_resistance(temperature)
        ntc_voltage = round(eval(formula), 3)
        logging.info('-------------------------Set temperature %s-------------------------' % temperature)
        dc_source.set_voltage(ntc_voltage)
        logging.info('-------------------------Set voltage %.3fV-------------------------' % ntc_voltage)
        time.sleep(t_delay)


def testcase(formula, ntc, dc_source, t_delay):

    # config log pattern
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S')

    # get initial and final temperature
    temperature_init = int(raw_input("input initial temperature:"))
    temperature_end = int(raw_input("input final temperature:"))

    # initialize dc source and wait
    r = ntc.get_resistance(temperature_init)
    ntc_voltage = round(eval(formula), 3)
    dc_source.initialize(ntc_voltage)
    raw_input("press 'enter' to start test:")

    # change temperature
    change_temperature(ntc, dc_source, formula, temperature_init, temperature_end, t_delay)
    temperature_init, temperature_end = temperature_end, temperature_init
    change_temperature(ntc, dc_source, formula, temperature_init, temperature_end, t_delay)


if __name__ == '__main__':

    formula, ntc, dc_source, t_delay = preprocess()
    testcase(formula, ntc, dc_source, t_delay)

