import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet.util import selection
from spydrnet.util.selection import Selection
import time
from spydrnet_shrec.analysis.pin_clock_domain_analysis import pin_clock_domain_analysis
import sys
import os
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
    global get_next
    global get_previous
    global fix_name
    global check_next
    get_next = 0
    get_previous = 0
    fix_name = 0
    check_next = 0
    global get_next_total_time
    global get_previous_total_time
    global fix_name_total_time
    global check_next_total_time
    get_next_total_time = 0
    get_previous_total_time = 0
    fix_name_total_time = 0
    check_next_total_time = 0

    uniquify(original_netlist)
    t2 = time.time()
    original_instances = list(x for x in original_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    # get_hports_instances(original_netlist,organ_name,suffix)

    old_stdout = sys.stdout # backup current stdout
    sys.stdout = open(os.devnull, "w")
    information = pin_clock_domain_analysis(original_netlist)
    sys.stdout = old_stdout # reset old stdout

    for item in information:
        info = sorted(list(x for x in set(fix_instance_connection_name(x.parent.parent.item,suffix) for x in information[item] if (organ_name not in x.parent.parent.item.name and 'COMPLEX' not in x.parent.parent.item.name))))
        add_info(item.parent.parent.item,item.item,info)
    get_pin_connections(original_instances,organ_name,suffix)
    t3 = time.time()
    print("GET ORIGINAL PIN CONNECTION TIME:",t3-t2)
    t4 = time.time()
    modified_instances = list(x for x in modified_netlist.get_hinstances(recursive=True,filter = lambda x: (filter_instances(x.item,organ_name)) is True))
    # get_hports_instances(modified_netlist,organ_name,suffix)

    old_stdout = sys.stdout # backup current stdout
    sys.stdout = open(os.devnull, "w")
    information = pin_clock_domain_analysis(modified_netlist)
    sys.stdout = old_stdout # reset old stdout

    for item in information:
        info = sorted(list(x for x in set(fix_instance_connection_name(x.parent.parent.item,suffix) for x in information[item] if (organ_name not in x.parent.parent.item.name and 'COMPLEX' not in x.parent.parent.item.name))))
        add_info(item.parent.parent.item,item.item,info)
    get_pin_connections(modified_instances,organ_name,suffix)
    t5 = time.time()
    print("GET MODIFIED PIN CONNECTIONS TIME:",t5-t4)

    original_non_leafs = {}
    for instance in original_netlist.get_hinstances(recursive = True,filter= lambda x: (not x.item.is_leaf()) is True):
        if instance.item.reference.name in original_non_leafs.keys():
            original_non_leafs[instance.item.reference.name] += list(x for x in instance.item.reference.children if (organ_name not in x.name and 'COMPLEX' not in x.name))
        else:
            original_non_leafs.update({instance.item.reference.name:list(x for x in instance.item.reference.children if (organ_name not in x.name and 'COMPLEX' not in x.name))})
    original_non_leafs.update({original_netlist.top_instance.reference.name:list(x for x in instance.item.reference.children if (organ_name not in x.name and 'COMPLEX' not in x.name))})

    not_matched = compare_pin_connections(original_non_leafs,modified_instances,suffix,original_netlist.name)
    t1 = time.time()
    print("FULL CHECK PIN CONNECTIONS TIME:",t1-t0)

    print("get_next visited",get_next,"for total time of",get_next_total_time)
    print("check_next visited",check_next,"for total time of",check_next_total_time)
    print('get_previous visited',get_previous,"for total time of",get_previous_total_time)
    print('fix_name visited', fix_name,"for total time of",fix_name_total_time)
    if not_matched:
        # for item in not_matched:
        #     print(item.name,' from ',item.parent.name)
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
    global fix_name
    fix_name += 1
    t0 = time.time()
    modified_name_prefix = None
    start_index = current_instance.name.find(suffix)
    stop_index = start_index + len(suffix) + 2
    if start_index is -1:
        modified_name_prefix = current_instance.name
    else :
        modified_name_prefix = current_instance.name[:start_index-1] + current_instance.name[stop_index:]
    t1 = time.time()
    global fix_name_total_time
    fix_name_total_time += t1-t0
    return modified_name_prefix

def get_hports_instances(netlist,organ_name,suffix):
    desired_port_names = ['CLK','RST']
    for port in netlist.get_hports(filter=lambda x: (x.item.direction is sdn.IN and any(name in x.item.name.upper() for name in desired_port_names))):
        for pin in port.item.get_pins(selection = Selection.INSIDE):
            next_instances = get_next_instances(pin,organ_name,'','')
            next_instances = check_instances(next_instances,organ_name)
            for instance in next_instances:
                add_info(instance.instance,instance,[netlist.top_instance.name])

def check_instances(instance_list,organ_name):
    to_remove = []
    to_add = []
    # possible_next = []
    for instance in instance_list:
        if "BUF" in instance.instance.reference.name.upper():
            to_remove.append(instance)
            for pin in instance.instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x: (x.inner_pin.port.direction is sdn.OUT)):
                possible_next = get_next_instances(pin,organ_name,'','')
                to_add = to_add + check_instances(possible_next,organ_name)

        elif not instance.instance.is_leaf():
            to_remove.append(instance)
            possible_next = []
            for current_pin in instance.inner_pin.port.get_hpins():
                if current_pin.item.wire:
                    for pin2 in current_pin.item.wire.get_pins(selection=selection.Selection.OUTSIDE,filter=lambda x: (x is not current_pin)is True):
                        if pin2.instance in instance.instance.reference.children:
                            possible_next.append(pin2)
            to_add = to_add + check_instances(possible_next,organ_name)
    instance_list = instance_list + to_add
    instance_list = list(x for x in instance_list if x not in to_remove)
    return instance_list


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
                    add_info(instance,pin,neighbor_pins)
                elif pin.inner_pin.port.direction is sdn.IN:
                    get_previous = True
                    if pin.inner_pin.port.name in instance._data:
                        if instance[pin.inner_pin.port.name]:
                            get_previous = False
                            # print("get previous is false for",pin.inner_pin.port.name,"of",instance.name,'from',instance.parent.name)
                    if get_previous:
                        previous_pin = get_previous_instance(pin,organ_name,key,suffix)
                        if previous_pin is None:
                            neighbor_pins = []
                        else:
                            neighbor_pins = [fix_instance_connection_name(previous_pin.instance,suffix)]
                        add_info(instance,pin,neighbor_pins)

                # add_info(instance,pin,neighbor_pins)
                # if pin.inner_pin.port.name in instance._data:
                #     instance[pin.inner_pin.port.name] = instance[pin.inner_pin.port.name] + neighbor_pins
                # else:
                #     instance[pin.inner_pin.port.name] = neighbor_pins
            else:
                # if not pin.inner_pin.port.name in instance._data:
                #     instance[pin.inner_pin.port.name] = []
                add_info(pin.instance,pin,[])

