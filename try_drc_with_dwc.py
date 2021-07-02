import os
import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet_shrec import apply_nmr, insert_organs
from spydrnet_shrec.analysis.find_voter_insertion_points import find_voter_insertion_points
from spydrnet_shrec.transformation.replication.organ import XilinxDWCDetector
from design_rule_check import check_design

def get_modified_netlists(example_name):

    netlist = sdn.load_example_netlist_by_name(example_name)

    uniquify(netlist)
    
    sdn.compose(netlist,example_name + ".edf")

    hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x: x.item.reference.is_leaf() is True))
    instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    hports_to_replicate = list(netlist.get_hports())
    ports_to_replicate = list(x.item for x in hports_to_replicate)


    insertion_points = find_voter_insertion_points(netlist, [*hinstances_to_replicate, *hports_to_replicate], {'FDRE', 'FDSE', 'FDPE', 'FDCE'})
    replicas = apply_nmr([*instances_to_replicate, *ports_to_replicate], 2, name_suffix='DWC', rename_original=True)

    sdn.compose(netlist,example_name+"_just_dwc.edf")
    detectors = insert_organs(replicas, insertion_points, XilinxDWCDetector(), 'DETECTOR')
    netlist.compose(example_name+"_modified.edf")


def run():
    # examples_list = ['b13','adder','three_stage_synchronizer','synchronizer_test','n_bit_counter','lfsr_kc705','lfsr_zybo','fourBitCounter','basic_clock_crossing']

    examples_list = sdn.example_netlist_names
    
    #these don't work to be replicated and so must be removed.
    examples_list.remove("Readme")
    examples_list.remove("unique_challenge")
    examples_list.remove("hierarchical_luts")
    examples_list.remove("unique_different_modules")


    results = []
    for example in examples_list:
        print('\n',example)
        current_dict = {"name": example,"just_dwc":"x","with_detectors":"x","unique":"x"}
        get_modified_netlists(example)
        current_dict.update(just_dwc= check_design(sdn.parse(example+".edf"),sdn.parse(example+"_just_dwc.edf"),"DWC","DETECTOR"))
        current_dict.update(with_detectors = check_design(sdn.parse(example+".edf"),sdn.parse(example+"_modified.edf"),"DWC","DETECTOR"))
        results.append(current_dict)
        if 'unique_different_modules' in example:
            None
        else:
            os.remove(example+".edf")
            os.remove(example+"_just_dwc.edf")
            os.remove(example+"_modified.edf")

    dwc_success = 0
    dwc_failed = 0
    detector_success =0
    detector_failed = 0
    for item in results:
        if (item["just_dwc"]):
            dwc_success += 1
        else:
            dwc_failed += 1
        if (item["with_detectors"]):
            detector_success += 1
        else:
            detector_failed += 1
    
    print("TMR TEST:\n\tPassed:",dwc_success,", Failed: ",dwc_failed)
    print("DETECTOR TEST:\n\tPassed:",detector_success,", Failed: ",detector_failed)

    print('Remove generated text files? y/n')
    n = input()
    if n is 'y':
        dir = "."
        files = os.listdir(dir)
        for file in files:
            if file.endswith(".txt") and file.find("connections_") is not -1:
                os.remove(os.path.join(dir,file))

    if detector_failed or dwc_failed:
        return False
    else:
        return True

run()
