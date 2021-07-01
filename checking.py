import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet_shrec import apply_nmr, insert_organs
from spydrnet_shrec.analysis.find_voter_insertion_points import find_voter_insertion_points
from spydrnet_shrec.transformation.replication.organ import XilinxTMRVoter
import os
from check_by_instance_properties import compare_properties
# from check_by_step_improve import check_replication_by_step
# from check_by_pin_connections import check_by_pin_connections
'''
Check TMR Tool Using Examples Netlists

This file can be run to ensure that the TMR tool is working correctly.

This file loads all of the built in SpyDrNet examples that are able to be triplicated and generates the following netlists:
    1) uniquified
    2) triplicated
    3) triplicated with voters

Then compare_paths() from check_paths_final.py is called to make sure that these new netlists were generated correctly.

Then the generated netlists are removed
'''

def get_modified_netlists(example_name):

    netlist = sdn.load_example_netlist_by_name(example_name)

    uniquify(netlist)
    
    sdn.compose(netlist,example_name + ".edf")

    # hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x: x.item.reference.is_leaf() is True))
    # instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    # hports_to_replicate = list(netlist.get_hports())
    # ports_to_replicate = list(x.item for x in hports_to_replicate)
    hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x:(x.item.reference.is_leaf() and 'OBUF' not in x.item.name)is True))
    instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    hports_to_replicate = list(netlist.get_hports(filter = lambda x: x.item.direction is sdn.IN))
    ports_to_replicate = list(x.item for x in hports_to_replicate)

    insertion_points = find_voter_insertion_points(netlist, [*hinstances_to_replicate, *hports_to_replicate], {'FDRE', 'FDSE', 'FDPE', 'FDCE'})
    replicas = apply_nmr([*instances_to_replicate, *ports_to_replicate], 3, name_suffix='TMR', rename_original=True)

    sdn.compose(netlist,example_name+"_just_tmr.edf")
    voters = insert_organs(replicas, insertion_points, XilinxTMRVoter(), 'VOTER')
    netlist.compose(example_name+"_modified.edf")


def make_dict(example):
    the_dict = {"name": example,"just_tmr":"x","with_voters":"x","unique":"x"}
    return the_dict


def run():
    # examples_list = sdn.example_netlist_names

    # #these don't work to be triplicated and so must be removed
    # examples_list.remove("Readme")
    # examples_list.remove("unique_challenge")
    # examples_list.remove("unique_different_modules")
    # examples_list.remove("hierarchical_luts")
    # examples_list.remove("b13")
    examples_list = ['b13','adder','three_stage_synchronizer','synchronizer_test','n_bit_counter','lfsr_kc705','lfsr_zybo','fourBitCounter','basic_clock_crossing']

    results = []
    for example in examples_list:
        print('\n',example)
        current_dict = {"name": example,"just_tmr":"x","with_voters":"x","unique":"x"}
        get_modified_netlists(example)
        current_dict.update(just_tmr= compare_properties(sdn.parse(example+".edf"),sdn.parse(example+"_just_tmr.edf"),"TMR","VOTER"))
        current_dict.update(with_voters = compare_properties(sdn.parse(example+".edf"),sdn.parse(example+"_modified.edf"),"TMR","VOTER"))
        results.append(current_dict)
        os.remove(example+".edf")
        os.remove(example+"_just_tmr.edf")
        os.remove(example+"_modified.edf")
        #os.remove(example+"_uniquified.edf")

    tmr_success = 0
    tmr_failed = 0
    voter_success =0
    voter_failed = 0
    for item in results:
        if (item["just_tmr"]):
            tmr_success += 1
        else:
            tmr_failed += 1
        if (item["with_voters"]):
            voter_success += 1
        else:
            voter_failed += 1
    
    print("TMR TEST:\n\tSuccess:",tmr_success,", Failed: ",tmr_failed)
    print("VOTER TEST:\n\tSuccess:",voter_success,", Failed: ",voter_failed)
    if voter_failed or tmr_failed:
        return False
    else:
        return True

run()