def add_info(current_instance,current_pin,info):
    if current_pin.__class__ is sdn.OuterPin:
        current_pin = current_pin.inner_pin
    if current_pin.port.name in current_instance._data:
        current_instance[current_pin.port.name] = current_instance[current_pin.port.name] + info
    else:
        current_instance[current_pin.port.name] = info

    #maybe to add:
    #current_instance[sdn.Href(current_pin,current_pin.instance)] if it's not already an href

    # if current_pin.inner_pin.port.name in current_instance._data:
    #     current_instance[current_pin.inner_pin.port.name] = current_instance[current_pin.inner_pin.port.name] + info
    # else:
    #     current_instance[current_pin.inner_pin.port.name] = info


def get_next_instances(current_pin,organ_name,key,suffix):
    global get_next
    get_next += 1
    t0 = time.time()

    next_instances = []
    next_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin)))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    t1 = time.time()
    global get_next_total_time
    get_next_total_time += t1-t0
    return next_instances

def check_next_list(next_instances,organ_name,key,suffix):
    global check_next
    global check_next_total_time
    check_next += 1
    t0 = time.time()
    to_remove = []
    to_add = []
    got_voters_next_so_done = False
    for i in range(len(next_instances)):
        if organ_name in next_instances[i].instance.name.upper() or 'COMPLEX' in next_instances[i].instance.name:
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
        t1 = time.time()
        check_next_total_time += t1-t0
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
            # wires = []
            wires = list(x for x in instance.inner_pin.port.get_wires(selection = Selection.OUTSIDE))
            # for pin2 in instance.inner_pin.port.get_pins(selection = Selection.OUTSIDE):
            #     if pin2.wire:
            #         wires.append(pin2.wire)
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
    t1 = time.time()
    check_next_total_time += t1-t0
    return next_instances

