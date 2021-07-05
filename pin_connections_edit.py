import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet.util import selection
from spydrnet.util.selection import Selection
'''
Check By Pin Connections
========================

Looks at each leaf instance's pins in both netlists and finds what it drives/what drives it and makes sure corresponding instance pins between the netlists match up.

        :param original netlist: original netlist
        :param modified netlist: the replicated netlist. Can contain voters/detectors
        :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
        :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
        :return: bool (matched,not_matched)

    Note: to see the results of the comparison, uncomment the appropriate lines.
'''
def check_by_pin_connections(original_netlist,modified_netlist,suffix,organ_name):
    global top_instances
    top_instances = [original_netlist.top_instance,modified_netlist.top_instance]

    original_instances = list(x for x in original_netlist.get_instances(filter = lambda x: (filter_instances(x,organ_name)) is True))
    get_pin_connections(original_instances,organ_name,suffix)
    modified_instances = list(x for x in modified_netlist.get_instances(filter = lambda x: (filter_instances(x,organ_name)) is True))
    get_pin_connections(modified_instances,organ_name,suffix)

    not_matched = compare_pin_connections(original_instances,modified_instances,suffix,original_netlist.name)
    if not_matched:
        for item in not_matched:
            print(item.name,' from ',item.parent.name)
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

def fix_instance_connection_name(current_instance,suffix):
    modified_name_prefix = None
    start_index = current_instance.name.find(suffix)
    stop_index = start_index + len(suffix) + 2
    if start_index is -1:
        modified_name_prefix = current_instance.name
    # elif stop_index is -1:
    #     modified_name_prefix = current_instance.name[:start_index-1]
    else :
        modified_name_prefix = current_instance.name[:start_index-1] + current_instance.name[stop_index:]
    return modified_name_prefix

def get_pin_connections(instance_list,organ_name,suffix):
    for instance in instance_list:
        start_index = instance.name.find(suffix)
        stop_index = start_index + len(suffix) + 2
        if start_index is -1:
            key = ''
        else:
            key = instance.name[start_index:stop_index]
        for pin in instance.get_pins(selection = Selection.OUTSIDE):
            if pin.wire:
                if pin.inner_pin.port.direction is sdn.OUT:
                    pins = set(x.instance for x in get_next_instances(pin,organ_name,key,suffix))
                    pin_num = sorted(list(fix_instance_connection_name(x,suffix) for x in pins))
                elif pin.inner_pin.port.direction is sdn.IN:
                    pins = get_previous_instance(pin,organ_name,key,suffix)
                    if pins[0] is None:
                        pin_num = []
                    else:
                        pin_num = sorted(list(fix_instance_connection_name(x.instance,suffix) for x in pins))

                if pin.inner_pin.port.name in instance._data:
                    instance[pin.inner_pin.port.name] = instance[pin.inner_pin.port.name]+ pin_num
                else:
                    instance[pin.inner_pin.port.name] = pin_num
            else:
                if not pin.inner_pin.port.name in instance._data:
                    instance[pin.inner_pin.port.name] = []


def get_next_instances(current_pin,organ_name,key,suffix):
    next_instances = []
    next_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin)))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    next_instances = set(next_instances)
    return list(x for x in next_instances)

def check_next_list(next_instances,organ_name,key,suffix):
    to_remove = []
    to_add = []
    for i in range(len(next_instances)):
        if organ_name in next_instances[i].instance.name.upper() or 'COMPLEX' in next_instances[i].instance.name:
            output_pin = next(next_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.OUT),None)
            if output_pin.wire:
                possible_next = get_next_instances(output_pin,organ_name,'',suffix)
                to_add = to_add + possible_next
            to_remove.append(next_instances[i])
    next_instances = next_instances + to_add
    for instance in next_instances:
        if key in instance.instance.name:
            None
        elif suffix not in instance.instance.name:
            #maybe move this around to be like check for drivers. First check leaf or not. then do rest.
            if key in instance.inner_pin.port.name:
                None
            elif suffix not in instance.inner_pin.port.name:
                None
            #     wires = []
            #     for pin2 in instance.inner_pin.port.get_pins(selection = Selection.OUTSIDE):
            #         if pin2.wire:
            #             wires.append(pin2.wire)
            #     if not wires:
            #         to_remove.append(instance)
            #     else:
            #         None
            elif 'COMPLEX' in instance.inner_pin.port.name:
                None
            else:
                to_remove.append(instance)
        else:
            to_remove.append(instance)
    next_instances = list(x for x in next_instances if not x in to_remove)
    return list(x for x in set(next_instances))

