from time import time
import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet.util.selection import Selection
from spydrnet_tmr.utils.design_rule_check.util import find_key, get_original_name

def check_connections(original_netlist,modified_netlist,suffix,organ_names=[],write_enable=False):
    '''
    Looks at each leaf instance's pins in both netlists and finds what it drives/what drives it and makes sure corresponding instance pins between the netlists match up.

    For example, if the instance '**a_lut_3**' has a pin that drives the data_in port on the instance '**a_flip_flop**' in the original design, it will make sure that '**a_lut_3_TMR_0**' has a pin that drives the data_in port on '**a_flip_flop_TMR_0**' (it will check this for each TMR_1 and TMR_2 as well)

    :param original_netlist: original netlist
    :param modified_netlist: the replicated netlist. Can contain organs (voters/detectors)
    :param suffix: string appended to the replicated instances' names (e.g. 'TMR' or 'DWC')
    :param organ_name: list of names of the organs inserted into the design (e.g. ['VOTER', 'DETECTOR'])
    :param write_enable: output results to text file
    :type write_enable: bool
    :return: bool (matched, not_matched)
    '''

    class_object = DRCConnections(original_netlist,modified_netlist,suffix,organ_names,write_enable)
    print("NEW CHECKING CONNECTIONS")
    return class_object._check_connections()


