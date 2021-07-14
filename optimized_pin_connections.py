import spydrnet as sdn
from spydrnet.uniquify import uniquify
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
    global organs
    organs = [organ_name,'COMPLEX']

    uniquify(original_netlist)
    original_instances = list(x for x in original_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    get_pin_connections(original_instances,organ_name,suffix)
    original_instances = list(x for x in original_instances if x.item.is_leaf())

    modified_instances = list(x for x in modified_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    get_pin_connections(modified_instances,organ_name,suffix)
    modified_instances = list(x for x in modified_instances if x.item.is_leaf())

    original_non_leafs = {}
    for instance in original_netlist.get_hinstances(recursive = True,filter= lambda x: (not x.item.is_leaf()) is True):
        if instance.item.reference.name in original_non_leafs.keys():
            original_non_leafs[instance.item.reference.name] += list(x for x in instance.item.reference.children if not (any(organ in x.name for organ in organs)))
        else:
            original_non_leafs.update({instance.item.reference.name:list(x for x in instance.item.reference.children if not (any(organ in x.name for organ in organs)))})
    original_non_leafs.update({original_netlist.top_instance.reference.name:list(x for x in original_netlist.top_instance.reference.children if not (any(organ in x.name for organ in organs)))})

    not_matched = compare_pin_connections(original_non_leafs,modified_instances,suffix,original_netlist.name)
    if not_matched:
        # for item in not_matched:
        #     print(item.name,' from ',item.parent.name)
        return False
    else:
        return True

def filter_instances(instance,organ_name):
    # if not instance.is_leaf():
    #     return False
    if any(organ in instance.name for organ in organs):
        return False
    elif 'GND' in instance.name:
        return False
    else:
        return True

def fix_instance_connection_name(current_instance,suffix):
    modified_name_prefix = None
    start_index = current_instance.name.find(suffix)
    stop_index = start_index + len(suffix) + 2
    if start_index is -1:
        modified_name_prefix = current_instance.name
    else :
        modified_name_prefix = current_instance.name[:start_index-1] + current_instance.name[stop_index:]
    return modified_name_prefix

def find_key(instance,suffix):
    start_index = instance.name.find(suffix)
    stop_index = start_index + len(suffix) + 2
    if start_index is -1:
        key = ''
    else:
        key = instance.name[start_index:stop_index]
    return key

def get_pin_connections(instance_list,organ_name,suffix):
    in_pins_todo_later = []
    for instance in instance_list:
        instance = instance.item
        if instance.is_leaf():
            key = find_key(instance,suffix)
            for pin in instance.get_pins(selection = Selection.OUTSIDE):
                if pin.wire:
                    if pin.inner_pin.port.direction is sdn.OUT:
                        get_pin_connections_helper(instance,pin,organ_name,suffix,key)
                    elif pin.inner_pin.port.direction is sdn.IN:
                        in_pins_todo_later.append(pin)
                    else:
                        add_info(pin.instance,pin,['INOUT_PORT'])
                else:
                    add_info(pin.instance,pin,[])
        elif not instance.is_leaf():
            for port in instance.get_hports(filter=lambda x: (x.item.direction is sdn.IN)is True):
                key = find_key(port,suffix)
                for pin in port.item.get_pins(selection = Selection.INSIDE):
                    if pin.wire:
                        pins = list(x for x in get_next_instances(pin,organ_name,key,suffix))
                        add_drivers(instance,pins,suffix,key)
    for pin in in_pins_todo_later:
        get_pin_connections_helper(pin.instance,pin,organ_name,suffix,find_key(pin.instance,suffix))

def add_drivers(instance,pins,suffix,key):
    for pin in pins:
        if key in pin.instance.name or suffix not in pin.instance.name:
            add_info(pin.instance,pin,[fix_instance_connection_name(instance,suffix)])

def get_pin_connections_helper(instance,pin,organ_name,suffix,key):
    if pin.inner_pin.port.direction is sdn.OUT:
        pins = list(x for x in get_next_instances(pin,organ_name,key,suffix))
        pins_to_add = set(x.instance for x in pins)
        neighbor_pins = sorted(list(x for x in set(fix_instance_connection_name(x,suffix) for x in pins_to_add)))
        add_info(instance,pin,neighbor_pins)
        add_drivers(instance,pins,suffix,key)
    elif pin.inner_pin.port.direction is sdn.IN:
        get_previous = True
        if pin.inner_pin.port.name in instance._data:
            if instance[pin.inner_pin.port.name]:
                get_previous = False
        if get_previous:
            previous_pin = get_previous_instance(pin,organ_name,key,suffix)
            if previous_pin is None:
                neighbor_pins = []
            else:
                neighbor_pins = [fix_instance_connection_name(previous_pin.instance,suffix)]
            add_info(instance,pin,neighbor_pins)

def add_info(current_instance,current_pin,info):
    if current_pin.__class__ is sdn.OuterPin:
        current_pin = current_pin.inner_pin
    if current_pin.port.name in current_instance._data:
        current_instance[current_pin.port.name].update(set(info))
    else:
        current_instance[current_pin.port.name] = set(info)

def get_next_instances(current_pin,organ_name,key,suffix):
    next_instances = []
    next_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin)))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    return next_instances