def get_organ_previous(current_pin,organ_name):
    previous_instances = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin and organ_name not in x.instance.name and 'COMPLEX' not in x.instance.name)is True))
    return previous_instances

def get_previous_instance(current_pin,organ_name,key,suffix):
    previous_instances = []
    to_remove = []
    to_add = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin)))
    for i in range(len(previous_instances)):
        if organ_name in previous_instances[i].instance.name or 'COMPLEX' in previous_instances[i].instance.name:
            input_pins = list(pin for pin in previous_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.IN))
            possible_next = []
            for pin in input_pins:
                possible_next = possible_next + get_organ_previous(pin,organ_name)
            to_add = to_add + possible_next.copy()
            to_remove.append(previous_instances[i])
    previous_instances = previous_instances + to_add
    previous_instances = list(x for x in previous_instances if x not in to_remove)
    driver = None
    for instance in previous_instances:
        if instance.instance.is_leaf() and instance.inner_pin.port.direction is sdn.OUT:
            if key in instance.instance.name:
                driver = instance
            elif suffix not in instance.instance.name:
                driver = instance
        elif not instance.instance.is_leaf():
            if key in instance.inner_pin.port.name or suffix not in instance.inner_pin.port.name:
                if instance.instance not in top_instances:
                    if instance.instance.reference.name is current_pin.instance.parent.name:
                        if instance.inner_pin.port.direction is sdn.IN:
                            driver = instance
                    else:
                        if instance.inner_pin.port.direction is sdn.OUT:
                            driver = instance
                else:
                    if instance.inner_pin.port.direction is sdn.IN:
                        driver = instance
    return [driver]

def compare_pin_connections(original,modified,suffix,name):
    # print("results printed to connections_"+name+".txt")
    f = open("connections_"+name+".txt",'w')
    not_matched = []
    for instance_modified in modified:
        modified_name_prefix = None
        start_index = instance_modified.name.find(suffix)
        stop_index = start_index + len(suffix) + 2
        if start_index is -1:
            modified_name_prefix = instance_modified.name
        # elif stop_index is -1:
        #     modified_name_prefix = instance_modified.name[:start_index-1]
        else :
            modified_name_prefix = instance_modified.name[:start_index-1] + instance_modified.name[stop_index:]
        matched = False
        for instance_original in original:
            if modified_name_prefix == instance_original.name.strip():
                if instance_modified.parent.name.strip() == instance_original.parent.name.strip():
                    matched = True
                    for port in instance_modified.get_ports():
                        try:
                            instance_original[port.name]
                        except KeyError:
                            instance_original[port.name] = None
                        if instance_modified[port.name] == instance_original[port.name]:
                            None
                            f.write("MATCH: "+instance_modified.name+' '+str(instance_modified[port.name])+'---'+str(instance_original[port.name])+' '+instance_original.name+' Port:'+port.name+'\n')
                        else:
                            f.write("NOT MATCH: "+instance_modified.name+' '+str(instance_modified[port.name])+'---'+str(instance_original[port.name])+' '+instance_original.name+' Port:'+port.name+'\n')
                            not_matched.append(instance_modified)
                        instance_modified._data.pop(port.name)
                    break
        if not matched:
            f.write(instance_modified.name + ' had no one to compare to\n')
            not_matched.append(instance_modified)
    f.close()
    return not_matched



netlist = sdn.parse('stopwatch_no_buf.edf')
netlist2 = sdn.parse('stopwatch_no_buf_modified.edf')

print(check_by_pin_connections(netlist,netlist2,'TMR','VOTER'))