class DRCConnections():
    def __init__(self,original_netlist,modified_netlist,suffix,organ_names,write_enable):
        self.original_netlist = original_netlist
        self.modified_netlist = modified_netlist
        self.suffix = suffix
        self.write_enable =write_enable
        self.output_txt_file_name = 'drc_connection_results_'+original_netlist.name+'.txt'
        self.top_instances = [original_netlist.top_instance,modified_netlist.top_instance]
        self.organs = organ_names
        self.input_pins_todo_later = []
        self.original_port_dict = {}
        self.modified_port_dict = {}
        self.not_matched = []
        self.organs.append('COMPLEX')

        self.previous = 0
        self.next = 0
        self.compare = 0

    def _check_connections(self):
        uniquify(self.original_netlist)
        self.get_instance_lists()
        # t0 = time()
        self.get_pin_connections(self.original_instances_all,self.original_port_dict,self.original_netlist)
        # t1= time()
        # print("GETTING OLD CONNECTIONS TIME: ",t1-t0)
        # t2 = time()
        self.get_pin_connections(self.modified_instances_all,self.modified_port_dict,self.modified_netlist)
        # t3 = time()
        # print("GETTING NEW CONNECTIONS TIME: ",t3-t2)
        #self.check_pin_connections() make sure we connect to only our domain??
        self.compare_pin_connections()
        print("TIME NEXT: ",self.next)
        print("TIME PREVIOUS: ",self.previous)
        print("TIME COMPARE: ",self.compare)
        if self.not_matched:
            print("FAILED")
            return False
        else:
            print("PASSED")
            return True

    def get_instance_lists(self):
        self.original_instances_all = list(x for x in self.original_netlist.get_hinstances(
                                            recursive=True,filter = lambda x: 
                                                (self.filter_instances(x.item)) is True))
        self.modified_instances_all = list(x for x in self.modified_netlist.get_hinstances(
                                            recursive=True,filter = lambda x: 
                                                (self.filter_instances(x.item)) is True))
        # self.modified_instances_leafs = list(x for x in self.modified_instances_all if x.item.is_leaf())

        # self.original_non_leafs = {}
        # for instance in self.original_netlist.get_hinstances(recursive=True,filter=lambda x: x.item.is_leaf()):
        #     if instance.parent.name in self.original_non_leafs.keys():
        #         self.original_non_leafs[instance.parent.name] += [instance]
        #     else:
        #         self.original_non_leafs[instance.parent.name] = [instance]
    
    def is_organ(self,instance):
        if any(organ in instance.name for organ in self.organs):
            return True
        return False
    
    def filter_instances(self,instance):
        if self.is_organ(instance):
            return False
        # elif 'GND' in instance.name:
        #     return False
        # elif 'VCC' in instance.name:
        #     return False
        else:
            return True

    def get_pin_connections(self,instance_list,dict,netlist):
        self.input_pins_todo_later = []
        for instance in instance_list:
            if instance.item.is_leaf():
                self.get_leaf_pin_connections(instance,dict)
            else:
                self.get_non_leaf_pin_connections(instance,dict)
        self.get_netlist_hport_connections(netlist,dict)
        self.do_pins_todo_later(dict)

    def get_leaf_pin_connections(self,instance,dict):
        key = find_key(instance.item,self.suffix)
        for pin in instance.get_hpins():
            port = pin.parent.item
            associate_outer_pin = instance.item.pins[pin.item]
            if associate_outer_pin.wire:
                if port.direction is sdn.OUT:
                    self.get_pin_connections_helper(instance.item,pin,key,dict)
                elif port.direction is sdn.IN:
                    self.input_pins_todo_later.append((pin,key))
                else:
                    dict[pin.name].update(set('INOUT_PORT'))
            else:
                dict[pin.name] = set()
    
    def get_non_leaf_pin_connections(self,instance,dict):
        for port in instance.get_hports():
            key = find_key(port.item,self.suffix)
            for hpin in port.item.get_hpins():
                if port.item.direction is sdn.IN:
                    if hpin.item.wire:
                        pins = set(x for x in self.get_next_instances(hpin,hpin.item,key))
                        self.add_drivers(instance,pins,dict)
                elif port.item.direction is sdn.OUT:
                    instance_item = instance
                    if instance.__class__ is sdn.HRef:
                        instance_item = instance.item
                    pin = instance_item.pins[hpin.item]
                    if pin.wire:
                        pins = set(x for x in self.get_next_instances(hpin,pin,key))
                        self.add_drivers(instance,pins,dict)

    def get_netlist_hport_connections(self,netlist,dict):
        instance = netlist.top_instance
        self.get_non_leaf_pin_connections(instance,dict)
    
    def do_pins_todo_later(self,dict):
        for pin in self.input_pins_todo_later:
            instance = pin[0].parent.parent.item
            key = pin[1]
            self.get_pin_connections_helper(instance,pin[0],key,dict)

    def get_pin_connections_helper(self,instance,hpin,key,dict):
        associated_outter_pin = instance.pins[hpin.item]
        port = hpin.parent.item
        if port.direction is sdn.OUT:
            pins = set(x for x in self.get_next_instances(hpin,associated_outter_pin,key))
            neighbor_pins = set(x.name for x in pins)
            self.add_info_to_dict(hpin,neighbor_pins,dict)
            self.add_drivers(instance,pins,dict)
        elif port.direction is sdn.IN:
            get_previous = True
            if hpin.name in dict.keys():
                get_previous = False
            if get_previous:
                previous_pins = set(x.name for x in self.get_previous_instances(hpin,associated_outter_pin,key))
                self.add_info_to_dict(hpin,previous_pins,dict)

    def add_drivers(self,instance,pins,dict):
        for pin in pins:
            self.add_info_to_dict(pin,[instance.name],dict)

    def add_info_to_dict(self,pin,info,dict):
        if pin.name in dict.keys():
            dict[pin.name].update(set(info))
        else:
            dict[pin.name] = set(info)

    def get_next_instances(self,hpin,current_pin,key):
        t0 = time()
        next_instances = list(pin for pin in current_pin.wire.get_hpins() if pin is not hpin)
        next_instances = self.check_next_instances(next_instances,key)
        t1 = time()
        self.next += (t1-t0)
        return next_instances

    # add check organ next. IF it's our organ, get all those next. If not, get none of them.
    # maybe can do that all just in check next list, maybe not though. but what if not our organ outputs to non replicated.

    def check_next_instances(self,next_instances,key):
        to_remove = []
        to_add = []
        for i,instance_pin in enumerate(next_instances):
            instance_of_pin = instance_pin.parent.parent.item
            if self.is_organ(instance_of_pin):
                organ_output_pins = list(x for x in instance_of_pin.get_hpins() if x.parent.item.direction is sdn.OUT)
                if organ_output_pins:
                    for pin in organ_output_pins:
                        associate_outter_pin = instance_of_pin.pins[pin.item]
                        if associate_outter_pin.wire:
                            possible_next = self.get_organ_next(pin,associate_outter_pin,key)
                            to_add = to_add + possible_next
                to_remove.append(instance_pin)
        next_instances += to_add
        next_instances = list(x for x in next_instances if not x in to_remove)
        return next_instances
    
    def get_organ_next(self,organ_hpin,organ_current_pin,key):
        to_remove = []
        to_add = []
        next_instances = list(pin for pin in organ_current_pin.wire.get_hpins() if pin is not organ_hpin)
        for i,instance_pin in enumerate(next_instances):
            instance_of_pin = instance_pin.parent.parent.item
            if self.is_organ(instance_of_pin):
                organ_output_pins = list(x for x in instance_of_pin.get_hpins() if x.parent.item.direction is sdn.OUT)
                if organ_output_pins:
                    for pin in organ_output_pins:
                        associate_outter_pin = instance_of_pin.pins[pin.item]
                        if associate_outter_pin.wire:
                            possible_next = self.get_organ_next(pin,associate_outter_pin,key)
                            to_add = to_add + possible_next
                to_remove.append(instance_pin)
        next_instances += to_add
        for instance_pin in next_instances:
            instance_of_pin = instance_pin.parent.parent.item
            if instance_of_pin.is_leaf():
                if key not in instance_of_pin.name and self.suffix in instance_of_pin.name:
                    to_remove.append(instance_pin)
            else:
                port = instance_pin.parent.item
                wires = list(x for x in port.get_wires(selection = Selection.OUTSIDE))
                if not wires and not instance_of_pin in self.top_instances:
                    to_remove.append(instance_pin)
                else:
                    if key not in port.name and self.suffix in port.name:
                        if 'COMPLEX' not in port.name:
                            to_remove.append(instance_pin)

        next_instances = list(x for x in next_instances if not x in to_remove)
        return next_instances


    def get_previous_instances(self,hpin,current_pin,key):
        t0 = time()
        previous_instances = []
        to_remove = []
        to_add = []
        previous_instances = list(pin for pin in current_pin.wire.get_hpins() if not (pin.parent.parent.item.is_leaf() and pin.parent.item.direction is sdn.IN))
        for i,instance_pin in enumerate(previous_instances):
            instance_of_pin = instance_pin.parent.parent.item
            if self.is_organ(instance_of_pin):
                input_pins = list(pin for pin in instance_of_pin.get_hpins() if pin.parent.item.direction is sdn.IN)
                possible_next = []
                for hpin in input_pins:
                    associated_outter_pin = hpin.parent.parent.item.pins[hpin.item]
                    possible_next += self.get_organ_previous(hpin,associated_outter_pin)
                to_add = to_add + possible_next
                to_remove.append(instance_pin)
        previous_instances = previous_instances + to_add
        previous_instances = list(x for x in previous_instances if x not in to_remove)
        driver = self.find_driver(previous_instances,hpin)
        t1 = time()
        self.previous += (t1-t0)
        return driver

    def get_organ_previous(self,hpin,current_pin):
        previous_instances = []
        previous_instances = list(pin for pin in current_pin.wire.get_hpins() if (pin is not hpin and not self.is_organ(pin.parent.parent.item))is True)
        return previous_instances

    def find_driver(self,instance_list,current_hpin):
        driver = []
        for instance_pin in instance_list:
            instance_of_pin = instance_pin.parent.parent
            port = instance_pin.parent.item
            if instance_of_pin.item.is_leaf() and port.direction is sdn.OUT:
                driver.append(instance_pin)
            else:
                if instance_of_pin is current_hpin.parent.parent.parent:
                    if port.direction is sdn.IN:
                        driver.append(instance_pin)
                else:
                    if port.direction is sdn.OUT:
                        driver.append(instance_pin)
        return driver

    def compare_pin_connections(self):
        t0 = time()
        f = None
        if self.write_enable:
            f = open(self.output_txt_file_name,'w')
        for key in self.modified_port_dict.keys():
            if 'GND' not in key and 'VCC' not in key:
                key_without_suffixes = get_original_name(key,self.suffix)
                try:
                    self.original_port_dict[key_without_suffixes]
                except KeyError:
                    if f:
                        f.write(key+ ' had no one to compare to\n')
                    continue
                
                list_without_suffixes = set(get_original_name(x,self.suffix) for x in self.modified_port_dict[key])
                if list_without_suffixes == self.original_port_dict[key_without_suffixes]:
                    if f:
                        f.write("MATCH: "+key+' '+str(self.modified_port_dict[key])+'---'+str(self.original_port_dict[key_without_suffixes])+' '+key_without_suffixes+'\n')
                else:
                    if f:
                        f.write("NOT MATCH: "+key+' '+str(self.modified_port_dict[key])+'---'+str(self.original_port_dict[key_without_suffixes])+' '+key_without_suffixes+'\n')
                    self.not_matched.append(key)
        t1 = time()
        self.compare += (t1-t0)
