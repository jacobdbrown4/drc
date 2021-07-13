import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet.util.selection import Selection
import time
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
    t0 = time.time()
    global top_instances
    top_instances = [original_netlist.top_instance,modified_netlist.top_instance]

    uniquify(original_netlist)
    t2 = time.time()
    original_instances = list(x for x in original_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    get_pin_connections(original_instances,organ_name,suffix)
    t3 = time.time()
    print("GET ORIGINAL PIN CONNECTION TIME:",t3-t2)
    t4 = time.time()
    modified_instances = list(x for x in modified_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    get_pin_connections(modified_instances,organ_name,suffix)
    t5 = time.time()
    print("GET MODIFIED PIN CONNECTIONS TIME:",t5-t4)

    original_non_leafs = {}
    for instance in original_netlist.get_hinstances(recursive = True,filter= lambda x: (not x.item.is_leaf()) is True):
        if instance.item.reference.name in original_non_leafs.keys():
            original_non_leafs[instance.item.reference.name] += list(x for x in instance.item.reference.children)
        else:
            original_non_leafs.update({instance.item.reference.name:list(x for x in instance.item.reference.children)})
    original_non_leafs.update({original_netlist.top_instance.reference.name:list(x for x in original_netlist.top_instance.reference.children)})

    not_matched = compare_pin_connections(original_non_leafs,modified_instances,suffix,original_netlist.name)
    t1 = time.time()
    print("FULL CHECK PIN CONNECTIONS TIME:",t1-t0)
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
    else :
        modified_name_prefix = current_instance.name[:start_index-1] + current_instance.name[stop_index:]
    return modified_name_prefix

def get_pin_connections(instance_list,organ_name,suffix):
    for instance in instance_list:
        instance = instance.item
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
                    neighbor_pins = sorted(list(x for x in set(fix_instance_connection_name(x,suffix) for x in pins)))
                elif pin.inner_pin.port.direction is sdn.IN:
                    previous_pin = get_previous_instance(pin,organ_name,key,suffix)
                    if previous_pin is None:
                        neighbor_pins = []
                    else:
                        neighbor_pins = [fix_instance_connection_name(previous_pin.instance,suffix)]

                if pin.inner_pin.port.name in instance._data:
                    instance[pin.inner_pin.port.name] = instance[pin.inner_pin.port.name] + neighbor_pins
                else:
                    instance[pin.inner_pin.port.name] = neighbor_pins
            else:
                if not pin.inner_pin.port.name in instance._data:
                    instance[pin.inner_pin.port.name] = []


def get_next_instances(current_pin,organ_name,key,suffix):
    next_instances = []
    next_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin)))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    return next_instances

def check_next_list(next_instances,organ_name,key,suffix):
    to_remove = []
    to_add = []
    for i in range(len(next_instances)):
        if organ_name in next_instances[i].instance.name.upper() or 'COMPLEX' in next_instances[i].instance.name:
            print("Found voter out of: ",len(next_instances))
            output_pin = next(next_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.OUT),None)
            if output_pin.wire:
                possible_next = get_next_instances(output_pin,organ_name,'',suffix)
                to_add = to_add + possible_next
            to_remove.append(next_instances[i])
    next_instances = next_instances + to_add
    for instance in next_instances:
        if instance.instance.is_leaf():
            if key in instance.instance.name:
                None
            elif suffix not in instance.instance.name:
                None
            else:
                to_remove.append(instance)
        elif not instance.instance.is_leaf():
            wires = []
            for pin2 in instance.inner_pin.port.get_pins(selection = Selection.OUTSIDE):
                if pin2.wire:
                    wires.append(pin2.wire)
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
    i = 0
    previous_instances.reverse()
    for instance in previous_instances:
        if instance.instance.is_leaf() and instance.inner_pin.port.direction is sdn.OUT:
            if key in instance.instance.name:
                driver = instance
                # print(len(previous_instances),' - ',i)
                return driver
            elif suffix not in instance.instance.name:
                driver = instance
                # print(len(previous_instances),' - ',i)
                return driver
        elif not instance.instance.is_leaf():
            if key in instance.inner_pin.port.name or suffix not in instance.inner_pin.port.name:
                if instance.instance not in top_instances:
                    if instance.instance.reference.name is current_pin.instance.parent.name:
                        if instance.inner_pin.port.direction is sdn.IN:
                            driver = instance
                            # print(len(previous_instances),' - ',i)
                            return driver
                    else:
                        if instance.inner_pin.port.direction is sdn.OUT:
                            driver = instance
                            # print(len(previous_instances),' - ',i)
                            return driver
                else:
                    if instance.inner_pin.port.direction is sdn.IN:
                        driver = instance
                        # print(len(previous_instances),' - ',i)
                        return driver
        # i+=1
    # if len(previous_instances) > i + 1:
    # print(len(previous_instances),' - ',i)
    return driver

def compare_pin_connections(original,modified,suffix,name):
    t6 = time.time()
    # print("results printed to connections_"+name+".txt")
    f = open("connections_"+name+".txt",'w')
    not_matched = []
    for instance_modified in modified:
    #     modified_name_prefix = None
    #     start_index = instance_modified.item.name.find(suffix)
    #     stop_index = start_index + len(suffix) + 2
    #     if start_index is -1:
    #         modified_name_prefix = instance_modified.item.name
    #     else :
    #         modified_name_prefix = instance_modified.item.name[:start_index-1] + instance_modified.item.name[stop_index:]
        # modified_name_prefix = None
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
    t7 = time.time()
    print("COMPARING CONNECTIONS TIME",t7-t6)
    return not_matched

