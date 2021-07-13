# from check_by_instance_connections import check_by_instance_connections
# from check_by_instance_properties import compare_properties
# from check_by_step import check_replication_by_step
# from check_by_pin_connections import check_by_pin_connections
from time_pin_connections import check_by_pin_connections
'''
Design Rule Check
=================

    Checks a modified design by running it through a series of checks:

        check_by_instance_connections - checks what each instance connects to in the modified design against the original design
        compare_properties - finds instances with the same name and same parent and compares their properties.
        check_replication_by_step - finds the steps in both an original and modified design and compare them to be sure that they are still the same.
        check_by_pin_connections - looks what pins are connected in the original netlist and makes sure the corresponding pins in the new netlist are still connected.

    :param original netlist: original netlist
    :param modified netlist: the replicated netlist. Can contain voters/detectors
    :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
    :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
    :return: bool (matched,not_matched)
'''
import time
def check_design(original_netlist,modified_netlist,suffix,organ_name):
    # t0 = time.clock()
    print("CHECKING DESIGN")
    passed = True
    # if not check_by_instance_connections(original_netlist,modified_netlist,suffix,organ_name):
    #     print("FAILED check by instance connections")
    #     passed = False
    # if not compare_properties(original_netlist,modified_netlist,suffix,organ_name):
    #     print("FAILED compare properties")
    #     passed = False
    # if not check_replication_by_step(original_netlist,modified_netlist,suffix,organ_name):
    #     print('FAILED check by step')
    #     passed = False
    if not check_by_pin_connections(original_netlist,modified_netlist,suffix,organ_name):
        print("FAILED check by pin connections")
        passed = False
    if passed:
        print("PASSED")
    # t1 = time.clock()
    # print("TIME:",t1-t0)
    return passed