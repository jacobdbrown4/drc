import spydrnet as sdn
from spydrnet.util.selection import Selection

'''
Check By Instance Connections
=============================

Checks what each instance connects to in the modified design against the original design

        :param original netlist: original netlist
        :param modified netlist: the replicated netlist. Can contain voters/detectors
        :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
        :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
        :return: bool (matched,not_matched)

    Note: to see the results of the comparison, uncomment the appropriate lines.
'''

def check_by_instance_connections(original_netlist,modified_netlist,suffix,organ_name):

    global top_instance
    top_instance = modified_netlist.top_instance

    original_instances = list(x for x in original_netlist.get_instances(filter=lambda x: filter_instances(x,organ_name) is True))
    modified_instances = list(x for x in modified_netlist.get_instances(filter=lambda x: filter_instances(x,organ_name) is True))

    # f = open("connections_"+original_netlist.name+".txt",'w')
    for instance in original_instances:
        start_index = instance.name.find(suffix)
        # stop_index = start_index+5
        stop_index = start_index + len(suffix) + 2
        if start_index is -1:
                key = ''
        else:
            key = (instance.name[start_index:stop_index])
        instance["EDIF.outputs_to"] = set(list(non_key_name(instance.instance,suffix) for instance in get_next_instances(instance,organ_name,key,suffix)))
        # f.write('\n'+instance.name)
        # f.write('\n\t'+"OUTPUTS TO:"+ '\t'+str(instance["EDIF.outputs_to"]))
    for instance in modified_instances:
        start_index = instance.name.find(suffix)
        # stop_index = start_index+5
        stop_index = start_index + len(suffix) + 2
        if start_index is -1:
                key = ''
        else:
            key = (instance.name[start_index:stop_index])
        instance["EDIF.outputs_to"] = set(list(non_key_name(instance.instance,suffix) for instance in get_next_instances(instance,organ_name,key,suffix)))
        # f.write('\n'+instance.name)
        # f.write('\n\t'+"OUTPUTS TO:"+ '\t'+str(instance["EDIF.outputs_to"]))
    # f.close()

    not_matched = compare_properties(original_instances,modified_instances,original_netlist.name,suffix)
    for instance in original_instances:
        instance._data.pop('EDIF.outputs_to')
    for instance in modified_instances:
        instance._data.pop('EDIF.outputs_to')
    if not_matched:
        # print("FAILED")
        for item in not_matched:
            None
            # print(item.name)
        return False
    else:
        return True

def filter_instances(instance,organ_name):
    # if not instance.is_leaf():
    #     # return False
    #     None
    if organ_name in instance.name:
        return False
    elif 'GND' in instance.name:
        return False
    elif 'COMPLEX' in instance.name:
        return False
    else:
        return True

def get_next_instances(current_instance,organ_name,key,suffix):
    next_instances = []
    for pin in current_instance.get_pins(filter=lambda x: (x.inner_pin.port.direction is sdn.OUT),selection=Selection.OUTSIDE):
        if pin.wire:
            next_instances = next_instances + list(pin2 for pin2 in pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not pin)))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    next_instances = set(next_instances)
    return list(x for x in next_instances)

def check_next_list(next_instances,organ_name,key,suffix):
    to_remove = []
    to_add = []
    for i in range(len(next_instances)):
        if organ_name in next_instances[i].instance.name.upper() or 'COMPLEX' in next_instances[i].instance.name:
            possible_next = get_next_instances(next_instances[i].instance,organ_name,'',suffix)
            to_add = to_add + possible_next.copy()
            to_remove.append(next_instances[i])
    for instance in to_add:
        if key in instance.instance.name:
            None
        elif suffix not in instance.instance.name:
            if key in instance.inner_pin.port.name:
                None
            elif suffix not in instance.inner_pin.port.name:
                None
            elif 'COMPLEX' in instance.inner_pin.port.name:
                None
            else:
                to_remove.append(instance)
        else:
            to_remove.append(instance)
    next_instances = list(x for x in next_instances if not x in to_remove)
    next_instances = next_instances + to_add
    next_instances = list(x for x in next_instances if not x in to_remove)
    return list(x for x in set(next_instances))

def compare_property(property,original_instance,modified_instance):
    if original_instance["EDIF."+property] == modified_instance["EDIF."+property]:
        return True
    else:
        return False

def compare_properties(original,modified,name,suffix):
    # f = open("connections_"+name+".txt",'a')
    not_matched = []
    for instance_modified in modified:
        modified_name_prefix = None
        start_index = instance_modified.name.find(suffix)
        stop_index = instance_modified.name.find("_",start_index+1)
        if start_index is -1:
            modified_name_prefix = instance_modified.name
        elif stop_index is -1:
            modified_name_prefix = instance_modified.name[:start_index-1]
        else :
            modified_name_prefix = instance_modified.name[:start_index-1] + instance_modified.name[stop_index+2:]

        for instance_original in original:
            matched = False
            if modified_name_prefix.strip() == instance_original.name.strip():
                if compare_property("outputs_to",instance_original,instance_modified):
                    # f.write('\n\t'+instance_modified.name+"---"+instance_original.name)
                    # f.write("\n\t\tOUTPUTS TO")
                    # f.write('\n\t\t\t'+ str(instance_modified["EDIF.outputs_to"])+ '----matched----'+str(instance_original["EDIF.outputs_to"]))
                    matched = True
                    break
        if not matched:
            # f.write('\n\t'+instance_modified.name)
            # f.write("\n\t\tOUTPUTS TO")
            # f.write('\n\t\t\t'+str(instance_modified["EDIF.outputs_to"]) + ' DID NOT MATCH ANYTHING')
            not_matched.append(instance_modified)
    # f.close()
    return not_matched

def non_key_name(instance,suffix):
    name_no_key = None
    start_index = instance.name.find(suffix)
    stop_index = instance.name.find("_",start_index+1)
    if start_index is -1:
        name_no_key = instance.name
    elif stop_index is -1:
        name_no_key = instance.name[:start_index-1]
    else :
        name_no_key = instance.name[:start_index-1] + instance.name[stop_index+2:]
    return name_no_key



# netlist = sdn.parse("adder.edf")
# netlist2 = sdn.parse("adder_modified.edf")

# print(check_by_instance_connections(netlist,netlist2,'TMR','VOTER'))
