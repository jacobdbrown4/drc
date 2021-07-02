from check_by_instance_connections import check_by_instance_connections
from check_by_instance_properties import compare_properties
from check_by_step import check_replication_by_step
# from check_by_pin_connections import check_by_pin_connections
from pin_connections_edit import check_by_pin_connections
'''
Design Rule Check
=================

    Checks a modified design by running it through a check:

        check_by_pin_connections - looks what pins are connected in the original netlist and makes sure the corresponding pins in the new netlist are still connected.

    :param original netlist: original netlist
    :param modified netlist: the replicated netlist. Can contain voters/detectors
    :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
    :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
    :return: bool (matched,not_matched)
'''

def check_design(original_netlist,modified_netlist,suffix,organ_name):
    print("CHECKING DESIGN")
    passed = check_by_pin_connections(original_netlist,modified_netlist,suffix,organ_name)
    if passed:
        print("PASSED")
    else:
        print("FAILED")
    return passed