def get_organ_previous(current_pin,organ_name):
    previous_instances = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin and organ_name not in x.instance.name and 'COMPLEX' not in x.instance.name)is True))
    return previous_instances

def filter_previous_instances(instance_list):
    #gotta be a leaf and out
    #or its parent and in
    # or a non leaf and out
    None

def get_previous_instance(current_pin,organ_name,key,suffix):
    global get_previous
    global get_previous_total_time
    get_previous += 1
    t0 = time.time()
    previous_instances = []
    to_remove = []
    to_add = []
    previous_instances = list(pin2 for pin2 in current_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x is not current_pin and not (x.instance.is_leaf() and x.inner_pin.port.direction is sdn.IN))is True))
    for i in range(len(previous_instances)):
        if organ_name in previous_instances[i].instance.name or 'COMPLEX' in previous_instances[i].instance.name:
            input_pins = list(pin for pin in previous_instances[i].instance.get_pins(selection = Selection.OUTSIDE,filter=lambda x:x.inner_pin.port.direction is sdn.IN))
            possible_next = []
            for pin in input_pins:
                possible_next = possible_next + get_organ_previous(pin,organ_name)
            to_add = to_add + possible_next
            to_remove.append(previous_instances[i])
        # elif not (previous_instances[i].instance.is_leaf() and previous_instances[i].inner_pin.port.direction is sdn.OUT):
        #     to_remove.append(previous_instances[i])
    previous_instances = previous_instances + to_add
    previous_instances = list(x for x in previous_instances if x not in to_remove)
    driver = None
    # previous_instances.reverse()
    for instance in previous_instances:
        if instance.instance.is_leaf() and instance.inner_pin.port.direction is sdn.OUT:
            if key in instance.instance.name:
                driver = instance
                t1 = time.time()
                get_previous_total_time += t1-t0
                return driver
            elif suffix not in instance.instance.name:
                driver = instance
                t1 = time.time()
                get_previous_total_time += t1-t0
                return driver
        elif not instance.instance.is_leaf():
            if key in instance.inner_pin.port.name or suffix not in instance.inner_pin.port.name:
                if instance.instance not in top_instances:
                    if instance.instance.reference.name is current_pin.instance.parent.name:
                        if instance.inner_pin.port.direction is sdn.IN:
                            driver = instance
                            t1 = time.time()
                            get_previous_total_time += t1-t0
                            return driver
                    else:
                        if instance.inner_pin.port.direction is sdn.OUT:
                            driver = instance
                            t1 = time.time()
                            get_previous_total_time += t1-t0
                            return driver
                else:
                    if instance.inner_pin.port.direction is sdn.IN:
                        driver = instance
                        t1 = time.time()
                        get_previous_total_time += t1-t0
                        return driver
    t1 = time.time()
    get_previous_total_time += t1-t0
    return driver

def compare_pin_connections(original,modified,suffix,name):
    t6 = time.time()
    print("results printed to connections_"+name+".txt")
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
    t7 = time.time()
    print("COMPARING CONNECTIONS TIME",t7-t6)
    return not_matched

