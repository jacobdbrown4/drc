import spydrnet as sdn
from spydrnet.util.selection import Selection
'''
Check By Pin Connections
---------------------------

Looks what pins are connected in the original netlist and makes sure the corresponding pins in the new netlist are still connected.

        :param original netlist: original netlist
        :param modified netlist: the replicated netlist. Can contain voters/detectors
        :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
        :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
        :return: bool (matched,not_matched)

    Note: to see the results of the comparison, uncomment the appropriate lines.
'''
def check_by_pin_connections(original_netlist,modified_netlist,suffix,organ_name):

    original_instances = list(x for x in original_netlist.get_instances(filter = lambda x: (filter_instances(x,organ_name)) is True))
    get_pin_connections(original_instances)
    modified_instances = list(x for x in modified_netlist.get_instances(filter = lambda x: (filter_instances(x,organ_name)) is True))
    get_pin_connections(modified_instances)

    not_matched = compare_pin_connections(original_instances,modified_instances,suffix,original_netlist.name)

    if not_matched:
        # print("FAILED")
        for item in not_matched:
            print(item.name)
            None
        print(original_netlist.name)
        return False
    else:
        return True

def filter_instances(instance,organ_name):
    if not instance.is_leaf():
        return False
    elif organ_name in instance.name:
        return False
    elif 'GND' in instance.name:
        return False
    elif 'COMPLEX' in instance.name:
        return False
    else:
        return True

def get_pin_connections(instance_list):
    for instance in instance_list:
        for pin in instance.get_pins(selection = Selection.OUTSIDE):
            if pin.wire:
                if pin.inner_pin.port.name in instance._data:
                    instance[pin.inner_pin.port.name] += 1
                else:
                    instance[pin.inner_pin.port.name] = 1
            else:
                if pin.inner_pin.port.name in instance._data:
                    None
                else:
                    instance[pin.inner_pin.port.name] = 0

def compare_pin_connections(original,modified,suffix,name):
    # f = open("connections_"+name+".txt",'w')
    not_matched = []
    for instance_modified in modified:
        modified_name_prefix = None
        start_index = instance_modified.name.find(suffix)
        # stop_index = instance_modified.name.find("_",start_index+4)
        stop_index = start_index + 5
        if start_index is -1:
            modified_name_prefix = instance_modified.name
        elif stop_index is -1:
            modified_name_prefix = instance_modified.name[:start_index-1]
        else :
            modified_name_prefix = instance_modified.name[:start_index-1] + instance_modified.name[stop_index:]
        matched = False
        for instance_original in original:
            if modified_name_prefix == instance_original.name.strip():
                if instance_modified.parent.name.strip() in instance_original.parent.name.strip():
                    matched = True
                    for port in instance_modified.get_ports():
                        try:
                            instance_original[port.name]
                        except KeyError:
                            instance_original[port.name] = None
                        if instance_modified[port.name] == instance_original[port.name]:
                            None
                            # f.write("MATCH: "+instance_modified.name+' '+str(instance_modified[port.name])+'---'+str(instance_original[port.name])+' '+instance_original.name+'\n')
                        else:
                            # f.write("NOT MATCH: "+instance_modified.name+' '+str(instance_modified[port.name])+'---'+str(instance_original[port.name])+'\n')
                            not_matched.append(instance_modified)
                    break
        if not matched:
            # f.write(instance_modified.name + ' had no one to compare to\n')
            not_matched.append(instance_modified)
    # f.close()
    return not_matched



# netlist = sdn.parse('adder.edf')
# netlist2 = sdn.parse('adder_modified.edf')

# check_by_pin_connections(netlist,netlist2,'TMR','VOTER')