def check_next_list(next_instances,organ_name,key,suffix):
    to_remove = []
    to_add = []
    got_voters_next_so_done = False
    for i in range(len(next_instances)):
        if any(organ in next_instances[i].instance.name for organ in organs):
            output_pin = next(next_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.OUT),None)
            if output_pin.wire:
                possible_next = get_next_instances(output_pin,organ_name,key,suffix)
                to_add = to_add + possible_next
            to_remove.append(next_instances[i])
            if key in next_instances[i].instance.name.upper() or suffix not in next_instances[i].instance.name.upper():
                got_voters_next_so_done = True
    next_instances = next_instances + to_add
    if got_voters_next_so_done:
        next_instances = list(x for x in next_instances if not x in to_remove)
        return next_instances
    for instance in next_instances:
        if instance.instance.is_leaf():
            if key in instance.instance.name:
                None
            elif suffix not in instance.instance.name:
                None
            else:
                to_remove.append(instance)
        elif not instance.instance.is_leaf():
            wires = list(x for x in instance.inner_pin.port.get_wires(selection = Selection.OUTSIDE))
            if not wires:
                to_remove.append(instance)
            else:
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
    return next_instances

def get_organ_previous(current_pin,organ_name):
    previous_instances = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin and organ_name not in x.instance.name and 'COMPLEX' not in x.instance.name)is True))
    return previous_instances

def get_previous_instance(current_pin,organ_name,key,suffix):
    previous_instances = []
    to_remove = []
    to_add = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin and not (x.instance.is_leaf() and x.inner_pin.port.direction is sdn.IN))is True))
    for i in range(len(previous_instances)):
        if any(organ in previous_instances[i].instance.name for organ in organs):
            input_pins = list(pin for pin in previous_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.IN))
            possible_next = []
            for pin in input_pins:
                possible_next = possible_next + get_organ_previous(pin,organ_name)
            to_add = to_add + possible_next
            to_remove.append(previous_instances[i])
    previous_instances = previous_instances + to_add
    previous_instances = list(x for x in previous_instances if x not in to_remove)
    return find_driver(previous_instances,current_pin,key,suffix)

def find_driver(instance_list,current_pin,key,suffix):
    driver = None
    for instance in instance_list:
        if instance.instance.is_leaf() and instance.inner_pin.port.direction is sdn.OUT:
            if key in instance.instance.name:
                driver = instance
                return driver
            elif suffix not in instance.instance.name:
                driver = instance
                return driver
        elif not instance.instance.is_leaf():
            if key in instance.inner_pin.port.name or suffix not in instance.inner_pin.port.name:
                if instance.instance not in top_instances:
                    if instance.instance.reference.name is current_pin.instance.parent.name:
                        if instance.inner_pin.port.direction is sdn.IN:
                            driver = instance
                            return driver
                    else:
                        if instance.inner_pin.port.direction is sdn.OUT:
                            driver = instance
                            return driver
                else:
                    if instance.inner_pin.port.direction is sdn.IN:
                        driver = instance
                        return driver
    return driver

def compare_pin_connections(original,modified,suffix,name):
    # print("results printed to connections_"+name+".txt")
    f = open("connections_"+name+".txt",'w')
    not_matched = []
    for instance_modified in modified:
        modified_name_prefix = fix_instance_connection_name(instance_modified.item,suffix)
        matched = False
        if instance_modified.parent.item.reference.name in original.keys():
            for instance_original in original[instance_modified.parent.item.reference.name]:
                if modified_name_prefix == instance_original.name:
                        matched = True
                        instance_modified = instance_modified.item
                        for port in instance_modified.get_ports():
                            try:
                                instance_original[port.name]
                            except KeyError:
                                instance_original[port.name] = None
                            if instance_modified[port.name] == instance_original[port.name]:
                                None
                                f.write("MATCH: "+instance_modified.name+' '+str(instance_modified[port.name])+'---'+str(instance_original[port.name])+' '+instance_original.name+' Port:'+port.name+' Parent:'+instance_modified.parent.name+'\n')
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

# def compare_a_match(instance_modified,instance_original,f):
