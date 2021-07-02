import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet_shrec import apply_nmr, insert_organs
from spydrnet_shrec.analysis.find_voter_insertion_points import find_voter_insertion_points
from spydrnet_shrec.transformation.replication.organ import XilinxTMRVoter
from spydrnet_shrec.transformation.replication.uniquify_nmr_property import uniquify_nmr_property

def get_modified_netlist(example_name):

    # netlist = sdn.load_example_netlist_by_name(example_name)
    netlist = sdn.parse("stopwatch_no_buf.edf")

    uniquify(netlist)

    hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x: x.item.reference.is_leaf() is True))
    instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    hports_to_replicate = list(netlist.get_hports())
    ports_to_replicate = list(x.item for x in hports_to_replicate)
    # hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x:(x.item.reference.is_leaf() and 'OBUF' not in x.item.name.upper() and 'OUTBUF' not in x.item.name.upper() and 'segment' not in x.item.name and 'anode' not in x.item.name)is True))
    # instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    # hports_to_replicate = list(netlist.get_hports(filter = lambda x: (x.item.direction is sdn.IN and 'clk' not in x.item.name) is True))
    # ports_to_replicate = list(x.item for x in hports_to_replicate)

    insertion_points = find_voter_insertion_points(netlist, [*hinstances_to_replicate, *hports_to_replicate], {'FDRE', 'FDSE', 'FDPE', 'FDCE'})
    replicas = apply_nmr([*instances_to_replicate, *ports_to_replicate], 3, name_suffix='TMR', rename_original=True)

    voters = insert_organs(replicas, insertion_points, XilinxTMRVoter(), 'VOTER')
    # uniquify_nmr_property(replicas, {'HBLKNM', 'HLUTNM', 'SOFT_HLUTNM'}, "TMR")
    # netlist.compose(example_name+"_modified.edf")
    # for point in insertion_points:
    #     print(point.instance.name,' of ',point.instance.parent.name)
    # print('\n\n')

# get_modified_netlist('stopwatch_no_buf')


from design_rule_check import check_design
check_design(sdn.parse("codebreaker_edif.edf"),sdn.parse("codebreaker_edif_modified.edf"),'TMR','VOTER')