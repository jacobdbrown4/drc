import spydrnet as sdn
from spydrnet.util.selection import Selection
from spydrnet.uniquify import uniquify


def check_replication_by_step(original_netlist,modified_netlist,suffix='',organ_name='None'):
    '''
    Finds the steps in both an original and modified (replicated) design and compares them to be sure that they are still the same.

    A 'step' is going from one instance to the next downstream. For example, an input buffer is the first step. Then the LUT or flip flop or whatever is the next step.

        :param original netlist: original netlist
        :param modified netlist: the replicated netlist. Can contain voters/detectors
        :param suffix: suffix appended to the replicated instances' names e.g. 'TMR' or 'DWC'
        :param organ_name: name of organ inserted e.g. 'VOTER' or 'DETECTOR'
        :return: bool (matched,not_matched)

    Note: if check_replication_by_step returns false, try uniquifying the original netlist before checking.
    Note: to see the steps found and the results of the comparison, uncomment appropriate lines.
    '''

    uniquify(original_netlist)
    global top_instance
    top_instance = [modified_netlist.top_instance,original_netlist.top_instance]
    original_steps = make_steps(original_netlist,organ_name)

    keys = find_keys(modified_netlist,suffix)
    modified_steps = {}
    for key in keys:
        modified_steps.update({key:make_steps(modified_netlist,organ_name,key,suffix)})
    not_matched = compare_steps(original_steps,modified_steps,original_netlist.name)

    #print("Results printed to results_", original_netlist.name+".txt")
    # f = open("results_"+original_netlist.name+".txt","w")
    if not_matched:
        # print("Steps not matched")
        # f.write("Steps not matched\n")
        # for item in not_matched:
        #     f.write('\t'+item['key']+'\t'+str(item['instances'])+'\n')
        # f.close()
        return False
    else:
        # f.write("\nAll steps in the modified design match the corresponding step in the original design\n")
        # f.close()
        return True

def make_steps(current_netlist,organ_name,key='',suffix=''):
    steps = []
    list_of_ports = list(port for port in current_netlist.get_hports(filter = lambda x: (x.item.direction is sdn.IN and (key in x.item.name or suffix not in x.item.name) is True)))
    list_of_pins = []
    for port in list_of_ports:
        list_of_pins = list_of_pins + list(pin for pin in port.get_pins(selection = Selection.OUTSIDE))
    list_of_roots = []
    for pin in list_of_pins:
        list_of_roots = list_of_roots + (get_hports_next_instances(pin,organ_name,key,suffix))
        if current_netlist.top_instance in list_of_roots:
            list_of_roots.remove(current_netlist.top_instance)
    instances_seen = []
    instances_seen = set(list(x for x in set(list_of_roots)))
    i = 0
    next_instances = list(x for x in list_of_roots)
    while next_instances:
        steps.append(list(x.instance for x in next_instances))
        instances_seen.update(next_instances)
        next_instances = get_next_step(steps[i],instances_seen,organ_name,key,suffix)
        i += 1
    return steps

def get_next_step(current_step,instances_seen,organ_name,key,suffix):
    all_next_instances = set()
    for item in current_step:
        next_instances = get_next_instances(item,organ_name,key,suffix)
        next_instances = set(next_instances).symmetric_difference(instances_seen)
        next_instances = next_instances.difference(instances_seen)
        all_next_instances.update(next_instances)
    return list(x for x in all_next_instances)

def get_hports_next_instances(current_pin,organ_name,key,suffix):
    next_instances = []
    if current_pin.inner_pin.port.direction is sdn.IN:
        if current_pin.inner_pin.wire:
            next_instances = next_instances + list(pin2 for pin2 in current_pin.inner_pin.wire.get_pins(selection = Selection.OUTSIDE, filter = lambda x: (x.inner_pin.port.direction is sdn.IN and x is not current_pin)is True))
    elif current_pin.inner_pin.port.direction is sdn.OUT:
        out_port = current_pin.inner_pin.port
        for pin in out_port.get_pins(selection = Selection.OUTSIDE):
            if pin.wire:
                next_instances = next_instances + list(pin2 for pin2 in pin.wire.get_pins(selection = Selection.OUTSIDE,filter = lambda x:(x.inner_pin.port is not out_port) is True))
    next_instances = check_next_list(next_instances,organ_name,key,suffix)
    return next_instances

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
        if organ_name in next_instances[i].instance.name.upper():
            possible_next = get_next_instances(next_instances[i].instance,organ_name,'',suffix)
            if key in next_instances[i].instance.name:
                to_add = to_add + possible_next
            else:
                for x in possible_next:
                    if x.instance.is_leaf():
                        if suffix not in x.instance.name:
                            to_add.append(x)
                    else:
                        if suffix not in x.inner_pin.port.name:
                            to_add.append(x)
            to_remove.append(next_instances[i])
        elif 'COMPLEX' in next_instances[i].instance.name:
            possible_next = get_next_instances(next_instances[i].instance,organ_name,'',suffix)
            print(list(x.instance.name for x in possible_next))
            to_add = to_add + possible_next
            to_remove.append(next_instances[i])
        elif not next_instances[i].instance.is_leaf():
            if key in next_instances[i].inner_pin.port.name or suffix not in next_instances[i].inner_pin.port.name:
                None
            elif "COMPLEX" in next_instances[i].inner_pin.port.name:
                None
            else:
                to_remove.append(next_instances[i])
    next_instances = list(x for x in next_instances if not x in to_remove)
    next_instances = next_instances + to_add
    next_instances = list(x for x in next_instances if (key in x.instance.name or suffix not in x.instance.name))
    return next_instances

def find_keys(netlist,suffix):
    if suffix is '':
        return ''
    else:
        list_of_instances = list(instance for instance in netlist.get_instances())
        keys = []
        for instance in list_of_instances:
            start_index = instance.name.find(suffix)
            # stop_index = start_index+5
            stop_index = start_index + len(suffix) + 2
            if start_index is -1:
                None
            elif stop_index is -1:
                keys.append(instance.name[start_index:])
            else:
                keys.append(instance.name[start_index:stop_index])
    return set(keys)

def reformat(original_set,modified_set):
    original_list = original_set.copy()
    for i in range(len(original_list)):
        original_list[i] = sorted(list(instance.reference.name for instance in original_list[i]))
    for i in range(len(modified_set)):
        modified_set[i] = sorted(list(instance.reference.name for instance in modified_set[i]))
    return original_list,modified_set

def compare_steps(original,modified,name):
    steps_not_matched = []
    # f = open("results"+name+".txt","w")
    # f.write("\nRESULTS\n")
    for key in modified:
        # f.write(key+"\n")
        original_copy,modified[key] = reformat(original,modified[key])
        for i in range(len(modified[key])):
            try: 
                original_copy[i]
            except IndexError:
                original_copy.append(None)
            if (modified[key][i] == original_copy[i]) and (len(modified[key][i]) == len(original_copy[i])):
                None
                # f.write('\t'+str(modified[key][i])+"----matched----"+str(original_copy[i])+'\n')
            else:
                # f.write('\t'+str(modified[key][i])+" did not match the original design step"+'\n')
                # f.write('\tOriginal Design Step:'+str(original_copy[i])+'\n')
                steps_not_matched.append(modified[key][i])
            i += 1
    # f.close()
    return steps_not_matched

# netlist = sdn.parse("adder.edf")
# netlist2 = sdn.parse("adder_modified.edf")



# check_replication_by_step(netlist,netlist2,"TMR","VOTER")
# print(netlist.name)